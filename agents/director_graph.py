"""Backward-compatible shim for the modular director graph package.

The implementation lives in ``agents.director_graph_package``. This module keeps
legacy imports such as ``from agents.director_graph import run_phase_1_planning``
working while preventing new code from depending on a monolithic implementation
at this path.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_IMPL = import_module("agents.director_graph_package.legacy_impl")
_MODULES = tuple(
    import_module(name)
    for name in (
        "agents.director_graph_package.types",
        "agents.director_graph_package.llm",
        "agents.director_graph_package.state_store",
        "agents.director_graph_package.prompting",
        "agents.director_graph_package.shot_director_impl",
        "agents.director_graph_package.story_planner_impl",
        "agents.director_graph_package.prompt_compiler_impl",
        "agents.director_graph_package.quality_inspector_impl",
        "agents.director_graph_package.helpers",
        "agents.director_graph_package.nodes",
        "agents.director_graph_package.runners",
        "agents.director_graph_package.graph_api",
        "agents.director_graph_package.legacy_impl",
    )
)

_PUBLIC_EXPORTS = {
    "DirectorState",
    "LLMSettings",
    "ROOT_DIR",
    "OUTPUT_DIR",
    "STATE_FILE",
    "CHECKPOINT_FILE",
    "CONFIG_FILE",
    "SESSION_ID_RE",
    "MAX_QC_RETRIES",
    "STORY_PLANNER_MAX_SCHEMA_ATTEMPTS",
    "AGENT_CONFIG_PARENTS",
    "DEFAULT_LLM_MODEL",
    "load_config",
    "resolve_llm_settings",
    "_get_llm_settings",
    "call_llm",
    "clear_state",
    "load_state",
    "save_state",
    "build_system_prompt",
    "create_director_graph",
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
    "route_after_qc",
    "route_after_segment",
    "run_phase_1_planning",
    "run_full_pipeline",
    "run_phase_2_compile_segment",
    "run_shot_director_resume_from_partial",
    "run_shot_director_restart_from_story_plan",
}


def __getattr__(name: str) -> Any:
    for module in _MODULES:
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    names = set(globals()) | set(_PUBLIC_EXPORTS)
    for module in _MODULES:
        names.update(getattr(module, "__dict__", {}).keys())
    return sorted(names)


for _name in sorted(_PUBLIC_EXPORTS):
    try:
        globals()[_name] = __getattr__(_name)
    except AttributeError:
        pass

__all__ = sorted(name for name in _PUBLIC_EXPORTS if name in globals())
