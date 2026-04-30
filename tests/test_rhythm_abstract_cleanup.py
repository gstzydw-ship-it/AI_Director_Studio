from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph import _clean_rhythm_rewritten_script, _cleanup_rhythm_abstract_language  # noqa: E402


def test_cleanup_rhythm_abstract_language_rewrites_abstract_terms():
    original = (
        "【氛围与调度指导（atmosphere_strategy）】\n"
        "建议保留死寂气口，制造心理空间落差和仪式感，强化压迫感与张力。"
    )

    cleaned = _cleanup_rhythm_abstract_language(original, preserve_heading=True)

    assert cleaned.startswith("【氛围与调度指导（atmosphere_strategy）】")
    for banned in ["死寂气口", "心理空间落差", "仪式感", "压迫感", "张力"]:
        assert banned not in cleaned
    assert "短暂停顿" in cleaned
    assert "前后反应变化" in cleaned
    assert "信息揭示顺序" in cleaned
    assert "站位与视线压制" in cleaned
    assert "对峙强度" in cleaned


def test_cleanup_rhythm_abstract_language_rewrites_air_freeze_phrase():
    original = "空气像被按住了一样，所有人都没动。"

    cleaned = _cleanup_rhythm_abstract_language(original)

    assert "空气像被按住" not in cleaned
    assert "没有人接话" in cleaned


def test_clean_rhythm_rewritten_script_removes_markdown_wrappers():
    original = """# 【改写后剧本】

1-1 晨/内/乔熙公寓
▲乔熙拿起书包。

---

#"""

    cleaned = _clean_rhythm_rewritten_script(original)

    assert cleaned == "1-1 晨/内/乔熙公寓\n▲乔熙拿起书包。"
