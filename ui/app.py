"""
智能导演多Agent团队 — 本地 Web UI（FastAPI）
异步模式：后端立即返回任务ID，前端轮询状态
"""

import base64
import os
import sys
import json
import asyncio
import threading
import traceback
import re
import shutil
import hashlib
from io import BytesIO
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from fastapi import FastAPI, Request, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image, ImageOps, UnidentifiedImageError
import uvicorn

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


from agents.knowledge_base import build_vectordb, load_config
from agents.request_context import request_scope
from agents.utils import COMFLY_BASE_URL


app = FastAPI(title="智能导演多Agent团队", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板
ui_dir = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(ui_dir)
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
app.mount("/static", StaticFiles(directory=os.path.join(ui_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(ui_dir, "templates"))

# 全局任务状态
def _default_task_state() -> dict:
    return {
        "status": "idle",       # idle / running / done / error
        "step": "",             # 当前步骤
        "message": "",          # 状态消息
        "result": "",           # 最终结果（Seedance prompt）
        "error": "",            # 错误信息
        "started_at": "",       # 开始时间
        "agent_outputs": {},    # 各Agent的单独输出
        "input_script": "",     # 用户输入的剧本文本（持久化，刷新不丢）
        "input_aspect_ratio": "9:16",  # 画幅
        "input_ref_manifest": [],  # 参考图元数据（含缩略图）
        "project_name": "未命名项目",
        "archived": False,
        "model_profile_snapshot": {},
        "asset_selection": {},
        "style_preset": "",
        "director_review_required": False,
        "director_edits_by_segment": {},
        "shot_director_original_by_segment": {},
        "shot_director_approved_by_segment": {},
    }


DEFAULT_SESSION_ID = "local"
SESSION_ID_RE = re.compile(r"[^A-Za-z0-9_-]")

task_states: dict[str, dict] = {}
active_task_generations: dict[str, int] = {}
active_task_threads: dict[str, threading.Thread] = {}

RUNNING_STATUSES = {"running", "running_phase_1", "running_phase_2"}
BLOCKING_STATUSES = RUNNING_STATUSES | {"waiting_for_user_input"}
LIVE_TASK_STALL_TIMEOUT_SECONDS = int(os.getenv("DIRECTOR_UI_STALL_TIMEOUT_SECONDS", "900"))
ASSET_LIBRARY_DIR = os.path.join(OUTPUT_DIR, "client_assets")
MODEL_PROFILES_PATH = os.path.join(OUTPUT_DIR, "private", "model_profiles.json")
ASSET_TYPE_DIRS = {
    "character": "characters",
    "scene": "scenes",
    "prop": "props",
    "frame": "frames",
    "upload": "uploads",
}
IMAGE_ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _normalise_session_id(session_id: str | None) -> str:
    safe = SESSION_ID_RE.sub("", (session_id or DEFAULT_SESSION_ID).strip())[:80]
    return safe or DEFAULT_SESSION_ID


def _task_state(session_id: str) -> dict:
    session_id = _normalise_session_id(session_id)
    if session_id not in task_states:
        task_states[session_id] = _default_task_state()
    return task_states[session_id]


def _active_task_generation(session_id: str) -> int:
    return active_task_generations.get(_normalise_session_id(session_id), 0)


def _bump_task_generation(session_id: str) -> int:
    session_id = _normalise_session_id(session_id)
    active_task_generations[session_id] = active_task_generations.get(session_id, 0) + 1
    return active_task_generations[session_id]


def _has_live_task(session_id: str) -> bool:
    thread = active_task_threads.get(_normalise_session_id(session_id))
    return bool(thread and thread.is_alive())


def _register_task_thread(session_id: str, thread: threading.Thread) -> None:
    active_task_threads[_normalise_session_id(session_id)] = thread


def _unregister_task_thread(session_id: str) -> None:
    session_id = _normalise_session_id(session_id)
    if active_task_threads.get(session_id) is threading.current_thread():
        active_task_threads.pop(session_id, None)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _touch_task_progress(state: dict, now: str | None = None) -> None:
    state["last_progress_at"] = now or _now_iso()


def _progress_signature(state: dict) -> tuple:
    outputs = state.get("agent_outputs") or {}
    if not isinstance(outputs, dict):
        outputs = {}
    output_lengths = tuple(
        sorted((str(key), len(str(value or ""))) for key, value in outputs.items())
    )
    return (
        state.get("status"),
        state.get("step"),
        state.get("current_segment_index"),
        state.get("total_segments"),
        len(str(state.get("result") or "")),
        output_lengths,
    )


def _recover_stalled_live_task(
    session_id: str,
    state: dict,
    *,
    now: datetime | None = None,
    timeout_seconds: int | None = None,
) -> bool:
    """Mark a live but non-progressing worker as failed so the UI can recover."""
    session_id = _normalise_session_id(session_id)
    if state.get("status") not in RUNNING_STATUSES or not _has_live_task(session_id):
        return False

    timeout = timeout_seconds or LIVE_TASK_STALL_TIMEOUT_SECONDS
    if timeout <= 0:
        return False

    progress_at = _parse_iso_datetime(state.get("last_progress_at")) or _parse_iso_datetime(state.get("started_at"))
    if progress_at is None:
        _touch_task_progress(state)
        return False

    current_time = now or datetime.now()
    stalled_seconds = (current_time - progress_at).total_seconds()
    if stalled_seconds < timeout:
        return False

    previous_step = state.get("step") or "unknown"
    started_at = state.get("started_at") or "unknown time"
    _bump_task_generation(session_id)
    active_task_threads.pop(session_id, None)
    state["status"] = "error"
    state["step"] = "error"
    state["message"] = (
        f"执行超时: {previous_step} 已超过 {int(timeout)} 秒没有产生新进展，"
        "已自动停止等待，可重新提交任务。"
    )
    state["error"] = (
        "watchdog timeout: live worker produced no progress "
        f"for {int(stalled_seconds)}s; previous_step={previous_step}; started_at={started_at}"
    )
    _save_task_state_for_session(session_id, state)
    return True


task_state = _task_state(DEFAULT_SESSION_ID)


def _session_output_dir(session_id: str) -> str:
    return os.path.join(OUTPUT_DIR, "sessions", _normalise_session_id(session_id))


def _migrate_legacy_state_if_needed(session_id: str) -> bool:
    """Move a pre-share-mode global task snapshot into the current session."""
    session_id = _normalise_session_id(session_id)
    if session_id != DEFAULT_SESSION_ID:
        return False

    legacy_state = os.path.join(OUTPUT_DIR, "pipeline_state.json")
    legacy_checkpoint = os.path.join(OUTPUT_DIR, "director_graph.sqlite")
    session_dir = _session_output_dir(session_id)
    session_state = os.path.join(session_dir, "pipeline_state.json")

    if os.path.exists(session_state) or not os.path.exists(legacy_state):
        return False

    os.makedirs(session_dir, exist_ok=True)
    shutil.copy2(legacy_state, session_state)
    for source in [
        legacy_checkpoint,
        f"{legacy_checkpoint}-wal",
        f"{legacy_checkpoint}-shm",
    ]:
        if os.path.exists(source):
            shutil.copy2(source, os.path.join(session_dir, os.path.basename(source)))

    try:
        with open(session_state, "r", encoding="utf-8") as file:
            _task_state(session_id).update(json.load(file))
    except Exception:
        pass
    return True

# Agent 角色名 → 存储 key 的映射
_AGENT_KEY_MAP = {
    "节奏总控导演": "rhythm_rewrite_director",
    "场景分析师": "scene_analyst",
    "结构规划师": "story_planner",
    "镜头导演": "shot_director",
    "Seedance编译师": "prompt_compiler",
    "质检导演": "quality_inspector",
}

_AGENT_DISPLAY_NAMES = {
    "rhythm_rewrite_director": "🎼 节奏改写",
    "scene_analyst": "📋 场景分析",
    "story_planner": "🎬 结构规划",
    "shot_director": "🎥 镜头设计",
    "prompt_compiler": "✍️ Seedance Prompt",
    "quality_inspector": "🔍 质检报告",
}

MAX_REFERENCE_IMAGES = 12
REFERENCE_IMAGE_MAX_EDGE = 1280
REFERENCE_IMAGE_JPEG_QUALITY = 82
SEGMENT_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}

def _load_latest_results_on_startup():
    """在服务器启动时，只恢复本机会话的 LangGraph 状态快照。"""
    try:
        _migrate_legacy_state_if_needed(DEFAULT_SESSION_ID)
        with request_scope(session_id=DEFAULT_SESSION_ID):
            disk_state = load_state()
        if disk_state:
            _task_state(DEFAULT_SESSION_ID).update(disk_state)
    except Exception:
        return


from agents.director_graph import (
    clear_state,
    load_state,
    recover_repairable_pipeline_state,
    run_phase_1_planning,
    run_phase_2_compile_segment,
    run_shot_director_restart_from_story_plan,
    run_shot_director_resume_from_partial,
    save_state,
    _normalise_compiled_prompt,
)


def _save_task_state_for_session(
    session_id: str,
    state: dict,
) -> bool:
    """Persist a UI task snapshot into the session-owned state file."""
    try:
        with request_scope(session_id=_normalise_session_id(session_id)):
            save_state(dict(state))
        return True
    except Exception:
        return False


def _merge_latest_disk_state_for_session(session_id: str, target_state: dict) -> bool:
    """Keep partial graph output when the worker fails after an intermediate persist."""
    try:
        with request_scope(session_id=_normalise_session_id(session_id)):
            latest_state = load_state()
    except Exception:
        return False
    if not isinstance(latest_state, dict) or not latest_state:
        return False
    target_state.update(latest_state)
    return True


def _recover_stale_running_state(session_id: str, state: dict) -> bool:
    """Mark disk states left running by a dead/restarted worker as interrupted."""
    if state.get("status") not in RUNNING_STATUSES or _has_live_task(session_id):
        return False

    previous_step = state.get("step") or "unknown"
    started_at = state.get("started_at") or "unknown time"
    print(f"  [Recovery] Session {session_id}: 检测到残留运行状态 ({previous_step} @ {started_at})，标记为 interrupted")
    state["status"] = "error"
    state["step"] = "error"
    state["message"] = "上次任务已中断：后台执行线程不存在。可重新运行，或在已有宏观规划基础上重试当前片段。"
    state["error"] = f"检测到状态仍为 running，但当前服务进程中没有活动后台任务。上次步骤：{previous_step}；开始时间：{started_at}。"
    _save_task_state_for_session(session_id, state)
    return True

# 立即执行初始化
_load_latest_results_on_startup()

_STEP_LABELS = {
    "节奏总控导演":  ("step_0_rhythm",  "🎼 节奏总控导演正在改写剧本...（1/6）"),
    "场景分析师":  ("step_1_analyze",  "📋 场景分析师正在分析剧本...（2/6）"),
    "结构规划师":  ("step_2_plan",     "🎬 结构规划师正在拆片规划...（3/6）"),
    "镜头导演":    ("step_3_direct",   "🎥 镜头导演正在设计分镜...（4/6）"),
    "Seedance编译师": ("step_4_compile", "✍️ Seedance编译师正在生成Prompt...（5/6）"),
    "质检导演":    ("step_5_inspect",  "🔍 质检导演正在审查产物...（6/6）"),
}


def _make_task_callback(session_id: str = DEFAULT_SESSION_ID):
    """生成 CrewAI task_callback，用于实时更新前端步骤状态并保存各 Agent 输出。

    注意：此函数目前未被新版流水线（stream_callback 路径）调用，仅保留以兼容可能
    存在的旧版 CrewAI 工作流。修复要点：不再 `global task_state`（会导致多 session
    相互污染），而是通过 closure 捕获 session_id 并在运行时解析对应的 task_state。
    """
    session_id = _normalise_session_id(session_id)

    def callback(task_output):
        local_state = _task_state(session_id)
        agent_role = getattr(task_output, "agent", "") or ""
        output_text = ""
        if hasattr(task_output, "raw"):
            output_text = str(task_output.raw)
        elif hasattr(task_output, "output"):
            output_text = str(task_output.output)
        else:
            output_text = str(task_output)

        # 保存当前 Agent 的输出
        for role_key, agent_key in _AGENT_KEY_MAP.items():
            if role_key in agent_role:
                local_state.setdefault("agent_outputs", {})[agent_key] = output_text
                break

        # 更新进度到下一步
        all_roles = list(_STEP_LABELS.keys())
        for role_key, (step_id, msg) in _STEP_LABELS.items():
            if role_key in agent_role:
                idx = all_roles.index(role_key)
                if idx + 1 < len(all_roles):
                    next_role = all_roles[idx + 1]
                    next_step, next_msg = _STEP_LABELS[next_role]
                    local_state["step"] = next_step
                    local_state["message"] = next_msg
                break

    return callback


def _refresh_task_state_from_disk(session_id: str = DEFAULT_SESSION_ID):
    """Read the latest LangGraph state snapshot, if one exists."""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    if _recover_stalled_live_task(session_id, task_state):
        return
    previous_progress = _progress_signature(task_state)
    try:
        _migrate_legacy_state_if_needed(session_id)
        with request_scope(session_id=session_id):
            disk_state = load_state()
            if not _has_live_task(session_id):
                disk_state, _ = recover_repairable_pipeline_state(disk_state)
    except Exception:
        return
    if disk_state:
        has_live_task = _has_live_task(session_id)
        live_status_fields = {}
        if has_live_task and task_state.get("status") in RUNNING_STATUSES:
            # LangGraph persists phase progress directly to disk while the worker is
            # running. Keep disk step/message authoritative so /api/status reflects
            # the exact backend stage instead of the UI thread's initial snapshot.
            disk_status = str(disk_state.get("status") or "")
            if disk_status not in RUNNING_STATUSES and disk_status not in BLOCKING_STATUSES:
                live_status_fields = {
                    key: task_state.get(key)
                    for key in ("status", "step", "message")
                    if task_state.get(key) is not None
                }
        _recover_stale_running_state(session_id, disk_state)
        if not has_live_task and not disk_state.get("thread_id") and disk_state.get("status") in BLOCKING_STATUSES:
            disk_state["status"] = "idle"
            disk_state["step"] = ""
            disk_state["message"] = "检测到旧状态机残留记录，已切换为可重新启动状态。"
            _save_task_state_for_session(session_id, disk_state)
        task_state.update(disk_state)
        if live_status_fields:
            task_state.update(live_status_fields)
        if has_live_task and _progress_signature(task_state) != previous_progress:
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)
        _recover_stalled_live_task(session_id, task_state)


def _mask_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:3]}***{text[-4:]}"


def _mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            lower_key = str(key).lower()
            if "api_key" in lower_key or lower_key in {"apikey", "token", "secret"}:
                masked[key] = _mask_secret(item)
            else:
                masked[key] = _mask_sensitive(item)
        return masked
    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]
    return value


def _host_from_base_url(base_url: Any) -> str:
    text = str(base_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return parsed.netloc or parsed.path.split("/", 1)[0]


def _public_task_state(session_id: str = DEFAULT_SESSION_ID) -> dict:
    state = dict(_task_state(session_id))
    image_refs = state.get("reference_image_b64s") or []
    if image_refs:
        state["reference_image_b64s"] = f"{len(image_refs)} reference images omitted from status response"
    if isinstance(state.get("model_profile_snapshot"), dict):
        snapshot = _mask_sensitive(state["model_profile_snapshot"])
        snapshot["base_url_host"] = _host_from_base_url(snapshot.get("base_url"))
        state["model_profile_snapshot"] = snapshot
    error = state.get("error")
    if isinstance(error, str) and len(error) > 5000:
        state["error"] = error[:5000] + "\n... traceback truncated ..."
    return state


def _ensure_asset_dirs() -> None:
    for dirname in ASSET_TYPE_DIRS.values():
        os.makedirs(os.path.join(ASSET_LIBRARY_DIR, dirname), exist_ok=True)
    os.makedirs(os.path.dirname(MODEL_PROFILES_PATH), exist_ok=True)


def _normalise_asset_type(asset_type: str | None) -> str:
    value = (asset_type or "").strip().lower()
    aliases = {
        "person": "character",
        "role": "character",
        "location": "scene",
        "place": "scene",
        "object": "prop",
        "frame_reference": "frame",
    }
    value = aliases.get(value, value)
    return value if value in ASSET_TYPE_DIRS else "upload"


def _safe_filename(filename: str, fallback: str = "asset") -> str:
    stem, ext = os.path.splitext(filename or "")
    safe_stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem).strip("._")
    safe_ext = "".join(ch for ch in ext.lower() if ch.isalnum() or ch == ".")
    return f"{safe_stem or fallback}{safe_ext or '.bin'}"

def _file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _dedupe_asset_path(folder: str, original_filename: str, content: bytes) -> tuple[str, bool]:
    safe_name = _safe_filename(original_filename)
    stem, ext = os.path.splitext(safe_name)
    digest = _file_sha256(content)

    for existing in os.listdir(folder):
        existing_path = os.path.join(folder, existing)
        if not os.path.isfile(existing_path):
            continue
        try:
            with open(existing_path, "rb") as f:
                if _file_sha256(f.read()) == digest:
                    return existing_path, True
        except Exception:
            continue

    final_name = f"{stem}_{digest[:12]}{ext}"
    return os.path.join(folder, final_name), False



def _parse_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        candidates = value
    else:
        text = str(value or "")
        try:
            parsed = json.loads(text)
            candidates = parsed if isinstance(parsed, list) else re.split(r"[,，\n]+", text)
        except json.JSONDecodeError:
            candidates = re.split(r"[,，\n]+", text)
    tags: list[str] = []
    for item in candidates:
        tag = str(item or "").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _thumbnail_data_url(path: str, size: int = 180) -> str:
    try:
        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            canvas = Image.new("RGB", image.size, (20, 24, 31))
            rgba = image.convert("RGBA")
            canvas.paste(rgba, mask=rgba.getchannel("A"))
            image = canvas
        else:
            image = image.convert("RGB")
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=76)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def _asset_meta_path(path: str) -> str:
    return f"{path}.meta.json"


def _read_asset_meta(path: str) -> dict[str, Any]:
    meta_path = _asset_meta_path(path)
    if not os.path.exists(meta_path):
        return {}
    try:
        with open(meta_path, "r", encoding="utf-8-sig") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_asset_meta(path: str, meta: dict[str, Any]) -> None:
    with open(_asset_meta_path(path), "w", encoding="utf-8") as file:
        json.dump(meta, file, ensure_ascii=False, indent=2)


def _asset_url(asset_type: str, filename: str) -> str:
    return f"/api/assets/file/{asset_type}/{quote(filename)}"


def _asset_from_path(asset_type: str, path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path) or path.endswith(".meta.json"):
        return None
    _, ext = os.path.splitext(path)
    filename = os.path.basename(path)
    meta = _read_asset_meta(path)
    asset_type = _normalise_asset_type(meta.get("type") or asset_type)
    return {
        "id": str(meta.get("id") or f"{asset_type}:{filename}"),
        "name": str(meta.get("name") or os.path.splitext(filename)[0]),
        "type": asset_type,
        "filename": filename,
        "url": _asset_url(asset_type, filename),
        "thumbnail": _thumbnail_data_url(path) if ext.lower() in IMAGE_ASSET_EXTENSIONS else "",
        "tags": _parse_tags(meta.get("tags") or []),
        "description": str(meta.get("description") or ""),
        "purpose": str(meta.get("purpose") or ""),
        "timecode": str(meta.get("timecode") or ""),
        "timestamp_seconds": meta.get("timestamp_seconds"),
        "created_at": str(meta.get("created_at") or ""),
        "source_video": str(meta.get("source_video") or ""),
    }


def _read_asset_library() -> dict[str, Any]:
    _ensure_asset_dirs()
    assets: list[dict[str, Any]] = []
    for asset_type, dirname in ASSET_TYPE_DIRS.items():
        folder = os.path.join(ASSET_LIBRARY_DIR, dirname)
        for filename in sorted(os.listdir(folder)):
            asset = _asset_from_path(asset_type, os.path.join(folder, filename))
            if asset:
                assets.append(asset)

    groups = {asset_type: [] for asset_type in ("character", "scene", "prop", "frame")}
    groups["upload"] = []
    for asset in assets:
        groups.setdefault(asset["type"], []).append(asset)
    return {"assets": assets, "groups": groups}


def _load_model_profiles() -> list[dict[str, Any]]:
    _ensure_asset_dirs()
    if not os.path.exists(MODEL_PROFILES_PATH):
        return []
    try:
        with open(MODEL_PROFILES_PATH, "r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except Exception:
        return []
    profiles = data.get("profiles", []) if isinstance(data, dict) else data
    return [item for item in profiles if isinstance(item, dict)]


def _save_model_profiles(profiles: list[dict[str, Any]]) -> None:
    _ensure_asset_dirs()
    with open(MODEL_PROFILES_PATH, "w", encoding="utf-8") as file:
        json.dump({"profiles": profiles}, file, ensure_ascii=False, indent=2)


def _normalise_model_list_payload(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = re.split(r"[,，\n]+", value)
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = []
    models: list[str] = []
    for candidate in candidates:
        model = str(candidate or "").strip()
        if model and model not in models:
            models.append(model)
    return models


def _normalise_model_profile_payload(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    profile_id = str(payload.get("id") or existing.get("id") or f"profile_{datetime.now().strftime('%Y%m%d%H%M%S')}").strip()
    profile_id = re.sub(r"[^A-Za-z0-9_-]", "_", profile_id)[:80] or "profile"
    incoming_key = str(payload.get("api_key") or "").strip()
    if incoming_key and set(incoming_key) <= {"*"}:
        incoming_key = str(existing.get("api_key") or "")
    if not incoming_key and existing.get("api_key") and not payload.get("clear_api_key"):
        incoming_key = str(existing.get("api_key") or "")

    agent_models = payload.get("agent_models")
    if not isinstance(agent_models, dict):
        agent_models = existing.get("agent_models") if isinstance(existing.get("agent_models"), dict) else {}

    return {
        "id": profile_id,
        "name": str(payload.get("name") or existing.get("name") or "Local Model Profile").strip(),
        "base_url": str(payload.get("base_url") or existing.get("base_url") or "").strip().rstrip("/"),
        "api_key": incoming_key,
        "default_model": str(payload.get("default_model") or payload.get("model") or existing.get("default_model") or "").strip(),
        "agent_models": agent_models,
        "fallback_models": _normalise_model_list_payload(payload.get("fallback_models", existing.get("fallback_models", []))),
        "vectordb_base_url": str(payload.get("vectordb_base_url") or existing.get("vectordb_base_url") or "").strip().rstrip("/"),
        "embedding_model": str(payload.get("embedding_model") or existing.get("embedding_model") or "").strip(),
        "max_tokens": payload.get("max_tokens", existing.get("max_tokens", "")),
        "max_retries": payload.get("max_retries", existing.get("max_retries", 2)),
        "timeout_seconds": payload.get("timeout_seconds", existing.get("timeout_seconds", "")),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _sanitize_model_profile(profile: dict[str, Any]) -> dict[str, Any]:
    clean = _mask_sensitive(dict(profile))
    clean["api_key_set"] = bool(profile.get("api_key"))
    clean["base_url_host"] = _host_from_base_url(profile.get("base_url"))
    return clean


def _find_model_profile(profile_id: str) -> dict[str, Any] | None:
    for profile in _load_model_profiles():
        if str(profile.get("id") or "") == profile_id:
            return profile
    return None


def _model_profile_snapshot(profile_id: str = "", raw_profile_json: str = "") -> dict[str, Any]:
    if raw_profile_json:
        try:
            payload = json.loads(raw_profile_json)
        except json.JSONDecodeError as exc:
            raise ValueError("model_profile_snapshot_json is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("model_profile_snapshot_json must be an object")
        return _normalise_model_profile_payload(payload)
    if profile_id:
        profile = _find_model_profile(profile_id)
        if not profile:
            raise ValueError(f"Model profile not found: {profile_id}")
        snapshot = dict(profile)
        snapshot["snapshot_at"] = datetime.now().isoformat(timespec="seconds")
        return snapshot
    return {}


def _parse_json_object(raw: str, field_name: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _segment_key(segment_index: int) -> str:
    return str(max(1, int(segment_index)))


def _extract_segment_block(text: str, segment_index: int) -> str:
    fragment_id = f"F{int(segment_index):02d}"
    match = re.search(
        rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)",
        text or "",
    )
    return match.group(1).strip() if match else ""


def _replace_segment_block(text: str, segment_index: int, replacement: str) -> str:
    fragment_id = f"F{int(segment_index):02d}"
    pattern = re.compile(
        rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)"
    )
    replacement = (replacement or "").strip()
    if not replacement:
        return text or ""
    if pattern.search(text or ""):
        return pattern.sub(replacement.rstrip() + "\n", text or "", count=1).strip() + "\n"
    glue = "\n\n" if text and text.strip() else ""
    return f"{(text or '').rstrip()}{glue}{replacement}\n"


def _apply_director_edit_to_state(
    state: dict[str, Any],
    segment_index: int,
    edited_yaml: str,
    edit_payload: dict[str, Any] | None = None,
    *,
    approved: bool = False,
) -> dict[str, Any]:
    key = _segment_key(segment_index)
    outputs = state.setdefault("agent_outputs", {})
    if not isinstance(outputs, dict):
        outputs = {}
        state["agent_outputs"] = outputs
    original_map = state.setdefault("shot_director_original_by_segment", {})
    edits_map = state.setdefault("director_edits_by_segment", {})
    approved_map = state.setdefault("shot_director_approved_by_segment", {})
    source = str(outputs.get("shot_director") or "")
    original_map.setdefault(key, _extract_segment_block(source, segment_index))
    edits_map[key] = {
        "edited_yaml": edited_yaml,
        "edit_payload": edit_payload or {},
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    if approved:
        approved_map[key] = edited_yaml
        outputs["shot_director"] = _replace_segment_block(source, segment_index, edited_yaml)
        outputs[f"shot_director_prompt_source_segment_{segment_index}"] = edited_yaml
        state["director_review_required"] = False
    state["current_segment_index"] = segment_index
    state["active_segment_index"] = segment_index
    return state


def _state_has_visible_outputs(state: dict) -> bool:
    outputs = state.get("agent_outputs") or {}
    if state.get("result"):
        return True
    return any(re.match(r"compiled_segment_\d+$", key) for key in outputs)


def _latest_visible_session(exclude_session_id: str | None = None) -> dict | None:
    sessions_dir = os.path.join(OUTPUT_DIR, "sessions")
    if not os.path.isdir(sessions_dir):
        return None

    excluded = _normalise_session_id(exclude_session_id) if exclude_session_id else ""
    state_paths: list[str] = []
    for name in os.listdir(sessions_dir):
        state_path = os.path.join(sessions_dir, name, "pipeline_state.json")
        if os.path.isfile(state_path):
            state_paths.append(state_path)

    for state_path in sorted(state_paths, key=os.path.getmtime, reverse=True):
        session_id = _normalise_session_id(os.path.basename(os.path.dirname(state_path)))
        if session_id == excluded:
            continue
        try:
            with open(state_path, "r", encoding="utf-8-sig") as f:
                state = json.load(f)
        except Exception:
            continue
        if not _state_has_visible_outputs(state):
            continue
        return {
            "session_id": session_id,
            "status": state.get("status", ""),
            "current_segment_index": state.get("current_segment_index", 1),
            "total_segments": state.get("total_segments", 0),
            "updated_at": datetime.fromtimestamp(os.path.getmtime(state_path)).isoformat(),
        }
    return None


def _compiled_prompt_result(agent_outputs: dict) -> str:
    compiled_items: list[tuple[int, str]] = []
    for key, value in agent_outputs.items():
        match = re.match(r"compiled_segment_(\d+)$", key)
        if match and value:
            compiled_items.append((int(match.group(1)), value.strip()))
    return "\n\n".join(value for _, value in sorted(compiled_items))


def _can_resume_saved_phase2_segment(state: dict, segment_index: int) -> bool:
    """Allow a recovered idle/error session to continue Phase 2 from saved Phase 1 outputs."""
    if segment_index < 1:
        return False
    total_segments = int(state.get("total_segments") or 0)
    if total_segments < 1 or segment_index > total_segments:
        return False
    outputs = state.get("agent_outputs") or {}
    if not isinstance(outputs, dict):
        return False
    return (
        bool(outputs.get("story_planner"))
        and bool(outputs.get("shot_director"))
    )


def _previous_generated_segment_index(state: dict) -> int:
    outputs = state.get("agent_outputs") or {}
    compiled_segments = [
        int(match.group(1))
        for key in outputs
        if (match := re.match(r"compiled_segment_(\d+)$", key))
    ]
    if compiled_segments:
        return max(compiled_segments)
    if state.get("status") == "done":
        total_segments = int(state.get("total_segments") or 0)
        return total_segments if total_segments else 0
    current_segment = int(state.get("current_segment_index") or 1)
    return current_segment - 1 if current_segment > 1 else 0


def _clear_segment_and_downstream(state: dict, segment_index: int) -> tuple[bool, int, str]:
    """清除指定片段及其后续所有片段，用于"重跑某一段"的场景。

    会把 agent_outputs 里所有 compiled_segment_N / quality_inspector_segment_N
    （N >= segment_index）一并删除；prompt_compiler / quality_inspector 指回 N-1 段；
    同时把 current_segment_index 设回 segment_index，让流水线从该段起重新运行。
    """
    if segment_index < 1:
        return False, 0, "片段编号必须 >= 1。"

    total_segments = int(state.get("total_segments") or 0)
    if total_segments and segment_index > total_segments:
        return False, segment_index, f"片段 {segment_index} 超出总段数 {total_segments}。"

    outputs = state.setdefault("agent_outputs", {})

    # 收集所有已生成的片段号，筛选出 >= segment_index 的
    compiled_indices = [
        int(match.group(1))
        for key in list(outputs.keys())
        if (match := re.match(r"compiled_segment_(\d+)$", key))
    ]
    targets = sorted({idx for idx in compiled_indices if idx >= segment_index})

    # 也要覆盖 quality_inspector_segment_N 可能单独存在的情况
    qc_indices = [
        int(match.group(1))
        for key in list(outputs.keys())
        if (match := re.match(r"quality_inspector_segment_(\d+)$", key))
    ]
    targets = sorted(set(targets) | {idx for idx in qc_indices if idx >= segment_index})

    if not targets:
        return False, segment_index, f"片段 {segment_index} 及之后暂无可清除的 Prompt。"

    removed_any = False
    for idx in targets:
        for key in [
            f"compiled_segment_{idx}",
            f"quality_inspector_segment_{idx}",
        ]:
            if outputs.pop(key, None) is not None:
                removed_any = True

    if not removed_any:
        return False, segment_index, f"片段 {segment_index} 及之后没有可清除的 Prompt。"

    prior_index = segment_index - 1
    prior_prompt = outputs.get(f"compiled_segment_{prior_index}", "") if prior_index >= 1 else ""
    prior_qc = outputs.get(f"quality_inspector_segment_{prior_index}", "") if prior_index >= 1 else ""
    if prior_prompt:
        outputs["prompt_compiler"] = prior_prompt
    else:
        outputs.pop("prompt_compiler", None)
    if prior_qc:
        outputs["quality_inspector"] = prior_qc
    else:
        outputs.pop("quality_inspector", None)

    state.pop("active_segment_index", None)
    state.pop("tail_frame_analysis", None)
    state.pop("system_guard_report", None)
    state["qc_retry_count"] = 0
    state["revision_instruction"] = ""
    state["last_qc_status"] = ""
    state["last_cleared_segment"] = segment_index
    state["current_segment_index"] = segment_index
    state["status"] = "waiting_for_user_input"
    state["step"] = "step_3_direct"
    state["director_review_required"] = True
    cleared_range = (
        f"片段 {segment_index}"
        if len(targets) == 1
        else f"片段 {segment_index} 及其后 {len(targets) - 1} 段"
    )
    state["message"] = f"已清除{cleared_range}，请重新生成。"
    state["result"] = _compiled_prompt_result(outputs)
    state["error"] = ""
    return True, segment_index, state["message"]


def _clear_previous_segment_in_state(state: dict) -> tuple[bool, int, str]:
    """旧接口：清除最近已生成的一段。内部转调 _clear_segment_and_downstream。"""
    previous_segment = _previous_generated_segment_index(state)
    if previous_segment < 1:
        return False, 0, "还没有可清除的上一段。"
    total_segments = int(state.get("total_segments") or 0)
    if total_segments and previous_segment > total_segments:
        previous_segment = total_segments
    return _clear_segment_and_downstream(state, previous_segment)


def _infer_reference_purpose(index: int) -> str:
    purposes = {
        1: "主角人物身份、五官、发型、身形与服装一致性锁定",
        2: "对手角色/第二核心角色身份、五官、发型、身形与服装一致性锁定",
        3: "场景空间、轴线、光线与首帧环境基底锁定",
        4: "多人位置关系、视线方向与调度关系锁定",
    }
    return purposes.get(index, "补充参考图，仅按用户说明限定用途")


def _encode_reference_image_for_llm(content: bytes, filename: str) -> tuple[str, dict[str, str]]:
    """Resize and re-encode an uploaded image so vision requests stay small."""
    try:
        image = Image.open(BytesIO(content))
    except UnidentifiedImageError as exc:
        raise ValueError(f"{filename} 不是可读取的图片文件") from exc

    image = ImageOps.exif_transpose(image)
    original_size = image.size
    image.thumbnail((REFERENCE_IMAGE_MAX_EDGE, REFERENCE_IMAGE_MAX_EDGE), Image.Resampling.LANCZOS)

    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")

    output = BytesIO()
    image.save(
        output,
        format="JPEG",
        quality=REFERENCE_IMAGE_JPEG_QUALITY,
        optimize=True,
        progressive=True,
    )
    encoded_bytes = output.getvalue()
    metadata = {
        "original_size": f"{original_size[0]}x{original_size[1]}",
        "processed_size": f"{image.size[0]}x{image.size[1]}",
        "original_bytes": str(len(content)),
        "processed_bytes": str(len(encoded_bytes)),
    }
    data_url = f"data:image/jpeg;base64,{base64.b64encode(encoded_bytes).decode('ascii')}"
    return data_url, metadata


def _parse_reference_manifest(raw_manifest: str) -> list[dict[str, str]]:
    if not raw_manifest:
        return []
    try:
        manifest = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        raise ValueError("参考图清单 JSON 格式错误") from exc
    if not isinstance(manifest, list):
        raise ValueError("参考图清单必须是数组")
    parsed: list[dict[str, str]] = []
    for item in manifest:
        if not isinstance(item, dict):
            parsed.append({})
            continue
        parsed.append(
            {
                "label": str(item.get("label") or ""),
                "filename": str(item.get("filename") or ""),
                "purpose": str(item.get("purpose") or ""),
                "note": str(item.get("note") or ""),
            }
        )
    return parsed


async def _read_reference_uploads(
    reference_image_files: list[UploadFile] | None,
    manifest_overrides: list[dict[str, str]] | None = None,
):
    image_data_urls: list[str] = []
    manifest: list[dict[str, str]] = []
    manifest_overrides = manifest_overrides or []
    if reference_image_files and len(reference_image_files) > MAX_REFERENCE_IMAGES:
        raise ValueError(f"一次最多上传 {MAX_REFERENCE_IMAGES} 张参考图；建议保留人物、场景和位置关系核心图。")

    for upload in reference_image_files or []:
        if not upload or not upload.filename:
            continue
        content = await upload.read()
        if not content:
            continue
        index = len(image_data_urls) + 1
        override = manifest_overrides[index - 1] if index - 1 < len(manifest_overrides) else {}
        purpose = override.get("purpose") or _infer_reference_purpose(index)
        note = override.get("note") or ""
        if note:
            purpose = f"{purpose}；补充说明：{note}"
        image_data_url, image_metadata = _encode_reference_image_for_llm(content, upload.filename)
        image_data_urls.append(image_data_url)
        manifest.append(
            {
                "label": override.get("label") or f"@图片{index}",
                "filename": upload.filename,
                "purpose": purpose,
                "processed_size": image_metadata["processed_size"],
                "processed_bytes": image_metadata["processed_bytes"],
                "original_size": image_metadata["original_size"],
                "original_bytes": image_metadata["original_bytes"],
            }
        )
    return image_data_urls, manifest


async def _save_segment_video_upload(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None

    _, ext = os.path.splitext(upload.filename)
    ext = ext.lower()
    if ext not in SEGMENT_VIDEO_EXTENSIONS:
        raise ValueError("上一段视频仅支持 mp4、mov、avi、webm 格式。")

    content = await upload.read()
    if not content:
        return None

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "uploaded_segment_videos")
    os.makedirs(output_dir, exist_ok=True)
    safe_stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in os.path.splitext(upload.filename)[0]).strip("._") or "segment"
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_stem}{ext}"
    path = os.path.join(output_dir, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _extract_tail_frame_b64_from_video(video_path: str) -> str | None:
    """Extract the final readable video frame and return it as JPEG base64."""
    if not video_path or not os.path.exists(video_path):
        return None
    cap = None
    try:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        candidate_positions = []
        if frame_count > 0:
            candidate_positions.extend([
                max(frame_count - 2, 0),
                max(frame_count - 6, 0),
                max(int(frame_count * 0.95), 0),
                max(int(frame_count * 0.70), 0),
            ])
        candidate_positions.append(0)

        frame = None
        for pos in dict.fromkeys(candidate_positions):
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, candidate = cap.read()
            if ok and candidate is not None:
                frame = candidate
                break
        if frame is None:
            return None

        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
        if not ok:
            return None

        # tobytes() 数据量可能较大（数百KB），只计算一次
        encoded_bytes = encoded.tobytes()
        output_dir = os.path.join(OUTPUT_DIR, "auto_tail_frames")
        os.makedirs(output_dir, exist_ok=True)
        frame_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.splitext(os.path.basename(video_path))[0]}_tail.jpg"
        with open(os.path.join(output_dir, frame_name), "wb") as f:
            f.write(encoded_bytes)
        return base64.b64encode(encoded_bytes).decode("utf-8")
    except Exception as exc:
        print(f"  [Video] WARN: 自动抽取尾帧失败：{exc}")
        return None
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def _run_pipeline_in_thread(
    script: str,
    aspect_ratio: str,
    reference_images: str,
    reference_image_b64s: list[str] | None = None,
    reference_image_manifest: list[dict[str, str]] | None = None,
    speed_mode: bool = True,
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
    model_profile_snapshot: dict[str, Any] | None = None,
    asset_selection: dict[str, Any] | None = None,
):
    """在后台线程中执行流水线阶段一（全局规划）"""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)

    def _stream_callback(agent_name: str, chunk: str):
        if agent_name:
            out_key = _AGENT_KEY_MAP.get(agent_name, agent_name)
            if out_key not in task_state["agent_outputs"]:
                task_state["agent_outputs"][out_key] = ""
            task_state["agent_outputs"][out_key] += chunk
            _touch_task_progress(task_state)

    try:
        with request_scope(session_id=session_id, stream_callback=_stream_callback):
            if task_generation != _active_task_generation(session_id):
                return
            # 彻底清空上一轮的输出状态，避免污染
            preserved_inputs = {
                "input_script": task_state.get("input_script") or script,
                "input_aspect_ratio": task_state.get("input_aspect_ratio") or aspect_ratio,
                "input_ref_manifest": task_state.get("input_ref_manifest") or [],
                "model_profile_snapshot": task_state.get("model_profile_snapshot") or model_profile_snapshot or {},
                "asset_selection": task_state.get("asset_selection") or asset_selection or {},
            }
            task_state.clear()
            task_state.update(_default_task_state())
            task_state.update(preserved_inputs)
            task_state["step"] = "step_1_analyze"
            task_state["status"] = "running_phase_1"
            task_state["message"] = "🎼 节奏总控导演正在改写剧本...（1/6）"
            started_at = datetime.now().isoformat()
            task_state["started_at"] = started_at
            task_state["last_progress_at"] = started_at
            task_state["result"] = ""
            task_state["error"] = ""
            task_state["agent_outputs"] = {}
            
            # Phase 1 creates state autonomously
            state = run_phase_1_planning(
                script=script,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images if reference_images else None,
                reference_image_b64s=reference_image_b64s,
                reference_image_manifest=reference_image_manifest,
                speed_mode=speed_mode,
                model_profile_snapshot=model_profile_snapshot or preserved_inputs.get("model_profile_snapshot") or {},
                asset_selection=asset_selection or preserved_inputs.get("asset_selection") or {},
            )
            if task_generation != _active_task_generation(session_id):
                return
            task_state.update(state)
            _touch_task_progress(task_state)
        
        # 保存结果到文件以便审计
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        try:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for agent_key, agent_output in task_state.get("agent_outputs", {}).items():
                safe_key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(agent_key))[:80] or "agent"
                agent_file = os.path.join(output_dir, f"{timestamp}_{safe_key}.md")
                if isinstance(agent_output, (dict, list)):
                    text_output = json.dumps(agent_output, ensure_ascii=False, indent=2)
                elif agent_output is None:
                    text_output = ""
                else:
                    text_output = str(agent_output)
                try:
                    with open(agent_file, "w", encoding="utf-8", errors="replace") as f:
                        f.write(text_output)
                except OSError as write_exc:
                    print(f"  [UI] WARN: 写入审计文件失败 ({agent_file}): {write_exc}")
        except OSError as exc:
            print(f"  [UI] WARN: 创建审计目录失败 ({output_dir}): {exc}")

    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["step"] = "error"
        task_state["message"] = f"执行失败: {str(e)}"
        task_state["error"] = traceback.format_exc()
        _save_task_state_for_session(session_id, task_state)
    finally:
        _unregister_task_thread(session_id)

def _resume_pipeline_in_thread(
    segment_index: int,
    tail_frame_b64: str = None,
    video_path: str = None,
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
):
    """在后台线程中恢复执行流水线阶段二（单段编译）"""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)

    def _stream_callback(agent_name: str, chunk: str):
        if agent_name:
            out_key = _AGENT_KEY_MAP.get(agent_name, agent_name)
            if out_key not in task_state["agent_outputs"]:
                task_state["agent_outputs"][out_key] = ""
            task_state["agent_outputs"][out_key] += chunk
            _touch_task_progress(task_state)

    try:
        with request_scope(session_id=session_id, stream_callback=_stream_callback):
            if task_generation != _active_task_generation(session_id):
                return
            task_state["status"] = "running_phase_2"
            task_state["step"] = "step_4_compile"
            task_state["message"] = f"✍️ Seedance编译师正在生成片段 {segment_index}..."
            _touch_task_progress(task_state)
            state = run_phase_2_compile_segment(segment_index, tail_frame_b64, video_path)
            if task_generation != _active_task_generation(session_id):
                return
            task_state.update(state)
            _touch_task_progress(task_state)
        
        # 强制用 normalised 版本覆写 task_state 中的流式累积脏数据
        final_outputs = task_state.get("agent_outputs", {})
        key = f"compiled_segment_{segment_index}"
        raw_prompt = final_outputs.get(key, "")
        if raw_prompt:
            clean_prompt = _normalise_compiled_prompt(raw_prompt, segment_index)
            final_outputs[key] = clean_prompt
            final_outputs["prompt_compiler"] = clean_prompt
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 只存新生成的 compile（已经是清洗后的版本）
        comp = final_outputs.get(key)
        if comp:
            with open(os.path.join(output_dir, f"{timestamp}_prompt_compiler_seg{segment_index}.md"), "w", encoding="utf-8") as f:
                f.write(comp)
                
    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["step"] = "error"
        task_state["message"] = f"执行失败: {str(e)}"
        task_state["error"] = traceback.format_exc()
        _save_task_state_for_session(session_id, task_state)
    finally:
        _unregister_task_thread(session_id)


def _resume_shot_director_in_thread(
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
):
    """Resume Phase 1 shot director from persisted layout/blocking output."""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    try:
        with request_scope(session_id=session_id):
            if task_generation != _active_task_generation(session_id):
                return
            task_state["status"] = "running_phase_1"
            task_state["step"] = "step_3_direct"
            task_state["message"] = "正在复用已完成的镜头摆位骨架，续跑三段镜头导演..."
            task_state["error"] = ""
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)

            state = run_shot_director_resume_from_partial()
            if task_generation != _active_task_generation(session_id):
                return
            task_state.update(state)
            _touch_task_progress(task_state)
    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["step"] = "error"
        task_state["message"] = f"执行失败: {str(e)}"
        task_state["error"] = traceback.format_exc()
        _save_task_state_for_session(session_id, task_state)
    finally:
        _unregister_task_thread(session_id)


def _restart_shot_director_from_planner_in_thread(
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
):
    """Resume Phase 1 by rerunning shot director from the saved story planner."""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    try:
        with request_scope(session_id=session_id):
            if task_generation != _active_task_generation(session_id):
                return
            task_state["status"] = "running_phase_1"
            task_state["step"] = "step_3_direct"
            task_state["message"] = "已复用前三步宏观规划，正在重新启动镜头导演摆位骨架...（4/6）"
            task_state["error"] = ""
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)

            state = run_shot_director_restart_from_story_plan()
            if task_generation != _active_task_generation(session_id):
                return
            task_state.update(state)
            _touch_task_progress(task_state)
    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["step"] = "error"
        task_state["message"] = f"执行失败: {str(e)}"
        task_state["error"] = traceback.format_exc()
        _save_task_state_for_session(session_id, task_state)
    finally:
        _unregister_task_thread(session_id)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    response = templates.TemplateResponse(request=request, name="index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def _is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost"}


@app.get("/api/status")
async def get_status(session_id: str = DEFAULT_SESSION_ID):
    """前端轮询此接口获取实时状态"""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    return JSONResponse(_public_task_state(session_id))


@app.get("/api/latest_session")
async def get_latest_session(exclude_session_id: str = ""):
    """返回最近一个有可见片段输出的会话，供空白页面自动恢复。"""
    latest = _latest_visible_session(exclude_session_id)
    if not latest:
        return JSONResponse({"success": False, "error": "暂无可恢复的历史会话。"})
    return JSONResponse({"success": True, **latest})


def _project_summary(session_id: str, state: dict[str, Any], state_path: str = "") -> dict[str, Any]:
    updated_at = ""
    if state_path and os.path.exists(state_path):
        updated_at = datetime.fromtimestamp(os.path.getmtime(state_path)).isoformat(timespec="seconds")
    return {
        "session_id": session_id,
        "name": state.get("project_name") or f"项目 {session_id}",
        "status": state.get("status") or "idle",
        "current_segment_index": state.get("current_segment_index") or 1,
        "total_segments": state.get("total_segments") or 0,
        "archived": bool(state.get("archived")),
        "updated_at": updated_at,
    }


@app.get("/api/projects/recent")
async def api_projects_recent(include_archived: bool = False):
    sessions_dir = os.path.join(OUTPUT_DIR, "sessions")
    projects: list[dict[str, Any]] = []
    if os.path.isdir(sessions_dir):
        paths = []
        for name in os.listdir(sessions_dir):
            state_path = os.path.join(sessions_dir, name, "pipeline_state.json")
            if os.path.isfile(state_path):
                paths.append((name, state_path))
        for name, state_path in sorted(paths, key=lambda item: os.path.getmtime(item[1]), reverse=True):
            try:
                with open(state_path, "r", encoding="utf-8-sig") as file:
                    state = json.load(file)
            except Exception:
                continue
            if state.get("archived") and not include_archived:
                continue
            projects.append(_project_summary(_normalise_session_id(name), state, state_path))

    current = _task_state(DEFAULT_SESSION_ID)
    if not any(item["session_id"] == DEFAULT_SESSION_ID for item in projects):
        projects.insert(0, _project_summary(DEFAULT_SESSION_ID, current))
    return JSONResponse({"success": True, "projects": projects[:24]})


@app.post("/api/projects/new")
async def api_projects_new(payload: dict[str, Any] = Body(default={})):
    name = str((payload or {}).get("name") or "未命名项目").strip() or "未命名项目"
    requested_session_id = (payload or {}).get("session_id")
    session_id = _normalise_session_id(requested_session_id or f"project_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    if not requested_session_id:
        base_session_id = session_id
        counter = 1
        while os.path.exists(os.path.join(_session_output_dir(session_id), "pipeline_state.json")):
            session_id = _normalise_session_id(f"{base_session_id}_{counter}")
            counter += 1
    _bump_task_generation(session_id)
    with request_scope(session_id=session_id):
        clear_state()
    state = _default_task_state()
    state["project_name"] = name
    state["created_at"] = datetime.now().isoformat(timespec="seconds")
    state["message"] = "新项目已创建。"
    task_states[session_id] = state
    _save_task_state_for_session(session_id, state)
    return JSONResponse({"success": True, "project": _project_summary(session_id, state)})


@app.post("/api/projects/archive")
async def api_projects_archive(payload: dict[str, Any] = Body(default={})):
    session_id = _normalise_session_id(str((payload or {}).get("session_id") or DEFAULT_SESSION_ID))
    _refresh_task_state_from_disk(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "当前项目仍有任务运行，先停止或等待完成后再归档。"}, status_code=409)
    state = _task_state(session_id)
    state["archived"] = True
    state["archived_at"] = datetime.now().isoformat(timespec="seconds")
    state["message"] = "项目已归档。"
    _save_task_state_for_session(session_id, state)
    return JSONResponse({"success": True, "project": _project_summary(session_id, state)})


REFERENCE_IMAGES_DIR = os.path.join(ROOT_DIR, "reference_images")

@app.get("/api/reference_library")
async def get_reference_library():
    """返回本地 reference_images 目录下的所有图片"""
    if not os.path.exists(REFERENCE_IMAGES_DIR):
        os.makedirs(REFERENCE_IMAGES_DIR, exist_ok=True)
    images = []
    for f in os.listdir(REFERENCE_IMAGES_DIR):
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            images.append(f)
    return JSONResponse({"success": True, "images": sorted(images)})

@app.get("/api/reference_library/{filename}")
async def get_reference_image(filename: str):
    """返回本地库中的指定参考图"""
    file_path = os.path.join(REFERENCE_IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        return JSONResponse({"success": False, "error": "文件不存在"}, status_code=404)
    return FileResponse(file_path)


@app.get("/api/assets/library")
async def api_assets_library():
    library = _read_asset_library()
    return JSONResponse({"success": True, **library})


@app.get("/api/assets/file/{asset_type}/{filename:path}")
async def api_asset_file(asset_type: str, filename: str):
    asset_type = _normalise_asset_type(asset_type)
    dirname = ASSET_TYPE_DIRS[asset_type]
    safe_name = os.path.basename(filename)
    file_path = os.path.join(ASSET_LIBRARY_DIR, dirname, safe_name)
    if not os.path.isfile(file_path):
        return JSONResponse({"success": False, "error": "Asset file not found"}, status_code=404)
    return FileResponse(file_path)


@app.post("/api/assets/import")
async def api_assets_import(
    asset_type: str = Form("character"),
    name: str = Form(""),
    tags: str = Form(""),
    description: str = Form(""),
    purpose: str = Form(""),
    file: UploadFile = File(...),
):
    if not file or not file.filename:
        return JSONResponse({"success": False, "error": "No asset file uploaded"}, status_code=400)
    asset_type = _normalise_asset_type(asset_type)
    _, ext = os.path.splitext(file.filename)
    if asset_type != "upload" and ext.lower() not in IMAGE_ASSET_EXTENSIONS:
        return JSONResponse({"success": False, "error": "Asset library only accepts png/jpg/jpeg/webp images"}, status_code=400)
    content = await file.read()
    if not content:
        return JSONResponse({"success": False, "error": "Uploaded asset is empty"}, status_code=400)

    _ensure_asset_dirs()
    dirname = ASSET_TYPE_DIRS[asset_type]
    folder = os.path.join(ASSET_LIBRARY_DIR, dirname)
    path, existed = _dedupe_asset_path(folder, file.filename or "asset", content)

    if not existed:
        filename = os.path.basename(path)
        with open(path, "wb") as output:
            output.write(content)
        meta = {
            "id": f"{asset_type}:{filename}",
            "type": asset_type,
            "name": name.strip() or os.path.splitext(file.filename)[0],
            "tags": _parse_tags(tags),
            "description": description.strip(),
            "purpose": purpose.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_asset_meta(path, meta)

    asset = _asset_from_path(asset_type, path)
    return JSONResponse({"success": True, "asset": asset, "deduplicated": existed})


@app.post("/api/assets/import_batch")
async def api_assets_import_batch(
    asset_type: str = Form("character"),
    tags: str = Form(""),
    description: str = Form(""),
    purpose: str = Form(""),
    files: list[UploadFile] = File(...),
):
    _ensure_asset_dirs()
    asset_type = _normalise_asset_type(asset_type)
    dirname = ASSET_TYPE_DIRS[asset_type]
    folder = os.path.join(ASSET_LIBRARY_DIR, dirname)
    results: list[dict] = []
    skipped = 0
    for file in files:
        if not file or not file.filename:
            continue
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in IMAGE_ASSET_EXTENSIONS:
            continue
        content = await file.read()
        if not content:
            continue
        safe_name = os.path.splitext(file.filename)[0]
        path, existed = _dedupe_asset_path(folder, file.filename or "asset", content)
        if existed:
            skipped += 1
            results.append(_asset_from_path(asset_type, path))
            continue
        filename = os.path.basename(path)
        with open(path, "wb") as output:
            output.write(content)
        meta = {
            "id": f"{asset_type}:{filename}",
            "type": asset_type,
            "name": safe_name,
            "tags": _parse_tags(tags),
            "description": description.strip(),
            "purpose": purpose.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_asset_meta(path, meta)
        asset = _asset_from_path(asset_type, path)
        results.append(asset)
    return JSONResponse({"success": True, "assets": results, "count": len(results), "skipped": skipped})


@app.post("/api/video/extract_frames")
async def api_video_extract_frames(
    video_file: UploadFile = File(...),
    interval_seconds: int = Form(3),
    max_frames: int = Form(12),
    purpose: str = Form("action_reference"),
):
    if not video_file or not video_file.filename:
        return JSONResponse({"success": False, "error": "No video uploaded"}, status_code=400)
    _, ext = os.path.splitext(video_file.filename)
    if ext.lower() not in SEGMENT_VIDEO_EXTENSIONS:
        return JSONResponse({"success": False, "error": "Video must be mp4/mov/avi/webm"}, status_code=400)

    _ensure_asset_dirs()
    upload_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_filename(video_file.filename, 'video')}"
    upload_path = os.path.join(ASSET_LIBRARY_DIR, ASSET_TYPE_DIRS["upload"], upload_name)
    content = await video_file.read()
    if not content:
        return JSONResponse({"success": False, "error": "Uploaded video is empty"}, status_code=400)
    with open(upload_path, "wb") as output:
        output.write(content)

    try:
        import cv2
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"OpenCV is not available: {exc}"}, status_code=500)

    cap = cv2.VideoCapture(upload_path)
    if not cap.isOpened():
        cap.release()
        return JSONResponse({"success": False, "error": "Cannot open uploaded video"}, status_code=400)

    interval_seconds = max(1, int(interval_seconds or 3))
    max_frames = max(1, min(int(max_frames or 12), 60))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_seconds = frame_count / fps if frame_count > 0 else 0
    timestamps = [i * interval_seconds for i in range(max_frames)]
    if duration_seconds > 0:
        timestamps = [second for second in timestamps if second <= duration_seconds]
    if not timestamps:
        timestamps = [0]

    def format_timecode(seconds: float) -> str:
        minutes = int(seconds // 60)
        whole_seconds = int(seconds % 60)
        return f"{minutes:02d}:{whole_seconds:02d}"

    assets: list[dict[str, Any]] = []
    try:
        for index, seconds in enumerate(timestamps, start=1):
            cap.set(cv2.CAP_PROP_POS_MSEC, float(seconds) * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 84])
            if not ok:
                continue
            timecode = format_timecode(float(seconds))
            frame_name = f"{os.path.splitext(upload_name)[0]}_{index:03d}_{timecode.replace(':', '-')}.jpg"
            frame_path = os.path.join(ASSET_LIBRARY_DIR, ASSET_TYPE_DIRS["frame"], frame_name)
            with open(frame_path, "wb") as frame_output:
                frame_output.write(encoded.tobytes())
            meta = {
                "id": f"frame:{frame_name}",
                "type": "frame",
                "name": f"{os.path.splitext(video_file.filename)[0]} {timecode}",
                "tags": ["video_frame"],
                "description": "",
                "purpose": purpose.strip() or "action_reference",
                "source_video": upload_name,
                "timecode": timecode,
                "timestamp_seconds": round(float(seconds), 3),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            _write_asset_meta(frame_path, meta)
            asset = _asset_from_path("frame", frame_path)
            if asset:
                assets.append(asset)
    finally:
        cap.release()

    return JSONResponse({"success": True, "video": upload_name, "frames": assets})


@app.get("/api/model_profiles")
async def api_model_profiles():
    profiles = [_sanitize_model_profile(profile) for profile in _load_model_profiles()]
    return JSONResponse({"success": True, "profiles": profiles})


@app.post("/api/model_profiles")
async def api_save_model_profile(payload: dict[str, Any] = Body(...)):
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "Model profile payload must be an object"}, status_code=400)
    profiles = _load_model_profiles()
    existing = next((item for item in profiles if str(item.get("id") or "") == str(payload.get("id") or "")), None)
    profile = _normalise_model_profile_payload(payload, existing)
    if not profile["name"]:
        return JSONResponse({"success": False, "error": "Profile name is required"}, status_code=400)
    if not profile["base_url"]:
        return JSONResponse({"success": False, "error": "BaseURL is required"}, status_code=400)

    replaced = False
    for index, item in enumerate(profiles):
        if str(item.get("id") or "") == profile["id"]:
            profiles[index] = profile
            replaced = True
            break
    if not replaced:
        profiles.append(profile)
    _save_model_profiles(profiles)
    return JSONResponse({"success": True, "profile": _sanitize_model_profile(profile)})


@app.post("/api/model_profiles/test")
async def api_test_model_profile(payload: dict[str, Any] = Body(...)):
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "Model profile payload must be an object"}, status_code=400)
    existing = _find_model_profile(str(payload.get("id") or "")) if payload.get("id") else None
    profile = _normalise_model_profile_payload(payload, existing)
    base_url = profile.get("base_url")
    if not base_url:
        return JSONResponse({"success": False, "error": "BaseURL is required"}, status_code=400)
    headers = {"Authorization": f"Bearer {profile.get('api_key', '')}"} if profile.get("api_key") else {}
    try:
        async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
            response = await client.get(f"{base_url}/models", headers=headers)
        if response.status_code >= 400:
            return JSONResponse(
                {
                    "success": False,
                    "error": f"Connection reached {_host_from_base_url(base_url)} but returned HTTP {response.status_code}",
                    "base_url_host": _host_from_base_url(base_url),
                }
            )
        return JSONResponse({"success": True, "base_url_host": _host_from_base_url(base_url), "status_code": response.status_code})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc), "base_url_host": _host_from_base_url(base_url)})


@app.post("/api/director_edits/save")
async def api_director_edits_save(payload: dict[str, Any] = Body(...)):
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "Payload must be an object"}, status_code=400)
    session_id = _normalise_session_id(str(payload.get("session_id") or DEFAULT_SESSION_ID))
    segment_index = int(payload.get("segment_index") or payload.get("segment") or 1)
    edited_yaml = str(payload.get("edited_yaml") or payload.get("director_yaml") or "").strip()
    if not edited_yaml:
        return JSONResponse({"success": False, "error": "edited_yaml is required"}, status_code=400)
    _refresh_task_state_from_disk(session_id)
    state = _task_state(session_id)
    edit_payload = payload.get("edit_payload") if isinstance(payload.get("edit_payload"), dict) else {}
    _apply_director_edit_to_state(state, segment_index, edited_yaml, edit_payload, approved=False)
    state["message"] = f"Director edit saved for segment {segment_index}."
    _save_task_state_for_session(session_id, state)
    return JSONResponse({"success": True, "state": _public_task_state(session_id)})


@app.post("/api/director_edits/submit")
async def api_director_edits_submit(payload: dict[str, Any] = Body(...)):
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "Payload must be an object"}, status_code=400)
    session_id = _normalise_session_id(str(payload.get("session_id") or DEFAULT_SESSION_ID))
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "A task is already running. Please wait for it to finish."}, status_code=409)
    segment_index = int(payload.get("segment_index") or payload.get("segment") or 1)
    edited_yaml = str(payload.get("edited_yaml") or payload.get("director_yaml") or "").strip()
    if not edited_yaml:
        return JSONResponse({"success": False, "error": "edited_yaml is required"}, status_code=400)

    _refresh_task_state_from_disk(session_id)
    state = _task_state(session_id)
    edit_payload = payload.get("edit_payload") if isinstance(payload.get("edit_payload"), dict) else {}
    _apply_director_edit_to_state(state, segment_index, edited_yaml, edit_payload, approved=True)
    task_generation = _bump_task_generation(session_id)
    now = _now_iso()
    state["status"] = "running_phase_2"
    state["step"] = "step_4_compile"
    state["message"] = f"Seedance compiler is generating segment {segment_index} from approved director edit."
    state["error"] = ""
    state["started_at"] = now
    _touch_task_progress(state, now)
    _save_task_state_for_session(session_id, state)

    tail_frame_b64 = str(payload.get("tail_frame_b64") or "")
    thread = threading.Thread(
        target=_resume_pipeline_in_thread,
        args=(segment_index, tail_frame_b64 if tail_frame_b64 else None, None, task_generation, session_id),
        daemon=True,
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": "Director edit approved; prompt compilation started."})

@app.post("/api/run")
async def api_run(
    request: Request,
    script: str = Form(...),
    aspect_ratio: str = Form("16:9"),
    speed_mode: str = Form("false"),
    session_id: str = Form(DEFAULT_SESSION_ID),
    reference_images: str = Form(""),
    reference_image_manifest_json: str = Form(""),
    model_profile_id: str = Form(""),
    model_profile_snapshot_json: str = Form(""),
    asset_selection_json: str = Form(""),
    style_preset: str = Form(""),
    reference_image_files: list[UploadFile] | None = File(None),
):
    """启动流水线（宏观规划阶段一）"""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    _refresh_task_state_from_disk(session_id)

    # 自动清理：如果已有任务在执行或处于阻塞状态，自动中断并清理前段任务
    if task_state.get("status") in BLOCKING_STATUSES:
        print(f"  [AutoClean] Session {session_id}: 发现前置任务 ({task_state.get('status')})，自动清理并启动新流水线")
        with request_scope(session_id=session_id):
            clear_state()
        task_state.clear()
        task_state.update(_default_task_state())
        _save_task_state_for_session(session_id, task_state)

    try:
        selected_model_profile = _model_profile_snapshot(model_profile_id, model_profile_snapshot_json)
        selected_asset_selection = _parse_json_object(asset_selection_json, "asset_selection_json")
        reference_manifest_overrides = _parse_reference_manifest(reference_image_manifest_json)
        reference_image_b64s, reference_image_manifest = await _read_reference_uploads(
            reference_image_files,
            reference_manifest_overrides,
        )
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)})

    # 持久化用户输入（刷新页面后可恢复）。先重置整份会话状态，避免上一轮
    # active_segment_index / last_qc_status / tail_frame_analysis 等运行态残留。
    preserved_project_name = task_state.get("project_name")
    preserved_created_at = task_state.get("created_at")
    task_generation = _bump_task_generation(session_id)
    task_state.clear()
    task_state.update(_default_task_state())
    if preserved_project_name:
        task_state["project_name"] = preserved_project_name
    if preserved_created_at:
        task_state["created_at"] = preserved_created_at
    task_state["input_script"] = script
    task_state["input_aspect_ratio"] = aspect_ratio
    task_state["style_preset"] = style_preset
    task_state["model_profile_snapshot"] = selected_model_profile
    task_state["asset_selection"] = selected_asset_selection
    # 生成参考图缩略图用于前端恢复显示
    ref_thumbs = []
    for i, b64 in enumerate(reference_image_b64s):
        manifest_item = reference_image_manifest[i] if i < len(reference_image_manifest) else {}
        # 生成小缩略图（前端展示用，不超过 80x80）
        thumb = ""
        try:
            raw = b64.split(",", 1)[-1] if "," in b64 else b64
            if not raw:
                raise ValueError("参考图 base64 为空")
            img = Image.open(BytesIO(base64.b64decode(raw)))
            img.load()  # 触发格式校验，避免延迟解码失败
            img.thumbnail((80, 80))
            buf = BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=50)
            thumb = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception as exc:
            print(f"  [UI] WARN: 生成参考图 #{i+1} 缩略图失败: {type(exc).__name__}: {exc}")
            thumb = ""
        ref_thumbs.append({
            "filename": manifest_item.get("filename", f"图片{i+1}"),
            "purpose": manifest_item.get("purpose", ""),
            "label": manifest_item.get("label", ""),
            "thumbnail": thumb,
        })
    task_state["input_ref_manifest"] = ref_thumbs

    # 在后台线程执行阶段一
    thread = threading.Thread(
        target=_run_pipeline_in_thread,
        args=(
            script,
            aspect_ratio,
            reference_images,
            reference_image_b64s,
            reference_image_manifest,
            speed_mode.lower() in {"1", "true", "yes", "on"},
            task_generation,
            session_id,
            selected_model_profile,
            selected_asset_selection,
        ),
        daemon=True
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": "流水线已启动"})

@app.post("/api/resume")
async def api_resume(
    request: Request,
    segment_index: int = Form(...),
    session_id: str = Form(DEFAULT_SESSION_ID),
    tail_frame_b64: str = Form(""),
    previous_video_file: UploadFile | None = File(None),
):
    """恢复执行单段编译（阶段二）"""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)

    _refresh_task_state_from_disk(session_id)
    # 自动清理死任务
    if _has_live_task(session_id) is False and task_state.get("status") in RUNNING_STATUSES:
        task_state["status"] = "waiting_for_user_input"
        _save_task_state_for_session(session_id, task_state)
    # 允许从 error 状态重试（Phase 2 失败后用户点重试按钮）
    if task_state.get("status") == "error" and int(task_state.get("total_segments") or 0) > 0:
        task_state["status"] = "waiting_for_user_input"
        task_state["error"] = ""
        _save_task_state_for_session(session_id, task_state)
    if (
        not _has_live_task(session_id)
        and task_state.get("status") in {"idle", "aborted", "error"}
        and _can_resume_saved_phase2_segment(task_state, segment_index)
    ):
        task_state["status"] = "waiting_for_user_input"
        task_state["error"] = ""
        task_state["current_segment_index"] = segment_index
        task_state["active_segment_index"] = segment_index
        _save_task_state_for_session(session_id, task_state)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "已有任务正在执行中，请等待当前步骤完成。"})
    if task_state.get("status") != "waiting_for_user_input":
        return JSONResponse({"success": False, "error": "当前未处于等待交互状态"})

    approved_map = task_state.get("shot_director_approved_by_segment") or {}
    if task_state.get("director_review_required") and _segment_key(segment_index) not in approved_map:
        return JSONResponse({"success": False, "error": "Please confirm director edits before prompt compilation."})

    try:
        video_path = await _save_segment_video_upload(previous_video_file)
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)})
    if video_path and not tail_frame_b64:
        tail_frame_b64 = _extract_tail_frame_b64_from_video(video_path) or ""

    task_generation = _bump_task_generation(session_id)
    now = _now_iso()
    task_state["status"] = "running_phase_2"
    task_state["step"] = "step_4_compile"
    task_state["message"] = f"✍️ Seedance编译师正在生成片段 {segment_index}..."
    task_state["error"] = ""
    task_state["current_segment_index"] = segment_index
    task_state["active_segment_index"] = segment_index
    task_state["started_at"] = now
    _touch_task_progress(task_state, now)
    _save_task_state_for_session(session_id, task_state)
    thread = threading.Thread(
        target=_resume_pipeline_in_thread,
        args=(
            segment_index,
            tail_frame_b64 if tail_frame_b64 else None,
            video_path,
            task_generation,
            session_id,
        ),
        daemon=True
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": "已恢复执行编译步骤"})


@app.post("/api/retry_shot_director")
async def api_retry_shot_director(
    session_id: str = Form(DEFAULT_SESSION_ID),
    script: str = Form(""),
):
    """Resume or restart the shot director from the best persisted checkpoint.
    
    If a new script is provided and differs from the previous one, clear the
    story_planner output and re-run the full Phase 1 pipeline (rhythm rewrite,
    scene analysis, story planning) before running shot director.
    """
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "已有任务正在执行中，请等待当前步骤完成。"})

    outputs = task_state.get("agent_outputs") or {}
    if not outputs.get("story_planner"):
        return JSONResponse({"success": False, "error": "缺少结构规划输出，无法续跑镜头导演。"})
    if outputs.get("shot_director"):
        return JSONResponse({"success": False, "error": "镜头导演最终输出已存在，无需续跑。"})

    # 检测剧本是否发生变化
    script_changed = False
    if script and script.strip():
        old_script = task_state.get("input_script", "")
        disk_state = load_state()
        if disk_state:
            old_script = disk_state.get("script", "")
        # 简单比较：去除空白后比较
        if script.strip().replace(" ", "").replace("\n", "") != old_script.replace(" ", "").replace("\n", ""):
            script_changed = True
            print(f"[UI] 检测到剧本变化，将重新运行完整Phase 1")

    # 如果剧本发生变化，清除相关输出并重新运行完整Phase 1
    if script_changed:
        task_state["input_script"] = script.strip()
        # 清除 story_planner 及之后的输出，保留 rhythm_rewrite 和 scene_analyst（可选）
        outputs.pop("story_planner", None)
        outputs.pop("shot_director_layout", None)
        outputs.pop("shot_director_blocking", None)
        outputs.pop("shot_director_guard", None)
        outputs.pop("shot_director_final", None)
        outputs.pop("shot_director", None)
        task_state["agent_outputs"] = outputs
        task_state["total_segments"] = 0
        task_state["segment_names"] = []
        
        # 更新持久化状态
        disk_state = load_state()
        if disk_state:
            disk_state["script"] = script.strip()
            disk_state["original_script"] = script.strip()
            disk_state["agent_outputs"] = outputs
            disk_state["total_segments"] = 0
            disk_state["segment_names"] = []
            save_state(disk_state)
        
        # 重新运行完整Phase 1
        task_generation = _bump_task_generation(session_id)
        task_state["status"] = "running_phase_1"
        task_state["step"] = "step_1_rhythm"
        task_state["message"] = "剧本已更新，正在重新运行完整规划流程...（1/6）"
        task_state["error"] = ""
        _save_task_state_for_session(session_id, task_state)
        
        # 获取其他必要的输入参数
        aspect_ratio = task_state.get("input_aspect_ratio", "9:16")
        reference_images = ""
        ref_manifest = task_state.get("input_ref_manifest", [])
        
        thread = threading.Thread(
            target=_run_pipeline_in_thread,
            args=(
                script.strip(),
                aspect_ratio,
                reference_images,
            ),
            kwargs={
                "reference_image_b64s": [],
                "reference_image_manifest": ref_manifest,
                "speed_mode": True,
                "task_generation": task_generation,
                "session_id": session_id,
            },
            daemon=True,
        )
        _register_task_thread(session_id, thread)
        thread.start()
        return JSONResponse(
            {
                "success": True,
                "message": "剧本已更新，正在重新运行完整规划流程...",
            }
        )

    # 剧本未变化，正常续跑shot_director
    has_layout_checkpoint = bool(outputs.get("shot_director_layout"))
    task_generation = _bump_task_generation(session_id)
    task_state["status"] = "running_phase_1"
    task_state["step"] = "step_3_direct"
    task_state["message"] = (
        "正在复用已完成的镜头摆位骨架，续跑三段镜头导演..."
        if has_layout_checkpoint
        else "已复用前三步宏观规划，正在重新启动镜头导演摆位骨架...（4/6）"
    )
    task_state["error"] = ""
    _save_task_state_for_session(session_id, task_state)

    thread = threading.Thread(
        target=(
            _resume_shot_director_in_thread
            if has_layout_checkpoint
            else _restart_shot_director_from_planner_in_thread
        ),
        args=(task_generation, session_id),
        daemon=True,
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse(
        {
            "success": True,
            "message": (
                "已从镜头导演中间产物继续执行"
                if has_layout_checkpoint
                else "已从结构规划继续执行镜头导演"
            ),
        }
    )


@app.post("/api/abort")
async def api_abort(session_id: str = Form(DEFAULT_SESSION_ID)):
    """中断当前运行的流水线"""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    _refresh_task_state_from_disk(session_id)
    if task_state.get("status") in BLOCKING_STATUSES:
        _bump_task_generation(session_id)
        task_state["status"] = "aborted"
        task_state["step"] = ""
        task_state["message"] = "任务已被手动中断"
        _save_task_state_for_session(session_id, task_state)
        # 保存已有的中间输出
        if task_state.get("agent_outputs"):
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
            try:
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                for agent_key, agent_output in task_state["agent_outputs"].items():
                    safe_key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(agent_key))[:80] or "agent"
                    agent_file = os.path.join(output_dir, f"{timestamp}_aborted_{safe_key}.md")
                    if isinstance(agent_output, (dict, list)):
                        text_output = json.dumps(agent_output, ensure_ascii=False, indent=2)
                    elif agent_output is None:
                        text_output = ""
                    else:
                        text_output = str(agent_output)
                    try:
                        with open(agent_file, "w", encoding="utf-8", errors="replace") as f:
                            f.write(text_output)
                    except OSError as write_exc:
                        print(f"  [UI] WARN: 写入中断快照失败 ({agent_file}): {write_exc}")
            except OSError as exc:
                print(f"  [UI] WARN: 创建中断快照目录失败 ({output_dir}): {exc}")
        return JSONResponse({"success": True, "message": "任务已中断，已保存中间结果"})
    return JSONResponse({"success": True, "message": "当前没有运行中的任务"})


@app.post("/api/reset")
async def api_reset(session_id: str = Form(DEFAULT_SESSION_ID)):
    """一键清空当前任务，允许调试时从空白状态重新启动。"""
    session_id = _normalise_session_id(session_id)
    _bump_task_generation(session_id)
    with request_scope(session_id=session_id):
        clear_state()
    task_state = _task_state(session_id)
    task_state.clear()
    task_state.update(_default_task_state())
    return JSONResponse({"success": True, "message": "当前任务已清空，可以重新启动调试。"})


@app.post("/api/clear_previous_segment")
async def api_clear_previous_segment(session_id: str = Form(DEFAULT_SESSION_ID)):
    """清除最近已生成的一段，保留全局规划与更早片段，方便回退重跑。"""
    session_id = _normalise_session_id(session_id)
    _bump_task_generation(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    changed, segment_index, message = _clear_previous_segment_in_state(task_state)
    if not changed:
        return JSONResponse({"success": False, "error": message})

    with request_scope(session_id=session_id):
        save_state(task_state)
    return JSONResponse(
        {
            "success": True,
            "message": message,
            "cleared_segment": segment_index,
            "state": _public_task_state(session_id),
        }
    )


@app.post("/api/clear_segment")
async def api_clear_segment(
    segment_index: int = Form(...),
    session_id: str = Form(DEFAULT_SESSION_ID),
):
    """清除指定片段及其后续所有片段，用于"重跑某段"时自动清掉下游脏数据。"""
    session_id = _normalise_session_id(session_id)
    _bump_task_generation(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    changed, cleared_index, message = _clear_segment_and_downstream(task_state, segment_index)
    if not changed:
        return JSONResponse({"success": False, "error": message})

    with request_scope(session_id=session_id):
        save_state(task_state)
    return JSONResponse(
        {
            "success": True,
            "message": message,
            "cleared_segment": cleared_index,
            "state": _public_task_state(session_id),
        }
    )


@app.get("/api/config")
async def api_get_config():
    config = load_config()
    # 脱敏：隐藏所有 API key，但保留 base_url 和 model 供前端展示
    if "llm" in config and "api_key" in config["llm"]:
        config["llm"]["api_key"] = "***"
    if "vectordb" in config and "api_key" in config["vectordb"]:
        config["vectordb"]["api_key"] = "***"
    for agent_config in config.get("agent_models", {}).values():
        if isinstance(agent_config, dict) and "api_key" in agent_config:
            agent_config["api_key"] = "***"
    # 标记配置为后端锁定，前端不可覆盖
    config["_config_locked"] = True
    config["_config_note"] = "模型配置由 config/settings.yaml 定死，前端不可修改"
    return JSONResponse(config)


@app.post("/api/build_vectordb")
async def api_build_vectordb(request: Request):
    if not _is_local_request(request):
        return JSONResponse({"success": False, "error": "知识库重建仅允许本机管理员执行。"})
    try:
        build_vectordb(force_rebuild=True)
        return JSONResponse({"success": True, "message": "向量知识库已重建"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


def start_ui():
    config = load_config()
    ui_config = config.get("ui", {}) if isinstance(config, dict) else {}
    host = ui_config.get("host", "127.0.0.1")
    port = ui_config.get("port", 8686)
    print("\n  Director Agent Team UI starting...")
    print(f"  URL: http://{host}:{port}")
    print("  Press Ctrl+C to quit\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_ui()
