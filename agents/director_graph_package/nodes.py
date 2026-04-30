"""Package node entry points backed by the migrated director implementation."""
from __future__ import annotations

from typing import Any

from . import legacy_impl as _impl
from . import story_planner_impl as _story_planner_impl
from . import shot_director_impl as _shot_director_impl


def rhythm_rewrite_director_node(state: Any) -> Any:
    return _impl.rhythm_rewrite_director_node(state)


def director_showrunner_node(state: Any) -> Any:
    return _impl.director_showrunner_node(state)


def scene_analyst_node(state: Any) -> Any:
    return _impl.scene_analyst_node(state)


def story_planner_node(state: Any) -> Any:
    return _story_planner_impl.story_planner_node(state)


def shot_director_node(state: Any) -> Any:
    return _shot_director_impl.shot_director_node(state)


def wait_for_segment_request_node(state: Any) -> Any:
    return _impl.wait_for_segment_request_node(state)


def prompt_compiler_node(state: Any) -> Any:
    return _impl.prompt_compiler_node(state)


def quality_inspector_node(state: Any) -> Any:
    return _impl.quality_inspector_node(state)


def qc_router_node(state: Any) -> Any:
    return _impl.qc_router_node(state)


def segment_complete_node(state: Any) -> Any:
    return _impl.segment_complete_node(state)


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
