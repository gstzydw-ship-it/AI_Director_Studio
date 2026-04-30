from __future__ import annotations

import json
import os
from typing import Any

from ..request_context import request_session_id
from .types import CHECKPOINT_FILE, DirectorState, OUTPUT_DIR, SESSION_ID_RE


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
