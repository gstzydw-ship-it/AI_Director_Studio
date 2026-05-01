"""Package runner entry points backed by the migrated director implementation."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from . import legacy_impl as _impl


def _sync_package_graph_api() -> None:
    from .graph_api import create_director_graph

    _impl.create_director_graph = create_director_graph


@contextmanager
def _bind_package_shot_director_node():
    from .nodes import shot_director_node

    previous = _impl.shot_director_node
    _impl.shot_director_node = shot_director_node
    try:
        yield
    finally:
        _impl.shot_director_node = previous


def route_after_qc(state: Any) -> Any:
    return _impl.route_after_qc(state)


def route_after_segment(state: Any) -> Any:
    return _impl.route_after_segment(state)


def _config(*args: Any, **kwargs: Any) -> Any:
    return _impl._config(*args, **kwargs)


def _invoke_graph(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl._invoke_graph(*args, **kwargs)


def _normalise_graph_result(*args: Any, **kwargs: Any) -> Any:
    return _impl._normalise_graph_result(*args, **kwargs)


def _merge_state_update(*args: Any, **kwargs: Any) -> Any:
    return _impl._merge_state_update(*args, **kwargs)


def _prepare_phase_2_compile_state(*args: Any, **kwargs: Any) -> Any:
    return _impl._prepare_phase_2_compile_state(*args, **kwargs)


def _run_phase_2_compile_direct(*args: Any, **kwargs: Any) -> Any:
    return _impl._run_phase_2_compile_direct(*args, **kwargs)


def run_phase_1_planning(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl.run_phase_1_planning(*args, **kwargs)


def run_phase_2_compile_segment(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl.run_phase_2_compile_segment(*args, **kwargs)


def run_full_pipeline(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl.run_full_pipeline(*args, **kwargs)


def run_shot_director_resume_from_partial(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    with _bind_package_shot_director_node():
        return _impl.run_shot_director_resume_from_partial(*args, **kwargs)


def run_shot_director_restart_from_story_plan(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    with _bind_package_shot_director_node():
        return _impl.run_shot_director_restart_from_story_plan(*args, **kwargs)


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
    "_merge_state_update",
    "_prepare_phase_2_compile_state",
    "_run_phase_2_compile_direct",
]
