"""编造检测与就近否定检测的单元测试。

对应改造：
  - agents/director_graph.py 新增 _has_negation_near()
  - _prompt_guard_report 里的编造检测改用窗口否定，不再整句丢弃

运行：
  cd AI_Director_Studio
  python -m pytest tests/test_guard_fabrication.py -v
"""

from __future__ import annotations

import os
import sys
import types

import pytest

# 保证以仓库根目录为工作路径时能 import agents.*
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub_module(name: str, **attrs) -> types.ModuleType:
    """在 sys.modules 里放一个最小模块占位，用于隔离测试时跳过重依赖。"""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# director_graph 顶部导入了 langgraph 等运行时依赖，单元测试用不到它们。
# 在 import 前打桩，避免测试环境必须装全套依赖。
if False and "langgraph" not in sys.modules:
    _stub_module("langgraph")
    _stub_module("langgraph.checkpoint")
    _stub_module("langgraph.checkpoint.sqlite", SqliteSaver=object)
    _stub_module(
        "langgraph.graph",
        END="__end__",
        START="__start__",
        StateGraph=object,
    )
    _stub_module("langgraph.types", Command=object, interrupt=lambda *_a, **_kw: None)

# knowledge_base 拉了 openai 和 numpy；测试不需要这条链路，整体打桩为空模块。
if False and "numpy" not in sys.modules:
    _stub_module("numpy")
if False and "openai" not in sys.modules:
    _stub_module("openai", OpenAI=object)


from agents.director_graph import _has_negation_near, _prompt_guard_report  # noqa: E402


# ---------------------------------------------------------------------------
# _has_negation_near —— 窗口内否定检测
# ---------------------------------------------------------------------------

class TestHasNegationNear:
    """直接验证"本句窗口 + 否定词"的语义。"""

    def _pos(self, text: str, phrase: str) -> tuple[int, int]:
        idx = text.index(phrase)
        return idx, idx + len(phrase)

    def test_left_side_negation_in_same_sentence(self):
        """命中点左侧本句内有"禁止"，应判定为被否定。"""
        text = "禁止员工低语"
        start, end = self._pos(text, "员工低语")
        assert _has_negation_near(text, start, end) is True

    def test_negation_across_sentence_boundary_should_not_block(self):
        """前一句的否定不该影响后一句的命中——这是老逻辑的主要漏检点。"""
        text = "禁止字幕。员工开始低语议论。"
        start, end = self._pos(text, "员工开始低语")
        # "员工开始低语"这句本身没有否定词，应返回 False（不被否定）
        assert _has_negation_near(text, start, end) is False

    def test_no_negation_returns_false(self):
        """完全没有否定词的情况。"""
        text = "背景里员工低语议论此事"
        start, end = self._pos(text, "员工低语")
        assert _has_negation_near(text, start, end) is False

    def test_right_side_negation(self):
        """否定词在命中点右侧同句内（比如"员工低语不许出现"）。"""
        text = "员工低语不许在镜头里出现"
        start, end = self._pos(text, "员工低语")
        # "不许"在右侧窗口内，且与命中点同句
        assert _has_negation_near(text, start, end) is True

    def test_far_negation_beyond_window(self):
        """超出窗口距离的否定不该影响判定。"""
        filler = "，" + "某" * 80 + "，"  # >30 字填充
        text = f"禁止任何情况{filler}员工开始低语"
        start, end = self._pos(text, "员工开始低语")
        # "禁止"距离命中点超过 30 字窗口，不生效
        assert _has_negation_near(text, start, end) is False

    def test_window_size_respected(self):
        """window 参数按预期控制距离。"""
        text = "不得出现" + "某" * 10 + "员工低语"
        start, end = self._pos(text, "员工低语")
        # "不得"距离命中点 14 字左右，window=30 能覆盖
        assert _has_negation_near(text, start, end, window=30) is True
        # window=5 时应该够不到
        assert _has_negation_near(text, start, end, window=5) is False

    def test_semicolon_acts_as_sentence_boundary(self):
        """中文分号；和英文分号;都应该作为句界。"""
        text = "禁止所有议论；员工开始低语"
        start, end = self._pos(text, "员工开始低语")
        assert _has_negation_near(text, start, end) is False

    def test_newline_acts_as_sentence_boundary(self):
        """换行也是句界。"""
        text = "禁止这些行为\n员工低语出现在背景"
        start, end = self._pos(text, "员工低语")
        assert _has_negation_near(text, start, end) is False


# ---------------------------------------------------------------------------
# _prompt_guard_report —— 编造检测端到端
# ---------------------------------------------------------------------------

class TestPromptGuardFabrication:
    """通过 _prompt_guard_report 的编造检测分支间接验证完整链路。

    测试场景都是 Bug 4/修复后的回归用例，
    script 留空或不含目标短语，以隔离编造检测逻辑。
    """

    SCRIPT_EMPTY = ""

    def test_constraint_section_with_negation_not_flagged(self):
        """Bug 4 回归：prompt 含"禁止员工低语"属于约束段，不应误判为编造。"""
        prompt = (
            "0-3 秒：大堂空镜，灯光渐亮。\n"
            "3-6 秒：乔熙快步进入。\n"
            "【约束】禁止新增员工低语，禁止字幕。"
        )
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "员工低语" not in report
        assert "编造" not in report

    def test_real_fabrication_in_timeline_flagged(self):
        """时间轴正文里真的出现"员工低语"且无否定，应报编造。"""
        prompt = (
            "0-3 秒：大堂空镜。\n"
            "3-6 秒：员工低语议论此事，乔熙听见。\n"
            "【约束】禁止字幕。"
        )
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "疑似编造" in report
        assert "员工低语" in report

    def test_inline_negation_suppresses_flag(self):
        """正文内就近否定（"不得出现员工低语"）应被屏蔽，不报错。"""
        prompt = (
            "0-3 秒：大堂空镜，不得出现员工低语或类似议论。\n"
            "3-6 秒：乔熙快步进入。"
        )
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "编造" not in report

    def test_cross_sentence_negation_does_not_mask_fabrication(self):
        """关键改进点：前一句的"禁止"不该屏蔽后一句的真编造。

        老的 _without_negative_clauses 会把含"禁止字幕"的整句丢掉，
        但这里"禁止字幕"和"员工低语"本就不在一句，新逻辑能正确报编造。
        """
        prompt = (
            "0-3 秒：大堂空镜，禁止字幕出现。\n"
            "3-6 秒：几名员工低语议论。"
        )
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "疑似编造" in report
        assert "员工低语" in report

    def test_script_allowlist_overrides_fabrication(self):
        """若原剧本本来就要求员工低语，即使 prompt 里出现也不算编造。"""
        prompt = "3-6 秒：员工低语议论。"
        script = "（背景：大堂内员工低语议论纷纷）"
        report = _prompt_guard_report(prompt, script)
        assert "编造" not in report

    def test_clean_prompt_no_issues(self):
        """干净 prompt 应返回空报告（或至少不含编造字样）。"""
        prompt = (
            "0-3 秒：大堂空镜，灯光渐亮。\n"
            "3-6 秒：乔熙快步进入。\n"
            "【约束】禁止字幕。"
        )
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "编造" not in report

    def test_bystander_whisper_flagged(self):
        """另一类编造："路人低声议论"。"""
        prompt = "3-6 秒：路人低声议论此事。"
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "疑似编造" in report

    def test_group_unified_response_flagged(self):
        """再一类编造："众人异口同声回应"。"""
        prompt = "3-6 秒：众人异口同声回应"
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "疑似编造" in report

    def test_group_unified_response_with_inline_negation(self):
        """就近否定屏蔽群体回应编造。"""
        prompt = "3-6 秒：避免众人异口同声回应。"
        report = _prompt_guard_report(prompt, self.SCRIPT_EMPTY)
        assert "编造" not in report


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
