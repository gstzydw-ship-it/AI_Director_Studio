from __future__ import annotations

import json
import os
from typing import Any

from ..request_context import request_session_id
from .types import CHECKPOINT_FILE, DirectorState, OUTPUT_DIR, SESSION_ID_RE


def _agent_outputs(state: DirectorState) -> dict[str, str]:
    return dict(state.get("agent_outputs") or {})


def _merge_state_update(state: DirectorState, update: DirectorState) -> DirectorState:
    merged: DirectorState = dict(state)
    merged.update(update)
    return merged


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def _normalise_session_id(session_id: str | None) -> str:
    safe = SESSION_ID_RE.sub("", (session_id or "local").strip())[:80]
    return safe or "local"


def _session_output_dir() -> str:
    session_id = _normalise_session_id(request_session_id.get("local"))
    return os.path.join(OUTPUT_DIR, "sessions", session_id)


def _state_file() -> str:
    return os.path.join(_session_output_dir(), "pipeline_state.json")


def _checkpoint_file() -> str:
    return os.path.join(_session_output_dir(), "director_graph.sqlite")


def load_state() -> dict[str, Any]:
    state_file = _state_file()
    if not os.path.exists(state_file):
        return {}
    with open(state_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any]) -> None:
    os.makedirs(_session_output_dir(), exist_ok=True)
    clean_state = dict(state)
    clean_state.pop("__interrupt__", None)
    with open(_state_file(), "w", encoding="utf-8") as f:
        json.dump(clean_state, f, ensure_ascii=False, indent=2)


def clear_state() -> None:
    checkpoint_file = _checkpoint_file()
    for path in [_state_file(), checkpoint_file, f"{checkpoint_file}-wal", f"{checkpoint_file}-shm"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except (PermissionError, OSError):
                pass


def recover_repairable_pipeline_state(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    repaired = dict(state or {})
    changed = False

    if repaired.get("status") in {"running", "running_phase_1", "running_phase_2"}:
        repaired["status"] = "idle"
        repaired["message"] = "检测到上次任务中断，已恢复为可重新启动状态。"
        changed = True

    outputs = repaired.get("agent_outputs")
    if outputs is None or not isinstance(outputs, dict):
        repaired["agent_outputs"] = {}
        changed = True

    return repaired, changed


def _persist_update(state: DirectorState, update: DirectorState) -> DirectorState:
    merged: DirectorState = dict(state)
    merged.update(update)
    save_state(dict(merged))
    return update


def _prepare_phase_2_compile_state(
    state: DirectorState,
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> DirectorState:
    from .segment_flow_impl import (
        _analyze_tail_frame,
        _analyze_video_segment,
        _extract_tail_frame_from_video,
    )

    total_segments = int(state.get("total_segments") or 1)
    requested_segment = max(1, min(segment_index, total_segments))

    if video_path and os.path.exists(video_path):
        try:
            tail_frame_analysis = _analyze_video_segment(video_path, requested_segment)
        except Exception as exc:
            fallback_tail_b64 = tail_frame_b64
            tail_frame_note = ""
            if not fallback_tail_b64:
                fallback_tail_b64, tail_frame_path, tail_frame_error = _extract_tail_frame_from_video(
                    video_path,
                    requested_segment,
                )
                if tail_frame_path:
                    tail_frame_note = f"Auto-extracted tail frame: {tail_frame_path}\n"
                elif tail_frame_error:
                    tail_frame_note = f"Tail-frame extraction also failed: {tail_frame_error}\n"
            fallback = _analyze_tail_frame(fallback_tail_b64, requested_segment)
            tail_frame_analysis = (
                f"Full video continuity analysis failed, so the pipeline fell back to tail-frame analysis. "
                f"Failure reason: {exc}\n\n"
                f"{tail_frame_note}"
                f"{fallback}"
            )
    else:
        tail_frame_analysis = _analyze_tail_frame(tail_frame_b64, requested_segment)

    return _persist_update(
        state,
        {
            "status": "running_phase_2",
            "step": "step_4_compile",
            "message": f"Seedance compiler is generating segment {requested_segment} prompt...",
            "active_segment_index": requested_segment,
            "tail_frame_analysis": tail_frame_analysis,
            "qc_retry_count": 0,
            "revision_instruction": "",
            "error": "",
        },
    )


def _normalise_graph_result(result: dict[str, Any], thread_id: str) -> dict[str, Any]:
    from .segment_flow_impl import _combined_prompt as _seg_combined_prompt

    state = dict(result)
    interrupted = bool(state.pop("__interrupt__", None))
    state["thread_id"] = thread_id
    if interrupted:
        state["status"] = "waiting_for_user_input"
        state.setdefault("message", "等待用户确认后继续...")
    state.setdefault("agent_outputs", {})
    state.setdefault("result", _seg_combined_prompt(state.get("agent_outputs", {})))
    save_state(state)
    return state
