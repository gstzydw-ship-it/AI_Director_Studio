"""Package node entry points backed by the migrated director implementation."""
from __future__ import annotations

from typing import Any

from . import prompt_compiler_impl as _prompt_compiler_impl
from . import quality_inspector_impl as _quality_inspector_impl
from . import story_planner_impl as _story_planner_impl
from . import shot_director_impl as _shot_director_impl
from . import rhythm_rewrite_impl as _rhythm_rewrite_impl
from . import planning_context_impl as _planning_context_impl
from . import segment_flow_impl as _segment_flow_impl
from . import storyboard_designer_impl as _storyboard_designer_impl


def rhythm_rewrite_director_node(state: Any) -> Any:
    return _rhythm_rewrite_impl.rhythm_rewrite_director_node(state)


def director_showrunner_node(state: Any) -> Any:
    return _planning_context_impl.director_showrunner_node(state)


def scene_analyst_node(state: Any) -> Any:
    return _planning_context_impl.scene_analyst_node(state)


def story_planner_node(state: Any) -> Any:
    return _story_planner_impl.story_planner_node(state)


def shot_director_node(state: Any) -> Any:
    return _shot_director_impl.shot_director_node(state)


def wait_for_segment_request_node(state: Any) -> Any:
    return _segment_flow_impl.wait_for_segment_request_node(state)


def prompt_compiler_node(state: Any) -> Any:
    return _prompt_compiler_impl.prompt_compiler_node(state)


def quality_inspector_node(state: Any) -> Any:
    return _quality_inspector_impl.quality_inspector_node(state)


def qc_router_node(state: Any) -> Any:
    return _quality_inspector_impl.qc_router_node(state)


def segment_complete_node(state: Any) -> Any:
    return _segment_flow_impl.segment_complete_node(state)


def storyboard_designer_node(state: Any) -> Any:
    return _storyboard_designer_impl.storyboard_designer_node(state)


__all__ = [
    "storyboard_designer_node",
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
