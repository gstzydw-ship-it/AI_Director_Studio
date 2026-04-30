from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph import (  # noqa: E402
    _rhythm_insert_continuity_rules,
    _validate_rhythm_insert_continuity,
    _validate_rhythm_structure_lock,
)


def test_rhythm_structure_lock_accepts_insertion_only_rewrite():
    original = """1-1 晨/内/乔熙公寓
人物：乔熙、小豆丁
【音效：闹钟铃响】
▲一张照片从书包里滑落。
乔熙OS：Why is Nash's photo here?
——闪回开始——
1-2 日/外/银杏树下
——闪回结束——
"""

    rewritten = """1-1 晨/内/乔熙公寓
人物：乔熙、小豆丁
【音效：闹钟铃响】
▲乔熙手上的动作停了一下。
▲一张照片从书包里滑落。
乔熙OS：Why is Nash's photo here?
▲她没有立刻抬头。
——闪回开始——
1-2 日/外/银杏树下
▲风吹过树叶。
——闪回结束——
"""

    ok, missing = _validate_rhythm_structure_lock(original, rewritten)

    assert ok is True
    assert missing == []


def test_rhythm_structure_lock_rejects_scene_and_event_drift():
    original = """1-1 晨/内/乔熙公寓
人物：乔熙、小豆丁
▲一张照片从书包里滑落。
乔熙OS：Why is Nash's photo here?
1-2 日/外/银杏树下
"""

    drifted = """1-1 日/内/公寓走廊
人物：Sunny、女儿
▲门边告示栏上贴着男人照片。
女儿OS：Why is Nash's photo here?
1-2 日/外/海边
"""

    ok, missing = _validate_rhythm_structure_lock(original, drifted)

    assert ok is False
    assert "1-1 晨/内/乔熙公寓" in missing


def test_rhythm_structure_lock_rejects_modified_original_line_substrings():
    original = """1-1 晨/内/乔熙公寓
【字幕：Four Years Ago
▲一张照片从书包里滑落。
"""

    rewritten = """1-1 晨/内/乔熙公寓
【字幕：Four Years Ago】
▲一张照片从书包里滑落。
"""

    ok, missing = _validate_rhythm_structure_lock(original, rewritten)

    assert ok is False
    assert "【字幕：Four Years Ago" in missing


def test_rhythm_insert_continuity_rejects_prop_ownership_jump():
    original = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片塞回书包。
乔熙：Come on, baby, let's go. Gonna be late.
"""

    rewritten = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片塞回书包。
▲小豆丁已经站在门口，单肩背着书包等她。
乔熙：Come on, baby, let's go. Gonna be late.
"""

    issues = _validate_rhythm_insert_continuity(original, rewritten)

    assert issues
    assert "道具归属跳变" in issues[0]


def test_rhythm_insert_continuity_rules_warn_against_prop_jump():
    rules = _rhythm_insert_continuity_rules()

    assert "画面逻辑优先" in rules
    assert "道具归属" in rules
    assert "同一件道具不能在相邻动作中同时被两个人持有" in rules
    assert "低歧义画面优先" in rules
    assert "攥进掌心" in rules
    assert "放到桌上" in rules


def test_rhythm_rewrite_knowledge_core_rules_include_visual_logic_and_low_ambiguity():
    knowledge_path = (
        Path(__file__).resolve().parents[1]
        / "knowledge"
        / "09_节奏总控与剧本改写规则.md"
    )
    rules = knowledge_path.read_text(encoding="utf-8")

    assert "规则 30：画面逻辑优先于情绪细节" in rules
    assert "同一件道具不能在相邻动作中同时被两个人持有" in rules
    assert "把照片放到桌上" in rules
    assert "规则 31：低歧义画面优先于微观手部状态" in rules
    assert "攥进掌心" in rules
