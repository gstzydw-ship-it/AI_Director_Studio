"""Compatibility graph-construction exports for the director graph pipeline."""

from langgraph.graph import END, START, StateGraph

from .nodes import (
    director_showrunner_node,
    prompt_compiler_node,
    qc_router_node,
    quality_inspector_node,
    rhythm_rewrite_director_node,
    scene_analyst_node,
    segment_complete_node,
    shot_director_node,
    story_planner_node,
    storyboard_designer_node,
    wait_for_segment_request_node,
)
from .runners import route_after_qc, route_after_segment
from .types import DirectorState


def create_director_graph():
    graph = StateGraph(DirectorState)
    graph.add_node("director_showrunner", director_showrunner_node)
    graph.add_node("scene_analyst", scene_analyst_node)
    graph.add_node("story_planner", story_planner_node)
    graph.add_node("shot_director", shot_director_node)
    graph.add_node("storyboard_designer", storyboard_designer_node)
    graph.add_node("wait_for_segment_request", wait_for_segment_request_node)
    graph.add_node("prompt_compiler", prompt_compiler_node)
    graph.add_node("quality_inspector", quality_inspector_node)
    graph.add_node("qc_router", qc_router_node)
    graph.add_node("segment_complete", segment_complete_node)

    # 先做轻量场景预分析，锁住参考图、站位姿势和空间锚点，再让剧情增强在该框架内可拍化。
    graph.add_node("rhythm_rewrite_director", rhythm_rewrite_director_node)
    graph.add_edge(START, "scene_analyst")
    graph.add_edge("scene_analyst", "director_showrunner")
    graph.add_edge("director_showrunner", "rhythm_rewrite_director")
    graph.add_edge("rhythm_rewrite_director", "story_planner")
    graph.add_edge("story_planner", "shot_director")
    graph.add_edge("shot_director", "storyboard_designer")
    graph.add_edge("storyboard_designer", "wait_for_segment_request")
    graph.add_edge("wait_for_segment_request", "prompt_compiler")
    graph.add_edge("prompt_compiler", "quality_inspector")
    graph.add_edge("quality_inspector", "qc_router")
    graph.add_conditional_edges(
        "qc_router",
        route_after_qc,
        {
            "prompt_compiler": "prompt_compiler",
            "segment_complete": "segment_complete",
        },
    )
    graph.add_conditional_edges(
        "segment_complete",
        route_after_segment,
        {
            "wait_for_segment_request": "wait_for_segment_request",
            END: END,
        },
    )
    return graph


__all__ = ["create_director_graph"]
