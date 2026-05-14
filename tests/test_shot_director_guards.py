from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.knowledge_base import get_agent_knowledge_files  # noqa: E402
from agents.director_graph_package import legacy_impl, runners  # noqa: E402
from agents.director_graph_package.shot_director_impl import (  # noqa: E402
    _clean_shot_director_output,
    _hard_shot_director_issues,
    _shot_director_rhythm_match_rules,
    _shot_director_source_event_rules,
    _validate_shot_director_output,
    _validate_shot_director_source_event_coverage,
    _validate_shot_director_script_fidelity,
    _validate_shot_director_vertical_discipline,
)
from agents.director_graph_package import shot_director_impl  # noqa: E402


def test_clean_shot_director_output_strips_thinking_and_markdown():
    raw = """<thinking>
fragment_id: F04
draft notes without required fields
</thinking>

```yaml
fragment_id: F04
fragment_intent: "回到现实"
reaction_coverage: "乔熙反应在片段内承接"
continuity_anchor: "照片在桌上，书包在小豆丁身上"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "承接回神"
    dialogue_coverage: "乔熙OS"
```

解释文字。
"""

    cleaned = _clean_shot_director_output(raw)

    assert cleaned.startswith("fragment_id: F04")
    assert "<thinking>" not in cleaned
    assert "解释文字" not in cleaned
    assert "main_shots:" in cleaned


def test_segment_shot_director_reports_connection_failure_after_llm_failure(monkeypatch):
    def fail_three_stage(**_kwargs):
        raise RuntimeError("LLM network connection failed")

    monkeypatch.setattr(shot_director_impl, "_run_shot_director_three_stage", fail_three_stage)
    captured_update = {}

    def fake_persist(state, update):
        captured_update.update(update)
        return {**dict(state), **dict(update)}

    monkeypatch.setattr(shot_director_impl, "_persist_update", fake_persist)

    state = {
        "script": "Alex opens the door. Blair reacts and steps back.",
        "aspect_ratio": "9:16",
        "total_segments": 1,
        "segment_names": ["segment01"],
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Alex opens the door.\n"
                "    - Blair reacts and steps back.\n"
            )
        },
    }

    with pytest.raises(RuntimeError, match="镜头导演大模型连接不成功"):
        shot_director_impl.run_shot_director_for_segment(state, 1)

    outputs = captured_update["agent_outputs"]
    runtime = captured_update["knowledge_metadata"]["shot_director"]["runtime"]

    assert captured_update["status"] == "error"
    assert captured_update["step"] == "error"
    assert "shot_director_segment_F01" not in outputs
    assert outputs["shot_director_error_fragment_F01"].startswith("镜头导演大模型连接不成功")
    assert "本地兜底" not in outputs["shot_director_error_fragment_F01"]
    assert runtime["local_fallback"] is False
    assert runtime["status"] == "connection_failed"
    assert runtime["final"]["status"] == "connection_failed"


def test_segment_shot_director_reports_connection_failure_after_logic_reviewer_failure(monkeypatch):
    def fake_three_stage(**_kwargs):
        output = (
            "- fragment_id: F01\n"
            "  fragment_intent: Door reaction\n"
            "  main_shots:\n"
            "    - shot_id: F01-S01\n"
            "      subject: Alex\n"
            "      shot_size: medium\n"
        )
        return output, {"final": {"status": "ok"}}, {"final": {"retrieval_mode": "stub"}}, {"final": output}

    def fail_review(**_kwargs):
        raise RuntimeError("镜头逻辑审查大模型连接不成功：offline")

    monkeypatch.setattr(shot_director_impl, "_run_shot_director_three_stage", fake_three_stage)
    monkeypatch.setattr(shot_director_impl, "_run_shot_director_review_board", fail_review)
    monkeypatch.setattr(shot_director_impl, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(shot_director_impl, "_hard_shot_director_issues", lambda issues: [])
    captured_update = {}

    def fake_persist(state, update):
        captured_update.update(update)
        return {**dict(state), **dict(update)}

    monkeypatch.setattr(shot_director_impl, "_persist_update", fake_persist)

    state = {
        "script": "Alex opens the door. Blair reacts.",
        "aspect_ratio": "9:16",
        "total_segments": 1,
        "segment_names": ["segment01"],
        "agent_outputs": {"story_planner": "- fragment_id: F01\n  source_script_events:\n    - Alex opens the door.\n"},
    }

    with pytest.raises(RuntimeError, match="镜头逻辑审查大模型连接不成功"):
        shot_director_impl.run_shot_director_for_segment(state, 1)

    outputs = captured_update["agent_outputs"]
    runtime = captured_update["knowledge_metadata"]["shot_director"]["runtime"]

    assert captured_update["status"] == "error"
    assert captured_update["step"] == "error"
    assert outputs["shot_director_error_fragment_F01"].startswith("镜头逻辑审查大模型连接不成功")
    assert runtime["status"] == "connection_failed"
    assert runtime["path"] == "logic_reviewer_connection_failed"
    assert runtime["review_board"]["status"] == "connection_failed"


def test_shot_director_fidelity_rejects_wake_up_reinterpretation():
    script = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。
▲小豆丁已经站在门口，单肩背着书包等她。
乔熙OS：It's been four years. He's married with a kid now. Sunny, wake up.
乔熙：Come on, baby, let's go. Gonna be late.
"""
    director_output = """fragment_id: F04
fragment_intent: "Sunny 睡醒"
reaction_coverage: "Sunny 睁眼"
continuity_anchor: "Sunny 仰卧在床上，伴侣站在床尾"
main_shots:
  - shot_id: "F04-S01"
    subject: "Sunny 睡颜"
    shot_size: "ECU"
    camera_height: "slightly_high"
    angle: "俯拍"
    movement: "static"
    lens: "85mm"
    depth: "shallow"
    shot_intent: "表现睡眠中的微表情"
    dialogue_coverage: "Sunny, wake up."
"""

    issues = _validate_shot_director_script_fidelity(director_output, script)

    assert any("剧本外前提" in issue for issue in issues)
    assert any("Sunny" in issue for issue in issues)


def test_shot_director_fidelity_rejects_photo_bag_state_drift():
    script = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。
▲小豆丁已经站在门口，单肩背着书包等她。
"""
    director_output = """fragment_id: F04
fragment_intent: "回到现实"
reaction_coverage: "乔熙把照片攥进掌心"
continuity_anchor: "照片被塞回书包"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "乔熙指尖压住照片"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_script_fidelity(director_output, script)

    assert any("照片/书包连续性" in issue for issue in issues)


def test_shot_director_fidelity_rejects_scene_space_drift():
    script = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。
▲小豆丁已经站在门口，单肩背着书包等她。
"""
    director_output = """fragment_id: F04
fragment_intent: "乔熙独坐车内"
reaction_coverage: "乔熙在车窗边回神"
continuity_anchor: "乔熙已落座车内，车尚未起步"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "车内回神"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_script_fidelity(director_output, script)

    assert any("剧本外前提" in issue and "车内" in issue for issue in issues)


def test_shot_director_coverage_rejects_missing_source_event_terms():
    planner = """fragment_id: F04
cast:
  active:
    - 人物甲
    - 人物乙
source_script_events:
  - "▲人物甲猛地回神，强压下心口闷痛，把照片放到桌上。"
  - "▲人物乙已经站在门口，单肩背着背包等她。"
main_shots:
  - shot_id: "F04-S01"
reaction_plan: "片段内承接"
"""
    director_output = """fragment_id: F04
fragment_intent: "人物甲放下照片"
reaction_coverage: "人物甲反应"
continuity_anchor: "照片在桌上"
main_shots:
  - shot_id: "F04-S01"
    subject: "人物甲"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "人物甲放下照片"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_source_event_coverage(director_output, planner)

    assert any("人物乙" in issue and "背包" in issue for issue in issues)


def test_shot_director_vertical_discipline_rejects_closeup_overuse_in_9x16():
    director_output = """fragment_id: F05
fragment_intent: "门口预压"
reaction_coverage: "人群反应"
continuity_anchor: "集团门口等待新老板"
main_shots:
  - shot_id: "F05-S01"
    subject: "乔熙"
    shot_size: "CU"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "85mm"
    depth: "shallow"
    shot_intent: "乔熙反应"
    dialogue_coverage: "none"
  - shot_id: "F05-S02"
    subject: "秘书"
    shot_size: "ECU"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "100mm"
    depth: "shallow"
    shot_intent: "秘书紧张"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_vertical_discipline(director_output, "9:16")

    assert any("全部使用特写类景别" in issue for issue in issues)
    assert any("多次面部特写" in issue for issue in issues)


def test_validate_shot_director_output_rejects_invalid_transition_type_and_missing_tail_state_card():
    director_output = """fragment_id: F01
schema_version: shot_director_v2
fragment_intent: "门口压迫建立"
reaction_coverage: "听者受压后停住"
continuity_anchor: "两人站在门口对峙"
shots:
  - shot_id: "F01-S01"
    subject: "商北琛"
    shot_size: "中近景"
    camera_height: "平视"
    angle: "正面"
    movement: "固定"
    lens: "50mm"
    depth: "浅景深"
    coverage_role: "承载压迫发言"
    cut_reason: "台词前半句落下后切出"
    companion_visibility: "乔熙在过肩边缘"
    tailframe_role: "尾帧交给听者反应"
    dialogue_coverage: "前半句落在说话者，后半句切听者反应"
    transition_type: "同一机位继续"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("transition_type" in issue for issue in issues)
    assert any("tail_state_card" in issue for issue in issues)



def test_shot_director_vertical_discipline_rejects_micro_detail_shot_pileup():
    director_output = """fragment_id: F01
fragment_intent: "穿衣手忙脚乱"
reaction_coverage: "小豆丁不配合"
continuity_anchor: "乔熙在公寓给小豆丁穿衣"
main_shots:
  - shot_id: "F01-S01"
    subject: "掌心"
    shot_size: "CU"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "85mm"
    depth: "shallow"
    shot_intent: "手忙脚乱"
    dialogue_coverage: "none"
sub_shots:
  - parent_shot_id: "F01-S01"
    trigger: "穿衣卡住"
    subject: "鞋尖"
    shot_size: "CU"
    beat_purpose: "细节强调"
    emotion_anchor: "慌乱"
  - parent_shot_id: "F01-S01"
    trigger: "衣服滑脱"
    subject: "袖口"
    shot_size: "CU"
    beat_purpose: "继续强调"
    emotion_anchor: "更乱"
"""

    issues = _validate_shot_director_vertical_discipline(director_output, "9:16")

    assert any("多个微细节局部" in issue for issue in issues)


def test_shot_director_allows_empty_sub_shots_array():
    director_output = """fragment_id: F01
schema_version: shot_director_v2
fragment_intent: "handoff"
reaction_coverage: "none"
continuity_anchor: "same lobby"
blocking_plan: "single stable shot"
state_chain:
  - track: "door"
    progression: "open -> open"
event_coverage:
  - source_event: "Event."
    covered_by: "F01-S01"
shots:
  - shot_id: "F01-S01"
    subject: "Actor"
    shot_size: "medium shot"
    camera_height: "eye level"
    angle: "front"
    movement: "static"
    camera_basis: "subject_relative"
    camera_scene_position: "room_axis_front"
    camera_looks_toward: "toward_actor"
    subject_position: "room_center"
    subject_facing: "toward_camera"
    visible_landmarks: "room_axis=background_center"
    lens: "35mm"
    depth: "medium"
    coverage_role: "speaker_coverage"
    cut_reason: "scene_entry"
    companion_visibility: "none"
    state_delta: "stable"
    tailframe_role: "tailframe_reset"
    dialogue_coverage: "none"
    transition_type: "scene_fixed"
    tail_state_card: "人物站位: Actor在room_center；接触关系: 无接触；道具/门/车门状态: 门保持open；视线朝向: toward_camera；距离关系: 单人中景距离"
    shot_intent: "cover event"
sub_shots: []
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert not any("sub_shots" in issue for issue in issues)


def test_shot_director_v1_uses_merged_shot_field():
    director_output = """- fragment_id: F01
  fragment_task: "建立关系"
  rhythm: "稳慢压"
  continuity_context: "本片段是一段建立关系；乔熙、商北琛在同一办公室空间内；单人镜只改变拍摄主体，不代表另一人离开。"
  shots:
    - shot_id: F01-S01
      duration: "0-3秒"
      task: "建立两人对峙关系"
      subject: "乔熙、商北琛"
      shot: "过肩视角半身以上中景"
      action: "乔熙站在桌前看向商北琛，商北琛隔桌回看她。"
      dialogue: "~"
      must_carry: "两人隔桌对峙关系清楚。"
      cut_point: "两人视线稳定对上、空间关系看清后切。"
      continuity: "乔熙仍在桌前，商北琛仍在桌后，保持同侧轴线。"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert issues == []


def test_shot_director_requires_construction_sheet_fields():
    director_output = """- fragment_id: F01
  schema_version: shot_director_v2
  fragment_intent: "建立关系 + 反应落点"
  reaction_coverage: "乔熙被命令击中后的反讽反应必须可见"
  continuity_anchor: "乔熙在桌前，商北琛在桌后，保持右前方同侧轴线与办公桌阻隔关系"
  shots:
    - shot_id: F01-S01
      subject: "乔熙、商北琛"
      shot_size: "双人中景"
      camera_height: "平视"
      angle: "右前方45度"
      movement: "固定"
      lens: "35mm"
      depth: "中景深"
      coverage_role: "建立两人距离和办公桌阻隔关系"
      cut_reason: "关系建立后，切到乔熙反应"
      companion_visibility: "两人同画面，办公桌在中间"
      tailframe_role: "把乔熙桌前站位交给下一镜"
      dialogue_coverage: "无对白"
      transition_type: stay_on_A
      tail_state_card: "人物站位：乔熙桌前、商北琛桌后；接触关系：无；道具/门状态：办公桌阻隔；视线朝向：互看；距离关系：隔桌对峙"
    - shot_id: F01-S02
      subject: "乔熙"
      shot_size: "中近景"
      camera_height: "平视"
      angle: "同侧过肩"
      movement: "固定"
      lens: "50mm"
      depth: "浅景深"
      coverage_role: "承接乔熙听完后的受击反应"
      cut_reason: "反问句落下后，停在乔熙受击反应尾帧"
      companion_visibility: "商北琛肩线在前景边缘"
      tailframe_role: "以乔熙视线停住作为尾帧"
      dialogue_coverage: "乔熙原台词：What's this? Trying to intimidate me?"
      transition_type: cut_to_B
      tail_state_card: "人物站位：乔熙仍在桌前；接触关系：无；道具/门状态：工牌仍挂在胸前；视线朝向：看向商北琛；距离关系：隔桌"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert issues == []


def test_shot_director_rejects_vague_cut_point_in_construction_sheet():
    director_output = """- fragment_id: F01
  schema_version: shot_director_v2
  fragment_intent: "建立关系"
  reaction_coverage: "无独立反应"
  continuity_anchor: "保持左右关系"
  shots:
    - shot_id: F01-S01
      subject: "乔熙、商北琛"
      shot_size: "双人中景"
      camera_height: "平视"
      angle: "右前方45度"
      movement: "固定"
      lens: "35mm"
      depth: "中景深"
      coverage_role: "建立对峙关系"
      cut_reason: "更有电影感"
      companion_visibility: "两人同画面"
      tailframe_role: "保持对峙尾帧"
      dialogue_coverage: "无对白"
      transition_type: stay_on_A
      tail_state_card: "人物站位：两人对峙；接触关系：无；道具/门状态：无；视线朝向：互看；距离关系：隔桌"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("cut_reason 过于空泛" in issue for issue in issues)


def test_shot_director_restart_rerun_waits_for_per_segment_generation():
    state = {
        "agent_outputs": {"story_planner": "planner-output"},
        "knowledge_metadata": {"shot_director": {"old": True}},
    }
    saved_states = []

    previous_load_state = legacy_impl.load_state
    previous_save_state = legacy_impl.save_state

    def fake_load_state():
        return state

    def fake_save_state(updated_state):
        saved_states.append(dict(updated_state))

    legacy_impl.load_state = fake_load_state
    legacy_impl.save_state = fake_save_state
    try:
        result = runners.run_shot_director_restart_from_story_plan()
    finally:
        legacy_impl.load_state = previous_load_state
        legacy_impl.save_state = previous_save_state

    assert saved_states and saved_states[-1]["step"] == "step_3_direct"
    assert "shot_director" not in state["knowledge_metadata"]
    assert result["status"] == "waiting_for_user_input"
    assert result["current_segment_index"] == 1


def test_shot_director_closeup_density_is_soft_issue():
    issues = [
        "F02 在 9:16 里出现多次面部特写，特写使用过密。",
        "F04 的 main_shots 缺少字段 subject。",
    ]

    assert _hard_shot_director_issues(issues) == ["F04 的 main_shots 缺少字段 subject。"]


def test_shot_director_runtime_rules_and_rule_card_are_present():
    rules = _shot_director_source_event_rules()
    rhythm_rules = _shot_director_rhythm_match_rules()
    critical_files = get_agent_knowledge_files("shot_director", critical_only=True)

    assert "英文短语只按当前人物台词/画外音处理" in rules
    assert "不能联想成剧本外的新动作或新人物" in rules
    assert "公寓不能改成车内" in rules
    assert "subject 只能来自当前片段的人物行" in rules
    assert "一个片段的面部特写最多一次" in rules
    assert "没必要每个细节动作都给镜头" in rules
    assert "参考《AI 导演系统工程文档规范》" in rhythm_rules
    assert "镜头数量由节奏任务决定" in rhythm_rules
    assert "9:16 竖屏下，半身/中景/双人关系镜头是主力" in rhythm_rules
    assert "rules/shot_director/SHOT-SOURCE-EVENT-FIDELITY-001.md" in critical_files
    assert "07_Seedance输出词典与模型适配.md" in critical_files
    assert "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md" not in critical_files


def test_shot_director_rhythm_compliance_rules_present():
    rules = _shot_director_source_event_rules()
    rhythm_rules = _shot_director_rhythm_match_rules()

    assert "不得重新判断整体节奏" in rules, "shot_director must not re-judge overall rhythm"
    assert "必须服从 atmosphere_strategy" in rules, "shot_director must obey atmosphere_strategy"
    assert "快慢" in rules, "rules must include tempo control"
    assert "停顿" in rules, "rules must include pause control"
    assert "卡断" in rules, "rules must include cut control"
    assert "反应归属" in rules, "rules must include reaction attribution"
    assert "尾帧承接" in rules, "rules must include tailframe continuity"
    assert "剧本事实" in rules, "rules must mention script facts"
    assert "台词原文" in rules, "rules must mention original dialogue"
    assert "动作道具连续性" in rules, "rules must mention action/prop continuity"
    assert "空间轴线安全" in rules, "rules must mention spatial axis safety"
    assert "后者优先" in rules, "rules must state script facts take priority over rhythm"
    assert "story_planner 与 rhythm supervisor 给出的片段节奏指令" in rhythm_rules, "rhythm rules must reference upstream instructions"
    assert "不得重新判断整体节奏" in rhythm_rules, "rhythm rules must not allow re-judging rhythm"
