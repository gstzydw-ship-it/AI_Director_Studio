from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package.prompt_compiler_impl import (
    _compiler_guard_report,
    _dialogue_coverage_contract_rules,
    _reaction_cut_and_action_path_rules,
)


def test_reaction_action_rules_require_cut_and_natural_action_sentence():
    rules = _reaction_cut_and_action_path_rules()

    assert "镜头切至" in rules
    assert "自然动作句" in rules
    assert "主体 + 一个主要动作 + 情绪/视线落点" in rules
    assert "切镜时机" in rules
    assert "扶住" in rules
    assert "弹开" in rules


def test_dialogue_coverage_rules_preserve_speech_but_require_visual_coverage():
    rules = _dialogue_coverage_contract_rules()

    assert "完整发言单元必须保持语义连续" in rules
    assert "不能理解为单镜头吃完整段台词" in rules
    assert "说话者起句 -> 对手/听者反应" in rules
    assert "compiler 只忠实翻译上游" in rules


def test_guard_flags_reaction_without_explicit_cut_and_unsafe_release_word():
    prompt = """片段2｜电梯碰撞｜冲入+松手｜~13秒

【时间轴】
8-11秒：乔熙与商北琛双人中景，摄影机位于两人正前方0度、眼平高度、固定机位。商北琛说“You gonna keep holding on or what?”；乔熙听完后瞬间回神，手从西装前襟弹开。
"""

    report = _compiler_guard_report(prompt, '商北琛：You gonna keep holding on or what?', "", "main_shots:\n- shot_id: F02-S01")

    assert "动作路径存在失控词" in report
    assert "受击/反应落点缺少明确切镜" in report


def test_guard_accepts_reaction_cut_with_natural_release_action():
    prompt = """片段2｜电梯碰撞｜冲入+松手｜~13秒

【时间轴】
8-11秒：商北琛半身中景，摄影机位于商北琛正前方0度、眼平高度、固定机位，商北琛看向乔熙说“You gonna keep holding on or what?”。镜头切至乔熙胸部以上中近景，摄影机位于乔熙正前方0度、眼平高度，画面前景右侧保留商北琛西装领口虚化，乔熙听完后回神。乔熙松开商北琛的西装前襟，双手收回身侧，眼神短暂停住。
"""

    report = _compiler_guard_report(prompt, '商北琛：You gonna keep holding on or what?', "", "main_shots:\n- shot_id: F02-S01")

    assert "动作路径存在失控词" not in report
    assert "动作描述过细" not in report
    assert "受击/反应落点缺少明确切镜" not in report


def test_guard_requires_cut_timing_in_shot_sequence():
    prompt = """片段1｜清晨客厅｜赶时间+安抚｜约8秒｜9:16竖屏

【画面基底】
清晨客厅，沙发和书包保持同一空间关系，乔熙穿通勤装，小豆丁穿居家衣服。

【镜头序列】
镜头1【3秒】【乔熙、小豆丁】双人中景，同侧固定机位。乔熙夹着手机拿起外套，小豆丁在沙发上抗拒穿衣。
镜头2【3秒】【乔熙】中近景，同侧过肩机位。乔熙听完停住，蹲到孩子面前，语速放慢。
镜头3【2秒】【乔熙】近景，同侧固定机位。乔熙拿起书包时照片掉出，她低头看清照片。尾帧：照片仍在她手里。

【约束】
保持人物身份、服装、客厅空间、书包和照片连续；不要字幕、logo、水印、额外人物、可读文字。
"""

    report = _compiler_guard_report(prompt, "乔熙拿起书包，照片掉出。", "", "main_shots:\n- shot_id: F01-S01")

    assert "镜头序列缺少切镜时机" in report


def test_guard_accepts_new_seedance_shot_sequence_format():
    prompt = """片段1｜清晨客厅｜赶时间+安抚｜约8秒｜9:16竖屏

【画面基底】
清晨客厅，沙发和书包保持同一空间关系，乔熙穿通勤装，小豆丁穿居家衣服。

【镜头序列】
镜头1【3秒】【乔熙、小豆丁】双人中景，同侧固定机位。乔熙夹着手机拿起外套，小豆丁在沙发上抗拒穿衣。（切镜时机：小豆丁喊出“不想上学”后切至镜头2）
镜头2【3秒】【乔熙】中近景，同侧过肩机位。乔熙听完停住，蹲到孩子面前，语速放慢。（切镜时机：乔熙安抚动作停住后切至镜头3）
镜头3【2秒】【乔熙】近景，同侧固定机位。乔熙拿起书包时照片掉出，她低头看清照片。尾帧：照片仍在她手里。

【约束】
保持人物身份、服装、客厅空间、书包和照片连续；不要字幕、logo、水印、额外人物、可读文字。
"""

    report = _compiler_guard_report(prompt, "小豆丁喊出“不想上学”。乔熙拿起书包，照片掉出。", "", "main_shots:\n- shot_id: F01-S01")

    assert "镜头序列缺少切镜时机" not in report
    assert "末尾镜头缺少尾帧状态" not in report
    assert "动作描述过细" not in report


def test_guard_flags_too_many_cuts_in_short_segment():
    prompt = """片段2｜电梯碰撞｜冲入+松手｜~13秒

【时间轴】
0-3秒：镜头切至乔熙中景，摄影机位于乔熙正前方0度、眼平高度，乔熙从门外向电梯门缝冲入并停在近门侧。
3-5秒：镜头切至双人中景，乔熙撞到商北琛胸前。
5-7秒：镜头切至手部中近景，商北琛扶住乔熙腰侧。
7-9秒：镜头切回商北琛中近景，商北琛说“You gonna keep holding on or what?”
9-11秒：反打至乔熙中近景，乔熙听完后回神。
11-13秒：镜头切至双人中景，乔熙双手从西装前襟松开，双手向自己胸前收回约一掌距离，再落回身侧。
"""

    report = _compiler_guard_report(prompt, '商北琛：You gonna keep holding on or what?', "", "main_shots:\n- shot_id: F02-S01")

    assert "PROMPT-CUT-BUDGET-001" in report
    assert "切镜超预算" in report


def test_guard_flags_short_window_with_multiple_cuts_and_long_dialogue():
    prompt = """片段2｜电梯碰撞｜冲入+松手｜~13秒

【时间轴】
6-8秒：镜头切至商北琛手部与乔熙腰侧中近景，商北琛扶住乔熙腰侧。切回商北琛胸部以上中近景，摄影机位于商北琛正前方0度、眼平高度，商北琛说“Long time no see—since when did you start throwing yourself at people?”
"""

    report = _compiler_guard_report(prompt, '商北琛：Long time no see—since when did you start throwing yourself at people?', "", "main_shots:\n- shot_id: F02-S01")

    assert "单个短时间段同时包含多次切镜和长台词" in report


def test_guard_flags_long_dialogue_consumed_by_one_static_shot():
    prompt = """片段1｜集团大堂电梯口｜命令落点｜~12秒

【时间轴】
0-6秒：商北琛半身中景，正面固定视角。商北琛看向严飞说“Meeting in ten minutes. Directors and above, be there.”，严飞站在旁边听完后后退，最后停在电梯门旁。
6-12秒：镜头切至商北琛背后中景，背后固定视角。商北琛走进封闭金属电梯轿厢，严飞停在门外，最后电梯门将合未合。

【约束】
电梯门后不得出现办公区、会议区、走廊、窗户或另一片大堂。"""

    report = _compiler_guard_report(prompt, '商北琛：Meeting in ten minutes. Directors and above, be there.', "", "main_shots:\n- shot_id: F01-S01")

    assert "时间轴第 1 个时间段让长台词/高压对白停留在单一画面" in report


def test_guard_accepts_long_dialogue_with_listener_reaction_cut():
    prompt = """片段1｜集团大堂电梯口｜命令落点｜~12秒

【时间轴】
0-6秒：商北琛半身中景，正面固定视角。商北琛看向严飞说“Meeting in ten minutes.”。镜头切至严飞中近景，同侧固定视角，严飞听见后下颌收紧，商北琛画外音继续说“Directors and above, be there.”，最后严飞停在电梯门旁。
6-12秒：镜头切至商北琛背后中景，背后固定视角。商北琛走进封闭金属电梯轿厢，严飞停在门外，最后电梯门将合未合。

【约束】
电梯门后不得出现办公区、会议区、走廊、窗户或另一片大堂。"""

    report = _compiler_guard_report(prompt, '商北琛：Meeting in ten minutes. Directors and above, be there.', "", "main_shots:\n- shot_id: F01-S01")

    assert "长台词/高压对白被单镜头吃完" not in report
    assert "时间轴第 1 个时间段让长台词/高压对白停留在单一画面" not in report
