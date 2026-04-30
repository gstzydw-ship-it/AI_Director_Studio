"""Temporary package-local node compatibility stubs.

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


rhythm_rewrite_director_node = _not_split_yet("rhythm_rewrite_director_node")
director_showrunner_node = _not_split_yet("director_showrunner_node")
scene_analyst_node = _not_split_yet("scene_analyst_node")
story_planner_node = _not_split_yet("story_planner_node")
shot_director_node = _not_split_yet("shot_director_node")
wait_for_segment_request_node = _not_split_yet("wait_for_segment_request_node")
prompt_compiler_node = _not_split_yet("prompt_compiler_node")
quality_inspector_node = _not_split_yet("quality_inspector_node")
qc_router_node = _not_split_yet("qc_router_node")
segment_complete_node = _not_split_yet("segment_complete_node")


__all__ = [
    "rhythm_rewrite_director_node",
    "director_showrunner_node",
    "scene_analyst_node",
    "story_planner_node",
    "shot_director_node",
    "wait_for_segment_request_node",
    "prompt_compiler_node",
    "quality_inspector_node",
    "qc_router_node",
    "segment_complete_node",
]
