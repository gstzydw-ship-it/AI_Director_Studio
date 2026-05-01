"""Package runner entry points backed by the migrated director implementation."""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any

from . import legacy_impl as _impl
from .state_store import (
    _agent_outputs,
    _checkpoint_file,
    _config as _state_store_config,
    _merge_state_update as _state_store_merge_state_update,
    _normalise_graph_result as _state_store_normalise_graph_result,
    _prepare_phase_2_compile_state as _state_store_prepare_phase_2_compile_state,
    _session_output_dir,
    clear_state,
    load_state,
    save_state,
)

_LEGACY_LOAD_STATE = _impl.load_state
_LEGACY_SAVE_STATE = _impl.save_state
_LEGACY_INVOKE_GRAPH = _impl._invoke_graph


def _load_runner_state() -> dict[str, Any]:
    if _impl.load_state is not _LEGACY_LOAD_STATE:
        return _impl.load_state()
    return load_state()


def _save_runner_state(state: dict[str, Any]) -> None:
    if _impl.save_state is not _LEGACY_SAVE_STATE:
        _impl.save_state(state)
        return
    save_state(state)


def _invoke_runner_graph(input_value: Any, thread_id: str) -> Any:
    if _impl._invoke_graph is not _LEGACY_INVOKE_GRAPH:
        return _impl._invoke_graph(input_value, thread_id)
    return _invoke_graph(input_value, thread_id)


def _rerun_shot_director(*, clear_knowledge_metadata: bool) -> Any:
    from .shot_director_impl import shot_director_node

    state = _load_runner_state()
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
    _save_runner_state(state)
    return shot_director_node(state)


def route_after_qc(state: Any) -> Any:
    from .quality_inspector_impl import route_after_qc as _route_after_qc

    return _route_after_qc(state)


def route_after_segment(state: Any) -> Any:
    from .segment_flow_impl import route_after_segment as _route_after_segment

    return _route_after_segment(state)


def _config(*args: Any, **kwargs: Any) -> Any:
    return _state_store_config(*args, **kwargs)


def _invoke_graph(input_value: Any, thread_id: str) -> Any:
    from langgraph.checkpoint.sqlite import SqliteSaver

    from .graph_api import create_director_graph

    os.makedirs(_session_output_dir(), exist_ok=True)
    with SqliteSaver.from_conn_string(_checkpoint_file()) as checkpointer:
        app = create_director_graph().compile(checkpointer=checkpointer)
        result = app.invoke(input_value, config=_config(thread_id))
    return _normalise_graph_result(result, thread_id)


def _normalise_graph_result(*args: Any, **kwargs: Any) -> Any:
    return _state_store_normalise_graph_result(*args, **kwargs)


def _merge_state_update(*args: Any, **kwargs: Any) -> Any:
    return _state_store_merge_state_update(*args, **kwargs)


def _prepare_phase_2_compile_state(*args: Any, **kwargs: Any) -> Any:
    return _state_store_prepare_phase_2_compile_state(*args, **kwargs)


def _run_phase_2_compile_direct(
    state: Any,
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> Any:
    from .nodes import segment_complete_node
    from .prompt_compiler_impl import prompt_compiler_node
    from .quality_inspector_impl import quality_inspector_node, qc_router_node

    prepared_update = _prepare_phase_2_compile_state(state, segment_index, tail_frame_b64, video_path)
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


def run_phase_1_planning(
    script: str,
    aspect_ratio: str,
    reference_images: str | None,
    reference_image_b64s: list[str] | None = None,
    reference_image_manifest: list[dict[str, str]] | None = None,
    speed_mode: bool = False,
) -> Any:
    reference_image_b64s = reference_image_b64s or []
    reference_image_manifest = reference_image_manifest or []
    reference_image_count = len(reference_image_b64s)
    stored_reference_images = reference_image_b64s

    clear_state()
    thread_id = f"director-{uuid.uuid4().hex}"
    initial_state = {
        "thread_id": thread_id,
        "status": "running_phase_1",
        "step": "step_1_analyze",
        "message": "节奏总控导演正在改写剧本...（1/6）",
        "script": script,
        "original_script": script,
        "atmosphere_strategy": "",
        "director_brief": "",
        "aspect_ratio": aspect_ratio,
        "speed_mode": speed_mode,
        "reference_images": reference_images,
        "reference_image_b64s": stored_reference_images,
        "reference_image_count": reference_image_count,
        "reference_image_manifest": reference_image_manifest,
        "knowledge_metadata": {},
        "agent_outputs": {},
        "current_segment_index": 1,
        "total_segments": 0,
        "segment_names": [],
        "started_at": datetime.now().isoformat(),
        "result": "",
        "error": "",
        "director_review_report": "",
    }
    save_state(dict(initial_state))
    return _invoke_graph(initial_state, thread_id)


def run_phase_2_compile_segment(
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> Any:
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
    return _invoke_graph(state, thread_id)


def run_full_pipeline(
    script: str,
    aspect_ratio: str = "16:9",
    reference_images: str | None = None,
    reference_image_b64s: list[str] | None = None,
    reference_image_manifest: list[dict[str, str]] | None = None,
    speed_mode: bool = False,
) -> Any:
    return run_phase_1_planning(
        script=script,
        aspect_ratio=aspect_ratio,
        reference_images=reference_images,
        reference_image_b64s=reference_image_b64s,
        reference_image_manifest=reference_image_manifest,
        speed_mode=speed_mode,
    )


def run_shot_director_resume_from_partial(*args: Any, **kwargs: Any) -> Any:
    return _rerun_shot_director(clear_knowledge_metadata=False)


def run_shot_director_restart_from_story_plan(*args: Any, **kwargs: Any) -> Any:
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
