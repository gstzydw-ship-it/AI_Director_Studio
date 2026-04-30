from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph import (  # noqa: E402
    _clean_shot_director_output,
    _hard_shot_director_issues,
    _shot_director_rhythm_match_rules,
    _shot_director_source_event_rules,
    _validate_shot_director_output,
    _validate_shot_director_source_event_coverage,
    _validate_shot_director_script_fidelity,
    _validate_shot_director_vertical_discipline,
)
from agents.knowledge_base import get_agent_knowledge_files  # noqa: E402


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
source_script_events:
  - "▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。"
  - "▲小豆丁已经站在门口，单肩背着书包等她。"
main_shots:
  - shot_id: "F04-S01"
reaction_plan: "片段内承接"
"""
    director_output = """fragment_id: F04
fragment_intent: "乔熙放下照片"
reaction_coverage: "乔熙反应"
continuity_anchor: "照片在桌上"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "乔熙放下照片"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_source_event_coverage(director_output, planner)

    assert any("小豆丁" in issue and "书包" in issue for issue in issues)


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
main_shots:
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
    shot_intent: "cover event"
sub_shots: []
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert not any("sub_shots" in issue for issue in issues)


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

    assert "wake up" in rules
    assert "不能改拍成乔熙睡觉" in rules
    assert "公寓不能改成车内" in rules
    assert "subject 只能来自当前片段的人物行" in rules
    assert "一个片段的面部特写最多一次" in rules
    assert "没必要每个细节动作都给镜头" in rules
    assert "参考《AI 导演系统工程文档规范》" in rhythm_rules
    assert "镜头数量由节奏任务决定" in rhythm_rules
    assert "9:16 竖屏下，半身/中景/双人关系镜头是主力" in rhythm_rules
    assert "rules/shot_director/SHOT-SOURCE-EVENT-FIDELITY-001.md" in critical_files
