"""Backward-compatible shim for the modular director graph package.

The implementation lives in ``agents.director_graph_package``. This module keeps
legacy imports such as ``from agents.director_graph import run_phase_1_planning``
working while preventing new code from depending on a monolithic implementation
at this path.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_MODULE_NAMES = (
    "agents.director_graph_package.types",
    "agents.director_graph_package.llm",
    "agents.director_graph_package.state_store",
    "agents.director_graph_package.prompting",
    "agents.director_graph_package.story_planner_impl",
    "agents.director_graph_package.shot_director_impl",
    "agents.director_graph_package.prompt_compiler_impl",
    "agents.director_graph_package.quality_inspector_impl",
    "agents.director_graph_package.helpers",
    "agents.director_graph_package.nodes",
    "agents.director_graph_package.runners",
    "agents.director_graph_package.graph_api",
    "agents.director_graph_package.legacy_impl",
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
    "_get_llm_extra_params",
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
    "storyboard_designer_node",
    "route_after_qc",
    "route_after_segment",
    "run_phase_1_planning",
    "run_full_pipeline",
    "run_phase_2_compile_segment",
    "resume_after_human_review",
    "generate_storyboard_for_segment",
    "run_shot_director_resume_from_partial",
    "run_shot_director_restart_from_story_plan",
    "_run_shot_director_review_board",
    "_run_shot_director_single_pass",
    "_run_shot_director_three_stage",
    "_collect_shot_director_issues",
}


def _sync_llm_overrides(module: Any) -> dict[str, Any]:
    originals: dict[str, Any] = {}
    load_config_override = globals().get("load_config")
    if load_config_override is not None and load_config_override is not _LOAD_CONFIG_WRAPPER:
        originals["load_config"] = module.load_config
        module.load_config = load_config_override

    extra_params_override = globals().get("_get_llm_extra_params")
    if extra_params_override is not None and extra_params_override is not _GET_LLM_EXTRA_PARAMS_WRAPPER:
        originals["_get_llm_extra_params"] = module._get_llm_extra_params
        module._get_llm_extra_params = extra_params_override
    return originals


def _restore_overrides(module: Any, originals: dict[str, Any]) -> None:
    for name, value in originals.items():
        setattr(module, name, value)


def load_config() -> dict[str, Any]:
    module = import_module("agents.director_graph_package.llm")
    return module.load_config()


def resolve_llm_settings(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.llm")
    originals = _sync_llm_overrides(module)
    try:
        return module.resolve_llm_settings(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


def _get_llm_settings(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.llm")
    originals = _sync_llm_overrides(module)
    try:
        return module._get_llm_settings(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


def _get_llm_extra_params(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.llm")
    originals = _sync_llm_overrides(module)
    try:
        return module._get_llm_extra_params(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


def call_llm(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.llm")
    originals = _sync_llm_overrides(module)
    try:
        return module.call_llm(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


def _sync_state_store_overrides(module: Any) -> dict[str, Any]:
    originals: dict[str, Any] = {}
    if "OUTPUT_DIR" in globals():
        originals["OUTPUT_DIR"] = module.OUTPUT_DIR
        module.OUTPUT_DIR = globals()["OUTPUT_DIR"]
    return originals


def load_state(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.state_store")
    originals = _sync_state_store_overrides(module)
    try:
        return module.load_state(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


def save_state(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.state_store")
    originals = _sync_state_store_overrides(module)
    try:
        return module.save_state(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


def clear_state(*args: Any, **kwargs: Any) -> Any:
    module = import_module("agents.director_graph_package.state_store")
    originals = _sync_state_store_overrides(module)
    try:
        return module.clear_state(*args, **kwargs)
    finally:
        _restore_overrides(module, originals)


_LOAD_CONFIG_WRAPPER = load_config
_GET_LLM_EXTRA_PARAMS_WRAPPER = _get_llm_extra_params


def _iter_modules():
    for module_name in _MODULE_NAMES:
        yield import_module(module_name)


def __getattr__(name: str) -> Any:
    for module in _iter_modules():
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    names = set(globals()) | set(_PUBLIC_EXPORTS)
    for module in _iter_modules():
        names.update(getattr(module, "__dict__", {}).keys())
    return sorted(names)


__all__ = sorted(_PUBLIC_EXPORTS)
