"""Tier 1 防漂移加固三件套的单元测试。

对应改造：
  - agents/director_graph.py
    * _inject_per_shot_scene_anchor()  —— 每段重复空间锚点
    * _reinforce_critical_constraints() —— 关键禁忌前置 + 每段追加
    * _compiler_guard_report() 新增"参考图用途未标注"硬规则

运行：
  cd AI_Director_Studio
  python -m pytest tests/test_antidrift_guards.py -v
"""

from __future__ import annotations

import os
import sys
import types

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# 与 test_guard_fabrication.py 相同的打桩，避免测试环境必须装 langgraph / openai。
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
if False and "numpy" not in sys.modules:
    _stub_module("numpy")
if False and "openai" not in sys.modules:
    _stub_module("openai", OpenAI=object)


from agents.director_graph import (  # noqa: E402
    _cleanup_timeline_constraints,
    _compiler_guard_report,
    _normalise_compiled_prompt,
)

pytestmark = pytest.mark.skip(reason="旧版强制注入禁忌到时间轴的策略已废弃，保留样例仅作历史参考。")


# ---------------------------------------------------------------------------
# 片段 3 的真实 prompt（去掉参考图标注版本，用于触发修复 3）
# ---------------------------------------------------------------------------

PROMPT_ELEVATOR_SEG3 = """片段3｜天御集团大堂｜电梯内对峙+调侃压制+受击抬头+触电松手｜~11秒
【风格锚点】
都市现实感电梯对手戏，冷静压迫里带一点突来的尴尬停顿。
【画幅锚点】
9:16竖屏。
【空间与首帧总控】
@图片5（上一段尾帧图）作为本段首帧、场景、构图、光线和空间锚点。电梯内均匀柔光，两人仍居中近距离面对面。
【时间轴】
0-3.5秒：商北琛过肩半身景，平视略低，从乔熙肩后斜拍。
3.5-6秒：乔熙半身中景，平视正面微仰，她寻声抬眼。
6-8.5秒：商北琛过肩半身景，平视，从乔熙肩后更贴近一点斜拍。
8.5-11秒：乔熙半身中景，平视正面，稳机停留。
【约束】
空间轴线保持电梯内面对面关系，不跳轴。电梯保持关闭状态，不重新打开，不出现门缝回弹。禁止把意外失衡写成怀里、拥抱、贴身亲密或亲密对视。禁止字幕、屏幕文字、英文字幕和文字浮层。
"""


# ---------------------------------------------------------------------------
# 修复 1：_inject_per_shot_scene_anchor
# ---------------------------------------------------------------------------

class TestSceneAnchorInjection:

    def test_extract_scene_anchor_from_total_control(self):
        """从【空间与首帧总控】块提取"电梯内"锚点短语。"""
        assert _extract_scene_anchor(PROMPT_ELEVATOR_SEG3) == "电梯内"

    def test_extract_scene_anchor_supports_lobby(self):
        """换成大堂场景也应能识别。"""
        prompt = "【空间与首帧总控】\n大堂内晨光。\n【时间轴】\n0-3秒：商北琛走入。\n"
        assert _extract_scene_anchor(prompt) == "大堂内"

    def test_extract_returns_empty_when_no_anchor(self):
        """没有可识别的场景关键词时返回空。"""
        prompt = "【空间与首帧总控】\n均匀柔光。\n【时间轴】\n0-3秒：特写。\n"
        assert _extract_scene_anchor(prompt) == ""

    def test_injects_anchor_into_each_timeline_segment(self):
        """时间轴里没带场景词的段，应该被注入"电梯内，"。"""
        result = _inject_per_shot_scene_anchor(PROMPT_ELEVATOR_SEG3)
        # 每个时间段描述的段首都应出现电梯内
        assert "0-3.5秒：电梯内，商北琛过肩半身景" in result
        assert "3.5-6秒：电梯内，乔熙半身中景" in result
        assert "6-8.5秒：电梯内，商北琛过肩半身景" in result
        assert "8.5-11秒：电梯内，乔熙半身中景" in result

    def test_injection_is_idempotent(self):
        """跑两次不应重复注入"电梯内电梯内"。"""
        once = _inject_per_shot_scene_anchor(PROMPT_ELEVATOR_SEG3)
        twice = _inject_per_shot_scene_anchor(once)
        assert twice == once
        assert "电梯内电梯内" not in twice
        assert "电梯内，电梯内" not in twice

    def test_skip_when_segment_already_has_scene_keyword(self):
        """本来就含场景词的段不注入。"""
        prompt = (
            "【空间与首帧总控】\n电梯内柔光。\n"
            "【时间轴】\n"
            "0-3秒：电梯内商北琛侧身。\n"
            "3-6秒：乔熙抬头。\n"
        )
        result = _inject_per_shot_scene_anchor(prompt)
        # 第一段已有"电梯内"，不加
        assert result.count("电梯内商北琛") == 1
        # 第二段没有场景词，应该被注入
        assert "3-6秒：电梯内，乔熙抬头" in result

    def test_noop_when_no_anchor_found(self):
        """锚点提取失败时应返回原 prompt。"""
        prompt = "【时间轴】\n0-3秒：特写。\n"
        assert _inject_per_shot_scene_anchor(prompt) == prompt


# ---------------------------------------------------------------------------
# 修复 2：_reinforce_critical_constraints
# ---------------------------------------------------------------------------

class TestCriticalConstraintReinforcement:

    def test_extract_known_taboos(self):
        """能从【约束】段抽出本片段触发的关键禁忌。"""
        taboos = _extract_critical_taboos(PROMPT_ELEVATOR_SEG3)
        assert "无字幕无屏幕文字" in taboos
        assert "零亲密接触保持物理距离" in taboos
        assert "电梯门保持闭合" in taboos

    def test_extract_empty_when_no_constraint_block(self):
        """没有【约束】块返回空列表。"""
        prompt = "【时间轴】\n0-3秒：特写。\n"
        assert _extract_critical_taboos(prompt) == []

    def test_appends_core_taboo_block_under_style_anchor(self):
        """【风格锚点】后面应该多一行【核心禁忌】。"""
        result = _reinforce_critical_constraints(PROMPT_ELEVATOR_SEG3)
        assert "【核心禁忌】" in result
        # 【核心禁忌】必须出现在【画幅锚点】之前（即紧跟【风格锚点】）
        style_idx = result.index("【风格锚点】")
        taboo_idx = result.index("【核心禁忌】")
        canvas_idx = result.index("【画幅锚点】")
        assert style_idx < taboo_idx < canvas_idx

    def test_appends_taboo_tail_to_each_timeline_segment(self):
        """每个时间段末尾都应追加"——...无字幕..."。"""
        result = _reinforce_critical_constraints(PROMPT_ELEVATOR_SEG3)
        # 每个时间段行都应在末尾含"——" + 禁忌短句
        for prefix in ["0-3.5秒：", "3.5-6秒：", "6-8.5秒：", "8.5-11秒："]:
            # 找该行
            line = next(l for l in result.splitlines() if l.startswith(prefix))
            assert "——" in line, f"段 {prefix} 未追加禁忌：{line}"
            assert "无字幕" in line or "零亲密" in line or "电梯门" in line

    def test_reinforcement_is_idempotent(self):
        """重复调用不应重复追加。"""
        once = _reinforce_critical_constraints(PROMPT_ELEVATOR_SEG3)
        twice = _reinforce_critical_constraints(once)
        assert once == twice
        # 不能出现双重追加
        assert twice.count("【核心禁忌】") == 1

    def test_noop_when_no_taboos_triggered(self):
        """没有触发任何禁忌时保持原样。"""
        prompt = "【风格锚点】\n干净场景。\n【时间轴】\n0-3秒：特写。\n【约束】\n保持风格。\n"
        assert _reinforce_critical_constraints(prompt) == prompt


# ---------------------------------------------------------------------------
# 修复 3：参考图用途标注硬规则（通过 _compiler_guard_report 触发）
# ---------------------------------------------------------------------------

class TestRefImagePurposeGuard:

    def test_unannotated_ref_image_flagged(self):
        """裸写 @图片1 且同句内没有用途词，应被质检抓出。"""
        prompt = (
            "【时间轴】\n"
            "0-3秒：电梯内，商北琛过肩半身景，@图片1出现在画面中，语气冷。\n"
        )
        report = _compiler_guard_report(prompt, "", "", "")
        assert "参考图用途未标注" in report
        assert "@图片1" in report

    def test_annotated_ref_image_not_flagged(self):
        """带"仅用于...身份/一致性"用途词的引用通过质检。"""
        prompt = (
            "【时间轴】\n"
            "0-3秒：电梯内，@图片1仅用于商北琛的人物身份、五官、发型、服装一致性。\n"
        )
        report = _compiler_guard_report(prompt, "", "", "")
        assert "参考图用途未标注" not in report

    def test_scene_anchor_ref_image_not_flagged(self):
        """标注为"场景锚点/首帧"的引用也算合规。"""
        prompt = (
            "【空间与首帧总控】\n"
            "@图片5（上一段尾帧图）作为本段首帧、场景、空间锚点。\n"
            "【时间轴】\n"
            "0-3秒：电梯内，商北琛过肩半身景。\n"
        )
        report = _compiler_guard_report(prompt, "", "", "")
        assert "参考图用途未标注" not in report

    def test_mixed_annotated_and_unannotated(self):
        """同一 prompt 里既有合规引用也有裸引用，裸引用仍被抓出。"""
        prompt = (
            "【空间与首帧总控】\n@图片5作为本段首帧场景锚点。\n"
            "【时间轴】\n"
            "0-3秒：电梯内，@图片7在背景闪过，镜头推近。\n"
        )
        report = _compiler_guard_report(prompt, "", "", "")
        assert "参考图用途未标注" in report
        assert "@图片7" in report
        # @图片5 合规，不应被列出
        assert "@图片5" not in report.split("参考图用途未标注")[1].split("\n")[0]


# ---------------------------------------------------------------------------
# 组合：_normalise_compiled_prompt 一次性跑完两个加固函数
# ---------------------------------------------------------------------------

class TestNormaliseIntegration:

    def test_normalise_applies_both_anchor_and_taboo(self):
        """走 _normalise_compiled_prompt 应同时注入场景锚点 + 核心禁忌 + 段末禁忌。"""
        result = _normalise_compiled_prompt(PROMPT_ELEVATOR_SEG3, segment_index=3)
        # 修复 1：每段带电梯内
        assert "0-3.5秒：电梯内，商北琛过肩半身景" in result
        # 修复 2：核心禁忌块出现
        assert "【核心禁忌】" in result
        # 修复 2：每段末尾禁忌
        first_seg_line = next(l for l in result.splitlines() if l.startswith("0-3.5秒："))
        assert "——" in first_seg_line

    def test_normalise_is_idempotent(self):
        """两次归一化不应造成重复注入。"""
        once = _normalise_compiled_prompt(PROMPT_ELEVATOR_SEG3, segment_index=3)
        twice = _normalise_compiled_prompt(once, segment_index=3)
        assert once == twice


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
