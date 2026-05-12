from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package import quality_inspector_impl as qi
from agents.director_graph_package.quality_inspector_impl import (
    quality_inspector_node,
)


def test_qc_router_delegates_retry_instruction_to_package_state_store(monkeypatch):
    captured = {}

    def fake_persist_update(state, update):
        captured["state"] = state
        captured["update"] = update
        return update

    monkeypatch.setattr(qi, "_persist_update", fake_persist_update)
    state = {
        "last_qc_status": "fail",
        "qc_retry_count": 0,
        "agent_outputs": {"quality_inspector": "retry this segment"},
    }

    update = qi.qc_router_node(state)

    assert update["qc_retry_count"] == 1
    assert update["revision_instruction"] == "retry this segment"
    assert update["step"] == "step_2_compile"
    assert captured["state"] is state


def test_route_after_qc_keeps_revision_compatibility_path_clear():
    assert qi.route_after_qc({"revision_instruction": "fix prompt"}) == "prompt_compiler"
    assert qi.route_after_qc({"revision_instruction": ""}) == "segment_complete"
    assert qi.route_after_qc({}) == "segment_complete"


def test_quality_inspector_flags_same_camera_continue_and_abstract_jargon(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    state = {
        "active_segment_index": 1,
        "agent_outputs": {
            "compiled_segment_1": """片段1｜办公室｜压迫对峙｜~8秒
【风格锚点】
冷硬现实。
【画幅锚点】
9:16竖屏。
【空间与首帧总控】
办公室内，桌面与门口可见。
【人物】
- 商北琛：总裁。
- 乔熙：助理。
【镜头序列】
0-4秒：商北琛胸部以上中近景，摄影机位于商北琛右前方30度、固定机位。商北琛说完后空气收紧，句尾仍坐在桌后。
4-8秒：同一机位继续，乔熙胸部以上中近景，摄影机位于乔熙左前方30度。乔熙低头，肩膀收紧，停在桌前。
【约束】
禁止字幕。""",
            "story_planner": "fragment_id: F01\nreaction_plan: 片段内承接受击反应",
            "shot_director": """fragment_id: F01
schema_version: shot_director_v2
fragment_intent: office pressure
reaction_coverage: listener reaction
continuity_anchor: office desk
shots:
  - shot_id: F01-S01
    coverage_role: speaker_start
    cut_reason: pressure_line
    companion_visibility: 乔熙画外
    tailframe_role: none
    dialogue_coverage: 商北琛起句，切乔熙听者反应
""",
        },
    }

    update = quality_inspector_node(state)
    report = update["agent_outputs"]["quality_inspector"]

    assert "PROMPT-NO-SAME-CAMERA-ABUSE-001" in report
    assert "PROMPT-VISIBLE-BODY-LANGUAGE-001" in report


def test_quality_inspector_accepts_local_fallback_v1_shot_contract(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    state = {
        "active_segment_index": 1,
        "agent_outputs": {
            "compiled_segment_1": "",
            "story_planner": "fragment_id: F01\nreaction_plan: none\nsource_script_events:\n  - Alex opens the door.\n",
            "shot_director": """fragment_id: F01
schema_version: shot_director_local_fallback_v1
fragment_task: local fallback beat
rhythm: readable action
shots:
  - shot_id: F01-S01
    duration: "0-3s"
    task: carry the door beat
    subject: Alex
    shot: stable medium shot
    action: Alex opens the door.
    dialogue: ""
    dialogue_coverage: none
    must_carry: Alex opens the door.
    cut_point: after the door opens
    continuity: keep screen direction
""",
        },
    }

    update = quality_inspector_node(state)
    report = update["agent_outputs"]["quality_inspector"]

    assert "残留 v2 字段 schema_version" not in report
    assert "缺少 v1 字段 duration" not in report
    assert "缺少 v1 字段 camera" not in report
    assert "缺少 v1 字段 size" not in report
    assert "残留 v2 字段 dialogue_coverage" not in report
