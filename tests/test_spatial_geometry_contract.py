from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph import (  # noqa: E402
    _collect_shot_director_issues,
    _compiler_guard_report,
    _repair_shot_layout_output,
    _spatial_geometry_contract_rules,
    _validate_shot_layout_output,
)


VALID_LAYOUT = """\
- fragment_id: "F01"
  fragment_intent: "电梯前收束"
  continuity_anchor: "商北琛位于大堂中轴，电梯门在前方"
  main_shots:
    - shot_id: "F01-S01"
      subject: "商北琛"
      shot_size: "半身中景"
      camera_height: "眼平高度"
      angle: "背后180度"
      movement: "固定机位"
      camera_basis: "scene_fixed"
      camera_scene_position: "lobby_axis_outside_elevator"
      camera_looks_toward: "toward_elevator_interior"
      subject_position: "lobby_axis_before_elevator"
      subject_facing: "toward_elevator"
      visible_landmarks: "elevator_door_frame=midground_ahead, employee_lines=background_left_right_blur"
      lens: "35mm"
      depth: "中景深"
      coverage_role: "tailframe_reset"
      cut_reason: "动作承接"
      companion_visibility: "员工列在左右后景虚化"
      tailframe_role: "tailframe_reset"
      shot_intent: "商北琛背对大堂进入电梯"
      dialogue_coverage: none
"""


def test_spatial_geometry_rules_are_part_of_contract():
    rules = _spatial_geometry_contract_rules()

    assert "camera_basis" in rules
    assert "scene_fixed" in rules
    assert "visible_landmarks" in rules
    assert "前景/中景/后景" in rules
    assert "镜头表达句" in rules
    assert "最终必须翻译成视角" in rules
    assert "坐标式空间说明" in rules


def test_layout_validation_requires_spatial_geometry_fields():
    broken = VALID_LAYOUT.replace('      camera_basis: "scene_fixed"\n', "")

    issues = _validate_shot_layout_output(broken, ["F01"])

    assert any("camera_basis" in issue for issue in issues)


def test_layout_repair_adds_dialogue_coverage_and_fixes_elevator_background():
    broken = """\
- fragment_id: "F01"
  fragment_intent: "entry pressure"
  continuity_anchor: "lobby axis toward elevator"
  main_shots:
    - shot_id: "F01-S01"
      subject: "Nash"
      shot_size: "MS"
      camera_height: "eye_level"
      angle: "frontal"
      movement: "static"
      camera_basis: "scene_fixed"
      camera_scene_position: "elevator_side_facing_lobby"
      camera_looks_toward: "toward_lobby_axis"
      subject_position: "lobby_axis_before_elevator"
      subject_facing: "toward_elevator"
      visible_landmarks:
        elevator_door: background_center_closed
        employee_lines: background_left_right_blur
      lens: "50mm"
      depth: "medium"
      coverage_role: "establish_relation"
      cut_reason: "scene_entry"
      companion_visibility: "employees remain on both sides"
      tailframe_role: "none"
      shot_intent: "Nash faces the elevator while holding the axis"
"""

    repaired = _repair_shot_layout_output(broken)
    issues = _validate_shot_layout_output(repaired, ["F01"])

    assert "dialogue_coverage: none" in repaired
    assert "elevator_door: foreground_edges_or_side_edges" in repaired
    assert "employee_lines: background_left_right_blur" in repaired
    assert not any("dialogue_coverage" in issue for issue in issues)
    assert not any("空间几何矛盾" in issue or "绌洪棿鍑犱綍鐭涚浘" in issue for issue in issues)


def test_layout_validation_rejects_camera_monotony_across_main_shots():
    monotone = """\
- fragment_id: "F01"
  fragment_intent: "dialogue and reaction"
  continuity_anchor: "same lobby axis"
  main_shots:
    - shot_id: "F01-S01"
      subject: "Boss"
      shot_size: "MS"
      camera_height: "eye_level"
      angle: "frontal"
      movement: "static"
      camera_basis: "subject_relative"
      camera_scene_position: "lobby_axis_front"
      camera_looks_toward: "toward_boss"
      subject_position: "lobby_center"
      subject_facing: "toward_assistant"
      visible_landmarks: "desk=foreground_edge, assistant=offscreen_right"
      lens: "50mm"
      depth: "medium"
      coverage_role: "speaker_coverage"
      cut_reason: "scene_entry"
      companion_visibility: "assistant stays offscreen right"
      tailframe_role: "none"
      shot_intent: "speaker coverage"
      dialogue_coverage: "Meeting in ten minutes."
    - shot_id: "F01-S02"
      subject: "Assistant"
      shot_size: "MCU"
      camera_height: "eye_level"
      angle: "frontal"
      movement: "static"
      camera_basis: "subject_relative"
      camera_scene_position: "lobby_axis_front"
      camera_looks_toward: "toward_boss"
      subject_position: "lobby_right"
      subject_facing: "toward_boss"
      visible_landmarks: "desk=foreground_edge, boss=offscreen_left"
      lens: "50mm"
      depth: "medium"
      coverage_role: "receiver_reaction_setup"
      cut_reason: "speaker_to_receiver"
      companion_visibility: "boss stays offscreen left"
      tailframe_role: "tailframe_reset"
      shot_intent: "receiver reaction"
      dialogue_coverage: none
"""

    issues = _validate_shot_layout_output(monotone, ["F01"])

    assert any("camera monotony" in issue for issue in issues)


def test_layout_validation_rejects_single_camera_overload():
    overloaded = """\
- fragment_id: "F02"
  fragment_intent: "collision and reaction"
  continuity_anchor: "door gap half open"
  main_shots:
    - shot_id: "F02-S01"
      subject: "Qiao and Boss"
      shot_size: "MS"
      camera_height: "eye_level"
      angle: "left_side_90"
      movement: "static"
      camera_basis: "scene_fixed"
      camera_scene_position: "elevator_threshold_side"
      camera_looks_toward: "toward_elevator_interior"
      subject_position: "door_threshold"
      subject_facing: "toward_each_other"
      visible_landmarks: "elevator_frame=side_edges, lobby_axis=background"
      lens: "35mm"
      depth: "medium"
      coverage_role: "speaker_coverage"
      cut_reason: "scene_entry"
      companion_visibility: "both characters remain visible"
      tailframe_role: "tailframe_reset"
      shot_intent: "collision, receiver reaction, then entering elevator freeze"
      dialogue_coverage: "Wait a second!"
"""

    issues = _validate_shot_layout_output(overloaded, ["F02"])

    assert any("single-camera overload" in issue for issue in issues)


def test_layout_validation_rejects_action_path_closeup_main_shot():
    action_closeup = """\
- fragment_id: "F03"
  fragment_intent: "threshold collision"
  continuity_anchor: "elevator door half open"
  main_shots:
    - shot_id: "F03-S01"
      subject: "Qiao"
      shot_size: "CU"
      camera_height: "eye_level"
      angle: "left_side_90"
      movement: "static"
      camera_basis: "scene_fixed"
      camera_scene_position: "elevator_threshold_side"
      camera_looks_toward: "toward_elevator_door"
      subject_position: "door_threshold"
      subject_facing: "toward_elevator"
      visible_landmarks: "elevator_frame=side_edges, lobby_axis=background"
      lens: "50mm"
      depth: "medium"
      coverage_role: "action_insert_slot"
      cut_reason: "action_path_visibility"
      companion_visibility: "Boss remains midground inside elevator"
      tailframe_role: "none"
      shot_intent: "Qiao rushes through the threshold and collides with Boss"
      dialogue_coverage: none
"""

    issues = _validate_shot_layout_output(action_closeup, ["F03"])

    assert any("动作路径/碰撞/过阈值不能用特写类 main_shot" in issue for issue in issues)


def test_layout_validation_rejects_micro_detail_as_main_shot():
    micro_detail = """\
- fragment_id: "F04"
  fragment_intent: "hand detail"
  continuity_anchor: "same lobby"
  main_shots:
    - shot_id: "F04-S01"
      subject: "指尖"
      shot_size: "CU"
      camera_height: "eye_level"
      angle: "frontal"
      movement: "static"
      camera_basis: "subject_relative"
      camera_scene_position: "lobby_axis_front"
      camera_looks_toward: "toward_hand"
      subject_position: "lobby_center"
      subject_facing: "toward_camera"
      visible_landmarks: "suit_front=midground"
      lens: "85mm"
      depth: "shallow"
      coverage_role: "action_insert_slot"
      cut_reason: "impact_visibility"
      companion_visibility: "Boss remains frame edge"
      tailframe_role: "none"
      shot_intent: "fingers release the suit fabric"
      dialogue_coverage: none
"""

    issues = _validate_shot_layout_output(micro_detail, ["F04"])

    assert any("局部不能作为 main_shot 主体" in issue for issue in issues)


def test_layout_validation_rejects_tailframe_closeup():
    tailframe_closeup = """\
- fragment_id: "F05"
  fragment_intent: "tailframe reset"
  continuity_anchor: "same office doorway"
  main_shots:
    - shot_id: "F05-S01"
      subject: "Qiao"
      shot_size: "CU"
      camera_height: "eye_level"
      angle: "frontal"
      movement: "static"
      camera_basis: "subject_relative"
      camera_scene_position: "doorway_axis_front"
      camera_looks_toward: "toward_qiao"
      subject_position: "doorway_threshold"
      subject_facing: "toward_camera"
      visible_landmarks: "door_frame=side_edges"
      lens: "50mm"
      depth: "shallow"
      coverage_role: "tailframe_reset"
      cut_reason: "space_reset"
      companion_visibility: "Boss remains offscreen right"
      tailframe_role: "tailframe_reset"
      shot_intent: "hold Qiao close-up as the tailframe reset"
      dialogue_coverage: none
"""

    issues = _validate_shot_layout_output(tailframe_closeup, ["F05"])

    assert any("尾帧镜头景别不合格" in issue for issue in issues)


def test_director_validation_rejects_impossible_background_elevator_anchor():
    director_output = """\
- fragment_id: "F01"
  fragment_intent: "电梯前收束"
  continuity_anchor: "商北琛位于大堂中轴，电梯门在前方"
  reaction_coverage: "none"
  blocking_plan: "商北琛面朝电梯停住"
  state_chain:
    - track: "position"
      progression: "大堂中轴 -> 电梯门前"
  event_coverage:
    - source_event: "商北琛进入电梯。"
      covered_by: "F01-S01"
      coverage_note: "覆盖进入电梯动作"
  main_shots:
    - shot_id: "F01-S01"
      subject: "商北琛"
      shot_size: "半身中景"
      camera_height: "眼平高度"
      angle: "正面"
      movement: "固定机位"
      camera_basis: "subject_relative"
      camera_scene_position: "elevator_side"
      camera_looks_toward: "toward_lobby_axis"
      subject_position: "lobby_axis_before_elevator"
      subject_facing: "toward_elevator"
      visible_landmarks: "elevator_door_frame=background_center, employee_lines=background_left_right_blur"
      lens: "50mm"
      depth: "中景深"
      coverage_role: "tailframe_reset"
      cut_reason: "动作承接"
      companion_visibility: "员工列在后景虚化"
      state_delta: "商北琛转身进入电梯"
      tailframe_role: "tailframe_reset"
      shot_intent: "进入电梯"
      dialogue_coverage: none
"""

    issues = _collect_shot_director_issues(
        director_output,
        expected_segments=["F01"],
        script="商北琛进入电梯。",
        planner_output='- fragment_id: "F01"\n  source_script_events:\n    - "商北琛进入电梯。"\n',
        aspect_ratio="9:16",
    )

    assert any("空间几何矛盾" in issue for issue in issues)
    assert any("人物相对正面机位不能承载" in issue for issue in issues)


def test_compiler_guard_rejects_generic_door_background_conflict():
    prompt = """片段1｜办公室门口｜转身出门｜~6秒
【时间轴】
0-3秒：乔熙半身中景，摄影机位于乔熙正前方0度、眼平高度、固定机位。乔熙面朝房门，后景房门门框清楚可见，最后她停在房门前。
3-6秒：同一机位继续，保留乔熙正面和后景房门门框。乔熙仍朝向房门，最后停在房门前。"""

    report = _compiler_guard_report(prompt, "", "", "")

    assert "通用门框前后景矛盾" in report
