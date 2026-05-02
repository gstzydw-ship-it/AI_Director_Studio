from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package.prompt_compiler_impl import (
    _camera_execution_rules,
    _camera_task_selection_rules,
    _compiler_guard_report,
    _shot_composition_task_selection_rules,
)


def test_camera_execution_rules_ban_ambiguous_camera_language():
    rules = _camera_execution_rules()

    assert "正面、左前方、右前方、左侧、右侧、背后" in rules
    assert "不要每段都写数字角度" in rules
    assert "轻微前推跟随" in rules
    assert "纵深中全景到半身中景" in rules
    assert "眼平高度" in rules
    assert "沉默就是回应" in rules


def test_camera_task_selection_rules_map_tasks_to_angles():
    rules = _camera_task_selection_rules()

    assert "优先左侧、右侧、左后方、右后方" in rules
    assert "优先背后、左后方、右后方" in rules
    assert "单一主机位持续承担整段" in rules
    assert "同段切换只能发生在选定一侧内部" in rules
    assert "cut_point" in rules


def test_shot_composition_rules_map_tasks_to_shot_sizes():
    rules = _shot_composition_task_selection_rules()

    assert "镜头任务到景别/镜头类型选择硬规则" in rules
    assert "建立空间、人物关系、尾帧交接" in rules
    assert "中景、半身关系景、双人中景或全身关系景" in rules
    assert "手部、道具、门缝、照片、手机、衣角等细节只能作为短 sub_shot" in rules
    assert "禁止连续用特写推进整段" in rules


def test_compiler_guard_flags_ambiguous_camera_and_abstract_phrases():
    prompt = """片段1｜天御集团大堂｜入场立威｜~12秒

【时间轴】
0-3秒：商北琛半身中景，平视三分之四角度，轻微前推跟随，他走向电梯。沉默就是回应，权力关系在这一拍里锁住。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "机位/运镜存在模糊描述" in report
    assert "不可生成的抽象情绪判断" in report
    assert "缺少可执行摄影机位置" in report


def test_compiler_guard_flags_director_jargon_that_needs_visual_translation():
    prompt = """片段1｜天御集团大堂｜入场立威｜~12秒

【时间轴】
0-4秒：商北琛半身中景，摄影机位于商北琛正前方0度、眼平高度。稳定器在同一运动里带到严飞和主管胸部以上受压反应。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "导演调度口语" in report
    assert "受压反应" in report


def test_compiler_guard_flags_broader_director_jargon_in_execution_text():
    prompt = """片段1｜电梯闯入｜卡断+钩子｜~8秒

【风格锚点】
冷峻压迫，权力关系紧绷。

【镜头序列】
镜头1【4秒】【乔熙】中景，摄影机位于电梯门外大堂中轴，乔熙冲向电梯。这里卡断在炸点，尾帧悬停，留足回味。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "导演调度口语" in report
    assert "卡断" in report
    assert "炸点" in report
    assert "尾帧悬停" in report


def test_compiler_guard_flags_complex_camera_fields_from_old_shot_director():
    prompt = """片段1｜日/内/天御集团大堂｜入场｜~12秒

【镜头序列】
镜头1【3秒】【商北琛、众员工】纵深中全景到商北琛半身中景，右前方眼平高度，稳定器在商北琛前方同速后退；商北琛从入口方向进入大堂。
镜头2【4秒】【商北琛、严飞、主管员工】商北琛半身中景，同一镜头内横移 truck right 到严飞和主管胸部以上反应，再横移 truck left 回到商北琛半身主位。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "复杂摄影字段" in report
    assert "truck right" in report


def test_compiler_guard_does_not_flag_style_anchor_only_jargon():
    prompt = """片段1｜天御集团大堂｜入场立威｜~12秒

【风格锚点】
冷峻压迫，权力关系紧绷。

【镜头序列】
镜头1【4秒】【商北琛】半身中景，摄影机位于商北琛正前方0度、眼平高度，商北琛看向严飞，严飞低头避开视线。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "导演调度口语" not in report


def test_compiler_guard_accepts_explicit_camera_position_language():
    prompt = """片段1｜天御集团大堂｜入场立威｜~12秒

【时间轴】
0-3秒：商北琛半身中景，摄影机位于商北琛正前方，正面平稳跟拍。商北琛向电梯方向步行，两侧员工停住手上动作并看向他。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "机位/运镜存在模糊描述" not in report
    assert "不可生成的抽象情绪判断" not in report
    assert "缺少可执行摄影机位置" not in report


def test_compiler_guard_rejects_single_segment_reverse_shot_language():
    prompt = """片段1｜总裁办公室｜压迫对白｜~10秒

【时间轴】
0-4秒：乔熙半身中景，左前方眼平，固定机位。乔熙看向商北琛，说出"Could you point out which part is wrong?"
4-8秒：反打至商北琛半身中景，右前方眼平，固定机位。商北琛看着乔熙，说出"They're your mistakes."
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "PROMPT-AXIS-LOCK-PER-SEGMENT-001" in report
    assert "单段 prompt 内出现" in report and "反打" in report


def test_compiler_guard_rejects_left_and_right_axis_in_one_timeline_block():
    prompt = """片段1｜总裁办公室｜压迫对白｜~10秒

【时间轴】
0-5秒：乔熙半身中景，左前方眼平，固定机位。镜头切至商北琛右前方半身中景，他冷声回应，乔熙在画外停住。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "PROMPT-AXIS-LOCK-PER-SEGMENT-001" in report
    assert "左前方" in report and "右前方" in report
