from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package import quality_inspector_impl as qi
from agents.director_graph_package.quality_inspector_impl import quality_inspector_node


def _valid_prompt(extra: str = "") -> str:
    return f"""片段1｜办公室｜压迫对峙｜约5秒｜9:16

【画面基底】
办公室内，桌面和门口位置清楚，商北琛与乔熙站在桌边。

【镜头序列】
镜头1【2.5秒】【商北琛、乔熙】双人半身关系景，桌边固定视角。商北琛向前半步，乔熙停住看向他。（切镜时机：乔熙停住后切至镜头2）
镜头2【2.5秒】【乔熙】中近景。乔熙下颌收紧，手指松开桌沿，视线仍看向商北琛。

尾帧：乔熙站在桌边看向商北琛，手离开桌沿，门保持关闭，下一段可从两人距离承接。

【约束】
严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌。
{extra}
"""


def _valid_planner() -> str:
    return """fragment_id: F01
reaction_plan: 片段内承接受击反应
source_script_events:
  - 商北琛向前施压，乔熙停住反应。
"""


def _valid_director(extra: str = "") -> str:
    return f"""fragment_id: F01
fragment_task: 完成双人压迫和乔熙受击反应。
rhythm: 短压迫后反应停顿
shots:
  - shot_id: F01-S01
    duration: 0-2.5秒
    task: 建立双人压迫关系。
    subject: 商北琛、乔熙
    shot: 双人半身关系景，桌边固定视角
    action: 商北琛向前半步，乔熙停住。
    dialogue: ~
    must_carry: 两人距离和门状态清楚。
    cut_point: 乔熙停住后切出。
    continuity: 门保持关闭，两人仍在桌边。
  - shot_id: F01-S02
    duration: 2.5-5秒
    task: 承接乔熙受击反应。
    subject: 乔熙
    shot: 中近景
    action: 乔熙下颌收紧，手指松开桌沿。
    dialogue: ~
    must_carry: 乔熙反应可读。
    cut_point: 手指松开后收束。
    continuity: 乔熙仍在桌边看向商北琛。
{extra}
"""


def _inspect(monkeypatch, *, prompt: str | None = None, director: str | None = None, state_extra: dict | None = None):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)
    state = {
        "active_segment_index": 1,
        "segment_names": ["F01"],
        "agent_outputs": {
            "compiled_segment_1": prompt if prompt is not None else _valid_prompt(),
            "story_planner": _valid_planner(),
            "shot_director": director if director is not None else _valid_director(),
        },
    }
    if state_extra:
        state.update(state_extra)
    return quality_inspector_node(state)["agent_outputs"]["quality_inspector"]


def test_seedance_gate_blocks_x_template_in_prompt(monkeypatch):
    prompt = _valid_prompt("template_id: COV-SD20-X-CROSS-AXIS")

    report = _inspect(monkeypatch, prompt=prompt)

    assert "总体评级：fail" in report
    assert "X_TEMPLATE_BLOCKED" in report
    assert "target=shot_director" in report


def test_seedance_gate_blocks_r1_without_motion_or_keyframe_reference(monkeypatch):
    report = _inspect(
        monkeypatch,
        state_extra={
            "coverage_contracts_by_segment": {
                "F01": {
                    "template_id": "COV-SD20-R1-FIGHT-BEAT",
                    "template_level": "R1",
                    "tail_state": "乔熙站在桌边看向商北琛。",
                }
            }
        },
    )

    assert "总体评级：fail" in report
    assert "R1_REFERENCE_REQUIRED" in report
    assert "video_reference/motion_reference/keyframe_sequence" in report


def test_seedance_gate_blocks_complexity_and_multi_actor_action(monkeypatch):
    director = _valid_director(
        """template_id: COV-SD20-W2-GROUP-STATIC-REACTION
template_level: W2
model_complexity_score: 5
tail_state: 三人停在办公室桌边。
action_budget_used:
  over_budget: true
main_character_count: 3
notes: 三人同时冲向文件并各自伸手争抢。
"""
    )

    report = _inspect(monkeypatch, director=director)

    assert "总体评级：fail" in report
    assert "SD20_COMPLEXITY_BUDGET" in report
    assert "SD20_MULTI_ACTOR_ACTION_BUDGET" in report


def test_seedance_gate_blocks_tail_text_dependency_and_abstract_emotion(monkeypatch):
    prompt = _valid_prompt(
        """template_id: COV-SD20-W1-PROP-INSERT
template_level: W1
尾帧：黑场结束，只留下压迫感。
文件文字清楚显示亲子鉴定结果，作为关键证据传递剧情。
"""
    )

    report = _inspect(monkeypatch, prompt=prompt)

    assert "总体评级：fail" in report
    assert "TAILFRAME_STATE_REQUIRED" in report
    assert "NO_SUBTITLE_SCREEN_TEXT" in report
    assert "VISIBLE_EMOTION_ANCHOR_REQUIRED" in report


def test_seedance_gate_blocks_missing_template_only_in_explicit_seedance_context(monkeypatch):
    prompt = _valid_prompt("Seedance 2.0 全能参考模式。")

    report = _inspect(monkeypatch, prompt=prompt)

    assert "总体评级：fail" in report
    assert "COVERAGE_TEMPLATE_REQUIRED" in report
