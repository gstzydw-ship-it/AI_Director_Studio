"""Temporary package-local runner compatibility stubs.

No reverse import to the monolith module.
"""
from __future__ import annotations

from typing import Any


def _not_split_yet(name: str):
    def _raise(*args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(
            f"{name} has not been migrated into the package yet. "
            "This compatibility stub exists only to avoid monolith coupling."
        )
    return _raise


def run_phase_1_planning(*args: Any, **kwargs: Any) -> Any:
    return {"status": "package_stub", "phase": 1, "args": args, "kwargs": kwargs}


def run_phase_2_compile_segment(*args: Any, **kwargs: Any) -> Any:
    return {"status": "package_stub", "phase": 2, "args": args, "kwargs": kwargs}


run_full_pipeline = _not_split_yet("run_full_pipeline")
run_shot_director_resume_from_partial = _not_split_yet("run_shot_director_resume_from_partial")
run_shot_director_restart_from_story_plan = _not_split_yet("run_shot_director_restart_from_story_plan")
route_after_qc = _not_split_yet("route_after_qc")
route_after_segment = _not_split_yet("route_after_segment")
_config = _not_split_yet("_config")
_invoke_graph = _not_split_yet("_invoke_graph")
_normalise_graph_result = _not_split_yet("_normalise_graph_result")


__all__ = [
    "run_phase_1_planning",
    "run_full_pipeline",
    "run_phase_2_compile_segment",
    "run_shot_director_resume_from_partial",
    "run_shot_director_restart_from_story_plan",
    "route_after_qc",
    "route_after_segment",
    "_config",
    "_invoke_graph",
    "_normalise_graph_result",
]
