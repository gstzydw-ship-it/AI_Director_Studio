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
import copy
import ipaddress
import socket
import time
from io import BytesIO
from datetime import datetime
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image, ImageOps, UnidentifiedImageError
import uvicorn

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


from agents.knowledge_base import build_vectordb, knowledge_index_status, load_config
from agents.request_context import request_scope
from agents.utils import COMFLY_BASE_URL, get_config_path, get_public_config_path


app = FastAPI(title="智能导演多Agent团队", version="0.2.0")

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
    }


DEFAULT_SESSION_ID = "local"
SESSION_ID_RE = re.compile(r"[^A-Za-z0-9_-]")

task_states: dict[str, dict] = {}
active_task_generations: dict[str, int] = {}
active_task_threads: dict[str, threading.Thread] = {}
vectordb_build_lock = threading.Lock()
vectordb_build_status: dict[str, str] = {
    "status": "idle",
    "message": "向量知识库尚未构建",
    "error": "",
    "started_at": "",
    "finished_at": "",
}

RUNNING_STATUSES = {"running", "running_phase_1", "running_phase_2"}
BLOCKING_STATUSES = RUNNING_STATUSES | {"waiting_for_user_input"}
LIVE_TASK_STALL_TIMEOUT_SECONDS = int(os.getenv("DIRECTOR_UI_STALL_TIMEOUT_SECONDS", "900"))


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
    session_id = _normalise_session_id(session_id)
    active_task_threads[session_id] = thread
    _append_task_log(session_id, "thread_registered", thread_name=thread.name, thread_id=thread.ident)


def _unregister_task_thread(session_id: str) -> None:
    session_id = _normalise_session_id(session_id)
    if active_task_threads.get(session_id) is threading.current_thread():
        active_task_threads.pop(session_id, None)
        _append_task_log(session_id, "thread_unregistered", thread_name=threading.current_thread().name)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _append_task_log(session_id: str, event: str, **fields: Any) -> None:
    session_id = _normalise_session_id(session_id)
    entry = {
        "ts": _now_iso(),
        "session_id": session_id,
        "event": event,
        **fields,
    }
    try:
        os.makedirs(_session_output_dir(session_id), exist_ok=True)
        with open(os.path.join(_session_output_dir(session_id), "task_events.log"), "a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:
        print(f"  [TaskLog] WARN: unable to write task log for {session_id}: {exc}")


def _state_log_summary(state: dict) -> dict:
    return {
        "status": state.get("status"),
        "step": state.get("step"),
        "message": state.get("message"),
        "review_agent": state.get("review_agent"),
        "current_segment_index": state.get("current_segment_index"),
        "active_segment_index": state.get("active_segment_index"),
    }


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
    "剧情增强导演": "director_showrunner",
    "总导演统筹": "director_showrunner",
    "节奏总控导演": "rhythm_rewrite_director",
    "场景分析师": "scene_analyst",
    "结构规划师": "story_planner",
    "镜头导演": "shot_director",
    "分镜流程图设计师": "storyboard_designer",
    "Seedance编译师": "prompt_compiler",
    "质检导演": "quality_inspector",
}

_AGENT_DISPLAY_NAMES = {
    "director_showrunner": "📝 剧情增强",
    "rhythm_rewrite_director": "🎼 节奏改写",
    "scene_analyst": "📋 场景预分析",
    "story_planner": "🎬 结构规划",
    "shot_director": "🎥 镜头设计",
    "storyboard_designer": "🎨 分镜流程图",
    "prompt_compiler": "✍️ Seedance Prompt",
    "quality_inspector": "🔍 质检报告",
}

MAX_REFERENCE_IMAGES = 12
REFERENCE_IMAGE_MAX_EDGE = 1280
REFERENCE_IMAGE_JPEG_QUALITY = 82
REFERENCE_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

AUTO_REFERENCE_SCENE_HINTS = (
    "场景",
    "空间",
    "环境",
    "地点",
    "场地",
    "公寓",
    "客厅",
    "卧室",
    "儿童房",
    "厨房",
    "餐厅",
    "门口",
    "大堂",
    "集团",
    "公司",
    "总部",
    "办公区",
    "办公室",
    "会议室",
    "小区",
    "街道",
    "走廊",
    "电梯",
    "酒店",
    "医院",
    "学校",
    "房间",
    "庭院",
    "车库",
    "停车场",
)

AUTO_REFERENCE_PROP_HINTS = (
    "道具",
    "手机",
    "手提包",
    "包",
    "咖啡",
    "腕表",
    "文件",
    "照片",
    "车",
    "钥匙",
    "合同",
    "戒指",
    "项链",
)

AUTO_REFERENCE_WEAK_TOKENS = {"场景", "空间", "环境", "地点", "场地", "集团", "公司", "总部"}
AUTO_REFERENCE_SPLIT_RE = re.compile(r"[\s_\-—~·,，、.。:：;；()（）\[\]【】]+")
SEGMENT_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
PREVIOUS_SEGMENT_TAIL_FRAME_ROLE = "previous_segment_tail_frame"
PREVIOUS_SEGMENT_TAIL_FRAME_PURPOSE = (
    "Carry only the visible ending state of the previous segment into the next segment; "
    "do not use this as a character, scene, or style master."
)

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
    resume_after_human_review,
    run_phase_1_planning,
    run_phase_2_compile_segment,
    run_shot_director_restart_from_story_plan,
    run_shot_director_resume_from_partial,
    save_state,
    _normalise_compiled_prompt,
)
from agents.director_graph_package.storyboard_designer_impl import (
    generate_storyboard_for_segment,
    generate_storyboard_image_for_segment,
)
from agents.director_graph_package import planning_context_impl as scene_card_impl


def _save_task_state_for_session(
    session_id: str,
    state: dict,
) -> bool:
    """Persist a UI task snapshot into the session-owned state file."""
    try:
        with request_scope(session_id=_normalise_session_id(session_id)):
            save_state(dict(state))
        _append_task_log(session_id, "state_saved", **_state_log_summary(state))
        return True
    except Exception as exc:
        _append_task_log(session_id, "state_save_failed", error=str(exc), traceback=traceback.format_exc())
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
    "场景分析师":  ("step_0_scene",    "📋 场景预分析正在读取参考图、人物站位和空间信息...（1/8）"),
    "剧情增强导演":  ("step_0_enhance", "📝 剧情增强导演正在按场景约束增强剧本...（2/8）"),
    "节奏总控导演":  ("step_0_rhythm",  "🎼 节奏总控导演正在改写剧本...（3/8）"),
    "结构规划师":  ("step_2_plan",     "🎬 结构规划师正在拆片规划...（4/8）"),
    "镜头导演":    ("step_3_direct",   "🎥 镜头导演正在设计分镜...（5/8）"),
    "Seedance编译师": ("step_4_compile", "✍️ Seedance编译师正在生成Prompt...（7/8）"),
    "质检导演":    ("step_5_inspect",  "🔍 质检导演正在审查产物...（8/8）"),
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
        if (
            not has_live_task
            and disk_state.get("status") in {"idle", ""}
            and disk_state.get("review_mode") == "agent_output"
            and disk_state.get("review_agent")
            and disk_state.get("review_output") is not None
        ):
            title = disk_state.get("review_title") or disk_state.get("review_agent") or "Agent 输出"
            disk_state["status"] = "waiting_for_user_input"
            disk_state["message"] = f"{title}已完成，请审核/修改后继续。"
            disk_state["error"] = ""
            _save_task_state_for_session(session_id, disk_state)
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
        if not has_live_task and not disk_state.get("thread_id") and disk_state.get("status") in RUNNING_STATUSES:
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


def _public_task_state(session_id: str = DEFAULT_SESSION_ID) -> dict:
    state = dict(_task_state(session_id))
    image_refs = state.get("reference_image_b64s") or []
    if image_refs:
        state["reference_image_b64s"] = f"{len(image_refs)} reference images omitted from status response"
    error = state.get("error")
    if isinstance(error, str) and len(error) > 5000:
        state["error"] = error[:5000] + "\n... traceback truncated ..."
    return state


def _clamp_annotation_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number > 1:
        return None
    return round(number, 4)


def _normalise_scene_layout_annotation(entry: dict[str, Any]) -> dict[str, Any] | None:
    annotations = entry.get("annotations") if isinstance(entry.get("annotations"), dict) else {}
    people: list[dict[str, Any]] = []
    for index, person in enumerate(annotations.get("people") or []):
        if not isinstance(person, dict):
            continue
        x = _clamp_annotation_number(person.get("x"))
        y = _clamp_annotation_number(person.get("y"))
        if x is None or y is None:
            continue
        people.append(
            {
                "label": str(person.get("label") or f"人{index + 1}")[:40],
                "x": x,
                "y": y,
                "color": str(person.get("color") or "")[:16],
            }
        )

    arrows: list[dict[str, float]] = []
    for arrow in annotations.get("arrows") or []:
        if not isinstance(arrow, dict):
            continue
        x1 = _clamp_annotation_number(arrow.get("x1"))
        y1 = _clamp_annotation_number(arrow.get("y1"))
        x2 = _clamp_annotation_number(arrow.get("x2"))
        y2 = _clamp_annotation_number(arrow.get("y2"))
        if None in (x1, y1, x2, y2):
            continue
        arrows.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    if not people and not arrows:
        return None

    scene_number = str(entry.get("scene_number") or "").strip() or "1"
    image_path = str(entry.get("image_path") or "").strip()
    annotated_image = str(entry.get("annotated_image") or "").strip()
    if annotated_image and not annotated_image.startswith("data:image/"):
        annotated_image = ""

    summary_people = ", ".join(f"{item['label']}({item['x']:.2f},{item['y']:.2f})" for item in people)
    summary_arrows = ", ".join(
        f"({item['x1']:.2f},{item['y1']:.2f})->({item['x2']:.2f},{item['y2']:.2f})"
        for item in arrows
    )
    summary_parts = []
    if summary_people:
        summary_parts.append(f"人物标点: {summary_people}")
    if summary_arrows:
        summary_parts.append(f"活动轨迹: {summary_arrows}")

    return {
        "scene_number": scene_number,
        "image_path": image_path,
        "cache_key": str(entry.get("cache_key") or "").strip(),
        "annotations": {"people": people, "arrows": arrows},
        "annotated_image": annotated_image,
        "summary": "；".join(summary_parts),
    }


def _upsert_scene_layout_annotations(state: dict, entries: list[dict[str, Any]]) -> int:
    normalised = [
        item
        for item in (_normalise_scene_layout_annotation(entry) for entry in entries if isinstance(entry, dict))
        if item
    ]
    state["scene_layout_annotations"] = normalised

    outputs = state.setdefault("agent_outputs", {})
    outputs["scene_layout_annotations"] = json.dumps(
        [{key: value for key, value in item.items() if key != "annotated_image"} for item in normalised],
        ensure_ascii=False,
    )

    images = list(state.get("reference_image_b64s") or [])
    manifest = [item if isinstance(item, dict) else {} for item in list(state.get("reference_image_manifest") or [])]
    while len(manifest) < len(images):
        manifest.append({})

    kept_images: list[str] = []
    kept_manifest: list[dict[str, Any]] = []
    for index, image in enumerate(images):
        item = manifest[index] if index < len(manifest) else {}
        role_text = " ".join(str(item.get(key) or "") for key in ("role", "type", "purpose")).lower()
        if "annotated_scene_layout" in role_text or "scene_layout_annotation" in role_text:
            continue
        kept_images.append(image)
        kept_manifest.append(item)

    for item in normalised:
        annotated_image = item.get("annotated_image")
        if not annotated_image:
            continue
        scene_number = item.get("scene_number") or "1"
        kept_images.append(str(annotated_image))
        kept_manifest.append(
            {
                "label": f"@图片{len(kept_images)}",
                "role": "annotated_scene_layout",
                "type": "scene_layout_annotation",
                "scene_number": str(scene_number),
                "source_layout_path": str(item.get("image_path") or ""),
                "purpose": f"场景{scene_number}用户标注后的俯视布局图：包含人物位置、移动轨迹、空间边界和固定物体。",
                "annotations_summary": str(item.get("summary") or ""),
            }
        )

    state["reference_image_b64s"] = kept_images
    state["reference_image_manifest"] = kept_manifest
    state["reference_image_count"] = len(kept_images)
    return len(normalised)


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


_SCENE_REFERENCE_NAME_HINTS = (
    "场景",
    "空间",
    "环境",
    "地点",
    "场地",
    "公寓",
    "客厅",
    "卧室",
    "厨房",
    "餐厅",
    "门口",
    "大堂",
    "公司",
    "集团",
    "办公室",
    "会议室",
    "小区",
    "街道",
    "走廊",
    "电梯",
    "酒店",
    "医院",
    "学校",
    "房间",
    "庭院",
    "车库",
    "停车场",
)


def _infer_reference_purpose(index: int, filename: str = "") -> str:
    base_name = os.path.splitext(filename or "")[0]
    if any(marker in base_name for marker in _SCENE_REFERENCE_NAME_HINTS):
        return "场景空间、轴线、光线与首帧环境基底锁定"
    purposes = {
        1: "主角人物身份、五官、发型、身形与服装一致性锁定",
        2: "对手角色/第二核心角色身份、五官、发型、身形与服装一致性锁定",
        3: "第三核心人物/补充人物身份、五官、发型、身形与服装一致性锁定",
        4: "第四核心人物/补充人物身份、五官、发型、身形与服装一致性锁定",
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


def _reference_asset_type(filename: str) -> str:
    base_name = os.path.splitext(filename or "")[0]
    if any(marker in base_name for marker in AUTO_REFERENCE_SCENE_HINTS):
        return "scene"
    if any(marker in base_name for marker in AUTO_REFERENCE_PROP_HINTS):
        return "prop"
    return "character"


def _reference_name_tokens(filename: str) -> list[str]:
    base_name = os.path.splitext(filename or "")[0].strip()
    tokens: set[str] = set()
    if base_name:
        tokens.add(base_name)
    for part in AUTO_REFERENCE_SPLIT_RE.split(base_name):
        part = part.strip()
        if len(part) >= 2:
            tokens.add(part)
    for hint in AUTO_REFERENCE_SCENE_HINTS + AUTO_REFERENCE_PROP_HINTS:
        if hint in base_name:
            tokens.add(hint)
    return sorted(tokens, key=lambda item: (-len(item), item))


def _score_reference_asset(script: str, filename: str) -> tuple[int, int, list[str]]:
    script_text = script or ""
    score = 0
    first_index = len(script_text) + 1
    matched_tokens: list[str] = []
    base_name = os.path.splitext(filename or "")[0]
    for token in _reference_name_tokens(filename):
        pos = script_text.find(token)
        if pos < 0:
            continue
        matched_tokens.append(token)
        first_index = min(first_index, pos)
        if token == base_name:
            score += 100
        else:
            score += min(60, max(12, len(token) * 8))
    if matched_tokens and base_name not in matched_tokens and all(token in AUTO_REFERENCE_WEAK_TOKENS for token in matched_tokens):
        return 0, first_index, []
    return score, first_index, matched_tokens


def _auto_reference_purpose(asset_type: str, filename: str, matched_tokens: list[str]) -> str:
    base_name = os.path.splitext(filename or "")[0]
    matched = "、".join(matched_tokens[:4]) or base_name
    if asset_type == "scene":
        return (
            f"自动匹配场景参考图：{base_name}；命中：{matched}；"
            "用于场景预分析生成俯视图和九宫格，并锁定空间、轴线、光线和固定物体。"
        )
    if asset_type == "prop":
        return f"自动匹配道具参考图：{base_name}；命中：{matched}；只锁定道具外观、材质和可见状态。"
    return f"自动匹配人物参考图：{base_name}；命中：{matched}；只锁定身份、五官、发型、身形和服装。"


def _build_auto_reference_matches(
    script: str,
    existing_manifest: list[dict[str, str]] | None = None,
    *,
    max_images: int = MAX_REFERENCE_IMAGES,
) -> list[dict[str, Any]]:
    if not script or not os.path.exists(REFERENCE_IMAGES_DIR):
        return []

    existing_names = {
        str(item.get("filename") or "").lower()
        for item in existing_manifest or []
        if isinstance(item, dict)
    }
    candidates: list[dict[str, Any]] = []
    for filename in os.listdir(REFERENCE_IMAGES_DIR):
        if not filename.lower().endswith(REFERENCE_IMAGE_EXTENSIONS):
            continue
        if filename.lower() in existing_names:
            continue
        file_path = os.path.join(REFERENCE_IMAGES_DIR, filename)
        if not os.path.isfile(file_path):
            continue
        score, first_index, matched_tokens = _score_reference_asset(script, filename)
        if score <= 0:
            continue
        asset_type = _reference_asset_type(filename)
        candidates.append(
            {
                "filename": filename,
                "path": file_path,
                "asset_type": asset_type,
                "score": score,
                "first_index": first_index,
                "matched_tokens": matched_tokens,
                "purpose": _auto_reference_purpose(asset_type, filename, matched_tokens),
            }
        )

    type_priority = {"character": 0, "scene": 1, "prop": 2}
    candidates.sort(
        key=lambda item: (
            -int(item["score"]),
            int(item["first_index"]),
            type_priority.get(str(item["asset_type"]), 9),
            str(item["filename"]),
        )
    )
    return candidates[:max_images]


def _auto_select_reference_images(
    script: str,
    existing_manifest: list[dict[str, str]] | None = None,
    *,
    max_images: int = MAX_REFERENCE_IMAGES,
) -> tuple[list[str], list[dict[str, str]], list[dict[str, Any]]]:
    existing_count = len(existing_manifest or [])
    remaining = max(0, max_images - existing_count)
    matches = _build_auto_reference_matches(script, existing_manifest, max_images=remaining)
    image_data_urls: list[str] = []
    manifest: list[dict[str, str]] = []
    selected: list[dict[str, Any]] = []
    start_index = existing_count + 1
    for offset, match in enumerate(matches):
        try:
            with open(match["path"], "rb") as file_obj:
                content = file_obj.read()
            image_data_url, image_metadata = _encode_reference_image_for_llm(content, match["filename"])
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            print(f"  [AutoReference] WARN: skip {match['filename']}: {type(exc).__name__}: {exc}")
            continue
        label = f"@图片{start_index + len(image_data_urls)}"
        image_data_urls.append(image_data_url)
        manifest.append(
            {
                "label": label,
                "filename": str(match["filename"]),
                "purpose": str(match["purpose"]),
                "asset_type": str(match["asset_type"]),
                "selected_by": "auto_reference_matcher",
                "matched_tokens": "、".join(match["matched_tokens"]),
                "match_score": str(match["score"]),
                "processed_size": image_metadata["processed_size"],
                "processed_bytes": image_metadata["processed_bytes"],
                "original_size": image_metadata["original_size"],
                "original_bytes": image_metadata["original_bytes"],
            }
        )
        selected.append({k: v for k, v in match.items() if k != "path"})
    return image_data_urls, manifest, selected


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
        purpose = override.get("purpose") or _infer_reference_purpose(index, upload.filename)
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


def _tail_frame_data_url(raw_b64: str) -> str:
    raw_b64 = (raw_b64 or "").strip()
    if raw_b64.startswith("data:image/"):
        return raw_b64
    return f"data:image/jpeg;base64,{raw_b64}"


def _tail_frame_raw_b64(image_b64: str) -> str:
    image_b64 = (image_b64 or "").strip()
    if "," in image_b64 and image_b64.startswith("data:"):
        return image_b64.split(",", 1)[1]
    return image_b64


def _previous_tail_frame_manifest(
    *,
    filename: str,
    segment_index: int,
    source: str,
    saved_path: str = "",
    video_path: str = "",
) -> dict[str, str]:
    previous_segment = max(int(segment_index or 0) - 1, 0)
    return {
        "filename": filename,
        "role": PREVIOUS_SEGMENT_TAIL_FRAME_ROLE,
        "type": "continuity_reference",
        "asset_type": "continuity",
        "selected_by": "previous_continuity_asset_helper",
        "source": source,
        "source_video_path": video_path,
        "saved_path": saved_path,
        "previous_segment_index": str(previous_segment),
        "target_segment_index": str(segment_index or ""),
        "purpose": PREVIOUS_SEGMENT_TAIL_FRAME_PURPOSE,
    }


def _extract_tail_frame_data_from_video(video_path: str, segment_index: int) -> tuple[str | None, str | None]:
    if not video_path or not os.path.exists(video_path):
        return None, None
    cap = None
    try:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None

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
            return None, None

        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
        if not ok:
            return None, None

        encoded_bytes = encoded.tobytes()
        output_dir = os.path.join(OUTPUT_DIR, "auto_tail_frames")
        os.makedirs(output_dir, exist_ok=True)
        safe_stem = "".join(
            ch if ch.isalnum() or ch in "._-" else "_"
            for ch in os.path.splitext(os.path.basename(video_path))[0]
        ).strip("._") or "segment"
        frame_name = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
            f"seg{int(segment_index or 0):02d}_{safe_stem}_tail.jpg"
        )
        output_path = os.path.join(output_dir, frame_name)
        with open(output_path, "wb") as f:
            f.write(encoded_bytes)
        return base64.b64encode(encoded_bytes).decode("utf-8"), output_path
    except Exception as exc:
        print(f"  [Video] WARN: continuity tail frame extraction failed: {exc}")
        return None, None
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def _build_previous_segment_video_tail_frame_asset(video_path: str, segment_index: int) -> dict[str, Any] | None:
    """Extract and register metadata for the previous segment video tail frame."""
    raw_b64, saved_path = _extract_tail_frame_data_from_video(video_path, segment_index)
    if not raw_b64:
        return None

    saved_path = saved_path or ""
    filename = os.path.basename(saved_path or "") or f"seg{int(segment_index or 0):02d}_tail_frame.jpg"
    return {
        "source": "previous_segment_video_tail_frame",
        "raw_b64": raw_b64,
        "image_data_url": _tail_frame_data_url(raw_b64),
        "saved_path": saved_path,
        "filename": filename,
        "manifest_item": _previous_tail_frame_manifest(
            filename=filename,
            segment_index=segment_index,
            source="previous_segment_video_tail_frame",
            saved_path=saved_path,
            video_path=video_path,
        ),
    }


def _previous_storyboard_tail_placeholder(state: dict, segment_index: int) -> dict[str, Any] | None:
    previous_segment = int(segment_index or 0) - 1
    if previous_segment < 1:
        return None
    outputs = state.get("agent_outputs") or {}
    storyboard_images = state.get("storyboard_images_by_segment") or {}
    image_path = (
        storyboard_images.get(str(previous_segment))
        or outputs.get(f"storyboard_image_seg{previous_segment:02d}")
        or outputs.get(f"storyboard_image_seg{previous_segment}")
    )
    if not image_path:
        return None
    return {
        "source": "previous_storyboard_last_panel_placeholder",
        "previous_segment_index": previous_segment,
        "target_segment_index": segment_index,
        "storyboard_image_path": str(image_path),
        "todo": "Crop the previous storyboard last panel into a real continuity image asset.",
    }


def _previous_out_state_text(state: dict, segment_index: int) -> str:
    previous_segment = int(segment_index or 0) - 1
    if previous_segment < 1:
        return ""
    outputs = state.get("agent_outputs") or {}
    text = str(outputs.get(f"compiled_segment_{previous_segment}") or "").strip()
    if text:
        return text
    return str(state.get("tail_frame_analysis") or "").strip()


def _select_previous_continuity_asset(
    state: dict,
    *,
    segment_index: int,
    video_path: str | None = None,
    tail_frame_b64: str = "",
) -> dict[str, Any]:
    if video_path:
        video_asset = _build_previous_segment_video_tail_frame_asset(video_path, segment_index)
        if video_asset:
            return video_asset

    raw_tail_frame = _tail_frame_raw_b64(tail_frame_b64)
    if raw_tail_frame:
        filename = f"seg{int(segment_index or 0):02d}_provided_tail_frame.jpg"
        return {
            "source": "provided_tail_frame",
            "raw_b64": raw_tail_frame,
            "image_data_url": _tail_frame_data_url(raw_tail_frame),
            "filename": filename,
            "manifest_item": _previous_tail_frame_manifest(
                filename=filename,
                segment_index=segment_index,
                source="provided_tail_frame",
            ),
        }

    storyboard_placeholder = _previous_storyboard_tail_placeholder(state, segment_index)
    if storyboard_placeholder:
        return storyboard_placeholder

    out_state_text = _previous_out_state_text(state, segment_index)
    if out_state_text:
        return {
            "source": "previous_out_state_text",
            "previous_segment_index": int(segment_index or 0) - 1,
            "target_segment_index": segment_index,
            "out_state_text": out_state_text,
        }

    return {
        "source": "none",
        "previous_segment_index": int(segment_index or 0) - 1,
        "target_segment_index": segment_index,
    }


def _apply_previous_continuity_asset_to_state(state: dict, asset: dict[str, Any] | None) -> None:
    if not asset:
        return
    state["previous_continuity_asset"] = {
        key: value
        for key, value in asset.items()
        if key not in {"image_data_url", "raw_b64", "manifest_item"}
    }

    image_data_url = str(asset.get("image_data_url") or "")
    manifest_item = asset.get("manifest_item")
    if not image_data_url or not isinstance(manifest_item, dict):
        return

    images = list(state.get("reference_image_b64s") or [])
    manifest = [item if isinstance(item, dict) else {} for item in list(state.get("reference_image_manifest") or [])]
    while len(manifest) < len(images):
        manifest.append({})

    kept_images: list[str] = []
    kept_manifest: list[dict[str, Any]] = []
    for index, image in enumerate(images):
        item = manifest[index] if index < len(manifest) else {}
        role_text = " ".join(str(item.get(key) or "") for key in ("role", "type", "purpose", "source"))
        if PREVIOUS_SEGMENT_TAIL_FRAME_ROLE in role_text:
            continue
        kept_images.append(image)
        kept_manifest.append(item)

    new_manifest_item = dict(manifest_item)
    new_manifest_item["label"] = str(new_manifest_item.get("label") or f"@image{len(kept_images) + 1}")
    kept_images.append(image_data_url)
    kept_manifest.append(new_manifest_item)

    state["reference_image_b64s"] = kept_images
    state["reference_image_manifest"] = kept_manifest
    state["reference_image_count"] = len(kept_images)


def _run_pipeline_in_thread(
    script: str,
    aspect_ratio: str,
    reference_images: str,
    reference_image_b64s: list[str] | None = None,
    reference_image_manifest: list[dict[str, str]] | None = None,
    speed_mode: bool = True,
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
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
            }
            task_state.clear()
            task_state.update(_default_task_state())
            task_state.update(preserved_inputs)
            task_state["step"] = "step_0_scene"
            task_state["status"] = "running_phase_1"
            task_state["message"] = "📋 场景预分析正在读取参考图、人物站位和空间信息...（1/8）"
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
    continuity_asset: dict[str, Any] | None = None,
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
            _apply_previous_continuity_asset_to_state(task_state, continuity_asset)
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


def _resume_after_human_review_in_thread(
    edited_output: str,
    review_agent: str,
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
):
    """Resume the LangGraph pipeline after the user reviews an agent output."""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    started = time.perf_counter()
    _append_task_log(
        session_id,
        "resume_after_review_started",
        review_agent=review_agent,
        task_generation=task_generation,
        edited_chars=len(edited_output or ""),
    )
    try:
        with request_scope(session_id=session_id):
            if task_generation != _active_task_generation(session_id):
                _append_task_log(
                    session_id,
                    "resume_after_review_aborted_stale_generation",
                    task_generation=task_generation,
                    active_generation=_active_task_generation(session_id),
                )
                return
            task_state["status"] = "running_phase_1"
            if review_agent in {"prompt_compiler", "quality_inspector"}:
                task_state["status"] = "running_phase_2"
            task_state["message"] = "已接收修改内容，正在交给下一个 Agent..."
            task_state["error"] = ""
            _touch_task_progress(task_state)
            _append_task_log(session_id, "resume_after_review_state_running", **_state_log_summary(task_state))

            state = resume_after_human_review(edited_output, review_agent)
            if task_generation != _active_task_generation(session_id):
                _append_task_log(
                    session_id,
                    "resume_after_review_result_discarded_stale_generation",
                    task_generation=task_generation,
                    active_generation=_active_task_generation(session_id),
                )
                return
            task_state.update(state)
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)
            _append_task_log(
                session_id,
                "resume_after_review_finished",
                elapsed_seconds=round(time.perf_counter() - started, 3),
                **_state_log_summary(task_state),
            )
    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            _append_task_log(
                session_id,
                "resume_after_review_exception_stale_generation",
                error=str(e),
                traceback=traceback.format_exc(),
            )
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["message"] = f"人工审核继续失败: {str(e)}"
        task_state["error"] = traceback.format_exc()
        failure_text = f"{str(e)}\n{task_state['error']}"
        failed_step = {
            "scene_analyst": "step_0_scene",
            "director_showrunner": "step_0_enhance",
            "rhythm_rewrite_director": "step_0_rhythm",
            "story_planner": "step_2_plan",
            "shot_director": "step_3_direct",
            "storyboard_designer": "step_4_storyboard",
            "prompt_compiler": "step_5_compile",
            "quality_inspector": "step_6_inspect",
        }
        for agent_name, step_name in failed_step.items():
            if agent_name in failure_text:
                task_state["step"] = step_name
                break
        else:
            task_state["step"] = "error"
        _save_task_state_for_session(session_id, task_state)
        _append_task_log(
            session_id,
            "resume_after_review_failed",
            elapsed_seconds=round(time.perf_counter() - started, 3),
            error=str(e),
            traceback=task_state["error"],
            **_state_log_summary(task_state),
        )
    finally:
        _unregister_task_thread(session_id)


def _generate_storyboard_in_thread(
    segment_index: int,
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
):
    """Generate storyboard only for a single segment without compiling prompts."""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    try:
        with request_scope(session_id=session_id):
            if task_generation != _active_task_generation(session_id):
                return
            task_state["status"] = "running_phase_1"
            task_state["step"] = "step_4_storyboard"
            task_state["message"] = f"🎨 正在生成片段 {segment_index} 分镜流程图..."
            task_state["error"] = ""
            task_state["active_segment_index"] = segment_index
            task_state["current_segment_index"] = segment_index
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)

            latest_state = load_state() or {}
            merged_state = dict(latest_state)
            merged_state.update(task_state)
            result = generate_storyboard_for_segment(merged_state, segment_index=segment_index)

            refreshed = load_state() or {}
            task_state.update(refreshed)
            task_state["status"] = "waiting_for_user_input"
            task_state["step"] = "step_4_storyboard"
            task_state["message"] = f"🎨 片段 {segment_index} 分镜首帧提示词已生成，请审核后手动生成图片"
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)
    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["step"] = "error"
        task_state["message"] = f"🎨 分镜流程图生成失败: {str(e)}"
        task_state["error"] = traceback.format_exc()
        _save_task_state_for_session(session_id, task_state)
    finally:
        _unregister_task_thread(session_id)


def _generate_storyboard_image_in_thread(
    segment_index: int,
    task_generation: int = 0,
    session_id: str = DEFAULT_SESSION_ID,
):
    """Generate the storyboard image after the prompt has been reviewed."""
    session_id = _normalise_session_id(session_id)
    task_state = _task_state(session_id)
    try:
        with request_scope(session_id=session_id):
            if task_generation != _active_task_generation(session_id):
                return
            task_state["status"] = "running_phase_1"
            task_state["step"] = "step_4_storyboard"
            task_state["message"] = f"🎨 正在根据片段 {segment_index} 分镜提示词生成图片..."
            task_state["error"] = ""
            task_state["active_segment_index"] = segment_index
            task_state["current_segment_index"] = segment_index
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)

            latest_state = load_state() or {}
            merged_state = dict(latest_state)
            merged_state.update(task_state)
            result = generate_storyboard_image_for_segment(merged_state, segment_index=segment_index)

            refreshed = load_state() or {}
            task_state.update(refreshed)
            task_state["status"] = "waiting_for_user_input"
            task_state["step"] = "step_4_storyboard"
            task_state["message"] = f"🎨 片段 {segment_index} 分镜图片已生成"
            if result.get("image_path"):
                task_state["message"] += f"（图片：{result['image_path']}）"
            _touch_task_progress(task_state)
            _save_task_state_for_session(session_id, task_state)
    except Exception as e:
        if task_generation != _active_task_generation(session_id):
            return
        _merge_latest_disk_state_for_session(session_id, task_state)
        task_state["status"] = "error"
        task_state["step"] = "error"
        task_state["message"] = f"🎨 分镜图片生成失败: {str(e)}"
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

@app.post("/api/reference_library/auto_select")
async def auto_select_reference_library(
    script: str = Form(...),
    reference_image_manifest_json: str = Form(""),
):
    try:
        existing_manifest = _parse_reference_manifest(reference_image_manifest_json)
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)})
    matches = _build_auto_reference_matches(script, existing_manifest)
    return JSONResponse(
        {
            "success": True,
            "images": [
                {
                    "filename": item["filename"],
                    "asset_type": item["asset_type"],
                    "purpose": item["purpose"],
                    "matched_tokens": item["matched_tokens"],
                    "match_score": item["score"],
                }
                for item in matches
            ],
        }
    )

@app.get("/api/reference_library/{filename}")
async def get_reference_image(filename: str):
    """返回本地库中的指定参考图"""
    file_path = os.path.join(REFERENCE_IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        return JSONResponse({"success": False, "error": "文件不存在"}, status_code=404)
    return FileResponse(file_path)

@app.post("/api/run")
async def api_run(
    request: Request,
    script: str = Form(...),
    aspect_ratio: str = Form("16:9"),
    speed_mode: str = Form("false"),
    session_id: str = Form(DEFAULT_SESSION_ID),
    reference_images: str = Form(""),
    reference_image_manifest_json: str = Form(""),
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
        reference_manifest_overrides = _parse_reference_manifest(reference_image_manifest_json)
        reference_image_b64s, reference_image_manifest = await _read_reference_uploads(
            reference_image_files,
            reference_manifest_overrides,
        )
        auto_b64s, auto_manifest, auto_selected = _auto_select_reference_images(
            script,
            reference_image_manifest,
        )
        if auto_b64s:
            reference_image_b64s.extend(auto_b64s)
            reference_image_manifest.extend(auto_manifest)
            print(
                "  [AutoReference] selected "
                + ", ".join(str(item["filename"]) for item in auto_selected)
            )
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)})

    # 持久化用户输入（刷新页面后可恢复）。先重置整份会话状态，避免上一轮
    # active_segment_index / last_qc_status / tail_frame_analysis 等运行态残留。
    task_generation = _bump_task_generation(session_id)
    task_state.clear()
    task_state.update(_default_task_state())
    task_state["input_script"] = script
    task_state["input_aspect_ratio"] = aspect_ratio
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

    try:
        video_path = await _save_segment_video_upload(previous_video_file)
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)})
    continuity_asset = _select_previous_continuity_asset(
        task_state,
        segment_index=segment_index,
        video_path=video_path,
        tail_frame_b64=tail_frame_b64,
    )
    tail_frame_b64 = str(continuity_asset.get("raw_b64") or _tail_frame_raw_b64(tail_frame_b64) or "")

    task_generation = _bump_task_generation(session_id)
    now = _now_iso()
    task_state["status"] = "running_phase_2"
    task_state["step"] = "step_4_compile"
    task_state["message"] = f"✍️ Seedance编译师正在生成片段 {segment_index}..."
    task_state["error"] = ""
    task_state["current_segment_index"] = segment_index
    task_state["active_segment_index"] = segment_index
    task_state["started_at"] = now
    _apply_previous_continuity_asset_to_state(task_state, continuity_asset)
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
            continuity_asset,
        ),
        daemon=True
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": "已恢复执行编译步骤"})


@app.post("/api/approve_agent_output")
async def api_approve_agent_output(
    session_id: str = Form(DEFAULT_SESSION_ID),
    agent_name: str = Form(""),
    edited_output: str = Form(""),
):
    """Approve or edit the latest paused agent output, then feed it downstream."""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    _append_task_log(
        session_id,
        "approve_agent_output_request",
        requested_agent=agent_name,
        edited_chars=len(edited_output or ""),
        live_task=_has_live_task(session_id),
        **_state_log_summary(task_state),
    )

    if _has_live_task(session_id):
        _append_task_log(session_id, "approve_agent_output_rejected", reason="live_task")
        return JSONResponse({"success": False, "error": "已有任务正在执行，请等待当前步骤完成。"})
    has_review_payload = bool(task_state.get("review_agent") and task_state.get("review_output") is not None)
    is_agent_review = task_state.get("review_mode") == "agent_output" or has_review_payload
    can_resume_failed_review = task_state.get("status") == "error" and is_agent_review
    can_resume_idle_review = task_state.get("status") in {"idle", ""} and is_agent_review
    if task_state.get("status") != "waiting_for_user_input" and not can_resume_failed_review and not can_resume_idle_review:
        _append_task_log(session_id, "approve_agent_output_rejected", reason="not_waiting_for_review")
        return JSONResponse({"success": False, "error": "当前没有等待审核的 Agent 输出。"})
    if not is_agent_review:
        _append_task_log(session_id, "approve_agent_output_rejected", reason="not_agent_review")
        return JSONResponse({"success": False, "error": "当前没有等待审核的 Agent 输出。"})
    if can_resume_failed_review or can_resume_idle_review:
        task_state["status"] = "waiting_for_user_input"
        task_state["step"] = task_state.get("step") if task_state.get("step") != "error" else ""
        task_state["error"] = ""
        task_state["started_at"] = ""
        _touch_task_progress(task_state)
        _save_task_state_for_session(session_id, task_state)

    review_agent = (agent_name or task_state.get("review_agent") or "").strip()
    if not review_agent:
        _append_task_log(session_id, "approve_agent_output_rejected", reason="missing_review_agent")
        return JSONResponse({"success": False, "error": "缺少要审核的 Agent 名称。"})
    if task_state.get("review_mode") != "agent_output":
        task_state["review_mode"] = "agent_output"
        _save_task_state_for_session(session_id, task_state)

    restore_fields = {
        "status": task_state.get("status"),
        "step": task_state.get("step"),
        "message": task_state.get("message"),
        "error": task_state.get("error"),
        "started_at": task_state.get("started_at"),
        "review_mode": task_state.get("review_mode"),
        "review_agent": task_state.get("review_agent"),
        "review_title": task_state.get("review_title"),
        "review_output": task_state.get("review_output"),
    }
    try:
        task_generation = _bump_task_generation(session_id)
        now = _now_iso()
        task_state["status"] = "running_phase_1"
        if review_agent in {"prompt_compiler", "quality_inspector"}:
            task_state["status"] = "running_phase_2"
        task_state["message"] = "已收到修改内容，正在继续流水线..."
        task_state["error"] = ""
        task_state["started_at"] = now
        _touch_task_progress(task_state, now)
        _append_task_log(
            session_id,
            "approve_agent_output_accepted",
            approved_agent=review_agent,
            task_generation=task_generation,
            **_state_log_summary(task_state),
        )

        thread = threading.Thread(
            target=_resume_after_human_review_in_thread,
            args=(edited_output, review_agent, task_generation, session_id),
            daemon=True,
        )
        _register_task_thread(session_id, thread)
        thread.start()
        return JSONResponse({"success": True, "message": "已确认，正在继续执行。"})
    except Exception as exc:
        task_state.update({key: value for key, value in restore_fields.items() if value is not None})
        task_state["status"] = "waiting_for_user_input"
        task_state["review_mode"] = "agent_output"
        task_state["review_agent"] = review_agent
        task_state["review_output"] = edited_output
        task_state["message"] = f"确认失败: {type(exc).__name__}: {exc}"
        task_state["error"] = traceback.format_exc()
        _touch_task_progress(task_state)
        _save_task_state_for_session(session_id, task_state)
        _append_task_log(
            session_id,
            "approve_agent_output_failed_before_thread",
            failed_agent=review_agent,
            error=str(exc),
            traceback=task_state["error"],
            **_state_log_summary(task_state),
        )
        return JSONResponse(
            {"success": False, "error": task_state["message"]},
            status_code=500,
        )


@app.post("/api/rerun_phase1")
async def api_rerun_phase1(
    session_id: str = Form(DEFAULT_SESSION_ID),
    script: str = Form(""),
    agent_name: str = Form(""),
):
    """Restart the macro planning flow from saved inputs.

    This is intentionally coarse-grained: scene analysis, story enhancement,
    rhythm rewrite, and story planning are tightly coupled, so the safe rerun
    path is to restart Phase 1 with the current script and saved references.
    """
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "已有任务正在执行中，请等待当前步骤完成。"})

    disk_state = load_state() or {}
    source_script = (
        script.strip()
        or str(task_state.get("input_script") or "").strip()
        or str(disk_state.get("script") or "").strip()
        or str(disk_state.get("original_script") or "").strip()
    )
    if not source_script:
        return JSONResponse({"success": False, "error": "缺少剧本内容，无法重跑规划流程。"})

    aspect_ratio = (
        str(task_state.get("input_aspect_ratio") or "").strip()
        or str(disk_state.get("aspect_ratio") or "").strip()
        or "9:16"
    )
    reference_images = str(disk_state.get("reference_images") or task_state.get("reference_images") or "")
    reference_image_b64s = list(disk_state.get("reference_image_b64s") or task_state.get("reference_image_b64s") or [])
    reference_image_manifest = list(
        disk_state.get("reference_image_manifest")
        or task_state.get("reference_image_manifest")
        or []
    )
    speed_mode = bool(disk_state.get("speed_mode") or task_state.get("speed_mode"))

    task_generation = _bump_task_generation(session_id)
    task_state["input_script"] = source_script
    task_state["input_aspect_ratio"] = aspect_ratio
    task_state["status"] = "running_phase_1"
    task_state["step"] = "step_0_scene"
    task_state["message"] = (
        f"正在从场景预分析重新运行规划流程"
        f"{f'（由 {agent_name} 重跑触发）' if agent_name else ''}..."
    )
    task_state["error"] = ""
    task_state["started_at"] = _now_iso()
    _touch_task_progress(task_state, task_state["started_at"])
    _save_task_state_for_session(session_id, task_state)

    thread = threading.Thread(
        target=_run_pipeline_in_thread,
        args=(
            source_script,
            aspect_ratio,
            reference_images,
            reference_image_b64s,
            reference_image_manifest,
            speed_mode,
            task_generation,
            session_id,
        ),
        daemon=True,
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": "已从场景预分析重新启动规划流程。"})


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
        reference_images = str(disk_state.get("reference_images") or task_state.get("reference_images") or "")
        reference_image_b64s = list(disk_state.get("reference_image_b64s") or task_state.get("reference_image_b64s") or [])
        ref_manifest = list(disk_state.get("reference_image_manifest") or task_state.get("reference_image_manifest") or [])
        speed_mode = bool(task_state.get("speed_mode"))
        
        thread = threading.Thread(
            target=_run_pipeline_in_thread,
            args=(
                script.strip(),
                aspect_ratio,
                reference_images,
                reference_image_b64s,
                ref_manifest,
                speed_mode,
                task_generation,
                session_id,
            ),
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


@app.post("/api/generate_storyboard")
async def api_generate_storyboard(
    segment_index: int = Form(...),
    session_id: str = Form(DEFAULT_SESSION_ID),
):
    """Generate storyboard flowchart for the current segment only."""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "已有任务正在执行中，请等待当前步骤完成。"})

    outputs = task_state.get("agent_outputs") or {}
    if not outputs.get("shot_director"):
        return JSONResponse({"success": False, "error": "镜头导演输出尚未完成，无法生成分镜流程图。"})

    total_segments = int(task_state.get("total_segments") or 0)
    if segment_index < 1 or (total_segments and segment_index > total_segments):
        return JSONResponse({"success": False, "error": f"片段 {segment_index} 超出有效范围。"})

    task_generation = _bump_task_generation(session_id)
    now = _now_iso()
    task_state["status"] = "running_phase_1"
    task_state["step"] = "step_4_storyboard"
    task_state["message"] = f"🎨 正在生成片段 {segment_index} 分镜流程图..."
    task_state["error"] = ""
    task_state["active_segment_index"] = segment_index
    task_state["current_segment_index"] = segment_index
    task_state["started_at"] = now
    _touch_task_progress(task_state, now)
    _save_task_state_for_session(session_id, task_state)

    thread = threading.Thread(
        target=_generate_storyboard_in_thread,
        args=(segment_index, task_generation, session_id),
        daemon=True,
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": f"🎨 片段 {segment_index} 分镜流程图已加入队列。"})


@app.post("/api/generate_storyboard_image")
async def api_generate_storyboard_image(
    segment_index: int = Form(...),
    session_id: str = Form(DEFAULT_SESSION_ID),
):
    """Generate storyboard image from an already-reviewed storyboard prompt."""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "已有任务正在执行中，请等待当前步骤完成。"})

    outputs = task_state.get("agent_outputs") or {}
    prompt = (
        outputs.get(f"storyboard_prompt_seg{segment_index:02d}")
        or outputs.get(f"storyboard_prompt_seg{segment_index}")
        or outputs.get("storyboard_designer")
    )
    if not prompt:
        return JSONResponse({"success": False, "error": "请先生成并审核分镜首帧提示词，再生成图片。"})

    total_segments = int(task_state.get("total_segments") or 0)
    if segment_index < 1 or (total_segments and segment_index > total_segments):
        return JSONResponse({"success": False, "error": f"片段 {segment_index} 超出有效范围。"})

    task_generation = _bump_task_generation(session_id)
    now = _now_iso()
    task_state["status"] = "running_phase_1"
    task_state["step"] = "step_4_storyboard"
    task_state["message"] = f"🎨 正在根据片段 {segment_index} 分镜提示词生成图片..."
    task_state["error"] = ""
    task_state["active_segment_index"] = segment_index
    task_state["current_segment_index"] = segment_index
    task_state["started_at"] = now
    _touch_task_progress(task_state, now)
    _save_task_state_for_session(session_id, task_state)

    thread = threading.Thread(
        target=_generate_storyboard_image_in_thread,
        args=(segment_index, task_generation, session_id),
        daemon=True,
    )
    _register_task_thread(session_id, thread)
    thread.start()
    return JSONResponse({"success": True, "message": f"🎨 片段 {segment_index} 分镜图片已加入队列。"})


@app.post("/api/save_storyboard_prompt")
async def api_save_storyboard_prompt(
    segment_index: int = Form(...),
    session_id: str = Form(DEFAULT_SESSION_ID),
    edited_output: str = Form(""),
):
    """Save edited storyboard image prompt without advancing the graph."""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    task_state = _task_state(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "已有任务正在执行中，请等待当前步骤完成。"})
    if segment_index < 1:
        return JSONResponse({"success": False, "error": "片段编号必须 >= 1。"})

    prompt = (edited_output or "").strip()
    if not prompt:
        return JSONResponse({"success": False, "error": "分镜生图提示词不能为空。"})

    outputs = dict(task_state.get("agent_outputs") or {})
    outputs[f"storyboard_prompt_seg{segment_index:02d}"] = prompt
    task_state["agent_outputs"] = outputs
    task_state["review_mode"] = "agent_output"
    task_state["review_agent"] = "storyboard_designer"
    task_state["review_title"] = "分镜流程图"
    task_state["review_output"] = prompt
    task_state["status"] = "waiting_for_user_input"
    task_state["step"] = "step_4_storyboard"
    task_state["message"] = "分镜生图提示词已保存，可以生成图片。"
    task_state["error"] = ""
    _touch_task_progress(task_state)
    _save_task_state_for_session(session_id, task_state)
    return JSONResponse({"success": True, "message": "分镜生图提示词已保存。"})


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


@app.post("/api/regenerate_scene_card")
async def api_regenerate_scene_card(
    scene_number: int = Form(...),
    session_id: str = Form(DEFAULT_SESSION_ID),
):
    """Regenerate one scene layout image and one 3x3 scene grid from its reference image."""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "当前流水线正在运行，不能同时重跑场景参考图。"})

    task_state = _task_state(session_id)
    scene_items = scene_card_impl._scene_reference_items(task_state)
    if scene_number < 1 or scene_number > len(scene_items):
        return JSONResponse(
            {
                "success": False,
                "error": f"场景编号 {scene_number} 不存在，当前可重跑 {len(scene_items)} 张场景参考图。",
            }
        )

    outputs = task_state.setdefault("agent_outputs", {})
    scene_output = str(outputs.get("scene_analyst") or task_state.get("scene_context_brief") or "")
    scene_output = re.split(r"\n\n(?:场景母版图|场景参考图):\s*\|", scene_output, maxsplit=1)[0]
    scene_item = scene_items[scene_number - 1]
    total_scenes = len(scene_items)
    scene_title = scene_card_impl._scene_reference_title(scene_item, scene_number)

    try:
        overhead_prompt = scene_card_impl._build_scene_card_overhead_prompt(
            task_state,
            scene_output,
            scene_item=scene_item,
            scene_number=scene_number,
            total_scenes=total_scenes,
        )
        prompt = scene_card_impl._build_scene_card_image_prompt(
            task_state,
            scene_output,
            scene_item=scene_item,
            scene_number=scene_number,
            total_scenes=total_scenes,
        )
        image_result, overhead_path = scene_card_impl._generate_scene_card_with_overhead(
            overhead_prompt,
            prompt,
            scene_item["image"],
            session_id,
            scene_number,
        )
        image_path = scene_card_impl._save_scene_card_image(image_result, session_id, scene_number)
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"重跑场景参考图失败：{type(exc).__name__}: {exc}"})

    existing_cards: list[dict[str, str]] = []
    if outputs.get("scene_card_images"):
        try:
            parsed = (
                json.loads(outputs["scene_card_images"])
                if isinstance(outputs["scene_card_images"], str)
                else outputs["scene_card_images"]
            )
            if isinstance(parsed, list):
                existing_cards = [dict(item) for item in parsed if isinstance(item, dict)]
        except Exception:
            existing_cards = []

    new_card = {
        "scene_number": str(scene_number),
        "scene_title": scene_title,
        "image_path": image_path,
        "grid_path": image_path,
        "layout_path": overhead_path,
        "layout_prompt": overhead_prompt,
        "prompt": prompt,
        "grid_prompt": prompt,
        "source_index": str(scene_item.get("source_index", scene_number - 1)),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    card_map = {str(card.get("scene_number") or index + 1): card for index, card in enumerate(existing_cards)}
    card_map[str(scene_number)] = new_card
    scene_cards = [card_map[str(index)] for index in range(1, total_scenes + 1) if str(index) in card_map]

    outputs["scene_card_images"] = json.dumps(scene_cards, ensure_ascii=False)
    if scene_number == 1 or not outputs.get("scene_card_image"):
        outputs["scene_card_prompt"] = prompt
        outputs["scene_card_image"] = image_path
        outputs["scene_layout_prompt"] = overhead_prompt
        outputs["scene_layout_image"] = overhead_path
        outputs["scene_grid_prompt"] = prompt
        outputs["scene_grid_image"] = image_path

    updated_images, updated_manifest = scene_card_impl._append_scene_card_references(task_state, scene_cards)
    task_state["reference_image_b64s"] = updated_images
    task_state["reference_image_manifest"] = updated_manifest
    task_state["reference_image_count"] = len(updated_images)
    task_state["agent_outputs"] = outputs
    task_state["message"] = f"场景{scene_number}俯视图和九宫格图已重新生成。"
    task_state["error"] = ""

    with request_scope(session_id=session_id):
        save_state(task_state)

    return JSONResponse(
        {
            "success": True,
            "message": task_state["message"],
            "scene_card": new_card,
            "state": _public_task_state(session_id),
        }
    )


@app.post("/api/save_scene_layout_annotations")
async def api_save_scene_layout_annotations(
    annotations_json: str = Form("[]"),
    session_id: str = Form(DEFAULT_SESSION_ID),
):
    """Persist user-drawn scene-layout markers/routes for downstream shot direction."""
    session_id = _normalise_session_id(session_id)
    _refresh_task_state_from_disk(session_id)
    if _has_live_task(session_id):
        return JSONResponse({"success": False, "error": "当前流水线正在运行，不能保存场景标注。"})

    try:
        parsed = json.loads(annotations_json or "[]")
    except json.JSONDecodeError:
        return JSONResponse({"success": False, "error": "场景标注数据不是有效 JSON。"})
    if not isinstance(parsed, list):
        return JSONResponse({"success": False, "error": "场景标注数据必须是列表。"})

    task_state = _task_state(session_id)
    saved_count = _upsert_scene_layout_annotations(task_state, parsed)
    task_state["message"] = (
        f"已保存 {saved_count} 张俯视图的人物标点和活动轨迹，镜头导演会作为空间调度参考。"
        if saved_count
        else "当前俯视图没有可保存的人物标点或活动轨迹。"
    )
    task_state["error"] = ""
    _touch_task_progress(task_state)

    with request_scope(session_id=session_id):
        save_state(task_state)

    return JSONResponse(
        {
            "success": True,
            "message": task_state["message"],
            "saved_count": saved_count,
            "state": _public_task_state(session_id),
        }
    )


@app.get("/api/storyboard_image")
async def api_storyboard_image(path: str = ""):
    """返回分镜流程图图片文件"""
    if not path:
        return JSONResponse({"success": False, "error": "缺少路径参数"}, status_code=400)

    requested_path = os.path.abspath(os.path.normpath(path))
    output_root = os.path.abspath(OUTPUT_DIR)
    legacy_storyboard_dir = os.path.join(output_root, "storyboards")
    session_root = os.path.join(output_root, "sessions")

    def _is_under(child: str, parent: str) -> bool:
        try:
            return os.path.commonpath([child, parent]) == parent
        except ValueError:
            return False

    # 安全检查：只允许访问 output/storyboards、output/sessions/*/storyboards
    # 或 output/sessions/*/scene_cards 下的图片。
    under_legacy_storyboards = _is_under(requested_path, legacy_storyboard_dir)
    under_session_storyboards = (
        _is_under(requested_path, session_root)
        and "storyboards" in set(os.path.normpath(requested_path).split(os.sep))
    )
    under_session_scene_cards = (
        _is_under(requested_path, session_root)
        and "scene_cards" in set(os.path.normpath(requested_path).split(os.sep))
    )
    if not (under_legacy_storyboards or under_session_storyboards or under_session_scene_cards):
        return JSONResponse({"success": False, "error": "非法路径"}, status_code=403)
    if not requested_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return JSONResponse({"success": False, "error": "只允许访问图片文件"}, status_code=403)
    if not os.path.exists(requested_path):
        return JSONResponse({"success": False, "error": "文件不存在"}, status_code=404)
    return FileResponse(requested_path)


@app.get("/api/config")
async def api_get_config():
    config = _public_model_config()
    return JSONResponse(config)


def _load_raw_settings() -> dict:
    config_path = get_config_path()
    try:
        with open(config_path, "r", encoding="utf-8-sig") as file:
            data = yaml.safe_load(file) or {}
    except FileNotFoundError:
        data = {}
    except yaml.YAMLError as exc:
        raise ValueError(f"配置文件 YAML 解析失败：{exc}") from exc
    return data if isinstance(data, dict) else {}


def _config_source_summary() -> dict:
    active_path = os.path.abspath(get_config_path())
    public_path = os.path.abspath(get_public_config_path())
    root_dir = os.path.abspath(ROOT_DIR)

    def _display_path(path: str) -> str:
        try:
            return os.path.relpath(path, root_dir)
        except ValueError:
            return path

    return {
        "active_path": active_path,
        "active_display": _display_path(active_path),
        "public_display": _display_path(public_path),
        "is_private": False,
        "message": "当前实际生效配置只读取前端保存的 config/settings.yaml。",
    }


def _save_raw_settings(config: dict) -> None:
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)


def _mask_config_key(section: dict) -> dict:
    result = dict(section or {})
    api_key = str(result.get("api_key") or "").strip()
    result["api_key"] = ""
    result["has_api_key"] = bool(api_key) and not _looks_like_env_placeholder(api_key)
    return result


def _looks_like_env_placeholder(value: str) -> bool:
    text = str(value or "").strip()
    return bool(re.fullmatch(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}", text) or re.fullmatch(r"%[A-Za-z_][A-Za-z0-9_]*%", text))


AGENT_LABELS: dict[str, str] = {
    "director_showrunner": "剧情增强",
    "rhythm_rewrite_director": "节奏总控",
    "scene_analyst": "场景预分析",
    "scene_vision_analyst": "场景视觉分析",
    "scene_card_designer": "场景俯视/九宫格生图",
    "story_planner": "拆片规划",
    "shot_director": "三段镜头导演",
    "prompt_compiler": "Seedance 编译",
    "quality_inspector": "质检报告",
    "storyboard_prompt_designer": "分镜提示词",
    "storyboard_designer": "分镜图片生成",
    "video_analyst": "视频/尾帧分析",
    "script_event_validator": "剧本事件校验",
}

AGENT_CATEGORIES: dict[str, str] = {
    "scene_vision_analyst": "vision",
    "video_analyst": "vision",
    "scene_card_designer": "image",
    "storyboard_designer": "image",
}

AGENT_MODEL_UI_NAMES: tuple[str, ...] = (
    "director_showrunner",
    "rhythm_rewrite_director",
    "scene_analyst",
    "story_planner",
    "shot_director",
    "prompt_compiler",
    "quality_inspector",
    "storyboard_designer",
)

MODEL_PROFILE_LABELS: dict[str, str] = {
    "text": "文本/视觉 Agent",
    "image": "生图 Agent",
    "embedding": "向量嵌入",
}


REMOVED_AGENT_MODEL_NAMES: set[str] = {
    "quality_inspector_llm_a",
    "quality_inspector_llm_b",
    "quality_inspector_llm_c",
    "quality_inspector_merger",
}

DERIVED_AGENT_MODEL_SOURCES: dict[str, str] = {
    "scene_vision_analyst": "scene_analyst",
    "video_analyst": "scene_analyst",
    "scene_card_designer": "storyboard_designer",
    "storyboard_prompt_designer": "prompt_compiler",
    "script_event_validator": "story_planner",
    "shot_director_layout": "shot_director",
    "shot_director_blocking": "shot_director",
    "shot_director_guard": "shot_director",
}


def _is_removed_agent_model(agent_name: str) -> bool:
    return str(agent_name) in REMOVED_AGENT_MODEL_NAMES


def _is_configurable_agent_model(agent_name: str) -> bool:
    name = str(agent_name)
    return name in AGENT_MODEL_UI_NAMES and not _is_removed_agent_model(name)


def _configured_agent_model_names(raw_config: dict) -> list[str]:
    agent_models = raw_config.get("agent_models") or {}
    if not isinstance(agent_models, dict):
        return []
    configured_names = {str(name) for name in agent_models}
    return [name for name in AGENT_MODEL_UI_NAMES if name in configured_names and _is_configurable_agent_model(name)]


def _agent_category(agent_name: str) -> str:
    return AGENT_CATEGORIES.get(agent_name, "text")


def _first_agent_config(raw_config: dict, category: str) -> dict:
    agent_models = raw_config.get("agent_models") or {}
    if not isinstance(agent_models, dict):
        return {}
    for agent_name, agent_config in agent_models.items():
        if _agent_category(str(agent_name)) == category and isinstance(agent_config, dict):
            return agent_config
    return {}


def _profile_source(raw_config: dict, profile: str) -> dict:
    if profile == "image":
        image_config = raw_config.get("image_generation")
        if isinstance(image_config, dict):
            return image_config
        return _first_agent_config(raw_config, "image")
    if profile == "embedding":
        vectordb_config = raw_config.get("vectordb")
        return vectordb_config if isinstance(vectordb_config, dict) else {}
    llm_config = raw_config.get("llm")
    return llm_config if isinstance(llm_config, dict) else {}


def _public_model_profiles(raw_config: dict) -> dict:
    profiles: dict[str, dict] = {}
    for profile, label in MODEL_PROFILE_LABELS.items():
        source = _profile_source(raw_config, profile)
        masked = _mask_config_key(source)
        masked["label"] = label
        profiles[profile] = masked
    if not profiles["image"].get("base_url"):
        profiles["image"]["base_url"] = COMFLY_BASE_URL
    return profiles


def _safe_knowledge_index_status() -> dict:
    try:
        return knowledge_index_status()
    except Exception as exc:
        return {
            "status": "error",
            "needs_rebuild": True,
            "message": f"知识库状态读取失败: {exc}",
            "error": str(exc),
        }


def _model_groups(models: list[str]) -> dict[str, list[str]]:
    def has_any(model: str, markers: tuple[str, ...]) -> bool:
        lower = model.lower()
        return any(marker in lower for marker in markers)

    embedding_markers = ("embed", "embedding", "bge", "text-embedding")
    image_markers = (
        "image", "gpt-image", "dall-e", "dalle", "flux", "midjourney", "mj-",
        "stable-diffusion", "sdxl", "seedream", "jimeng", "ideogram",
    )
    vision_markers = (
        "vision", "vl", "qwen-vl", "glm-4v", "gpt-4o", "gpt-5", "claude",
        "gemini", "moonshot-vision", "omni", "multimodal",
    )
    groups = {
        "text": [],
        "vision": [],
        "image": [],
        "embedding": [],
    }
    for model in models:
        if has_any(model, embedding_markers):
            groups["embedding"].append(model)
        elif has_any(model, image_markers):
            groups["image"].append(model)
        else:
            groups["text"].append(model)
            if has_any(model, vision_markers):
                groups["vision"].append(model)
    if not groups["vision"]:
        groups["vision"] = list(groups["text"])
    return groups


def _public_model_config() -> dict:
    raw_config = _load_raw_settings()
    public_config = copy.deepcopy(raw_config)
    public_config["llm"] = _mask_config_key(public_config.get("llm") or {})
    public_config["vectordb"] = _mask_config_key(public_config.get("vectordb") or {})
    public_config["image_generation"] = _mask_config_key(public_config.get("image_generation") or _profile_source(raw_config, "image"))
    agent_models = public_config.get("agent_models")
    if isinstance(agent_models, dict):
        for agent_name in list(agent_models.keys()):
            if not _is_configurable_agent_model(str(agent_name)):
                agent_models.pop(agent_name, None)
                continue
            agent_config = agent_models[agent_name]
            if isinstance(agent_config, dict):
                masked = _mask_config_key(agent_config)
                agent_config.clear()
                agent_config.update(masked)
    else:
        public_config["agent_models"] = {}
    public_config["_config_locked"] = False
    public_config["_config_note"] = "模型配置只以前端保存到 config/settings.yaml 的内容为准。"
    public_config["_config_source"] = _config_source_summary()
    public_agent_names = _configured_agent_model_names(public_config)
    public_config["_agent_order"] = public_agent_names
    public_config["_agent_labels"] = {name: AGENT_LABELS.get(name, name) for name in public_agent_names}
    public_config["_agent_categories"] = {name: _agent_category(name) for name in public_agent_names}
    public_config["_model_profiles"] = _public_model_profiles(raw_config)
    public_config["_knowledge_index"] = _safe_knowledge_index_status()
    return public_config


def _normalise_config_base_url(value: str) -> str:
    base_url = str(value or "").strip()
    if not base_url:
        raise ValueError("中转站地址不能为空。")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url
    return base_url.rstrip("/")


def _model_list_candidate_urls(base_url: str) -> list[str]:
    base_url = base_url.rstrip("/")
    urls = [f"{base_url}/models"]
    if not base_url.lower().endswith("/v1"):
        urls.append(f"{base_url}/v1/models")
    return urls


def _model_list_client_modes() -> tuple[tuple[bool, str], ...]:
    return (
        (False, "直连/绕开环境代理"),
        (True, "系统环境代理"),
    )


def _model_list_network_hint(base_url: str) -> str:
    host = urlparse(base_url).hostname
    if not host:
        return ""
    try:
        resolved_ips = {
            item[4][0]
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            if item and item[4]
        }
    except OSError:
        return ""
    fake_ip_network = ipaddress.ip_network("198.18.0.0/15")
    fake_ips = []
    for ip_text in sorted(resolved_ips):
        try:
            if ipaddress.ip_address(ip_text) in fake_ip_network:
                fake_ips.append(ip_text)
        except ValueError:
            continue
    if not fake_ips:
        return ""
    return (
        f"诊断提示：{host} 当前解析到 {', '.join(fake_ips)}，这是 Mihomo/Clash fake-ip 保留网段。"
        "说明 VPN/TUN 正在接管该域名；如果直连和系统代理都失败，需要在 VPN 里给该域名切换可用节点或直连规则，"
        "并确认中转站 Base URL 是供应商提供的真实 API 域名。"
    )


def _model_response_preview(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "").split(";", 1)[0] or "unknown"
    body = response.text.strip().replace("\r", " ").replace("\n", " ")
    if len(body) > 300:
        body = body[:300] + "..."
    return f"Content-Type {content_type}, body: {body or '<empty>'}"


def _extract_model_ids(raw_models: object) -> list[str]:
    models: list[str] = []
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("name")
            else:
                model_id = item
            model_id = str(model_id or "").strip()
            if model_id:
                models.append(model_id)
    return sorted(set(models), key=lambda item: item.lower())


def _normalise_optional_model(value: object) -> str:
    return str(value or "").strip()


@app.post("/api/model_list")
async def api_model_list(request: Request):
    if not _is_local_request(request):
        return JSONResponse({"success": False, "error": "模型列表仅允许本机管理员拉取。"}, status_code=403)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    raw_config = _load_raw_settings()
    profile = str(payload.get("profile") or "text").strip() or "text"
    if profile not in MODEL_PROFILE_LABELS:
        profile = "text"
    try:
        base_url = _normalise_config_base_url(str(payload.get("base_url") or _profile_source(raw_config, profile).get("base_url") or ""))
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    api_key = str(payload.get("api_key") or "").strip()
    if not api_key or api_key == "***":
        api_key = str(_profile_source(raw_config, profile).get("api_key") or "").strip()
    if _looks_like_env_placeholder(api_key):
        api_key = ""
    if not api_key:
        return JSONResponse({"success": False, "error": "请先填写 API Key，再拉取模型列表。"}, status_code=400)

    models: list[str] = []
    parsed_model_list = False
    proxy_mode = ""
    errors: list[str] = []
    try:
        candidate_urls = _model_list_candidate_urls(base_url)
        for trust_env, current_proxy_mode in _model_list_client_modes():
            with httpx.Client(
                timeout=httpx.Timeout(30.0, connect=10.0),
                trust_env=trust_env,
            ) as client:
                for url in candidate_urls:
                    try:
                        resp = client.get(
                            url,
                            headers={"Authorization": f"Bearer {api_key}"},
                        )
                    except httpx.HTTPError as exc:
                        errors.append(f"{url} 请求失败（{current_proxy_mode}）：{type(exc).__name__}: {exc}")
                        continue
                    if resp.status_code >= 400:
                        errors.append(f"{url} 返回 HTTP {resp.status_code}（{current_proxy_mode}）: {resp.text[:500]}")
                        continue
                    try:
                        data = resp.json()
                    except ValueError:
                        errors.append(f"{url} 返回的不是合法 JSON（{current_proxy_mode}，{_model_response_preview(resp)}）")
                        continue
                    raw_models = data.get("data") if isinstance(data, dict) else data
                    if not isinstance(raw_models, list):
                        errors.append(f"{url} JSON 中没有 data 模型数组（{current_proxy_mode}）。")
                        continue
                    models = _extract_model_ids(raw_models)
                    parsed_model_list = True
                    proxy_mode = current_proxy_mode
                    break
            if parsed_model_list:
                break
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"拉取模型列表失败：{type(exc).__name__}: {exc}"}, status_code=500)
    if not parsed_model_list:
        hint = _model_list_network_hint(base_url)
        if hint:
            errors.append(hint)
        return JSONResponse({"success": False, "error": "拉取模型列表失败：" + "；".join(errors)}, status_code=502)

    groups = _model_groups(models)
    return JSONResponse({
        "success": True,
        "profile": profile,
        "models": models,
        "groups": groups,
        "embedding_models": groups["embedding"],
        "image_models": groups["image"],
        "vision_models": groups["vision"],
        "proxy_mode": proxy_mode,
    })


def _resolve_saved_api_key(raw_config: dict, profile: str, submitted_key: str, fallback_key: str = "") -> str:
    submitted_key = str(submitted_key or "").strip()
    if submitted_key and submitted_key != "***":
        return submitted_key
    existing_key = str(_profile_source(raw_config, profile).get("api_key") or "").strip()
    if _looks_like_env_placeholder(existing_key):
        expanded = os.path.expandvars(existing_key).strip()
        existing_key = "" if expanded == existing_key else expanded
    return existing_key or fallback_key


def _ensure_config_section(raw_config: dict, section_name: str) -> dict:
    section = raw_config.setdefault(section_name, {})
    if not isinstance(section, dict):
        section = {}
        raw_config[section_name] = section
    return section


def _write_profile_credentials(section: dict, api_key: str, base_url: str) -> None:
    section["api_key"] = api_key
    section["base_url"] = base_url


def _agent_connection_preview(response: httpx.Response) -> str:
    body = response.text.strip().replace("\r", " ").replace("\n", " ")
    if len(body) > 260:
        body = body[:260] + "..."
    return body or response.reason_phrase or "empty response"


async def _probe_agent_connection(
    *,
    agent_name: str,
    label: str,
    category: str,
    base_url: str,
    api_key: str,
    model: str,
) -> dict:
    started = perf_counter()
    result = {
        "agent": agent_name,
        "label": label,
        "category": category,
        "base_url": base_url,
        "model": model,
        "success": False,
        "latency_ms": None,
        "message": "",
    }
    if not base_url:
        result["message"] = "缺少 Base URL"
        return result
    if not api_key:
        result["message"] = "缺少 API Key"
        return result
    if not model:
        result["message"] = "未选择模型"
        return result

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是连通性测试端点，只需回复 OK。"},
            {"role": "user", "content": f"测试 {label} ({agent_name}) 的模型连通性，请只回复 OK。"},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(20.0, connect=8.0, read=20.0, write=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            response = await client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        if response.status_code >= 400:
            result["message"] = f"HTTP {response.status_code}: {_agent_connection_preview(response)}"
            return result
        try:
            data = response.json()
        except ValueError:
            result["message"] = f"返回非 JSON: {_agent_connection_preview(response)}"
            return result
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            result["message"] = "响应缺少 choices 字段"
            return result
        result["success"] = True
        result["message"] = "连接正常"
        return result
    except httpx.TimeoutException as exc:
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        result["message"] = f"请求超时: {type(exc).__name__}"
        return result
    except httpx.HTTPError as exc:
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        result["message"] = f"请求失败: {type(exc).__name__}: {exc}"
        return result
    except Exception as exc:
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        result["message"] = f"测试异常: {type(exc).__name__}: {exc}"
        return result


async def _probe_embedding_connection(*, base_url: str, api_key: str, model: str) -> dict:
    started = perf_counter()
    result = {
        "agent": "embedding",
        "label": "向量嵌入",
        "category": "embedding",
        "base_url": base_url,
        "model": model,
        "success": False,
        "latency_ms": None,
        "message": "",
    }
    if not base_url:
        result["message"] = "缺少 Base URL"
        return result
    if not api_key:
        result["message"] = "缺少 API Key"
        return result
    if not model:
        result["message"] = "未选择 Embedding 模型"
        return result

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": "connection probe",
    }
    timeout = httpx.Timeout(20.0, connect=8.0, read=20.0, write=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            response = await client.post(f"{base_url.rstrip('/')}/embeddings", headers=headers, json=payload)
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        if response.status_code >= 400:
            result["message"] = f"HTTP {response.status_code}: {_agent_connection_preview(response)}"
            return result
        try:
            data = response.json()
        except ValueError:
            result["message"] = f"返回非 JSON: {_agent_connection_preview(response)}"
            return result
        embeddings = data.get("data") if isinstance(data, dict) else None
        if not isinstance(embeddings, list) or not embeddings:
            result["message"] = "响应缺少 data 字段"
            return result
        result["success"] = True
        result["message"] = "连接正常"
        return result
    except httpx.TimeoutException as exc:
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        result["message"] = f"请求超时: {type(exc).__name__}"
        return result
    except httpx.HTTPError as exc:
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        result["message"] = f"请求失败: {type(exc).__name__}: {exc}"
        return result
    except Exception as exc:
        result["latency_ms"] = round((perf_counter() - started) * 1000)
        result["message"] = f"测试异常: {type(exc).__name__}: {exc}"
        return result


@app.post("/api/config")
async def api_save_config(request: Request):
    if not _is_local_request(request):
        return JSONResponse({"success": False, "error": "系统配置仅允许本机管理员保存。"}, status_code=403)
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"配置请求不是合法 JSON：{exc}"}, status_code=400)

    try:
        raw_config = _load_raw_settings()
        text_base_url = _normalise_config_base_url(
            str(payload.get("text_base_url") or payload.get("base_url") or _profile_source(raw_config, "text").get("base_url") or "")
        )
        image_base_url = _normalise_config_base_url(
            str(payload.get("image_base_url") or _profile_source(raw_config, "image").get("base_url") or text_base_url)
        )
        embedding_base_url = _normalise_config_base_url(
            str(payload.get("embedding_base_url") or _profile_source(raw_config, "embedding").get("base_url") or text_base_url)
        )
        text_api_key = str(payload.get("text_api_key") or payload.get("api_key") or "").strip()
        image_api_key = str(payload.get("image_api_key") or "").strip()
        embedding_api_key = str(payload.get("embedding_api_key") or "").strip()
        default_model = _normalise_optional_model(payload.get("default_model"))
        embedding_model = _normalise_optional_model(payload.get("embedding_model"))
        agent_models_payload = payload.get("agent_models") or {}
        if not isinstance(agent_models_payload, dict):
            raise ValueError("agent_models 必须是对象。")
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    text_key = _resolve_saved_api_key(raw_config, "text", text_api_key)
    image_key = _resolve_saved_api_key(raw_config, "image", image_api_key, fallback_key=text_key)
    embedding_key = _resolve_saved_api_key(raw_config, "embedding", embedding_api_key, fallback_key=text_key)
    missing_profiles = [
        MODEL_PROFILE_LABELS[profile]
        for profile, key in (("text", text_key), ("image", image_key), ("embedding", embedding_key))
        if not key
    ]
    if missing_profiles:
        return JSONResponse({"success": False, "error": "API Key 不能为空：" + "、".join(missing_profiles)}, status_code=400)

    llm_config = _ensure_config_section(raw_config, "llm")
    _write_profile_credentials(llm_config, text_key, text_base_url)
    if default_model:
        llm_config["model"] = default_model

    image_config = _ensure_config_section(raw_config, "image_generation")
    _write_profile_credentials(image_config, image_key, image_base_url)

    vectordb_config = _ensure_config_section(raw_config, "vectordb")
    _write_profile_credentials(vectordb_config, embedding_key, embedding_base_url)
    if embedding_model:
        vectordb_config["embedding_model"] = embedding_model

    existing_agent_models = _ensure_config_section(raw_config, "agent_models")
    previous_agent_models = {
        str(name): dict(value)
        for name, value in existing_agent_models.items()
        if isinstance(value, dict)
    }
    agent_models: dict[str, dict] = {}
    raw_config["agent_models"] = agent_models

    known_agents = {
        str(name)
        for name in AGENT_MODEL_UI_NAMES
        if _is_configurable_agent_model(str(name))
    }
    agent_order = {name: index for index, name in enumerate(AGENT_MODEL_UI_NAMES)}
    selected_models: dict[str, str] = {}

    def write_agent_config(agent_name: str, selected_model: str, category: str) -> None:
        agent_config = dict(previous_agent_models.get(agent_name) or {})
        agent_config.pop("model", None)
        agent_config.pop("fallback_models", None)
        agent_config.pop("default_model", None)
        if _agent_category(agent_name) == "image":
            _write_profile_credentials(agent_config, image_key, image_base_url)
        else:
            _write_profile_credentials(agent_config, text_key, text_base_url)
        if selected_model:
            agent_config["model"] = selected_model
        if category == "image" and selected_model:
            image_config["model"] = selected_model
        agent_models[agent_name] = agent_config

    for agent_name in sorted(known_agents, key=lambda name: agent_order.get(name, len(agent_order))):
        selected_model = _normalise_optional_model(
            agent_models_payload.get(agent_name) or previous_agent_models.get(agent_name, {}).get("model")
        )
        selected_models[agent_name] = selected_model
        write_agent_config(agent_name, selected_model, _agent_category(agent_name))

    for derived_agent, source_agent in DERIVED_AGENT_MODEL_SOURCES.items():
        if source_agent not in selected_models:
            continue
        source_category = _agent_category(source_agent)
        write_agent_config(derived_agent, selected_models[source_agent], source_category)

    try:
        _save_raw_settings(raw_config)
    except OSError as exc:
        return JSONResponse({"success": False, "error": f"保存配置失败：{exc}"}, status_code=500)

    return JSONResponse({"success": True, "message": "系统配置已保存。", "config": _public_model_config()})


@app.post("/api/test_agent_connections")
async def api_test_agent_connections(request: Request):
    if not _is_local_request(request):
        return JSONResponse({"success": False, "error": "Agent 连通性测试仅允许本机管理员执行。"}, status_code=403)
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"测试请求不是合法 JSON：{exc}"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "测试请求必须是 JSON 对象。"}, status_code=400)

    try:
        raw_config = _load_raw_settings()
        text_base_url = _normalise_config_base_url(
            payload.get("text_base_url") or payload.get("base_url") or _profile_source(raw_config, "text").get("base_url") or ""
        )
        image_base_url = _normalise_config_base_url(
            payload.get("image_base_url") or _profile_source(raw_config, "image").get("base_url") or text_base_url
        )
        embedding_base_url = _normalise_config_base_url(
            payload.get("embedding_base_url") or _profile_source(raw_config, "embedding").get("base_url") or text_base_url
        )
        text_key = _resolve_saved_api_key(raw_config, "text", str(payload.get("text_api_key") or payload.get("api_key") or "").strip())
        image_key = _resolve_saved_api_key(raw_config, "image", str(payload.get("image_api_key") or "").strip(), fallback_key=text_key)
        embedding_key = _resolve_saved_api_key(
            raw_config,
            "embedding",
            str(payload.get("embedding_api_key") or "").strip(),
            fallback_key=text_key,
        )
        embedding_model = _normalise_optional_model(
            payload.get("embedding_model") or _profile_source(raw_config, "embedding").get("embedding_model")
        )
        agent_models_payload = payload.get("agent_models") or {}
        if not isinstance(agent_models_payload, dict):
            raise ValueError("agent_models 必须是对象。")
        requested_agents = payload.get("agent_names")
        if requested_agents is None:
            selected_agent_names = None
        elif isinstance(requested_agents, list):
            selected_agent_names = {str(name).strip() for name in requested_agents if str(name).strip()}
        else:
            raise ValueError("agent_names 必须是数组。")
        include_embedding = bool(payload.get("include_embedding"))
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"读取测试配置失败：{exc}"}, status_code=500)

    raw_agent_models = raw_config.get("agent_models") or {}
    if not isinstance(raw_agent_models, dict):
        raw_agent_models = {}
    all_agent_names = {
        str(name)
        for name in set(raw_agent_models.keys()) | set(agent_models_payload.keys())
        if _is_configurable_agent_model(str(name))
    }
    agent_source_names = selected_agent_names if selected_agent_names is not None else all_agent_names
    agent_order = {name: index for index, name in enumerate(AGENT_MODEL_UI_NAMES)}
    agent_names = sorted(
        (name for name in agent_source_names if _is_configurable_agent_model(name)),
        key=lambda name: agent_order.get(name, len(agent_order)),
    )

    semaphore = asyncio.Semaphore(4)

    async def _run_probe(agent_name: str) -> dict:
        category = _agent_category(agent_name)
        stored_agent = raw_agent_models.get(agent_name) if isinstance(raw_agent_models.get(agent_name), dict) else {}
        model = _normalise_optional_model(agent_models_payload.get(agent_name) or stored_agent.get("model"))
        base_url = image_base_url if category == "image" else text_base_url
        api_key = image_key if category == "image" else text_key
        async with semaphore:
            return await _probe_agent_connection(
                agent_name=agent_name,
                label=AGENT_LABELS.get(agent_name, agent_name),
                category=category,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )

    tasks = [_run_probe(agent_name) for agent_name in agent_names]
    if include_embedding:
        async def _run_embedding_probe() -> dict:
            async with semaphore:
                return await _probe_embedding_connection(
                    base_url=embedding_base_url,
                    api_key=embedding_key,
                    model=embedding_model,
                )

        tasks.append(_run_embedding_probe())

    results = await asyncio.gather(*tasks) if tasks else []
    ok_count = sum(1 for item in results if item.get("success"))
    return JSONResponse({
        "success": ok_count == len(results),
        "summary": {
            "total": len(results),
            "ok": ok_count,
            "failed": len(results) - ok_count,
        },
        "results": results,
    })


@app.post("/api/build_vectordb")
async def api_build_vectordb(request: Request):
    if not _is_local_request(request):
        return JSONResponse({"success": False, "error": "知识库重建仅允许本机管理员执行。"})
    with vectordb_build_lock:
        if vectordb_build_status.get("status") == "running":
            return JSONResponse({
                "success": True,
                "status": "running",
                "message": vectordb_build_status.get("message", "向量知识库正在构建中"),
            })

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    try:
        raw_config = _load_raw_settings()
        vectordb_config = _ensure_config_section(raw_config, "vectordb")
        embedding_base_url = _normalise_config_base_url(
            payload.get("embedding_base_url")
            or payload.get("base_url")
            or vectordb_config.get("base_url")
            or ""
        )
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"读取向量配置失败：{exc}"}, status_code=500)

    embedding_model = _normalise_optional_model(
        payload.get("embedding_model") or payload.get("model") or vectordb_config.get("embedding_model")
    )
    if not embedding_model:
        return JSONResponse({"success": False, "error": "请先选择向量嵌入模型。"}, status_code=400)
    embedding_key = _resolve_saved_api_key(
        raw_config,
        "embedding",
        str(payload.get("embedding_api_key") or payload.get("api_key") or "").strip(),
    )
    if _looks_like_env_placeholder(embedding_key):
        embedding_key = ""
    if not embedding_key:
        return JSONResponse({"success": False, "error": "请先填写向量嵌入 API Key。"}, status_code=400)

    _write_profile_credentials(vectordb_config, embedding_key, embedding_base_url)
    vectordb_config["embedding_model"] = embedding_model
    try:
        _save_raw_settings(raw_config)
    except OSError as exc:
        return JSONResponse({"success": False, "error": f"保存向量配置失败：{exc}"}, status_code=500)

    with vectordb_build_lock:
        if vectordb_build_status.get("status") == "running":
            return JSONResponse({
                "success": True,
                "status": "running",
                "message": vectordb_build_status.get("message", "向量知识库正在构建中"),
            })

        vectordb_build_status.update({
            "status": "running",
            "message": "向量知识库正在后台构建，请稍候...",
            "error": "",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": "",
        })

    def _build_worker() -> None:
        try:
            build_vectordb(force_rebuild=True)
            with vectordb_build_lock:
                vectordb_build_status.update({
                    "status": "done",
                    "message": "向量知识库已重建",
                    "error": "",
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                })
        except Exception as e:
            error_detail = str(e) or type(e).__name__
            if error_detail == "Connection error.":
                error_detail = (
                    "Embedding 中转站连接失败。"
                    f"当前向量模型：{embedding_model or '未配置'}；Base URL：{embedding_base_url or '未配置'}。"
                    "请检查该地址是否能访问 /v1/models 和 /v1/embeddings，或在模型配置页把“向量嵌入”切到可用的中转站/API Key。"
                )
            with vectordb_build_lock:
                vectordb_build_status.update({
                    "status": "error",
                    "message": "向量知识库构建失败",
                    "error": error_detail,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                })

    thread = threading.Thread(target=_build_worker, name="vectordb-build", daemon=True)
    thread.start()
    return JSONResponse({
        "success": True,
        "status": "running",
        "knowledge_index": _safe_knowledge_index_status(),
        "message": "向量知识库已开始后台构建",
    })


@app.get("/api/build_vectordb_status")
async def api_build_vectordb_status(request: Request):
    if not _is_local_request(request):
        return JSONResponse({"success": False, "error": "知识库状态仅允许本机管理员查看。"})
    with vectordb_build_lock:
        status = dict(vectordb_build_status)
    status["success"] = status.get("status") != "error"
    status["knowledge_index"] = _safe_knowledge_index_status()
    return JSONResponse(status)


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
