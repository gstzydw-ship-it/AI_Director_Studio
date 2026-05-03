from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package.prompt_compiler_impl import (
    _DIALOGUE_COVERAGE_TERMS_RE,
    _SOURCE_ACTION_BEAT_RE,
    _SOURCE_DIALOGUE_LINE_RE,
    _SOURCE_SOUND_LINE_RE,
    _compiler_guard_report,
    _dialogue_coverage_contract_rules,
)
from agents.director_graph_package.shot_director_impl import (
    _repair_shot_director_contract_output,
    _validate_shot_director_dialogue_coverage,
    _validate_shot_director_script_fidelity,
)


def test_dialogue_rules_forbid_single_setup_for_full_pressure_line():
    rules = _dialogue_coverage_contract_rules()

    assert "严禁一个镜头、一个景别、一个机位说完整句" in rules
    assert "对白内部写出明确切镜点" in rules
    assert "同一双人中景连续说完" in rules


def test_dialogue_coverage_terms_include_short_drama_script_signals():
    coverage = (
        "乔熙起句 Kiki, cover for me；切小豆丁听者反应；"
        "乔熙OS以画外音落在照片特写上；音效闹钟铃响；句尾乔熙僵住，眼眶微红。"
    )

    assert _DIALOGUE_COVERAGE_TERMS_RE.search(coverage)


def test_source_script_dialogue_sound_and_reaction_lines_are_detected():
    script = """1-1 晨/内/乔熙公寓
人物：乔熙、小豆丁
【特写-闹钟：7:30】
【音效：闹钟铃响】
▲乔熙手忙脚乱地给小豆丁穿衣服，一边打电话。
乔熙：Kiki, cover for me. I'll be right there!
▲小豆丁扭来扭去，不肯配合。
小豆丁：I don't want to go to school!
乔熙OS：Why is Nash's photo here?
▲乔熙看着照片，眼眶微红，手指不自觉地摩挲着照片边缘。
"""

    assert len(_SOURCE_DIALOGUE_LINE_RE.findall(script)) == 4
    assert len(_SOURCE_SOUND_LINE_RE.findall(script)) == 1
    assert len(_SOURCE_ACTION_BEAT_RE.findall(script)) == 1


def test_guard_flags_pressure_dialogue_when_only_block_opening_cut_exists():
    prompt = """片段1｜总裁办公室｜压迫质问｜~16秒
【时间轴】
0-7秒：镜头切至商北琛胸部以上中近景，摄影机位于商北琛右前方30度、眼平高度、固定机位。商北琛看向桌对面的乔熙，说“Your coffee's gotten better, but your brain clearly hasn't.” 他说完后仍坐在桌后，视线持续压向乔熙。
7-16秒：镜头切至两人双人中景，摄影机位于行政桌侧面左前方45度、眼平高度、固定机位。乔熙问“Mr. Pierce, could you point out which part is wrong?” 商北琛回击“They're your mistakes. You expect me to fix them?” 乔熙问“Can I get this to you tomorrow?” 商北琛说“Sunny, if it's not done, you're not leaving.” 乔熙说“Nash, you're doing this on purpose.” 商北琛说“On purpose? You think you're that important?” 句尾两人仍隔桌对峙，乔熙站在桌前，商北琛坐在桌后，报告留在桌面中央。
【约束】
禁止字幕。"""

    report = _compiler_guard_report(
        prompt,
        "商北琛：Your coffee's gotten better, but your brain clearly hasn't.",
        "",
        "main_shots:\n- shot_id: F01-S01",
    )

    assert "镜头资产缺少空间几何合同" in report
    assert "时间轴第 1 个时间段缺少结束状态" in report


def test_guard_accepts_pressure_dialogue_with_listener_reaction_cut_inside_line():
    prompt = """片段1｜总裁办公室｜压迫质问｜~16秒
【时间轴】
0-7秒：商北琛胸部以上中近景，摄影机位于商北琛右前方30度、眼平高度、固定机位。商北琛看向桌对面的乔熙，说“Your coffee's gotten better.” 镜头切至乔熙中近景，摄影机位于乔熙左前方45度、眼平高度，保留桌边和商北琛肩线轻虚，乔熙听见后下颌绷住；商北琛后半句以画外音继续：“but your brain clearly hasn't.” 句尾乔熙仍站在桌前，视线压回商北琛。
7-16秒：镜头切回两人双人中景，摄影机位于行政桌侧面左前方45度、眼平高度、固定机位。乔熙问“Mr. Pierce, could you point out which part is wrong?” 反打至商北琛中近景，商北琛回击“They're your mistakes. You expect me to fix them?” 镜头切至乔熙中近景，乔熙问“Can I get this to you tomorrow?” 商北琛画外音说“Sunny, if it's not done, you're not leaving.” 乔熙停顿后说“Nash, you're doing this on purpose.” 切回商北琛中近景，他说“On purpose? You think you're that important?” 句尾两人仍隔桌对峙，乔熙站在桌前，商北琛坐在桌后，报告留在桌面中央。
【约束】
禁止字幕。"""

    report = _compiler_guard_report(
        prompt,
        "商北琛：Your coffee's gotten better, but your brain clearly hasn't.",
        "",
        "main_shots:\n- shot_id: F01-S01",
    )

    assert "人物说话时严禁一个镜头、一个景别或一个机位说完整句" not in report
    assert "对白内部加入" not in report


def test_guard_rejects_same_camera_continue_wording_even_before_hidden_subject_switch():
    prompt = """片段1｜电梯口｜冲入+失衡｜~10秒
【时间轴】
0-5秒：乔熙半身中景，摄影机位于乔熙右前方30度、固定机位。乔熙冲到电梯门口，停在门缝前，视线盯住门内，句尾仍站在门旁。
5-10秒：同一机位继续，严飞胸部以上中近景，摄影机位于严飞左前方30度。严飞低头，肩膀收紧，停在电梯侧边。
【约束】
禁止字幕。"""

    report = _compiler_guard_report(prompt, "", "", "shots:\n- shot_id: F01-S01")

    assert "PROMPT-NO-SAME-CAMERA-ABUSE-001" in report
    assert "隐性切镜" in report


def test_guard_flags_abstract_director_words_for_visible_body_language_translation():
    prompt = """片段1｜办公室｜压迫对峙｜~8秒
【时间轴】
0-4秒：商北琛胸部以上中近景，摄影机位于商北琛右前方30度、固定机位。商北琛说完后，空气收紧，压迫感压在乔熙脸上，句尾两人仍隔桌对峙。
4-8秒：镜头切至乔熙胸部以上中近景，摄影机位于乔熙左前方30度、固定机位。乔熙嘴唇停住，下颌收紧，仍站在桌前。
【约束】
禁止字幕。"""

    report = _compiler_guard_report(prompt, "", "", "shots:\n- shot_id: F01-S01")

    assert "不可生成的抽象情绪判断" in report


def test_shot_director_validator_rejects_long_dialogue_without_coverage_design():
    director_output = """- fragment_id: F01
  fragment_intent: office pressure
  reaction_coverage: receiver reaction
  continuity_anchor: office desk
  main_shots:
    - shot_id: F01-S01
      subject: 商北琛
      shot_size: 中近景
      camera_height: eye_level
      angle: front_right
      movement: static
      camera_basis: subject_relative
      camera_scene_position: 办公桌侧前方
      camera_looks_toward: 朝向商北琛
      subject_position: 桌后
      subject_facing: 朝向乔熙
      visible_landmarks: 桌面报表
      lens: 50mm
      depth: shallow
      coverage_role: speaker_coverage
      cut_reason: pressure_line
      companion_visibility: 乔熙画外
      state_delta: 商北琛持续发话
      tailframe_role: none
      shot_intent: 压迫乔熙
      attention_target: 商北琛发话
      information_strategy: reveal pressure
      selection_reason: viewer attention needs the speaker pressure but the line still needs visual coverage
      rejected_alternatives: none
      dialogue_coverage: 商北琛：They're your mistakes. You expect me to fix them? Sunny, if it's not done, you're not leaving.
"""

    issues = _validate_shot_director_dialogue_coverage(director_output)

    assert any("不能交给 prompt_compiler 临场补" in issue for issue in issues)


def test_shot_director_validator_accepts_long_dialogue_with_reaction_cut_design():
    director_output = """- fragment_id: F01
  fragment_intent: office pressure
  reaction_coverage: receiver reaction
  continuity_anchor: office desk
  main_shots:
    - shot_id: F01-S01
      subject: 商北琛
      shot_size: 中近景
      camera_height: eye_level
      angle: front_right
      movement: static
      camera_basis: subject_relative
      camera_scene_position: 办公桌侧前方
      camera_looks_toward: 朝向商北琛
      subject_position: 桌后
      subject_facing: 朝向乔熙
      visible_landmarks: 桌面报表
      lens: 50mm
      depth: shallow
      coverage_role: speaker_start
      cut_reason: pressure_line_start
      companion_visibility: 乔熙画外
      state_delta: 商北琛起句后把后半句压到乔熙反应上
      tailframe_role: none
      shot_intent: 压迫乔熙
      attention_target: 商北琛发话
      information_strategy: speaker start then listener reaction
      selection_reason: viewer attention starts on speaker then cuts to listener reaction for pressure landing
      rejected_alternatives: none
      dialogue_coverage: 商北琛起句 They're your mistakes；切乔熙中近景听者反应；后半句 You expect me to fix them? 以画外音/L-cut 落在乔熙脸上。
"""

    issues = _validate_shot_director_dialogue_coverage(director_output)

    assert issues == []


def test_shot_director_deterministic_repair_fixes_dialogue_and_subject_alias():
    script = "人物：乔熙、商北琛\n商北琛：Sunny, if it's not done, you're not leaving."
    director_output = """- fragment_id: F01
  fragment_intent: office pressure
  reaction_coverage: receiver reaction
  continuity_anchor: office desk
  main_shots:
    - shot_id: F01-S01
      subject: Sunny
      shot_size: 中近景
      camera_height: eye_level
      angle: front_left
      movement: static
      camera_basis: subject_relative
      camera_scene_position: 办公桌前方
      camera_looks_toward: 朝向乔熙
      subject_position: 桌前
      subject_facing: 朝向商北琛
      visible_landmarks: 桌边报表
      lens: 50mm
      depth: shallow
      coverage_role: receiver_reaction_setup
      cut_reason: pressure_line
      companion_visibility: 商北琛画外
      state_delta: Sunny听完命令
      tailframe_role: none
      shot_intent: 承接受击
      attention_target: Sunny
      information_strategy: reveal pressure
      selection_reason: viewer attention needs the receiver reaction and desk continuity
      rejected_alternatives: speaker only rejected
      dialogue_coverage: 商北琛：They're your mistakes. You expect me to fix them? Sunny, if it's not done, you're not leaving.
"""

    repaired = _repair_shot_director_contract_output(director_output, script)

    assert "subject: 乔熙" in repaired
    assert "听者反应/反打" in repaired
    assert "画外音/OS/L-cut" in repaired
    assert _validate_shot_director_dialogue_coverage(repaired) == []
    assert _validate_shot_director_script_fidelity(repaired, script) == []
