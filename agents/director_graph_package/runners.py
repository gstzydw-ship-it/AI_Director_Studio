"""Package runner entry points backed by the migrated director implementation."""
from __future__ import annotations

from typing import Any

from . import legacy_impl as _impl
from .state_store import _agent_outputs, _config as _state_store_config, _merge_state_update, load_state, save_state


def _sync_package_graph_api() -> None:
    from .graph_api import create_director_graph
    from .shot_director_impl import shot_director_node

    _impl.create_director_graph = create_director_graph
    _impl.shot_director_node = shot_director_node


def _rerun_shot_director(*, clear_knowledge_metadata: bool) -> Any:
    from .shot_director_impl import shot_director_node

    state = load_state()
    if not state:
        raise RuntimeError("没有已保存的流水线状态，无法续跑镜头导演。")

    outputs = _agent_outputs(state)
    if not outputs.get("story_planner"):
        raise RuntimeError("缺少 story_planner 输出，无法续跑镜头导演。")
    if outputs.get("shot_director"):
        return state

    for key in (
        "shot_director_layout",
        "shot_director_blocking",
        "shot_director_guard",
        "shot_director_final",
        "shot_director",
    ):
        outputs.pop(key, None)

    if clear_knowledge_metadata:
        knowledge_metadata = state.get("knowledge_metadata")
        if isinstance(knowledge_metadata, dict):
            knowledge_metadata.pop("shot_director", None)

    state["agent_outputs"] = outputs
    state["status"] = "running_phase_1"
    state["step"] = "step_3_direct"
    state["message"] = (
        "已复用前三步宏观规划，正在重新启动镜头导演...（4/6）"
        if clear_knowledge_metadata
        else "已复用宏观规划，正在重新运行镜头导演...（4/6）"
    )
    state["error"] = ""
    save_state(state)
    return shot_director_node(state)


def route_after_qc(state: Any) -> Any:
    from .quality_inspector_impl import route_after_qc as _route_after_qc

    return _route_after_qc(state)


def route_after_segment(state: Any) -> Any:
    from .segment_flow_impl import route_after_segment as _route_after_segment

    return _route_after_segment(state)


def _config(*args: Any, **kwargs: Any) -> Any:
    return _state_store_config(*args, **kwargs)


def _invoke_graph(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl._invoke_graph(*args, **kwargs)


def _normalise_graph_result(*args: Any, **kwargs: Any) -> Any:
    return _impl._normalise_graph_result(*args, **kwargs)


def _merge_state_update(*args: Any, **kwargs: Any) -> Any:
    return _merge_state_update(*args, **kwargs)


def _prepare_phase_2_compile_state(*args: Any, **kwargs: Any) -> Any:
    return _impl._prepare_phase_2_compile_state(*args, **kwargs)


def _run_phase_2_compile_direct(
    state: Any,
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> Any:
    from .nodes import segment_complete_node
    from .prompt_compiler_impl import prompt_compiler_node
    from .quality_inspector_impl import quality_inspector_node, qc_router_node

    prepared_update = _impl._prepare_phase_2_compile_state(state, segment_index, tail_frame_b64, video_path)
    working_state = _merge_state_update(state, prepared_update)

    while True:
        compile_update = prompt_compiler_node(working_state)
        working_state = _merge_state_update(working_state, compile_update)

        inspect_update = quality_inspector_node(working_state)
        working_state = _merge_state_update(working_state, inspect_update)

        router_update = qc_router_node(working_state)
        working_state = _merge_state_update(working_state, router_update)
        if not working_state.get("revision_instruction"):
            break

    complete_update = segment_complete_node(working_state)
    return _merge_state_update(working_state, complete_update)


def run_phase_1_planning(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl.run_phase_1_planning(*args, **kwargs)


def run_phase_2_compile_segment(
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> Any:
    _sync_package_graph_api()

    state = load_state()
    if not state:
        raise RuntimeError("没有已保存的流水线状态，无法生成片段。")

    outputs = _agent_outputs(state)
    if not outputs.get("story_planner"):
        raise RuntimeError("缺少 story_planner 输出，无法生成片段。")

    if outputs.get("shot_director"):
        result = _run_phase_2_compile_direct(state, segment_index, tail_frame_b64, video_path)
        save_state(dict(result))
        return result

    thread_id = state.get("thread_id")
    if not thread_id:
        raise RuntimeError("缺少 thread_id，无法恢复图执行。")
    return _impl._invoke_graph(state, thread_id)


def run_full_pipeline(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _impl.run_full_pipeline(*args, **kwargs)


def run_shot_director_resume_from_partial(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _rerun_shot_director(clear_knowledge_metadata=False)


def run_shot_director_restart_from_story_plan(*args: Any, **kwargs: Any) -> Any:
    _sync_package_graph_api()
    return _rerun_shot_director(clear_knowledge_metadata=True)


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
