from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph import _compiler_guard_report


def test_guard_flags_overloaded_space_control_section():
    prompt = """片段1｜集团大堂电梯口｜入场｜~12秒
【空间与首帧总控】
@图片7用于集团大堂。大堂纵深轴线从门口直通尽头电梯，电梯门框位于画面前方尽头，两侧员工分布在中轴两边，严飞位于电梯门外一侧边缘，商北琛位于门口方向的轴线外端，前景左右保留电梯门框，中景保留员工列，后景保留门口方向，远端尽头保留大堂延伸和左右边缘关系，画面中轴、前景、中景、后景全部清楚可见。
【时间轴】
0-3秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛站在大堂中轴前段，视线看向电梯，最后停在原位。
3-6秒：镜头切至员工中景，摄影机位于员工左前方45度、眼平高度、固定机位，保留大堂中轴。员工停住并看向商北琛，最后仍在两侧。
【约束】
无新增人物。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "空间与首帧总控过载" in report


def test_guard_flags_elevator_opening_to_office_space():
    prompt = """片段1｜集团大堂电梯口｜入电梯｜~12秒
【时间轴】
0-4秒：商北琛中景，摄影机位于商北琛背后180度、眼平高度、固定机位。商北琛从大堂中轴走向电梯，视线不看严飞，最后停在电梯门前。
4-8秒：镜头切至电梯门外中景，摄影机位于电梯门外大堂中轴、眼平高度、固定机位。电梯门打开后露出另一片办公区和窗户，商北琛跨入电梯，最后站在门内。
【约束】
无新增对白。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "电梯空间漂移" in report
    assert "入电梯片段缺少轿厢物理锁" in report


def test_guard_requires_negative_space_lock_for_elevator_entry():
    prompt = """片段1｜集团大堂电梯口｜入电梯｜~12秒
【时间轴】
0-4秒：商北琛中景，摄影机位于商北琛背后180度、眼平高度、固定机位。商北琛从大堂中轴走向电梯，视线不看严飞，最后停在电梯门前。
4-8秒：镜头切至电梯门外中景，摄影机位于电梯门外大堂中轴、眼平高度、固定机位。电梯门内是封闭金属轿厢和控制面板，商北琛跨入电梯，最后站在轿厢中央。
【约束】
无新增对白。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "入电梯片段缺少负向空间锁" in report


def test_guard_requires_crowd_face_lock_when_named_characters_and_employees_coexist():
    prompt = """片段1｜集团大堂电梯口｜清场｜~12秒
【时间轴】
0-4秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、稳定器后退。众员工在两侧停住，视线看向商北琛，最后让出中轴。
4-8秒：镜头切至严飞中景，摄影机位于严飞左前方45度、眼平高度、固定机位，保留电梯门框。严飞后退让开，最后停在门外侧。
【约束】
商北琛和严飞身份一致。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "群演身份锁缺失" in report


def test_guard_flags_timeline_block_without_performance_beat():
    prompt = """片段1｜集团大堂电梯口｜空间说明｜~12秒
【时间轴】
0-4秒：集团大堂全景，摄影机位于大堂左前方45度、眼平高度、固定机位。前景是门框，中景是中轴，后景是电梯，两侧是员工列，最后画面保持大堂纵深。
4-8秒：镜头切至大堂中景，摄影机位于大堂右前方45度、眼平高度、固定机位，保留电梯门框和中轴。前景、中景、后景关系清楚，最后画面保持稳定。
【约束】
无新增对白。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "缺少人物动作/表情落点" in report


def test_guard_flags_scene_relative_rear_camera_wording():
    prompt = """片段1｜集团大堂电梯口｜入电梯｜~12秒
【时间轴】
0-4秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛看向电梯，最后停在电梯门前。
4-8秒：镜头切至电梯门外背后180度中景，摄影机眼平高度、固定机位。商北琛跨入封闭金属电梯轿厢，严飞停在门外，最后电梯门保持将合未合。
【约束】
电梯门后不得出现办公区、会议区、走廊、窗户或另一片大堂。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "伪精确空间机位" in report


def test_guard_keeps_cut_bridge_requirement_under_space_simplification():
    prompt = """片段1｜集团大堂电梯口｜空间简写｜~12秒
【时间轴】
0-4秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、稳定器后退。商北琛向电梯走去，视线扫过员工，最后停在电梯门前。
4-8秒：商北琛侧后方中景，摄影机眼平高度、固定机位。商北琛继续向前，严飞后退让开，最后两人停在电梯门两侧。
【约束】
无新增对白。"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "缺少段内交接词" in report
