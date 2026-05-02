from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
import agents.director_graph_package.nodes as pkg_nodes
import agents.director_graph_package.prompt_compiler_impl as prompt_compiler_impl
import agents.director_graph_package.quality_inspector_impl as quality_inspector_impl
import agents.director_graph_package.runners as pkg_runners


def _base_state(agent_outputs: dict[str, str]) -> dict:
    return {
        "thread_id": "thread-test",
        "status": "waiting_for_user_input",
        "script": "script",
        "aspect_ratio": "9:16",
        "total_segments": 2,
        "current_segment_index": 1,
        "agent_outputs": agent_outputs,
    }


def test_phase_2_resume_uses_persisted_shot_director_without_graph_resume(monkeypatch):
    state = _base_state(
        {
            "scene_analyst": "scene",
            "story_planner": "planner",
            "shot_director": "director",
        }
    )
    saved_states: list[dict] = []
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(pkg_runners._impl, "load_state", lambda: dict(state))
    monkeypatch.setattr(pkg_runners._impl, "save_state", lambda saved: saved_states.append(dict(saved)))
    monkeypatch.setattr(pkg_runners._impl, "_analyze_tail_frame", lambda tail_frame_b64, idx: f"tail-{idx}-{tail_frame_b64}")

    def fail_graph_resume(*_args, **_kwargs):
        raise AssertionError("phase 2 should not resume the graph when shot_director already exists")

    monkeypatch.setattr(pkg_runners, "_invoke_graph", fail_graph_resume)

    def prompt_node(node_state):
        calls.append(("compile", node_state["tail_frame_analysis"]))
        outputs = dg._agent_outputs(node_state)
        outputs["compiled_segment_2"] = "compiled"
        outputs["prompt_compiler"] = "compiled"
        return {
            "status": "running_phase_2",
            "step": "step_5_inspect",
            "agent_outputs": outputs,
        }

    def inspect_node(node_state):
        calls.append(("inspect", dg._agent_outputs(node_state)["compiled_segment_2"]))
        outputs = dg._agent_outputs(node_state)
        outputs["quality_inspector"] = "pass"
        return {
            "status": "running_phase_2",
            "last_qc_status": "pass",
            "agent_outputs": outputs,
        }

    def route_node(node_state):
        calls.append(("route", node_state["last_qc_status"]))
        return {"revision_instruction": ""}

    def complete_node(node_state):
        calls.append(("complete", str(node_state["active_segment_index"])))
        return {
            "status": "done",
            "step": "",
            "current_segment_index": 3,
            "result": "compiled",
            "agent_outputs": node_state["agent_outputs"],
        }

    monkeypatch.setattr(prompt_compiler_impl, "prompt_compiler_node", prompt_node)
    monkeypatch.setattr(quality_inspector_impl, "quality_inspector_node", inspect_node)
    monkeypatch.setattr(quality_inspector_impl, "qc_router_node", route_node)
    monkeypatch.setattr(pkg_nodes, "segment_complete_node", complete_node)

    result = dg.run_phase_2_compile_segment(9, tail_frame_b64="frame")

    assert result["status"] == "done"
    assert result["active_segment_index"] == 2
    assert result["agent_outputs"]["compiled_segment_2"] == "compiled"
    assert saved_states[0]["step"] == "step_4_compile"
    assert calls == [
        ("compile", "tail-2-frame"),
        ("inspect", "compiled"),
        ("route", "pass"),
        ("complete", "2"),
    ]


def test_phase_2_resume_falls_back_to_graph_without_shot_director(monkeypatch):
    state = _base_state({"story_planner": "planner"})
    invoked: dict[str, str] = {}

    monkeypatch.setattr(pkg_runners._impl, "load_state", lambda: dict(state))
    monkeypatch.setattr(
        pkg_runners,
        "_run_phase_2_compile_direct",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("direct path should not run")),
    )

    def graph_resume(_input_value, thread_id):
        invoked["thread_id"] = thread_id
        return {"status": "graph-resumed"}

    monkeypatch.setattr(pkg_runners, "_invoke_graph", graph_resume)

    result = dg.run_phase_2_compile_segment(1)

    assert result == {"status": "graph-resumed"}
    assert invoked == {"thread_id": "thread-test"}


def test_phase_2_resume_ignores_legacy_graph_override(monkeypatch):
    state = _base_state({"story_planner": "planner"})
    invoked: dict[str, str] = {}

    monkeypatch.setattr(pkg_runners._impl, "load_state", lambda: dict(state))
    monkeypatch.setattr(
        pkg_runners._impl,
        "_invoke_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("runner graph resume should not use legacy_impl._invoke_graph")
        ),
    )

    def package_graph_resume(_input_value, thread_id):
        invoked["thread_id"] = thread_id
        return {"status": "package-graph-resumed"}

    monkeypatch.setattr(pkg_runners, "_invoke_graph", package_graph_resume)

    result = dg.run_phase_2_compile_segment(1)

    assert result == {"status": "package-graph-resumed"}
    assert invoked == {"thread_id": "thread-test"}
