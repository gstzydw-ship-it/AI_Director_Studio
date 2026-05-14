import asyncio
import json


def test_retry_shot_director_ignores_script_text_by_default(monkeypatch, tmp_path):
    import ui.app as web_app

    session_id = "retry_shot_director_scoped"
    task_state = web_app._task_state(session_id)
    task_state.clear()
    task_state.update(
        {
            "status": "error",
            "step": "error",
            "input_script": "edited text in UI",
            "agent_outputs": {
                "scene_analyst": "scene ok",
                "director_showrunner": "enhance ok",
                "rhythm_rewrite_director": "rhythm ok",
                "story_planner": "plan ok",
            },
            "current_segment_index": 1,
            "total_segments": 1,
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

    def fail_full_pipeline(*_args, **_kwargs):
        raise AssertionError("shot director retry should not restart full Phase 1")

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_refresh_task_state_from_disk", lambda _session_id: None)
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: False)
    monkeypatch.setattr(web_app, "load_state", lambda: {"script": "saved script"})
    monkeypatch.setattr(web_app, "save_state", lambda _state: None)
    monkeypatch.setattr(web_app.threading, "Thread", InlineThread)
    monkeypatch.setattr(web_app, "_register_task_thread", lambda _session_id, _thread: None)
    monkeypatch.setattr(web_app, "_run_pipeline_in_thread", fail_full_pipeline)

    response = asyncio.run(
        web_app.api_retry_shot_director(
            session_id=session_id,
            script="different text from textarea",
            force_restart=False,
            allow_script_update=False,
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["success"] is True
    assert called["target"] == "_restart_shot_director_from_planner_in_thread"
    assert task_state["status"] == "running_phase_2"
    assert task_state["step"] == "step_3_direct"


def test_retry_shot_director_can_explicitly_restart_phase1_for_script_update(monkeypatch, tmp_path):
    import ui.app as web_app

    session_id = "retry_shot_director_script_update"
    task_state = web_app._task_state(session_id)
    task_state.clear()
    task_state.update(
        {
            "status": "error",
            "step": "error",
            "input_script": "old script",
            "input_aspect_ratio": "9:16",
            "agent_outputs": {"story_planner": "plan ok"},
            "current_segment_index": 1,
            "total_segments": 1,
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

    saved_disk_state = {
        "script": "old script",
        "reference_images": "",
        "reference_image_b64s": [],
        "reference_image_manifest": [],
    }

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_refresh_task_state_from_disk", lambda _session_id: None)
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: False)
    monkeypatch.setattr(web_app, "load_state", lambda: dict(saved_disk_state))
    monkeypatch.setattr(web_app, "save_state", lambda state: saved_disk_state.update(state))
    monkeypatch.setattr(web_app.threading, "Thread", InlineThread)
    monkeypatch.setattr(web_app, "_register_task_thread", lambda _session_id, _thread: None)

    response = asyncio.run(
        web_app.api_retry_shot_director(
            session_id=session_id,
            script="new script",
            force_restart=False,
            allow_script_update=True,
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["success"] is True
    assert called["target"] == "_run_pipeline_in_thread"
    assert task_state["status"] == "running_phase_1"
    assert task_state["step"] == "step_1_rhythm"
