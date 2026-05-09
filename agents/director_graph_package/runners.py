"""Package runner entry points backed by the migrated director implementation."""
from __future__ import annotations

import os
import sys
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
_STATE_STORE_LOAD_STATE = load_state
_STATE_STORE_SAVE_STATE = save_state
_STATE_STORE_CLEAR_STATE = clear_state
_RUNNER_INVOKE_GRAPH: Any | None = None

HUMAN_REVIEW_NODES = [
    "scene_analyst",
    "director_showrunner",
    "rhythm_rewrite_director",
    "story_planner",
    "shot_director",
    "storyboard_designer",
    "prompt_compiler",
    "quality_inspector",
]

REVIEW_AGENT_LABELS = {
    "director_showrunner": "剧情增强",
    "rhythm_rewrite_director": "节奏总控",
    "scene_analyst": "场景预分析",
    "story_planner": "结构规划",
    "shot_director": "三段镜头导演",
    "storyboard_designer": "分镜流程图",
    "prompt_compiler": "Seedance编译",
    "quality_inspector": "质检导演",
}

REVIEW_AGENT_STEPS = {
    "director_showrunner": "step_0_enhance",
    "rhythm_rewrite_director": "step_0_rhythm",
    "scene_analyst": "step_0_scene",
    "story_planner": "step_2_plan",
    "shot_director": "step_3_direct",
    "storyboard_designer": "step_4_storyboard",
    "prompt_compiler": "step_5_compile",
    "quality_inspector": "step_6_inspect",
}

_NEXT_NODE_TO_REVIEW_AGENT = {
    "director_showrunner": "scene_analyst",
    "rhythm_rewrite_director": "director_showrunner",
    "story_planner": "rhythm_rewrite_director",
    "shot_director": "story_planner",
    "storyboard_designer": "shot_director",
    "wait_for_segment_request": "storyboard_designer",
    "quality_inspector": "prompt_compiler",
    "qc_router": "quality_inspector",
}


def _top_level_override(name: str, original: Any) -> Any | None:
    module = sys.modules.get("agents.director_graph")
    if module is None:
        return None
    candidate = getattr(module, name, None)
    if candidate is not None and candidate is not original:
        return candidate
    return None


def _load_runner_state() -> dict[str, Any]:
    if _impl.load_state is not _LEGACY_LOAD_STATE:
        return _impl.load_state()
    if load_state is not _STATE_STORE_LOAD_STATE:
        return load_state()
    override = _top_level_override("load_state", _STATE_STORE_LOAD_STATE)
    if override is not None:
        return override()
    return load_state()


def _save_runner_state(state: dict[str, Any]) -> None:
    if _impl.save_state is not _LEGACY_SAVE_STATE:
        _impl.save_state(state)
        return
    if save_state is not _STATE_STORE_SAVE_STATE:
        save_state(state)
        return
    override = _top_level_override("save_state", _STATE_STORE_SAVE_STATE)
    if override is not None:
        override(state)
        return
    save_state(state)


def _clear_runner_state() -> None:
    if clear_state is not _STATE_STORE_CLEAR_STATE:
        clear_state()
        return
    override = _top_level_override("clear_state", _STATE_STORE_CLEAR_STATE)
    if override is not None:
        override()
        return
    clear_state()


def _invoke_runner_graph(input_value: Any, thread_id: str) -> Any:
    original = _RUNNER_INVOKE_GRAPH or _invoke_graph
    if _invoke_graph is not original:
        return _invoke_graph(input_value, thread_id)
    override = _top_level_override("_invoke_graph", original)
    if override is not None:
        return override(input_value, thread_id)
    return _invoke_graph(input_value, thread_id)


def _rerun_shot_director(*, clear_knowledge_metadata: bool) -> Any:
    from .nodes import shot_director_node  # late import so test monkeypatches take effect

    state = _load_runner_state()
    if not state:
        raise RuntimeError("没有已保存的流水线状态，无法续跑镜头导演。")

    outputs = _agent_outputs(state)
    if not outputs.get("story_planner"):
        raise RuntimeError("缺少 story_planner 输出，无法续跑镜头导演。")
    if outputs.get("shot_director") and not clear_knowledge_metadata:
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


def _human_review_enabled(input_value: Any) -> bool:
    if isinstance(input_value, dict):
        return bool(input_value.get("human_review_enabled"))
    state = _load_runner_state()
    return bool(state.get("human_review_enabled"))


def _review_agent_after_break(next_nodes: Any, state: dict[str, Any]) -> str:
    next_node = ""
    if isinstance(next_nodes, (list, tuple)) and next_nodes:
        next_node = str(next_nodes[0])
    elif isinstance(next_nodes, str):
        next_node = next_nodes

    agent = _NEXT_NODE_TO_REVIEW_AGENT.get(next_node, "")
    if agent:
        return agent

    outputs = state.get("agent_outputs") or {}
    for candidate in reversed(HUMAN_REVIEW_NODES):
        if _review_output_for_agent(state, candidate):
            return candidate
    return ""


def _review_output_for_agent(state: dict[str, Any], agent: str) -> str:
    outputs = state.get("agent_outputs") or {}
    if not isinstance(outputs, dict):
        return ""

    if agent == "shot_director":
        for key in (
            "shot_director",
            "shot_director_final",
            "shot_director_guard",
            "shot_director_blocking",
            "shot_director_layout",
        ):
            if outputs.get(key):
                return str(outputs.get(key))
        return ""

    if agent == "prompt_compiler":
        seg_idx = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
        for key in (f"compiled_segment_{seg_idx}", "prompt_compiler"):
            if outputs.get(key):
                return str(outputs.get(key))
        return str(state.get("result") or "")

    if agent == "quality_inspector":
        seg_idx = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
        for key in (f"quality_inspector_segment_{seg_idx}", "quality_inspector"):
            if outputs.get(key):
                return str(outputs.get(key))
        return ""

    if agent == "storyboard_designer":
        seg_idx = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
        for key in (
            f"storyboard_prompt_seg{seg_idx:02d}",
            f"storyboard_prompt_seg{seg_idx}",
            "storyboard_designer",
        ):
            if outputs.get(key):
                return str(outputs.get(key))
        image_path = (
            outputs.get(f"storyboard_image_seg{seg_idx:02d}")
            or outputs.get(f"storyboard_image_seg{seg_idx}")
            or outputs.get("storyboard_image")
        )
        return str(image_path or "")

    return str(outputs.get(agent) or "")


def _mark_human_review_state(state: dict[str, Any], next_nodes: Any) -> dict[str, Any]:
    agent = _review_agent_after_break(next_nodes, state)
    if not agent:
        return state

    label = REVIEW_AGENT_LABELS.get(agent, agent)
    state["status"] = "waiting_for_user_input"
    state["review_mode"] = "agent_output"
    state["review_agent"] = agent
    state["review_title"] = label
    state["review_output"] = _review_output_for_agent(state, agent)
    state["step"] = REVIEW_AGENT_STEPS.get(agent, state.get("step") or "")
    state["message"] = f"{label}已完成，请审核/修改后继续。"
    _save_runner_state(dict(state))
    return state


def _apply_human_review_edit(
    state: dict[str, Any],
    agent: str,
    edited_output: str,
) -> dict[str, Any]:
    outputs = dict(state.get("agent_outputs") or {})
    edited = edited_output or ""
    outputs[agent] = edited

    if agent == "scene_analyst":
        state["scene_context_brief"] = edited
    elif agent == "director_showrunner":
        from .planning_context_impl import _director_enhancement_contract, _extract_enhanced_script

        source_script = str(state.get("original_script") or state.get("script") or "")
        enhanced_script = _extract_enhanced_script(edited, source_script)
        state["script"] = enhanced_script
        state["enhanced_script"] = enhanced_script
        state["director_brief"] = _director_enhancement_contract(edited, enhanced_script)
    elif agent == "rhythm_rewrite_director":
        state["atmosphere_strategy"] = edited
    elif agent == "story_planner":
        from .story_planner_impl import _extract_segments

        total_segments, segment_names = _extract_segments(edited)
        state["total_segments"] = total_segments
        state["segment_names"] = segment_names
        state["current_segment_index"] = 1
    elif agent == "shot_director":
        outputs["shot_director"] = edited
        outputs["shot_director_final"] = edited
    elif agent == "storyboard_designer":
        seg_idx = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
        if edited:
            outputs[f"storyboard_prompt_seg{seg_idx:02d}"] = edited
    elif agent == "prompt_compiler":
        seg_idx = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
        outputs[f"compiled_segment_{seg_idx}"] = edited
        outputs["prompt_compiler"] = edited
        state["result"] = edited
    elif agent == "quality_inspector":
        seg_idx = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
        outputs[f"quality_inspector_segment_{seg_idx}"] = edited
        outputs["quality_inspector"] = edited

    state["agent_outputs"] = outputs
    state["human_review_enabled"] = True
    state.pop("review_mode", None)
    state.pop("review_agent", None)
    state.pop("review_title", None)
    state.pop("review_output", None)
    state["status"] = "running_phase_2" if agent in {"prompt_compiler", "quality_inspector"} else "running_phase_1"
    state["message"] = f"已确认 {REVIEW_AGENT_LABELS.get(agent, agent)} 输出，正在交给下一个 Agent..."
    state["error"] = ""
    return state


def _invoke_graph(input_value: Any, thread_id: str) -> Any:
    from langgraph.checkpoint.sqlite import SqliteSaver

    from .graph_api import create_director_graph

    os.makedirs(_session_output_dir(), exist_ok=True)
    review_enabled = _human_review_enabled(input_value)
    interrupt_after = HUMAN_REVIEW_NODES if review_enabled else None
    with SqliteSaver.from_conn_string(_checkpoint_file()) as checkpointer:
        app = create_director_graph().compile(
            checkpointer=checkpointer,
            interrupt_after=interrupt_after,
        )
        config = _config(thread_id)
        if input_value is None and review_enabled:
            saved_state = _load_runner_state()
            if saved_state:
                app.update_state(config, saved_state)
        result = app.invoke(input_value, config=config)
        snapshot = app.get_state(config)
    state = _normalise_graph_result(result, thread_id)
    if review_enabled and getattr(snapshot, "next", ()):
        state = _mark_human_review_state(dict(state), getattr(snapshot, "next", ()))
    return state


_RUNNER_INVOKE_GRAPH = _invoke_graph


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
    _save_runner_state(dict(working_state))

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


def _run_phase_2_until_review(
    state: Any,
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> Any:
    from .prompt_compiler_impl import prompt_compiler_node

    prepared_update = _prepare_phase_2_compile_state(state, segment_index, tail_frame_b64, video_path)
    working_state = _merge_state_update(state, prepared_update)
    working_state["human_review_enabled"] = True
    _save_runner_state(dict(working_state))

    compile_update = prompt_compiler_node(working_state)
    working_state = _merge_state_update(working_state, compile_update)
    working_state["human_review_enabled"] = True
    return _mark_human_review_state(dict(working_state), ("quality_inspector",))


def _resume_phase_2_review_direct(state: dict[str, Any], agent: str, edited: str) -> Any:
    from .nodes import segment_complete_node
    from .prompt_compiler_impl import prompt_compiler_node
    from .quality_inspector_impl import quality_inspector_node, qc_router_node

    working_state = _apply_human_review_edit(dict(state), agent, edited)
    working_state["human_review_enabled"] = True
    _save_runner_state(dict(working_state))

    if agent == "prompt_compiler":
        inspect_update = quality_inspector_node(working_state)
        working_state = _merge_state_update(working_state, inspect_update)
        working_state["human_review_enabled"] = True
        return _mark_human_review_state(dict(working_state), ("qc_router",))

    if agent == "quality_inspector":
        router_update = qc_router_node(working_state)
        working_state = _merge_state_update(working_state, router_update)
        working_state["human_review_enabled"] = True
        if working_state.get("revision_instruction"):
            compile_update = prompt_compiler_node(working_state)
            working_state = _merge_state_update(working_state, compile_update)
            working_state["human_review_enabled"] = True
            return _mark_human_review_state(dict(working_state), ("quality_inspector",))
        complete_update = segment_complete_node(working_state)
        working_state = _merge_state_update(working_state, complete_update)
        _save_runner_state(dict(working_state))
        return working_state

    raise RuntimeError(f"Agent {agent} is not a direct phase-2 review agent.")


def run_phase_1_planning(
    script: str,
    aspect_ratio: str,
    reference_images: str | None,
    reference_image_b64s: list[str] | None = None,
    reference_image_manifest: list[dict[str, str]] | None = None,
    speed_mode: bool = False,
    model_profile_snapshot: dict[str, Any] | None = None,
    asset_selection: dict[str, Any] | None = None,
) -> Any:
    reference_image_b64s = reference_image_b64s or []
    reference_image_manifest = reference_image_manifest or []
    reference_image_count = len(reference_image_b64s)
    stored_reference_images = reference_image_b64s

    _clear_runner_state()
    thread_id = f"director-{uuid.uuid4().hex}"
    initial_state = {
        "thread_id": thread_id,
        "status": "running_phase_1",
        "step": "step_0_scene",
        "message": "场景预分析正在读取参考图、人物站位和空间信息...（1/8）",
        "script": script,
        "original_script": script,
        "enhanced_script": "",
        "scene_context_brief": "",
        "atmosphere_strategy": "",
        "director_brief": "",
        "aspect_ratio": aspect_ratio,
        "speed_mode": speed_mode,
        "reference_images": reference_images,
        "reference_image_b64s": stored_reference_images,
        "reference_image_count": reference_image_count,
        "reference_image_manifest": reference_image_manifest,
        "model_profile_snapshot": model_profile_snapshot or {},
        "asset_selection": asset_selection or {},
        "director_review_required": False,
        "director_edits_by_segment": {},
        "shot_director_original_by_segment": {},
        "shot_director_approved_by_segment": {},
        "knowledge_metadata": {},
        "agent_outputs": {},
        "current_segment_index": 1,
        "total_segments": 0,
        "segment_names": [],
        "started_at": datetime.now().isoformat(),
        "result": "",
        "error": "",
        "director_review_report": "",
        "human_review_enabled": True,
    }
    _save_runner_state(dict(initial_state))
    return _invoke_runner_graph(initial_state, thread_id)


def run_phase_2_compile_segment(
    segment_index: int,
    tail_frame_b64: str | None = None,
    video_path: str | None = None,
) -> Any:
    state = _load_runner_state()
    if not state:
        raise RuntimeError("没有已保存的流水线状态，无法生成片段。")

    outputs = _agent_outputs(state)
    if not outputs.get("story_planner"):
        raise RuntimeError("缺少 story_planner 输出，无法生成片段。")

    if outputs.get("shot_director"):
        if state.get("human_review_enabled"):
            result = _run_phase_2_until_review(state, segment_index, tail_frame_b64, video_path)
            _save_runner_state(dict(result))
            return result
        result = _run_phase_2_compile_direct(state, segment_index, tail_frame_b64, video_path)
        _save_runner_state(dict(result))
        return result

    thread_id = state.get("thread_id")
    if not thread_id:
        raise RuntimeError("缺少 thread_id，无法恢复图执行。")
    return _invoke_runner_graph(state, thread_id)


def run_full_pipeline(
    script: str,
    aspect_ratio: str = "16:9",
    reference_images: str | None = None,
    reference_image_b64s: list[str] | None = None,
    reference_image_manifest: list[dict[str, str]] | None = None,
    speed_mode: bool = False,
    model_profile_snapshot: dict[str, Any] | None = None,
    asset_selection: dict[str, Any] | None = None,
) -> Any:
    return run_phase_1_planning(
        script=script,
        aspect_ratio=aspect_ratio,
        reference_images=reference_images,
        reference_image_b64s=reference_image_b64s,
        reference_image_manifest=reference_image_manifest,
        speed_mode=speed_mode,
        model_profile_snapshot=model_profile_snapshot,
        asset_selection=asset_selection,
    )


def resume_after_human_review(
    edited_output: str | None = None,
    review_agent: str | None = None,
) -> Any:
    state = _load_runner_state()
    if not state:
        raise RuntimeError("No saved pipeline state, cannot resume human review.")
    if state.get("status") != "waiting_for_user_input" or state.get("review_mode") != "agent_output":
        raise RuntimeError("Current pipeline is not waiting for an agent output review.")

    agent = (review_agent or state.get("review_agent") or "").strip()
    if agent not in HUMAN_REVIEW_NODES:
        raise RuntimeError(f"Unknown review agent: {agent or '<empty>'}")

    edited = edited_output if edited_output is not None else state.get("review_output") or ""
    if agent in {"prompt_compiler", "quality_inspector"}:
        return _resume_phase_2_review_direct(dict(state), agent, str(edited))

    updated_state = _apply_human_review_edit(dict(state), agent, str(edited))
    _save_runner_state(dict(updated_state))
    thread_id = updated_state.get("thread_id")
    if not thread_id:
        raise RuntimeError("Missing thread_id, cannot resume graph checkpoint.")
    return _invoke_runner_graph(None, str(thread_id))


def run_shot_director_resume_from_partial(*args: Any, **kwargs: Any) -> Any:
    return _rerun_shot_director(clear_knowledge_metadata=False)


def run_shot_director_restart_from_story_plan(*args: Any, **kwargs: Any) -> Any:
    return _rerun_shot_director(clear_knowledge_metadata=True)


__all__ = [
    "run_phase_1_planning",
    "run_full_pipeline",
    "run_phase_2_compile_segment",
    "resume_after_human_review",
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
