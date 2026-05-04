#!/usr/bin/env python3
"""
AI Director Pipeline — Native CLI (Tauri 无后端依赖版)

提供与 ui/app.py FastAPI 完全对等的命令行接口，供 Tauri Rust 层通过子进程调用。
所有路径均相对于项目根目录解析。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from io import BytesIO
from typing import Any

# ── 项目根目录路径解析 ────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SCRIPT_DIR)          # AI_Director_Studio/
_UI_DIR = os.path.join(_ROOT_DIR, "ui")            # ui/
_OUTPUT_DIR = os.path.join(_ROOT_DIR, "output")    # output/
_ASSET_LIBRARY_DIR = os.path.join(_OUTPUT_DIR, "client_assets")
_MODEL_PROFILES_PATH = os.path.join(_OUTPUT_DIR, "private", "model_profiles.json")
_SESSION_ID_RE = re.compile(r"[^A-Za-z0-9_-]")
_IMAGE_ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_SEGMENT_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
_MAX_REFERENCE_IMAGES = 12
_REFERENCE_IMAGE_MAX_EDGE = 1280
_REFERENCE_IMAGE_JPEG_QUALITY = 82
_DEFAULT_SESSION_ID = "local"
_LIVE_TASK_STALL_TIMEOUT_SECONDS = int(os.getenv("DIRECTOR_UI_STALL_TIMEOUT_SECONDS", "900"))

sys.path.insert(0, _ROOT_DIR)

# ── Agent 角色映射 ────────────────────────────────────────────────────────────
_AGENT_KEY_MAP = {
    "节奏总控导演": "rhythm_rewrite_director",
    "场景分析师": "scene_analyst",
    "结构规划师": "story_planner",
    "镜头导演": "shot_director",
    "Seedance编译师": "prompt_compiler",
    "质检导演": "quality_inspector",
}
_ASSET_TYPE_DIRS = {
    "character": "characters", "scene": "scenes", "prop": "props",
    "frame": "frames", "upload": "uploads",
}
_RUNNING_STATUSES = {"running", "running_phase_1", "running_phase_2"}
_BLOCKING_STATUSES = _RUNNING_STATUSES | {"waiting_for_user_input"}


# ════════════════════════════════════════════════════════════════════════════════
# 核心状态 & 会话管理
# ════════════════════════════════════════════════════════════════════════════════

def _normalise_session_id(session_id: str | None) -> str:
    safe = _SESSION_ID_RE.sub("", (session_id or _DEFAULT_SESSION_ID).strip())[:80]
    return safe or _DEFAULT_SESSION_ID


def _session_output_dir(session_id: str) -> str:
    return os.path.join(_OUTPUT_DIR, "sessions", _normalise_session_id(session_id))


def _ensure_dirs() -> None:
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(_OUTPUT_DIR, "sessions"), exist_ok=True)
    os.makedirs(os.path.dirname(_MODEL_PROFILES_PATH), exist_ok=True)
    os.makedirs(_ASSET_LIBRARY_DIR, exist_ok=True)
    for d in _ASSET_TYPE_DIRS.values():
        os.makedirs(os.path.join(_ASSET_LIBRARY_DIR, d), exist_ok=True)


# ════════════════════════════════════════════════════════════════════════════════
# 状态读写（封装 agents.director_graph）
# ════════════════════════════════════════════════════════════════════════════════

def _do_load_state(session_id: str) -> dict:
    """加载指定 session 的流水线状态。"""
    from agents.director_graph import load_state as _impl_load_state
    from agents.request_context import request_scope
    sid = _normalise_session_id(session_id)
    with request_scope(session_id=sid):
        return _impl_load_state() or {}


def _do_save_state(session_id: str, state: dict) -> bool:
    """保存流水线状态到磁盘。"""
    from agents.director_graph import save_state as _impl_save_state
    from agents.request_context import request_scope
    sid = _normalise_session_id(session_id)
    try:
        with request_scope(session_id=sid):
            _impl_save_state(dict(state))
        return True
    except Exception:
        return False


def _do_clear_state(session_id: str) -> None:
    from agents.director_graph import clear_state as _impl_clear_state
    from agents.request_context import request_scope
    sid = _normalise_session_id(session_id)
    with request_scope(session_id=sid):
        _impl_clear_state()


# ════════════════════════════════════════════════════════════════════════════════
# CLI 命令实现
# ════════════════════════════════════════════════════════════════════════════════

def cmd_status(session_id: str = _DEFAULT_SESSION_ID) -> dict:
    """GET /api/status"""
    _ensure_dirs()
    state = _do_load_state(session_id)
    # 脱敏
    if isinstance(state.get("model_profile_snapshot"), dict):
        state = dict(state)
        snap = _mask_sensitive(state["model_profile_snapshot"])
        snap["base_url_host"] = _host_from_base_url(snap.get("base_url"))
        state["model_profile_snapshot"] = snap
    if isinstance(state.get("error"), str) and len(state["error"]) > 5000:
        state = dict(state)
        state["error"] = state["error"][:5000] + "\n... truncated ..."
    return state


def cmd_model_profiles() -> list[dict]:
    """GET /api/model_profiles"""
    _ensure_dirs()
    if not os.path.exists(_MODEL_PROFILES_PATH):
        return []
    try:
        with open(_MODEL_PROFILES_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return []
    profiles = data.get("profiles", []) if isinstance(data, dict) else data
    return [_sanitize_model_profile(p) for p in profiles if isinstance(p, dict)]


def cmd_save_model_profile(payload: dict) -> dict:
    """POST /api/model_profiles"""
    _ensure_dirs()
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    profiles = cmd_model_profiles()
    # 去除脱敏字段后加载原始
    raw_profiles = []
    if os.path.exists(_MODEL_PROFILES_PATH):
        try:
            with open(_MODEL_PROFILES_PATH, "r", encoding="utf-8-sig") as f:
                raw_data = json.load(f)
            raw_profiles = raw_data.get("profiles", []) if isinstance(raw_data, dict) else raw_data
        except Exception:
            pass

    existing = next((p for p in raw_profiles if str(p.get("id", "")) == str(payload.get("id", ""))), None)
    profile = _normalise_model_profile_payload(payload, existing)
    if not profile.get("name"):
        raise ValueError("Profile name is required")
    if not profile.get("base_url"):
        raise ValueError("BaseURL is required")

    replaced = False
    for i, p in enumerate(raw_profiles):
        if str(p.get("id", "")) == profile["id"]:
            raw_profiles[i] = profile
            replaced = True
            break
    if not replaced:
        raw_profiles.append(profile)

    os.makedirs(os.path.dirname(_MODEL_PROFILES_PATH), exist_ok=True)
    with open(_MODEL_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump({"profiles": raw_profiles}, f, ensure_ascii=False, indent=2)
    return _sanitize_model_profile(profile)


def cmd_test_model_profile(payload: dict) -> dict:
    """POST /api/model_profiles/test"""
    import httpx, urllib.parse
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    # 加载已有 profile 以合并 api_key
    raw_profiles = []
    if os.path.exists(_MODEL_PROFILES_PATH):
        try:
            with open(_MODEL_PROFILES_PATH, "r", encoding="utf-8-sig") as f:
                raw_data = json.load(f)
            raw_profiles = raw_data.get("profiles", []) if isinstance(raw_data, dict) else raw_data
        except Exception:
            pass
    existing = next((p for p in raw_profiles if str(p.get("id", "")) == str(payload.get("id", ""))), None)
    profile = _normalise_model_profile_payload(payload, existing)
    base_url = profile.get("base_url", "")
    if not base_url:
        raise ValueError("BaseURL is required")
    headers = {"Authorization": f"Bearer {profile.get('api_key', '')}"} if profile.get("api_key") else {}
    host = _host_from_base_url(base_url)
    try:
        parsed = urllib.parse.urlparse(base_url if "://" in base_url else f"https://{base_url}")
        test_url = f"{parsed.scheme}://{parsed.netloc or parsed.path}/models"
        response = httpx.get(test_url, headers=headers, timeout=15.0, trust_env=False)
        return {"success": response.status_code < 400, "base_url_host": host, "status_code": response.status_code}
    except Exception as exc:
        return {"success": False, "error": str(exc), "base_url_host": host}


def cmd_projects_recent(include_archived: bool = False) -> list[dict]:
    """GET /api/projects/recent"""
    _ensure_dirs()
    sessions_dir = os.path.join(_OUTPUT_DIR, "sessions")
    projects = []
    if os.path.isdir(sessions_dir):
        paths = []
        for name in os.listdir(sessions_dir):
            state_path = os.path.join(sessions_dir, name, "pipeline_state.json")
            if os.path.isfile(state_path):
                paths.append((name, state_path))
        for name, state_path in sorted(paths, key=lambda x: os.path.getmtime(x[1]), reverse=True):
            try:
                with open(state_path, "r", encoding="utf-8-sig") as f:
                    state = json.load(f)
            except Exception:
                continue
            if state.get("archived") and not include_archived:
                continue
            projects.append({
                "session_id": _normalise_session_id(name),
                "name": state.get("project_name") or f"项目 {name}",
                "status": state.get("status") or "idle",
                "current_segment_index": state.get("current_segment_index") or 1,
                "total_segments": state.get("total_segments") or 0,
                "archived": bool(state.get("archived")),
                "updated_at": datetime.fromtimestamp(os.path.getmtime(state_path)).isoformat(),
            })
    return projects[:24]


def cmd_projects_new(name: str = "未命名项目", session_id: str | None = None) -> dict:
    """POST /api/projects/new"""
    _ensure_dirs()
    name = name.strip() or "未命名项目"
    sid = session_id or f"project_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    sid = _normalise_session_id(sid)
    # 避免 session_id 冲突
    base_sid = sid
    counter = 1
    while os.path.exists(os.path.join(_session_output_dir(sid), "pipeline_state.json")):
        sid = _normalise_session_id(f"{base_sid}_{counter}")
        counter += 1
    _do_clear_state(sid)
    state = _default_task_state()
    state["project_name"] = name
    state["created_at"] = datetime.now().isoformat(timespec="seconds")
    state["message"] = "新项目已创建。"
    _do_save_state(sid, state)
    return {
        "session_id": sid,
        "name": name,
        "status": "idle",
        "current_segment_index": 1,
        "total_segments": 0,
        "archived": False,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def cmd_projects_archive(session_id: str) -> dict:
    """POST /api/projects/archive"""
    _ensure_dirs()
    sid = _normalise_session_id(session_id)
    state = _do_load_state(sid)
    state["archived"] = True
    state["archived_at"] = datetime.now().isoformat(timespec="seconds")
    state["message"] = "项目已归档。"
    _do_save_state(sid, state)
    return {
        "session_id": sid,
        "name": state.get("project_name") or f"项目 {sid}",
        "status": state.get("status") or "idle",
        "current_segment_index": state.get("current_segment_index") or 1,
        "total_segments": state.get("total_segments") or 0,
        "archived": True,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def cmd_assets_library() -> dict:
    """GET /api/assets/library"""
    _ensure_dirs()
    assets = []
    for asset_type, dirname in _ASSET_TYPE_DIRS.items():
        folder = os.path.join(_ASSET_LIBRARY_DIR, dirname)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            fpath = os.path.join(folder, fname)
            asset = _asset_from_path(asset_type, fpath)
            if asset:
                assets.append(asset)
    groups = {k: [] for k in _ASSET_TYPE_DIRS}
    for asset in assets:
        groups.setdefault(asset["type"], []).append(asset)
    return {"assets": assets, "groups": groups}


def cmd_assets_import(asset_type: str, name: str, tags: str, description: str,
                      purpose: str, file_path: str) -> dict:
    """POST /api/assets/import"""
    _ensure_dirs()
    asset_type = _normalise_asset_type(asset_type)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    _, ext = os.path.splitext(file_path)
    if asset_type != "upload" and ext.lower() not in _IMAGE_ASSET_EXTENSIONS:
        raise ValueError("Asset library only accepts images: png/jpg/jpeg/webp/bmp")
    with open(file_path, "rb") as f:
        content = f.read()
    if not content:
        raise ValueError("Uploaded asset is empty")
    dirname = _ASSET_TYPE_DIRS[asset_type]
    folder = os.path.join(_ASSET_LIBRARY_DIR, dirname)
    path, existed = _dedupe_asset_path(folder, os.path.basename(file_path), content)
    if not existed:
        fname = os.path.basename(path)
        with open(path, "wb") as out:
            out.write(content)
        meta = {
            "id": f"{asset_type}:{fname}",
            "type": asset_type,
            "name": name.strip() or os.path.splitext(os.path.basename(file_path))[0],
            "tags": _parse_tags(tags),
            "description": description.strip(),
            "purpose": purpose.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_asset_meta(path, meta)
    asset = _asset_from_path(asset_type, path)
    return {"asset": asset, "deduplicated": existed}


def cmd_assets_import_batch(asset_type: str, tags: str, description: str,
                            purpose: str, file_paths: list[str]) -> dict:
    """POST /api/assets/import_batch"""
    _ensure_dirs()
    asset_type = _normalise_asset_type(asset_type)
    dirname = _ASSET_TYPE_DIRS[asset_type]
    folder = os.path.join(_ASSET_LIBRARY_DIR, dirname)
    results, skipped = [], 0
    for fp in file_paths:
        if not os.path.isfile(fp):
            continue
        _, ext = os.path.splitext(fp)
        if ext.lower() not in _IMAGE_ASSET_EXTENSIONS:
            continue
        with open(fp, "rb") as f:
            content = f.read()
        if not content:
            continue
        safe_name = os.path.splitext(os.path.basename(fp))[0]
        path, existed = _dedupe_asset_path(folder, os.path.basename(fp), content)
        if existed:
            skipped += 1
            asset = _asset_from_path(asset_type, path)
            if asset:
                results.append(asset)
            continue
        fname = os.path.basename(path)
        with open(path, "wb") as out:
            out.write(content)
        meta = {
            "id": f"{asset_type}:{fname}",
            "type": asset_type,
            "name": safe_name,
            "tags": _parse_tags(tags),
            "description": description.strip(),
            "purpose": purpose.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_asset_meta(path, meta)
        asset = _asset_from_path(asset_type, path)
        if asset:
            results.append(asset)
    return {"assets": results, "count": len(results), "skipped": skipped}


def cmd_video_extract_frames(video_file_path: str, interval_seconds: int = 3,
                             max_frames: int = 12, purpose: str = "action_reference") -> dict:
    """POST /api/video/extract_frames"""
    _ensure_dirs()
    if not os.path.isfile(video_file_path):
        raise FileNotFoundError(f"Video file not found: {video_file_path}")
    _, ext = os.path.splitext(video_file_path)
    if ext.lower() not in _SEGMENT_VIDEO_EXTENSIONS:
        raise ValueError("Video must be mp4/mov/avi/webm")

    upload_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_filename(os.path.basename(video_file_path), 'video')}"
    upload_dir = os.path.join(_ASSET_LIBRARY_DIR, _ASSET_TYPE_DIRS["upload"])
    upload_path = os.path.join(upload_dir, upload_name)
    shutil.copy2(video_file_path, upload_path)

    try:
        import cv2
    except Exception as exc:
        raise RuntimeError(f"OpenCV not available: {exc}")

    cap = cv2.VideoCapture(upload_path)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Cannot open video file")
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if frame_count > 0 else 0
    interval = max(1, int(interval_seconds or 3))
    max_f = max(1, min(int(max_frames or 12), 60))
    timestamps = [i * interval for i in range(max_f) if i * interval <= duration]
    if not timestamps:
        timestamps = [0.0]
    assets = []
    for i, sec in enumerate(timestamps, 1):
        cap.set(cv2.CAP_PROP_POS_MSEC, float(sec) * 1000)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 84])
        if not ok2:
            continue
        tc_min, tc_sec = int(sec // 60), int(sec % 60)
        timecode = f"{tc_min:02d}:{tc_sec:02d}"
        frame_name = f"{os.path.splitext(upload_name)[0]}_{i:03d}_{tc_min:02d}-{tc_sec:02d}.jpg"
        frame_path = os.path.join(_ASSET_LIBRARY_DIR, _ASSET_TYPE_DIRS["frame"], frame_name)
        with open(frame_path, "wb") as fo:
            fo.write(buf.tobytes())
        meta = {
            "id": f"frame:{frame_name}",
            "type": "frame",
            "name": f"{os.path.splitext(os.path.basename(video_file_path))[0]} {timecode}",
            "tags": ["video_frame"],
            "description": "",
            "purpose": purpose.strip() or "action_reference",
            "source_video": upload_name,
            "timecode": timecode,
            "timestamp_seconds": round(float(sec), 3),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_asset_meta(frame_path, meta)
        asset = _asset_from_path("frame", frame_path)
        if asset:
            assets.append(asset)
    cap.release()
    return {"video": upload_name, "frames": assets}


def cmd_director_edits_save(session_id: str, segment_index: int,
                             edited_yaml: str, edit_payload: dict | None = None) -> dict:
    """POST /api/director_edits/save"""
    sid = _normalise_session_id(session_id)
    state = _do_load_state(sid)
    if not state:
        raise RuntimeError("No pipeline state found for this session")
    state = _apply_director_edit_to_state(state, segment_index, edited_yaml, edit_payload, approved=False)
    _do_save_state(sid, state)
    return {"success": True, "state": _mask_task_state(state)}


def cmd_director_edits_submit(session_id: str, segment_index: int,
                               edited_yaml: str, edit_payload: dict | None = None) -> dict:
    """POST /api/director_edits/submit"""
    sid = _normalise_session_id(session_id)
    state = _do_load_state(sid)
    if not state:
        raise RuntimeError("No pipeline state found for this session")
    state = _apply_director_edit_to_state(state, segment_index, edited_yaml, edit_payload, approved=True)
    _do_save_state(sid, state)
    return {"success": True, "message": "已提交 Prompt 编译"}


# ════════════════════════════════════════════════════════════════════════════════
# Pipeline 执行命令（启动 Python 子线程）
# ════════════════════════════════════════════════════════════════════════════════

# 跨线程状态共享（通过 JSON 文件）
_ACTIVE_TASKS: dict[str, threading.Thread] = {}
_TASK_PROGRESS_FILE = os.path.join(_OUTPUT_DIR, "_native_cli_progress.json")


def _load_task_progress() -> dict:
    if os.path.exists(_TASK_PROGRESS_FILE):
        try:
            with open(_TASK_PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_task_progress(data: dict) -> None:
    try:
        with open(_TASK_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _spawn_background_worker(command: str, session_id: str, payload: dict) -> None:
    sid = _normalise_session_id(session_id)
    log_dir = os.path.join(_OUTPUT_DIR, "private")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"native_cli_{sid}_{command}.log")
    kwargs_json = json.dumps(payload, ensure_ascii=False)
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    with open(log_path, "a", encoding="utf-8") as log_file:
        subprocess.Popen(
            [
                sys.executable,
                os.path.abspath(__file__),
                command,
                "--session-id",
                sid,
                "--json-input",
                kwargs_json,
            ],
            cwd=_ROOT_DIR,
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )


def cmd_run_pipeline(script: str, aspect_ratio: str, session_id: str,
                     model_profile_snapshot: dict | None = None,
                     style_preset: str | None = None,
                     reference_image_b64s: list | None = None,
                     reference_image_manifest: list | None = None,
                     asset_selection: dict | None = None,
                     speed_mode: bool = False) -> dict:
    """POST /api/run — 在独立后台进程中启动 Phase 1"""
    _ensure_dirs()
    sid = _normalise_session_id(session_id)
    _save_task_progress({
        "session_id": sid,
        "status": "running_phase_1",
        "step": "queued",
        "message": "任务已提交，正在启动后台流水线...",
        "started_at": datetime.now().isoformat(),
    })
    _spawn_background_worker("run_pipeline_worker", sid, {
        "script": script,
        "aspect_ratio": aspect_ratio,
        "model_profile_snapshot": model_profile_snapshot,
        "style_preset": style_preset,
        "reference_image_b64s": reference_image_b64s,
        "reference_image_manifest": reference_image_manifest,
        "asset_selection": asset_selection,
        "speed_mode": speed_mode,
    })
    return {"success": True, "message": "Pipeline started"}


def _run_pipeline_phase1(script: str, aspect_ratio: str, session_id: str,
                          model_profile_snapshot: dict | None = None,
                          style_preset: str | None = None,
                          reference_image_b64s: list | None = None,
                          reference_image_manifest: list | None = None,
                          asset_selection: dict | None = None,
                          speed_mode: bool = False) -> None:
    try:
        from agents.director_graph import run_phase_1_planning as _run
        from agents.request_context import request_scope
    except ImportError:
        _save_task_progress({
            "session_id": session_id,
            "status": "error",
            "step": "error",
            "message": "无法导入 run_phase_1_planning，请检查 agents/director_graph.py 是否可用",
            "error": traceback.format_exc(),
        })
        _ACTIVE_TASKS.pop(session_id, None)
        return
    try:
        with request_scope(session_id=session_id):
            _save_task_progress({
                "session_id": session_id,
                "status": "running_phase_1",
                "step": "step_1_analyze",
                "message": "🎼 节奏总控导演正在改写剧本...（1/6）",
                "started_at": datetime.now().isoformat(),
            })
            state = _run(
                script=script,
                aspect_ratio=aspect_ratio,
                reference_images=None,
                reference_image_b64s=reference_image_b64s or [],
                reference_image_manifest=reference_image_manifest or [],
                speed_mode=speed_mode,
                model_profile_snapshot=model_profile_snapshot or {},
                asset_selection=asset_selection or {},
            )
            if isinstance(state, dict):
                state["style_preset"] = style_preset or ""
            _save_task_progress(dict(state))
            _do_save_state(session_id, state)
    except Exception as exc:
        _save_task_progress({
            "session_id": session_id,
            "status": "error",
            "step": "error",
            "message": f"执行失败: {exc}",
            "error": traceback.format_exc(),
        })
    finally:
        _ACTIVE_TASKS.pop(session_id, None)


def cmd_resume_pipeline(session_id: str, segment_index: int,
                         tail_frame_b64: str | None = None,
                         video_path: str | None = None) -> dict:
    """POST /api/resume — 在独立后台进程中启动 Phase 2"""
    _ensure_dirs()
    sid = _normalise_session_id(session_id)
    _save_task_progress({
        "session_id": sid,
        "status": "running_phase_2",
        "step": "queued",
        "message": f"片段 {segment_index} 已提交，正在启动后台编译...",
        "started_at": datetime.now().isoformat(),
    })
    _spawn_background_worker("resume_pipeline_worker", sid, {
        "segment_index": segment_index,
        "tail_frame_b64": tail_frame_b64,
        "video_path": video_path,
    })
    return {"success": True, "message": f"Phase 2 for segment {segment_index} started"}


def _run_pipeline_phase2(session_id: str, segment_index: int,
                           tail_frame_b64: str | None = None,
                           video_path: str | None = None) -> None:
    try:
        from agents.director_graph import run_phase_2_compile_segment as _run
        from agents.request_context import request_scope
        from agents.director_graph_package.legacy_impl import _normalise_compiled_prompt as _norm
    except ImportError:
        _save_task_progress({
            "session_id": session_id,
            "status": "error",
            "step": "error",
            "message": "无法导入 Phase 2 所需模块，请检查 agents/director_graph.py 是否可用",
            "error": traceback.format_exc(),
        })
        _ACTIVE_TASKS.pop(session_id, None)
        return
    try:
        with request_scope(session_id=session_id):
            _save_task_progress({
                "session_id": session_id,
                "status": "running_phase_2",
                "step": "step_4_compile",
                "message": f"✍️ Seedance编译师正在生成片段 {segment_index}...",
            })
            state = _run(segment_index, tail_frame_b64, video_path)
            # 清理流式污染
            outputs = state.get("agent_outputs", {})
            key = f"compiled_segment_{segment_index}"
            raw = outputs.get(key, "")
            if raw:
                outputs[key] = _norm(raw, segment_index)
                outputs["prompt_compiler"] = _norm(raw, segment_index)
            _save_task_progress(dict(state))
            _do_save_state(session_id, state)
    except Exception as exc:
        _save_task_progress({
            "session_id": session_id,
            "status": "error",
            "step": "error",
            "message": f"执行失败: {exc}",
            "error": traceback.format_exc(),
        })
    finally:
        _ACTIVE_TASKS.pop(session_id, None)


def cmd_pipeline_progress(session_id: str) -> dict:
    """GET /api/pipeline/progress"""
    progress = _load_task_progress()
    if progress.get("session_id") != session_id:
        # fallback to disk state
        return cmd_status(session_id)
    return progress


def cmd_is_pipeline_running(session_id: str) -> bool:
    sid = _normalise_session_id(session_id)
    progress = _load_task_progress()
    if progress.get("session_id") == sid and progress.get("status") in _RUNNING_STATUSES:
        return True
    state = _do_load_state(sid)
    return str(state.get("status") or "") in _RUNNING_STATUSES


# ════════════════════════════════════════════════════════════════════════════════
# 辅助函数（从 ui/app.py 迁移）
# ════════════════════════════════════════════════════════════════════════════════

def _default_task_state() -> dict:
    return {
        "status": "idle", "step": "", "message": "", "result": "", "error": "",
        "started_at": "", "agent_outputs": {}, "input_script": "",
        "input_aspect_ratio": "9:16", "input_ref_manifest": [],
        "project_name": "未命名项目", "archived": False,
        "model_profile_snapshot": {}, "asset_selection": {}, "style_preset": "",
        "director_review_required": False, "director_edits_by_segment": {},
        "shot_director_original_by_segment": {}, "shot_director_approved_by_segment": {},
        "current_segment_index": 1, "total_segments": 0, "segment_names": [],
    }


def _normalise_asset_type(value: str | None) -> str:
    value = (value or "").strip().lower()
    aliases = {"person": "character", "role": "character",
               "location": "scene", "place": "scene", "object": "prop",
               "frame_reference": "frame"}
    value = aliases.get(value, value)
    return value if value in _ASSET_TYPE_DIRS else "upload"


def _safe_filename(filename: str, fallback: str = "asset") -> str:
    stem, ext = os.path.splitext(filename or "")
    safe_stem = "".join(c if c.isalnum() or c in "._-" else "_" for c in stem).strip("._")
    safe_ext = "".join(c for c in ext.lower() if c.isalnum() or c == ".")
    return f"{safe_stem or fallback}{safe_ext or '.bin'}"


def _file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _dedupe_asset_path(folder: str, original_filename: str, content: bytes) -> tuple[str, bool]:
    safe_name = _safe_filename(original_filename)
    stem, ext = os.path.splitext(safe_name)
    digest = _file_sha256(content)
    os.makedirs(folder, exist_ok=True)
    for existing in os.listdir(folder):
        ep = os.path.join(folder, existing)
        if not os.path.isfile(ep):
            continue
        try:
            with open(ep, "rb") as f:
                if _file_sha256(f.read()) == digest:
                    return ep, True
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
    return [str(t).strip() for t in candidates if (t or "").strip()]


def _thumbnail_data_url(path: str, size: int = 180) -> str:
    try:
        from PIL import Image, ImageOps
        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            canvas = Image.new("RGB", image.size, (20, 24, 31))
            canvas.paste(image.convert("RGBA"), mask=image.convert("RGBA").getchannel("A"))
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


def _read_asset_meta(path: str) -> dict:
    mp = _asset_meta_path(path)
    if not os.path.exists(mp):
        return {}
    try:
        with open(mp, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_asset_meta(path: str, meta: dict) -> None:
    with open(_asset_meta_path(path), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _asset_from_path(asset_type: str, path: str) -> dict | None:
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
        "url": f"/api/assets/file/{asset_type}/{filename}",
        "thumbnail": _thumbnail_data_url(path) if ext.lower() in _IMAGE_ASSET_EXTENSIONS else "",
        "tags": _parse_tags(meta.get("tags") or []),
        "description": str(meta.get("description") or ""),
        "purpose": str(meta.get("purpose") or ""),
        "timecode": str(meta.get("timecode") or ""),
        "timestamp_seconds": meta.get("timestamp_seconds"),
        "created_at": str(meta.get("created_at") or ""),
        "source_video": str(meta.get("source_video") or ""),
    }


def _mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        masked = {}
        for k, v in value.items():
            lower = str(k).lower()
            if "api_key" in lower or lower in {"apikey", "token", "secret"}:
                masked[k] = _mask_secret(v)
            else:
                masked[k] = _mask_sensitive(v)
        return masked
    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]
    return value


def _mask_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:3]}***{text[-4:]}"


def _host_from_base_url(base_url: Any) -> str:
    from urllib.parse import urlparse
    text = str(base_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return parsed.netloc or parsed.path.split("/", 1)[0]


def _sanitize_model_profile(profile: dict) -> dict:
    clean = _mask_sensitive(dict(profile))
    clean["api_key_set"] = bool(profile.get("api_key"))
    clean["base_url_host"] = _host_from_base_url(profile.get("base_url"))
    return clean


def _normalise_model_profile_payload(payload: dict, existing: dict | None = None) -> dict:
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
        "fallback_models": _normalise_model_list(payload.get("fallback_models", existing.get("fallback_models", []))),
        "vectordb_base_url": str(payload.get("vectordb_base_url") or existing.get("vectordb_base_url") or "").strip().rstrip("/"),
        "embedding_model": str(payload.get("embedding_model") or existing.get("embedding_model") or "").strip(),
        "max_tokens": payload.get("max_tokens", existing.get("max_tokens", "")),
        "max_retries": payload.get("max_retries", existing.get("max_retries", 2)),
        "timeout_seconds": payload.get("timeout_seconds", existing.get("timeout_seconds", "")),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _normalise_model_list(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = re.split(r"[,，\n]+", value)
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = []
    return [str(c).strip() for c in candidates if (c or "").strip()]


def _segment_key(segment_index: int) -> str:
    return str(max(1, int(segment_index)))


def _extract_segment_block(text: str, segment_index: int) -> str:
    fragment_id = f"F{int(segment_index):02d}"
    match = re.search(
        rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)", text or ""
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


def _apply_director_edit_to_state(state: dict, segment_index: int,
                                   edited_yaml: str,
                                   edit_payload: dict | None = None,
                                   approved: bool = False) -> dict:
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


def _mask_task_state(state: dict) -> dict:
    result = dict(state)
    if isinstance(result.get("model_profile_snapshot"), dict):
        result["model_profile_snapshot"] = _mask_sensitive(result["model_profile_snapshot"])
    if isinstance(result.get("error"), str) and len(result["error"]) > 5000:
        result["error"] = result["error"][:5000] + "\n... truncated ..."
    return result


# ════════════════════════════════════════════════════════════════════════════════
# CLI 入口
# ════════════════════════════════════════════════════════════════════════════════

def main() -> None:
    _sys = __import__("sys")
    _diag_file = os.path.join(_OUTPUT_DIR, "_native_cli_diag.txt")
    def _diag(msg: str) -> None:
        try:
            with open(_diag_file, "a", encoding="utf-8") as f:
                f.write(f"[diag] {msg}\n")
        except Exception:
            pass

    _diag(f"CLI 启动 | Python={_sys.version} | argv={_sys.argv} | CWD={os.getcwd()}")
    try:
        _diag("调用 _ensure_dirs()...")
        _ensure_dirs()
        _diag("_ensure_dirs OK")
    except Exception as _e:
        _diag(f"_ensure_dirs FAIL: {_e}")
        _sys.stderr.write(f"[FATAL] _ensure_dirs failed: {_e}\n")
        _sys.stderr.flush()
        _sys.exit(1)

    parser = argparse.ArgumentParser(description="AI Director Native CLI")
    parser.add_argument("command", help="Command name")
    parser.add_argument("--session-id", default=_DEFAULT_SESSION_ID)
    parser.add_argument("--json-input", type=str, default=None,
                        help="JSON string with command arguments")
    parser.add_argument("--file-paths", type=str, default=None,
                        help="JSON array of file paths for batch operations")
    parser.add_argument("--out", type=str, default=None,
                        help="Output file path (default: stdout)")
    args = parser.parse_args()
    _diag(f"参数解析完成 | command={args.command} | session_id={args.session_id} | json_input={args.json_input[:80] if args.json_input else None}")

    result: dict = {"success": False, "error": "Unknown command"}
    cmd = args.command

    try:
        if args.json_input:
            kwargs = json.loads(args.json_input)
            _diag(f"kwargs 解析 OK: {str(kwargs)[:120]}")
        else:
            kwargs = {}
            _diag("无 kwargs（无 --json-input）")

        if cmd == "status":
            result = {"success": True, **cmd_status(kwargs.get("session_id", args.session_id))}
        elif cmd == "model_profiles":
            result = {"success": True, "profiles": cmd_model_profiles()}
        elif cmd == "save_model_profile":
            result = {"success": True, "profile": cmd_save_model_profile(kwargs)}
        elif cmd == "test_model_profile":
            test_result = cmd_test_model_profile(kwargs)
            result = {"success": test_result.get("success", False),
                     "base_url_host": test_result.get("base_url_host"),
                     "error": test_result.get("error")}
        elif cmd == "projects_recent":
            include_archived = kwargs.get("include_archived", False)
            result = {"success": True, "projects": cmd_projects_recent(include_archived)}
        elif cmd == "projects_new":
            result = {"success": True, "project": cmd_projects_new(
                kwargs.get("name", "未命名项目"), kwargs.get("session_id"))}
        elif cmd == "projects_archive":
            result = {"success": True, "project": cmd_projects_archive(args.session_id)}
        elif cmd == "assets_library":
            result = {"success": True, **cmd_assets_library()}
        elif cmd == "assets_import":
            file_path = kwargs.get("file_path")
            if not file_path:
                raise ValueError("--json-input must contain file_path")
            import_result = cmd_assets_import(
                asset_type=kwargs.get("asset_type", "character"),
                name=kwargs.get("name", ""),
                tags=kwargs.get("tags", ""),
                description=kwargs.get("description", ""),
                purpose=kwargs.get("purpose", ""),
                file_path=file_path,
            )
            result = {"success": True, **import_result}
        elif cmd == "assets_import_batch":
            fps = json.loads(args.file_paths) if args.file_paths else []
            import_result = cmd_assets_import_batch(
                asset_type=kwargs.get("asset_type", "character"),
                tags=kwargs.get("tags", ""),
                description=kwargs.get("description", ""),
                purpose=kwargs.get("purpose", ""),
                file_paths=fps,
            )
            result = {"success": True, **import_result}
        elif cmd == "video_extract_frames":
            video_path = kwargs.get("video_file_path")
            if not video_path:
                raise ValueError("--json-input must contain video_file_path")
            extract_result = cmd_video_extract_frames(
                video_file_path=video_path,
                interval_seconds=kwargs.get("interval_seconds", 3),
                max_frames=kwargs.get("max_frames", 12),
                purpose=kwargs.get("purpose", "action_reference"),
            )
            result = {"success": True, **extract_result}
        elif cmd == "director_edits_save":
            save_result = cmd_director_edits_save(
                session_id=args.session_id,
                segment_index=kwargs.get("segment_index", 1),
                edited_yaml=kwargs.get("edited_yaml", ""),
                edit_payload=kwargs.get("edit_payload"),
            )
            result = {"success": True, "state": save_result.get("state", {})}
        elif cmd == "director_edits_submit":
            submit_result = cmd_director_edits_submit(
                session_id=args.session_id,
                segment_index=kwargs.get("segment_index", 1),
                edited_yaml=kwargs.get("edited_yaml", ""),
                edit_payload=kwargs.get("edit_payload"),
            )
            result = {"success": True, "message": submit_result.get("message", "OK")}
        elif cmd == "run_pipeline":
            # 从 kwargs 解析 pipeline 参数
            result = cmd_run_pipeline(
                script=kwargs.get("script", ""),
                aspect_ratio=kwargs.get("aspect_ratio", "9:16"),
                session_id=args.session_id,
                model_profile_snapshot=kwargs.get("model_profile_snapshot"),
                style_preset=kwargs.get("style_preset"),
                reference_image_b64s=kwargs.get("reference_image_b64s"),
                reference_image_manifest=kwargs.get("reference_image_manifest"),
                asset_selection=kwargs.get("asset_selection"),
                speed_mode=bool(kwargs.get("speed_mode", False)),
            )
        elif cmd == "resume_pipeline":
            result = cmd_resume_pipeline(
                session_id=args.session_id,
                segment_index=kwargs.get("segment_index", 1),
                tail_frame_b64=kwargs.get("tail_frame_b64"),
                video_path=kwargs.get("video_path"),
            )
        elif cmd == "run_pipeline_worker":
            _run_pipeline_phase1(
                script=kwargs.get("script", ""),
                aspect_ratio=kwargs.get("aspect_ratio", "9:16"),
                session_id=args.session_id,
                model_profile_snapshot=kwargs.get("model_profile_snapshot"),
                style_preset=kwargs.get("style_preset"),
                reference_image_b64s=kwargs.get("reference_image_b64s"),
                reference_image_manifest=kwargs.get("reference_image_manifest"),
                asset_selection=kwargs.get("asset_selection"),
                speed_mode=bool(kwargs.get("speed_mode", False)),
            )
            result = {"success": True, "message": "Pipeline worker finished"}
        elif cmd == "resume_pipeline_worker":
            _run_pipeline_phase2(
                session_id=args.session_id,
                segment_index=kwargs.get("segment_index", 1),
                tail_frame_b64=kwargs.get("tail_frame_b64"),
                video_path=kwargs.get("video_path"),
            )
            result = {"success": True, "message": "Resume worker finished"}
        elif cmd == "pipeline_progress":
            result = {"success": True, **cmd_pipeline_progress(args.session_id)}
        elif cmd == "is_pipeline_running":
            result = {"success": True, "running": cmd_is_pipeline_running(args.session_id)}
        else:
            result = {"success": False, "error": f"Unknown command: {cmd}"}
    except Exception as exc:
        result = {"success": False, "error": str(exc), "traceback": traceback.format_exc()}

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
