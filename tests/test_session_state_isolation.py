from __future__ import annotations

import json
import os
import sys
import asyncio
from contextlib import contextmanager
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


def test_status_refresh_restores_idle_agent_review_payload(tmp_path, monkeypatch):
    import ui.app as web_app
    from agents import director_graph
    from agents.request_context import request_scope

    monkeypatch.setattr(director_graph, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: False)

    session_id = "web_idle_review"
    task_state = web_app._task_state(session_id)
    task_state.clear()

    with request_scope(session_id=session_id):
        director_graph.save_state(
            {
                "status": "idle",
                "step": "",
                "message": "当前俯视图没有可保存的人物标点或活动轨迹。",
                "review_mode": "agent_output",
                "review_agent": "scene_analyst",
                "review_title": "场景预分析",
                "review_output": "scene ok",
                "agent_outputs": {"scene_analyst": "scene ok"},
            }
        )

    web_app._refresh_task_state_from_disk(session_id)

    assert task_state["status"] == "waiting_for_user_input"
    assert task_state["review_agent"] == "scene_analyst"
    assert "审核/修改后继续" in task_state["message"]
    with request_scope(session_id=session_id):
        assert director_graph.load_state()["status"] == "waiting_for_user_input"


def test_scene_review_handoff_marks_director_showrunner_active():
    from agents.director_graph_package.runners import _apply_human_review_edit

    state = {
        "status": "waiting_for_user_input",
        "step": "step_0_scene",
        "agent_outputs": {},
        "review_mode": "agent_output",
        "review_agent": "scene_analyst",
        "review_title": "场景预分析",
        "review_output": "scene ok",
    }

    updated = _apply_human_review_edit(state, "scene_analyst", "scene ok")

    assert updated["status"] == "running_phase_1"
    assert updated["step"] == "step_0_enhance"
    assert updated["agent_outputs"]["scene_analyst"] == "scene ok"


def test_ui_pipeline_starts_with_story_enhancement_step(tmp_path, monkeypatch):
    import ui.app as web_app

    session_id = "web_story_enhance"
    generation = 7
    captured = {}

    @contextmanager
    def fake_request_scope(**_kwargs):
        yield None

    def fake_run_phase_1_planning(**_kwargs):
        captured["step_before_graph"] = web_app._task_state(session_id).get("step")
        captured["message_before_graph"] = web_app._task_state(session_id).get("message")
        return {
            "status": "waiting_for_user_input",
            "step": "step_0_enhance",
            "message": "剧情增强已完成，请审核/修改后继续。",
            "agent_outputs": {"director_showrunner": "增强版剧本: |\n  A rushes in."},
            "review_agent": "director_showrunner",
            "review_mode": "agent_output",
            "review_output": "增强版剧本: |\n  A rushes in.",
        }

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "request_scope", fake_request_scope)
    monkeypatch.setattr(web_app, "run_phase_1_planning", fake_run_phase_1_planning)
    web_app.active_task_generations[session_id] = generation

    web_app._run_pipeline_in_thread(
        script="A enters.",
        aspect_ratio="9:16",
        reference_images="",
        reference_image_b64s=[],
        reference_image_manifest=[],
        speed_mode=False,
        task_generation=generation,
        session_id=session_id,
    )

    assert captured["step_before_graph"] == "step_0_scene"
    assert "场景预分析" in captured["message_before_graph"]
    assert web_app._STEP_LABELS["场景分析师"][0] == "step_0_scene"
    assert web_app._STEP_LABELS["剧情增强导演"][0] == "step_0_enhance"


def test_approve_agent_output_failure_returns_json_and_restores_review(tmp_path, monkeypatch):
    import ui.app as web_app

    session_id = "web_approve_failure"
    task_state = web_app._task_state(session_id)
    task_state.clear()
    task_state.update(
        {
            "status": "waiting_for_user_input",
            "step": "step_0_scene",
            "message": "场景预分析已完成，请审核/修改后继续。",
            "review_mode": "agent_output",
            "review_agent": "scene_analyst",
            "review_title": "场景预分析",
            "review_output": "scene ok",
            "agent_outputs": {"scene_analyst": "scene ok"},
        }
    )

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_refresh_task_state_from_disk", lambda _session_id: None)
    monkeypatch.setattr(web_app, "_has_live_task", lambda _session_id: False)

    def fail_register(_session_id, _thread):
        raise RuntimeError("thread registry unavailable")

    monkeypatch.setattr(web_app, "_register_task_thread", fail_register)

    response = asyncio.run(
        web_app.api_approve_agent_output(
            session_id=session_id,
            agent_name="scene_analyst",
            edited_output="edited scene",
        )
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 500
    assert payload["success"] is False
    assert "thread registry unavailable" in payload["error"]
    assert task_state["status"] == "waiting_for_user_input"
    assert task_state["review_mode"] == "agent_output"
    assert task_state["review_agent"] == "scene_analyst"
    assert task_state["review_output"] == "edited scene"


def test_resume_after_review_failure_marks_failing_downstream_step(tmp_path, monkeypatch):
    import ui.app as web_app

    session_id = "web_rhythm_failure"
    task_state = web_app._task_state(session_id)
    task_state.clear()
    task_state.update(
        {
            "status": "running_phase_1",
            "step": "step_0_rhythm",
            "message": "已确认 剧情增强 输出，正在交给下一个 Agent...",
            "review_mode": "agent_output",
            "review_agent": "director_showrunner",
            "review_title": "剧情增强",
            "agent_outputs": {"director_showrunner": "enhanced"},
        }
    )

    monkeypatch.setattr(web_app, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web_app, "_merge_latest_disk_state_for_session", lambda _session_id, _state: None)

    def fail_resume(_edited_output, _review_agent):
        raise RuntimeError("LLM 接口返回 HTTP 504（agent=rhythm_rewrite_director）")

    monkeypatch.setattr(web_app, "resume_after_human_review", fail_resume)
    web_app.active_task_generations[session_id] = 1

    web_app._resume_after_human_review_in_thread(
        "enhanced",
        "director_showrunner",
        task_generation=1,
        session_id=session_id,
    )

    assert task_state["status"] == "error"
    assert task_state["step"] == "step_0_rhythm"
    assert "rhythm_rewrite_director" in task_state["message"]
