import asyncio
import json


def test_rerun_director_showrunner_preserves_scene_and_clears_downstream(monkeypatch):
    from agents.director_graph_package import nodes, runners

    saved = {}
    state = {
        "status": "waiting_for_user_input",
        "step": "step_0_enhance",
        "script": "A enters.",
        "original_script": "A enters.",
        "scene_context_brief": "scene constraints",
        "agent_outputs": {
            "scene_analyst": "scene ok",
            "director_showrunner": "old enhance",
            "rhythm_rewrite_director": "old rhythm",
            "story_planner": "old plan",
            "compiled_segment_1": "old prompt",
            "quality_inspector_segment_1": "old qc",
        },
        "knowledge_metadata": {
            "director_showrunner": {},
            "rhythm_rewrite_director": {},
            "story_planner": {},
        },
        "total_segments": 1,
        "segment_names": ["old"],
    }

    def fake_showrunner(working_state):
        outputs = dict(working_state["agent_outputs"])
        assert outputs["scene_analyst"] == "scene ok"
        assert outputs["director_showrunner"] == "old enhance"
        assert "rhythm_rewrite_director" not in outputs
        assert "story_planner" not in outputs
        outputs["director_showrunner"] = "new enhance"
        working_state.update(
            {
                "agent_outputs": outputs,
                "step": "step_0_rhythm",
                "message": "enhance done",
            }
        )
        return working_state

    monkeypatch.setattr(runners, "_load_runner_state", lambda: state)
    monkeypatch.setattr(runners, "_save_runner_state", lambda value: saved.update(value))
    monkeypatch.setattr(nodes, "director_showrunner_node", fake_showrunner)

    result = runners.rerun_phase_1_agent("director_showrunner")
    outputs = result["agent_outputs"]

    assert outputs["scene_analyst"] == "scene ok"
    assert outputs["director_showrunner"] == "new enhance"
    assert "rhythm_rewrite_director" not in outputs
    assert "story_planner" not in outputs
    assert "compiled_segment_1" not in outputs
    assert "quality_inspector_segment_1" not in outputs
    assert result["review_agent"] == "director_showrunner"
    assert result["step"] == "step_0_enhance"
    assert saved["review_agent"] == "director_showrunner"


def test_api_rerun_phase1_agent_uses_targeted_worker(monkeypatch, tmp_path):
    import ui.app as web_app

    session_id = "targeted_enhance"
    task_state = web_app._task_state(session_id)
    task_state.clear()
    task_state.update(
        {
            "status": "waiting_for_user_input",
            "scene_context_brief": "scene constraints",
            "agent_outputs": {"scene_analyst": "scene ok"},
        }
    )

    called = {}

    class InlineThread:
        def __init__(self, target, args=(), daemon=None):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            called["target"] = self.target.__name__
            called["args"] = self.args

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_refresh_task_state_from_disk", lambda _session_id: None)
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: False)
    monkeypatch.setattr(web_app.threading, "Thread", InlineThread)
    monkeypatch.setattr(web_app, "_register_task_thread", lambda _session_id, _thread: None)

    response = asyncio.run(
        web_app.api_rerun_phase1_agent(
            session_id=session_id,
            agent_name="director_showrunner",
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["success"] is True
    assert called["target"] == "_rerun_phase_1_agent_in_thread"
    assert called["args"][0] == "director_showrunner"
    assert task_state["step"] == "step_0_enhance"
    assert "重跑" in task_state["message"]
