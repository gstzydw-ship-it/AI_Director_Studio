"""Modular helpers for the director graph pipeline.

Submodules already extracted:
  - types       : DirectorState, LLMSettings, constants
  - llm         : call_llm, resolve_llm_settings, config helpers
  - state_store : load_state, save_state, clear_state, session helpers
  - prompting   : build_system_prompt, knowledge metadata helpers
  - helpers     : lightweight state helpers
  - nodes       : public graph nodes
  - runners     : public pipeline runners and routers
  - graph_api   : create_director_graph

Public graph API, nodes, and runners now resolve through package modules.
Some internal helpers are still reused from the legacy monolith while
Phase D continues to shrink the monolith.
"""

# Prefer already-extracted implementations from submodules.
from .llm import _get_llm_settings, call_llm, resolve_llm_settings
from .prompting import build_system_prompt
from .state_store import clear_state, load_state, save_state
from .types import DirectorState, LLMSettings

# Graph nodes / runners / graph API are exposed lazily so importing
# ``prompting`` does not also force-load the graph construction modules,
# which may still depend on legacy helpers.
def __getattr__(name: str):
    if name == "create_director_graph":
        from .graph_api import create_director_graph

        return create_director_graph

    if name in {
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
    }:
        from . import nodes as _nodes

        return getattr(_nodes, name)

    if name in {
        "route_after_qc",
        "route_after_segment",
        "run_phase_1_planning",
        "run_phase_2_compile_segment",
        "run_shot_director_resume_from_partial",
        "run_shot_director_restart_from_story_plan",
        "run_full_pipeline",
    }:
        from . import runners as _runners

        return getattr(_runners, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # graph nodes
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
    # routers
    "route_after_qc",
    "route_after_segment",
    # runners
    "run_phase_1_planning",
    "run_phase_2_compile_segment",
    "run_shot_director_resume_from_partial",
    "run_shot_director_restart_from_story_plan",
    "run_full_pipeline",
    # core helpers
    "call_llm",
    "create_director_graph",
    "clear_state",
    "load_state",
    "save_state",
    "build_system_prompt",
    "resolve_llm_settings",
    "_get_llm_settings",
    # types
    "DirectorState",
    "LLMSettings",
]
