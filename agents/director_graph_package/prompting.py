"""Package-local prompting compatibility exports."""
from __future__ import annotations

from typing import Any

from .helpers import build_system_prompt, _run_story_planner_with_schema_repair


def __getattr__(name: str) -> Any:
    if name in {"build_system_prompt", "_run_story_planner_with_schema_repair"}:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
