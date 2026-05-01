from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package.prompt_compiler_impl import (
    _compiler_guard_report,
    _timeline_continuity_contract_rules,
)


def test_timeline_continuity_rules_require_bridged_time_blocks():
    rules = _timeline_continuity_contract_rules()

    assert "同一机位继续" in rules
    assert "镜头切至/切回" in rules
    assert "单段内禁止反打" in rules
    assert "每个时间段最后一句必须写清结束状态" in rules
    assert "人物相对机位和场景固定机位不能混用" in rules


def test_guard_flags_time_block_that_restarts_without_bridge():
    prompt = """片段1｜大堂｜入场｜~12秒

【时间轴】
0-3秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛沿中轴走向电梯，最后停在大堂中轴前段。
3-6秒：员工群体中景，摄影机位于员工群体左前方45度、眼平高度、固定机位。员工看向商北琛，最后停在两侧员工列。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "缺少段内交接词" in report


def test_guard_flags_person_relative_camera_when_entering_elevator():
    prompt = """片段1｜大堂｜入场｜~12秒

【时间轴】
0-3秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛说完台词，最后停在大堂中轴前段。
3-6秒：镜头切至商北琛半身中景，摄影机位于商北琛正前方0度、眼平高度、固定机位，画面保留电梯门框。商北琛转入电梯，最后停在电梯内。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "人物相对机位与入电梯动作冲突" in report


def test_guard_accepts_bridged_same_space_timeline():
    prompt = """片段1｜大堂｜入场｜~12秒

【时间轴】
0-3秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛沿中轴走向电梯，员工停住动作，最后商北琛停在大堂中轴前段，电梯门框在后景可见。
3-6秒：镜头切至员工列反应中景，保留商北琛背影在右前景和电梯门框在后景，摄影机位于员工列左前方45度、眼平高度、固定机位。员工看向商北琛，最后两侧员工仍停在中轴两边。
6-9秒：镜头切回商北琛胸部以上中近景，保留后景电梯门框和两侧员工列虚化，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛说完台词，最后停在大堂中轴前段。
9-12秒：镜头切至电梯门外中景，摄影机固定在电梯门外大堂中轴，朝向电梯内部，眼平高度，画面保留门框和中轴地面。商北琛背对摄影机进入电梯，最后站定在轿厢中央偏后位置，电梯门停在将合未合的窄门缝。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "缺少段内交接词" not in report
    assert "缺少结束状态" not in report
    assert "人物相对机位与入电梯动作冲突" not in report


def test_guard_flags_impossible_elevator_background_anchor():
    prompt = """片段1｜大堂｜入场｜~12秒

【时间轴】
0-3秒：商北琛中景，摄影机位于商北琛正前方0度、眼平高度、固定机位。商北琛面朝电梯，后景电梯门框和两侧员工列虚化可见，最后商北琛停在中轴前段。
3-6秒：同一机位继续，保留商北琛正面和后景电梯门框。商北琛面朝电梯说完台词，最后仍站在中轴前段。
"""

    report = _compiler_guard_report(prompt, "", "", "main_shots:\n- shot_id: F01-S01")

    assert "空间前后景矛盾" in report
