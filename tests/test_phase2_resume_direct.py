from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
import agents.director_graph_package.nodes as pkg_nodes
import agents.director_graph_package.prompt_compiler_impl as prompt_compiler_impl
import agents.director_graph_package.quality_inspector_impl as quality_inspector_impl
import agents.director_graph_package.runners as pkg_runners
import agents.director_graph_package.shot_director_impl as shot_director_impl


class _FakeSaver:
    @classmethod
    def from_conn_string(cls, _conn_string):
        return cls()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


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


def test_graph_resume_keeps_segment_request_interrupt_out_of_agent_review(monkeypatch, tmp_path):
    state = _base_state({"story_planner": "planner"})
    state["human_review_enabled"] = True
    state["review_mode"] = "agent_output"
    state["review_agent"] = "story_planner"
    state["review_title"] = "结构规划"
    state["review_output"] = "planner"
    marked_reviews: list[dict] = []
    saved_states: list[dict] = []

    class FakeApp:
        def update_state(self, _config, _state):
            pass

        def invoke(self, _input_value, config=None):
            return {
                **state,
                "__interrupt__": ({"type": "segment_request"},),
                "status": "running_phase_1",
                "message": "Confirmed story planner output; continuing...",
            }

        def get_state(self, _config):
            return SimpleNamespace(next=("wait_for_segment_request",))

    class FakeGraph:
        def compile(self, **_kwargs):
            return FakeApp()

    monkeypatch.setattr(pkg_runners, "_checkpoint_file", lambda: str(tmp_path / "graph.sqlite"))
    monkeypatch.setattr(pkg_runners, "_session_output_dir", lambda: str(tmp_path))
    monkeypatch.setattr(pkg_runners, "_load_runner_state", lambda: dict(state))
    monkeypatch.setattr(pkg_runners, "_save_runner_state", lambda saved: saved_states.append(dict(saved)))
    monkeypatch.setattr(pkg_runners, "_normalise_graph_result", lambda result, thread_id: {
        key: value for key, value in result.items() if key != "__interrupt__"
    } | {"thread_id": thread_id, "status": "waiting_for_user_input"})
    monkeypatch.setattr(pkg_runners, "_mark_human_review_state", lambda review_state, next_nodes: marked_reviews.append(review_state) or review_state)

    import langgraph.checkpoint.sqlite as sqlite_mod
    import agents.director_graph_package.graph_api as graph_api

    monkeypatch.setattr(sqlite_mod, "SqliteSaver", _FakeSaver)
    monkeypatch.setattr(graph_api, "create_director_graph", lambda: FakeGraph())

    result = pkg_runners._invoke_graph(None, "thread-test")

    assert result["status"] == "waiting_for_user_input"
    assert result["thread_id"] == "thread-test"
    assert result.get("review_agent") is None
    assert result.get("review_mode") is None
    assert result["step"] == "step_3_direct"
    assert marked_reviews == []
    assert saved_states[-1].get("review_agent") is None


def test_graph_resume_still_marks_planner_review_after_story_planner_node(monkeypatch, tmp_path):
    state = _base_state({"story_planner": "planner"})
    state["human_review_enabled"] = True
    marked_reviews: list[tuple[dict, object]] = []

    class FakeApp:
        def update_state(self, _config, _state):
            pass

        def invoke(self, _input_value, config=None):
            return dict(state)

        def get_state(self, _config):
            return SimpleNamespace(next=("wait_for_segment_request",))

    class FakeGraph:
        def compile(self, **_kwargs):
            return FakeApp()

    def mark_review(review_state, next_nodes):
        marked_reviews.append((review_state, next_nodes))
        review_state["review_agent"] = "story_planner"
        return review_state

    monkeypatch.setattr(pkg_runners, "_checkpoint_file", lambda: str(tmp_path / "graph.sqlite"))
    monkeypatch.setattr(pkg_runners, "_session_output_dir", lambda: str(tmp_path))
    monkeypatch.setattr(pkg_runners, "_load_runner_state", lambda: dict(state))
    monkeypatch.setattr(pkg_runners, "_normalise_graph_result", lambda result, thread_id: dict(result) | {"thread_id": thread_id})
    monkeypatch.setattr(pkg_runners, "_mark_human_review_state", mark_review)

    import langgraph.checkpoint.sqlite as sqlite_mod
    import agents.director_graph_package.graph_api as graph_api

    monkeypatch.setattr(sqlite_mod, "SqliteSaver", _FakeSaver)
    monkeypatch.setattr(graph_api, "create_director_graph", lambda: FakeGraph())

    result = pkg_runners._invoke_graph({"human_review_enabled": True}, "thread-test")

    assert result["review_agent"] == "story_planner"
    assert marked_reviews[0][1] == ("wait_for_segment_request",)


def test_graph_resume_after_planner_review_clears_stale_review_fields(monkeypatch, tmp_path):
    state = _base_state({"story_planner": "planner"})
    state["human_review_enabled"] = True
    state["review_mode"] = "agent_output"
    state["review_agent"] = "story_planner"
    state["review_title"] = "结构规划"
    state["review_output"] = "planner"
    marked_reviews: list[tuple[dict, object]] = []
    saved_states: list[dict] = []

    class FakeApp:
        def update_state(self, _config, _state):
            pass

        def invoke(self, _input_value, config=None):
            return {
                **state,
                "status": "running_phase_1",
                "message": "Confirmed story planner output; continuing...",
            }

        def get_state(self, _config):
            return SimpleNamespace(next=("wait_for_segment_request",))

    class FakeGraph:
        def compile(self, **_kwargs):
            return FakeApp()

    monkeypatch.setattr(pkg_runners, "_checkpoint_file", lambda: str(tmp_path / "graph.sqlite"))
    monkeypatch.setattr(pkg_runners, "_session_output_dir", lambda: str(tmp_path))
    monkeypatch.setattr(pkg_runners, "_load_runner_state", lambda: dict(state))
    monkeypatch.setattr(pkg_runners, "_save_runner_state", lambda saved: saved_states.append(dict(saved)))
    monkeypatch.setattr(pkg_runners, "_normalise_graph_result", lambda result, thread_id: dict(result) | {"thread_id": thread_id})
    monkeypatch.setattr(pkg_runners, "_mark_human_review_state", lambda review_state, next_nodes: marked_reviews.append((review_state, next_nodes)) or review_state)

    import langgraph.checkpoint.sqlite as sqlite_mod
    import agents.director_graph_package.graph_api as graph_api

    monkeypatch.setattr(sqlite_mod, "SqliteSaver", _FakeSaver)
    monkeypatch.setattr(graph_api, "create_director_graph", lambda: FakeGraph())

    result = pkg_runners._invoke_graph(None, "thread-test")

    assert result["status"] == "waiting_for_user_input"
    assert result["step"] == "step_3_direct"
    assert result.get("review_agent") is None
    assert result.get("review_mode") is None
    assert marked_reviews == []
    assert saved_states[-1].get("review_agent") is None


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

    def shot_node(node_state, segment_index):
        calls.append(("shot", str(segment_index)))
        outputs = dg._agent_outputs(node_state)
        outputs["shot_director"] = "director"
        return {
            "status": "running_phase_2",
            "step": "step_4_compile",
            "active_segment_index": node_state["active_segment_index"],
            "agent_outputs": outputs,
        }

    monkeypatch.setattr(shot_director_impl, "run_shot_director_for_segment", shot_node)

    result = dg.run_phase_2_compile_segment(9, tail_frame_b64="frame")

    assert result["status"] == "done"
    assert result["active_segment_index"] == 2
    assert result["agent_outputs"]["compiled_segment_2"] == "compiled"
    assert saved_states[0]["step"] == "step_3_direct"
    assert calls == [
        ("shot", "9"),
        ("compile", "tail-2-frame"),
        ("inspect", "compiled"),
        ("route", "pass"),
        ("complete", "2"),
    ]


def test_phase_2_review_resume_skips_storyboard_before_prompt_compiler(monkeypatch):
    state = _base_state({"story_planner": "planner"})
    state["human_review_enabled"] = True
    calls: list[tuple[str, str]] = []
    marked_reviews: list[object] = []

    monkeypatch.setattr(
        pkg_runners,
        "_prepare_phase_2_compile_state",
        lambda _state, segment_index, *_args: {
            "status": "running_phase_2",
            "step": "step_3_direct",
            "active_segment_index": segment_index,
            "tail_frame_analysis": f"tail-{segment_index}",
            "qc_retry_count": 0,
            "revision_instruction": "",
        },
    )
    monkeypatch.setattr(pkg_runners, "_save_runner_state", lambda _saved: None)

    def mark_review(review_state, next_nodes):
        marked_reviews.append(next_nodes)
        review_state["review_agent"] = "quality_inspector"
        return review_state

    monkeypatch.setattr(pkg_runners, "_mark_human_review_state", mark_review)

    def shot_node(node_state, segment_index):
        calls.append(("shot", str(segment_index)))
        outputs = dg._agent_outputs(node_state)
        outputs["shot_director"] = "director"
        return {"agent_outputs": outputs}

    def prompt_node(node_state):
        calls.append(("compile", node_state["tail_frame_analysis"]))
        outputs = dg._agent_outputs(node_state)
        outputs["compiled_segment_2"] = "compiled"
        outputs["prompt_compiler"] = "compiled"
        return {"agent_outputs": outputs}

    def fail_storyboard(*_args, **_kwargs):
        raise AssertionError("storyboard should not run before prompt compiler on the temporary production path")

    monkeypatch.setattr(shot_director_impl, "run_shot_director_for_segment", shot_node)
    monkeypatch.setattr(prompt_compiler_impl, "prompt_compiler_node", prompt_node)
    monkeypatch.setattr(pkg_nodes, "storyboard_designer_node", fail_storyboard)

    result = pkg_runners._run_phase_2_until_review(state, 2)

    assert calls == [("shot", "2"), ("compile", "tail-2")]
    assert marked_reviews == [("quality_inspector",)]
    assert result["review_agent"] == "quality_inspector"
    assert "storyboard_designer" not in result["agent_outputs"]


def test_phase_1_review_resume_runs_next_agent_without_graph_resume(monkeypatch):
    state = _base_state({"scene_analyst": "scene"})
    state.update(
        {
            "review_mode": "agent_output",
            "review_agent": "scene_analyst",
            "review_output": "edited scene",
            "human_review_enabled": True,
        }
    )
    saved_states: list[dict] = []

    monkeypatch.setattr(pkg_runners, "_load_runner_state", lambda: dict(state))
    monkeypatch.setattr(pkg_runners, "_save_runner_state", lambda saved: saved_states.append(dict(saved)))
    monkeypatch.setattr(
        pkg_runners,
        "_invoke_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("phase 1 review should not resume graph")),
    )

    def director_node(node_state):
        outputs = dict(node_state.get("agent_outputs") or {})
        outputs["director_showrunner"] = "enhanced"
        return {"agent_outputs": outputs, "status": "running_phase_1", "step": "step_0_enhance"}

    monkeypatch.setattr(pkg_nodes, "director_showrunner_node", director_node)

    result = pkg_runners.resume_after_human_review("edited scene", "scene_analyst")

    assert result["status"] == "waiting_for_user_input"
    assert result["review_agent"] == "director_showrunner"
    assert result["review_output"] == "enhanced"
    assert result["scene_context_brief"] == "edited scene"
    assert saved_states[-1]["review_agent"] == "director_showrunner"


def test_story_planner_review_resume_waits_for_segment_without_graph_resume(monkeypatch):
    state = _base_state({"story_planner": "planner"})
    state.update(
        {
            "review_mode": "agent_output",
            "review_agent": "story_planner",
            "review_output": "- fragment_id: F01\n  source_script_events:\n    - event\n",
            "human_review_enabled": True,
        }
    )
    saved_states: list[dict] = []

    monkeypatch.setattr(pkg_runners, "_load_runner_state", lambda: dict(state))
    monkeypatch.setattr(pkg_runners, "_save_runner_state", lambda saved: saved_states.append(dict(saved)))
    monkeypatch.setattr(
        pkg_runners,
        "_invoke_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("story planner review should not resume graph")),
    )

    result = pkg_runners.resume_after_human_review(state["review_output"], "story_planner")

    assert result["status"] == "waiting_for_user_input"
    assert result["step"] == "step_3_direct"
    assert result.get("review_agent") is None
    assert result["total_segments"] == 1
    assert result["agent_outputs"]["story_planner"] == state["review_output"]
    assert saved_states[-1].get("review_agent") is None


def test_phase_2_resume_runs_direct_segment_shot_director_without_global_shot_plan(monkeypatch):
    state = _base_state({"story_planner": "planner"})

    monkeypatch.setattr(pkg_runners._impl, "load_state", lambda: dict(state))

    def direct_resume(_state, segment_index, tail_frame_b64=None, video_path=None):
        return {
            "status": "direct-segment",
            "segment_index": segment_index,
            "tail_frame_b64": tail_frame_b64,
            "video_path": video_path,
        }

    monkeypatch.setattr(pkg_runners, "_run_phase_2_compile_direct", direct_resume)
    monkeypatch.setattr(
        pkg_runners,
        "_invoke_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("phase 2 should not resume graph")),
    )

    result = dg.run_phase_2_compile_segment(1, tail_frame_b64="frame")

    assert result == {
        "status": "direct-segment",
        "segment_index": 1,
        "tail_frame_b64": "frame",
        "video_path": None,
    }


def test_phase_2_resume_ignores_legacy_graph_override(monkeypatch):
    state = _base_state({"story_planner": "planner"})

    monkeypatch.setattr(pkg_runners._impl, "load_state", lambda: dict(state))
    monkeypatch.setattr(
        pkg_runners._impl,
        "_invoke_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("runner graph resume should not use legacy_impl._invoke_graph")
        ),
    )

    monkeypatch.setattr(
        pkg_runners,
        "_invoke_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("phase 2 should not resume graph")),
    )

    monkeypatch.setattr(pkg_runners, "_run_phase_2_compile_direct", lambda *_args, **_kwargs: {"status": "direct"})

    result = dg.run_phase_2_compile_segment(1)

    assert result == {"status": "direct"}
