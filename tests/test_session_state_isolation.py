from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_director_graph_state_is_scoped_by_request_session(tmp_path, monkeypatch):
    from agents import director_graph
    from agents.request_context import request_scope

    monkeypatch.setattr(director_graph, "OUTPUT_DIR", str(tmp_path))

    with request_scope(session_id="web_a"):
        director_graph.save_state({"status": "a"})

    with request_scope(session_id="web_b"):
        director_graph.save_state({"status": "b"})

    with request_scope(session_id="web_a"):
        assert director_graph.load_state()["status"] == "a"

    with request_scope(session_id="web_b"):
        assert director_graph.load_state()["status"] == "b"

    assert not (tmp_path / "pipeline_state.json").exists()
    assert (tmp_path / "sessions" / "web_a" / "pipeline_state.json").exists()
    assert (tmp_path / "sessions" / "web_b" / "pipeline_state.json").exists()


def test_legacy_global_state_migrates_only_to_local_session(tmp_path, monkeypatch):
    import ui.app as web_app

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    (tmp_path / "pipeline_state.json").write_text(
        json.dumps({"status": "waiting_for_user_input"}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert web_app._migrate_legacy_state_if_needed("web_new") is False
    assert not (tmp_path / "sessions" / "web_new" / "pipeline_state.json").exists()

    assert web_app._migrate_legacy_state_if_needed(web_app.DEFAULT_SESSION_ID) is True
    assert (tmp_path / "sessions" / "local" / "pipeline_state.json").exists()


def test_stale_running_state_is_marked_interrupted(monkeypatch):
    import ui.app as web_app

    saved = {"called": False}
    monkeypatch.setattr(web_app, "_save_task_state_for_session", lambda *_args, **_kwargs: saved.update(called=True) or True)
    state = {
        "status": "running_phase_2",
        "step": "step_4_compile",
        "started_at": "2026-04-21T23:00:00",
    }

    assert web_app._recover_stale_running_state("local", state) is True
    assert state["status"] == "error"
    assert state["step"] == "error"
    assert "后台执行线程不存在" in state["message"]
    assert saved["called"] is True


def test_stalled_live_task_is_marked_error(monkeypatch):
    import ui.app as web_app

    saved = {"called": False}
    bumped = {"called": False}
    session_id = "web_stalled"
    now = datetime(2026, 4, 24, 15, 0, 0)
    state = {
        "status": "running_phase_1",
        "step": "step_1_analyze",
        "started_at": (now - timedelta(seconds=901)).isoformat(),
        "last_progress_at": (now - timedelta(seconds=901)).isoformat(),
        "agent_outputs": {},
    }

    web_app.active_task_threads[session_id] = object()
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: True)
    monkeypatch.setattr(web_app, "_save_task_state_for_session", lambda *_args, **_kwargs: saved.update(called=True) or True)
    monkeypatch.setattr(web_app, "_bump_task_generation", lambda _session_id: bumped.update(called=True) or 1)

    assert web_app._recover_stalled_live_task(
        session_id,
        state,
        now=now,
        timeout_seconds=900,
    ) is True
    assert state["status"] == "error"
    assert state["step"] == "error"
    assert "watchdog timeout" in state["error"]
    assert saved["called"] is True
    assert bumped["called"] is True
    assert session_id not in web_app.active_task_threads


def test_ui_error_state_merge_preserves_latest_disk_outputs(tmp_path, monkeypatch):
    import ui.app as web_app
    from agents import director_graph
    from agents.request_context import request_scope

    monkeypatch.setattr(director_graph, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))

    latest = {
        "status": "running_phase_1",
        "step": "step_3_direct",
        "agent_outputs": {"shot_director_layout": "layout yaml"},
        "knowledge_metadata": {"shot_director": {"runtime": {"layout": {"status": "success"}}}},
    }
    with request_scope(session_id="web_debug"):
        director_graph.save_state(latest)

    task_state = {"status": "running_phase_1", "agent_outputs": {}}

    assert web_app._merge_latest_disk_state_for_session("web_debug", task_state) is True
    assert task_state["agent_outputs"]["shot_director_layout"] == "layout yaml"
    assert task_state["knowledge_metadata"]["shot_director"]["runtime"]["layout"]["status"] == "success"


def test_status_refresh_uses_disk_progress_for_live_task(tmp_path, monkeypatch):
    import ui.app as web_app
    from agents import director_graph
    from agents.request_context import request_scope

    monkeypatch.setattr(director_graph, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: True)

    session_id = "web_live_progress"
    task_state = web_app._task_state(session_id)
    task_state.update(
        {
            "status": "running_phase_1",
            "step": "step_1_analyze",
            "message": "old in-memory progress",
            "agent_outputs": {},
        }
    )

    with request_scope(session_id=session_id):
        director_graph.save_state(
            {
                "status": "running_phase_1",
                "step": "step_3_direct",
                "message": "镜头导演动作调度已完成，规则守门导演正在做最终清洗...（4/6）",
                "agent_outputs": {"shot_director_blocking": "blocking yaml"},
            }
        )

    web_app._refresh_task_state_from_disk(session_id)

    assert task_state["status"] == "running_phase_1"
    assert task_state["step"] == "step_3_direct"
    assert "规则守门导演" in task_state["message"]
    assert task_state["agent_outputs"]["shot_director_blocking"] == "blocking yaml"
