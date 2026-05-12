from __future__ import annotations

from pathlib import Path
import sys


ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
from agents.director_graph_package import planning_context_impl as pci
from agents.director_graph_package import runners
from agents.director_graph_package import shot_director_impl as sdi


def test_director_showrunner_node_enhances_script_and_writes_contract(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    captured: dict[str, str] = {}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        if kwargs["agent_name"] == "director_showrunner_logic_reviewer":
            captured["review_system"] = system_prompt
            captured["review_user"] = user_prompt
            return (
                "审查结论: PASS\n"
                "增强版剧本: |\n"
                "  A rushes into the room.\n"
                "  A: Hello.\n"
                "多维审查:\n"
                "  - 角色: 物理逻辑审查员\n"
                "    通过: true\n"
                "    发现: 未发现硬逻辑错误\n"
                "    处理: 保留\n"
                "  - 角色: 冲突强度与画面冲击审查员\n"
                "    通过: true\n"
                "    发现: 动作有速度和压力\n"
                "    处理: 保留\n"
                "硬错误: 无\n"
                "评分:\n"
                "  施事逻辑: 5\n"
                "  道具连续性: 5\n"
                "  人物动机: 5\n"
                "  空间调度: 5\n"
                "  主线保护: 5\n"
                "  可拍性: 5\n"
                "  冲突强度: 5\n"
                "  画面冲击: 5\n"
                "逻辑审查:\n"
                "  - 未发现硬逻辑错误\n"
                "最终处理:\n"
                "  是否返修: false\n"
                "  返修轮次: 1\n"
                "  采纳意见: []\n"
                "  剩余风险: 无\n"
                "增强依据:\n"
                "  - 原文锚点: A enters the room.\n"
                "    增强方式: 将进入改成急匆匆进入\n"
                "    权限级别: L1_动作层增强\n"
                "    是否改动主线: 否\n"
                "主线保护:\n"
                "  - 人物和台词不变\n"
                "节奏总控交接:\n"
                "  - 入口动作需要起速\n"
                "需用户确认: 无\n"
            )
        assert kwargs["agent_name"] == "director_showrunner"
        captured["primary_system"] = system_prompt
        captured["primary_user"] = user_prompt
        return (
            "增强版剧本: |\n"
            "  A rushes into the room.\n"
            "  A: Hello.\n"
            "增强依据:\n"
            "  - 原文锚点: A enters the room.\n"
            "    增强方式: 将进入改成急匆匆进入\n"
            "    权限级别: L1_动作层增强\n"
            "    是否改动主线: 否\n"
            "主线保护:\n"
            "  - 人物和台词不变\n"
            "节奏总控交接:\n"
            "  - 入口动作需要起速\n"
            "需用户确认: 无\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "A enters the room.",
            "original_script": "A enters the room.",
            "scene_context_brief": "增强约束: 门在左侧，乔熙站在床边",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    assert result["script"].startswith("A rushes into the room.")
    assert result["enhanced_script"] == result["script"]
    assert result["original_script"] == "A enters the room."
    assert "剧情冲突增强导演" in captured["primary_system"]
    assert "必须输出的 YAML 字段" in captured["primary_user"]
    assert "增强版剧本" in captured["primary_user"]
    assert "不得新增台词" in captured["primary_user"]
    assert "禁止输出状态合同" in captured["primary_system"]
    assert "手机/电话尤其要谨慎" in captured["primary_system"]
    assert "每两句原台词之间最多补 1-2 个动作节拍" in captured["primary_user"]
    assert "通话结束后必须写清手机去向" in captured["primary_system"]
    assert "不要写“状态合同/入场状态/出场状态/道具状态变化/禁止连续性/特写/音效”" in captured["primary_user"]
    assert "【场景预分析约束】" in captured["primary_user"]
    assert "门在左侧，乔熙站在床边" in captured["primary_user"]
    assert "严格审查清单" in captured["review_user"]
    assert "施事逻辑" in captured["review_user"]
    assert "多维审查" in captured["review_user"]
    assert "冲突强度与画面冲击审查员" in captured["review_system"]
    assert "冲突强度 / 画面冲击" in captured["review_user"]
    assert "急匆匆一路小跑出来" in captured["review_user"]
    assert "增强版剧本" in result["agent_outputs"]["director_showrunner"]
    assert "增强版剧本" not in result["director_brief"]
    assert "增强依据" in result["director_brief"]
    assert "节奏总控交接" in result["director_brief"]


def test_director_showrunner_logic_review_can_replace_primary_output(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    calls: list[str] = []

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        agent_name = kwargs["agent_name"]
        calls.append(agent_name)
        if agent_name == "director_showrunner":
            assert "输出前必须进行逻辑审查" in system_prompt
            assert "施事是否真实可动" in user_prompt
            return (
                "增强版剧本: |\n"
                "  乔熙压住小豆丁乱动的衣角。\n"
                "增强依据:\n"
                "  - 原文锚点: 小豆丁扭来扭去。\n"
                "    增强方式: 用衣角乱动强化动作。\n"
                "    权限级别: L1 动作层增强\n"
                "    是否改动主线: 否\n"
                "主线保护:\n"
                "  - 母女关系不变\n"
                "节奏总控交接:\n"
                "  - 晨间节奏快\n"
                "需用户确认: 无\n"
            )
        assert agent_name == "director_showrunner_logic_reviewer"
        assert "衣角、文件、咖啡杯、照片等无生命物不能像有意志一样" in user_prompt
        return (
            "审查结论: PASS\n"
            "增强版剧本: |\n"
            "  小豆丁坐在沙发边扭动，衣摆被她攥皱。乔熙按住她的手，继续给她扣衣服。\n"
            "多维审查:\n"
            "  - 角色: 物理逻辑审查员\n"
            "    通过: true\n"
            "    发现: 衣角施事错误已修复\n"
            "    处理: 采纳修复\n"
            "  - 角色: 冲突强度与画面冲击审查员\n"
            "    通过: true\n"
            "    发现: 晨间冲突保持可见压力\n"
            "    处理: 通过\n"
            "硬错误:\n"
            "  - 类型: 施事错误\n"
            "    原句: 乔熙压住小豆丁乱动的衣角。\n"
            "    问题: 衣角不能主动乱动。\n"
            "    严重级别: P0\n"
            "    必须修复: true\n"
            "    修复结果: 改为小豆丁身体和手在动。\n"
            "评分:\n"
            "  施事逻辑: 5\n"
            "  道具连续性: 5\n"
            "  人物动机: 5\n"
            "  空间调度: 5\n"
            "  主线保护: 5\n"
            "  可拍性: 5\n"
            "  冲突强度: 5\n"
            "  画面冲击: 5\n"
            "逻辑审查:\n"
            "  - 问题: 衣角不能主动乱动。\n"
            "    判断: 施事错误。\n"
            "    修正方式: 改为小豆丁身体和手在动。\n"
            "最终处理:\n"
            "  是否返修: true\n"
            "  返修轮次: 1\n"
            "  采纳意见:\n"
            "    - 把衣角乱动改为孩子身体和手在动\n"
            "  剩余风险: 无\n"
            "增强依据:\n"
            "  - 原文锚点: 小豆丁扭来扭去。\n"
            "    增强方式: 改成孩子扭动和攥皱衣摆的可执行动作。\n"
            "    权限级别: L1 动作层增强\n"
            "    是否改动主线: 否\n"
            "主线保护:\n"
            "  - 母女关系不变\n"
            "节奏总控交接:\n"
            "  - 晨间节奏快\n"
            "需用户确认: 无\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "小豆丁扭来扭去。",
            "original_script": "小豆丁扭来扭去。",
            "scene_context_brief": "",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    assert calls == ["director_showrunner", "director_showrunner_logic_reviewer"]
    assert "衣摆被她攥皱" in result["enhanced_script"]
    assert "衣角不能主动乱动" in result["director_brief"]
    assert result["knowledge_metadata"]["director_showrunner"]["runtime"]["logic_review"]["status"] == "reviewed"


def test_director_showrunner_blocks_primary_when_logic_reviewer_fails(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(_system_prompt, _user_prompt, **kwargs):
        agent_name = kwargs["agent_name"]
        if agent_name == "director_showrunner":
            return (
                "审查结论: PASS\n"
                "增强版剧本: |\n"
                "  未审查增强稿。\n"
                "增强依据: []\n"
                "主线保护: []\n"
                "节奏总控交接: []\n"
                "需用户确认: 无\n"
            )
        assert agent_name == "director_showrunner_logic_reviewer"
        raise RuntimeError("HTTP 504 from reviewer")

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "原始剧本。",
            "original_script": "原始剧本。",
            "scene_context_brief": "",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    output = result["agent_outputs"]["director_showrunner"]
    runtime = result["knowledge_metadata"]["director_showrunner"]["runtime"]
    assert result["enhanced_script"] == "原始剧本。"
    assert "未审查增强稿" not in result["enhanced_script"]
    assert "审查结论: BLOCKED" in output
    assert "冲突强度与画面冲击审查员" in output
    assert runtime["status"] == "blocked_original_script_kept"
    assert runtime["logic_review"]["status"] == "blocked"
    assert runtime["logic_review"]["verdict"] == "BLOCKED"


def test_director_showrunner_retries_with_compact_prompt_after_504(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    calls: list[tuple[str, str]] = []

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        agent_name = kwargs["agent_name"]
        calls.append((agent_name, user_prompt))
        if agent_name == "director_showrunner" and len(calls) == 1:
            raise RuntimeError(
                "LLM 接口返回 HTTP 504（agent=director_showrunner, model=claude-opus-4-6，已重试 3 次）"
            )
        if agent_name == "director_showrunner":
            assert kwargs["max_retries"] == 1
            assert "【输出格式】" in user_prompt
            return (
                "增强版剧本: |\n"
                "  A stops at the door, grips the folder, then enters.\n"
                "增强依据: []\n"
                "主线保护:\n"
                "  - 原台词和人物关系不变\n"
                "节奏总控交接:\n"
                "  - 门口动作需要短暂停顿\n"
                "需用户确认: 无\n"
            )
        assert agent_name == "director_showrunner_logic_reviewer"
        return (
            "审查结论: PASS\n"
            "增强版剧本: |\n"
            "  A stops at the door, grips the folder, then enters.\n"
            "多维审查:\n"
            "  - 角色: 冲突强度与画面冲击审查员\n"
            "    通过: true\n"
            "    发现: 门口停顿形成可见压力\n"
            "    处理: 通过\n"
            "硬错误: 无\n"
            "评分:\n"
            "  施事逻辑: 5\n"
            "  道具连续性: 5\n"
            "  人物动机: 5\n"
            "  空间调度: 5\n"
            "  主线保护: 5\n"
            "  可拍性: 5\n"
            "  冲突强度: 5\n"
            "  画面冲击: 5\n"
            "逻辑审查: []\n"
            "最终处理:\n"
            "  是否返修: false\n"
            "  返修轮次: 1\n"
            "  采纳意见: []\n"
            "  剩余风险: 无\n"
            "增强依据: []\n"
            "主线保护: []\n"
            "节奏总控交接: []\n"
            "需用户确认: 无\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "A enters.",
            "original_script": "A enters.",
            "scene_context_brief": "增强约束: 门口保持通畅",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    assert [agent_name for agent_name, _prompt in calls] == [
        "director_showrunner",
        "director_showrunner",
        "director_showrunner_logic_reviewer",
    ]
    runtime = result["knowledge_metadata"]["director_showrunner"]["runtime"]
    assert runtime["status"] == "success"
    assert runtime["degraded_prompt_retry"]["status"] == "success"
    assert "grips the folder" in result["enhanced_script"]


def test_director_showrunner_sanitizes_visible_504_fallback(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(_system_prompt, _user_prompt, **kwargs):
        assert kwargs["agent_name"] == "director_showrunner"
        raise RuntimeError(
            "LLM 接口返回 HTTP 504（agent=director_showrunner, model=claude-opus-4-6，已重试 3 次）"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "A enters.",
            "original_script": "A enters.",
            "scene_context_brief": "",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    output = result["agent_outputs"]["director_showrunner"]
    assert "增强版剧本" in output
    assert "A enters." in output
    assert "LLM 服务临时不可用" in output
    assert "HTTP 504" not in output
    assert "claude-opus-4-6" not in output
    assert result["enhanced_script"] == "A enters."
    runtime = result["knowledge_metadata"]["director_showrunner"]["runtime"]
    assert runtime["status"] == "fallback"
    assert runtime["degraded_prompt_retry"]["status"] == "failed"


def test_sanitize_legacy_showrunner_504_fallback_output():
    old_output = (
        "主线保护:\n"
        "  - 使用当前剧本继续施工\n"
        "兜底原因: RuntimeError: LLM 接口返回 HTTP 504（agent=director_showrunner, "
        "model=claude-opus-4-6，已重试 3 次；timeout: total=180s；环境代理: 已绕开）\n"
    )

    sanitized = pci.sanitize_director_showrunner_fallback_output(old_output)

    assert "LLM 服务临时不可用" in sanitized
    assert "HTTP 504" not in sanitized
    assert "RuntimeError" not in sanitized
    assert "claude-opus-4-6" not in sanitized


def test_director_showrunner_system_prompt_is_capped():
    base = "核心规则\n" * 20
    rules = "===== 以下是必须优先执行的关键规则 =====\n" + ("知识规则很长\n" * 2000)

    capped = pci._cap_director_showrunner_system_prompt(base + rules, max_chars=1200)

    assert len(capped) <= 1200
    assert "核心规则" in capped
    assert "规则压缩提示" in capped


def test_director_showrunner_strict_review_runs_second_round_when_repair_required(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    review_rounds: list[str] = []

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        agent_name = kwargs["agent_name"]
        if agent_name == "director_showrunner":
            return (
                "增强版剧本: |\n"
                "  秘书和主管们停下手里的工作，在门口排开。\n"
                "增强依据: []\n"
                "主线保护: []\n"
                "节奏总控交接: []\n"
                "需用户确认: 无\n"
            )
        assert agent_name == "director_showrunner_logic_reviewer"
        review_rounds.append(user_prompt)
        if len(review_rounds) == 1:
            return (
                "审查结论: PASS\n"
                "增强版剧本: |\n"
                "  秘书和主管们从玻璃主入口附近聚拢到台阶前，整理衣服和文件。\n"
                "多维审查:\n"
                "  - 角色: 场景调度审查员\n"
                "    通过: false\n"
                "    发现: 群体来源已修，但需要二次门禁确认\n"
                "    处理: 返修后复审\n"
                "  - 角色: 冲突强度与画面冲击审查员\n"
                "    通过: false\n"
                "    发现: 聚拢动作仍偏静态，画面冲击不足\n"
                "    处理: 要求改成急促小跑聚拢\n"
                "硬错误:\n"
                "  - 类型: 人物动机\n"
                "    原句: 秘书和主管们停下手里的工作。\n"
                "    问题: 迎接老板的人不应像在门口办公。\n"
                "    严重级别: P1\n"
                "    必须修复: true\n"
                "    修复结果: 改为从入口附近聚拢。\n"
                "评分:\n"
                "  施事逻辑: 5\n"
                "  道具连续性: 5\n"
                "  人物动机: 3\n"
                "  空间调度: 4\n"
                "  主线保护: 5\n"
                "  可拍性: 4\n"
                "  冲突强度: 3\n"
                "  画面冲击: 3\n"
                "逻辑审查: []\n"
                "最终处理:\n"
                "  是否返修: true\n"
                "  返修轮次: 1\n"
                "  采纳意见: []\n"
                "  剩余风险: 需要复审\n"
                "增强依据: []\n"
                "主线保护: []\n"
                "节奏总控交接: []\n"
                "需用户确认: 无\n"
            )
        return (
            "审查结论: PASS\n"
            "增强版剧本: |\n"
            "  秘书和主管们从玻璃主入口附近聚拢到台阶前，整理衣服和文件，快速排成迎接队列。\n"
            "多维审查:\n"
            "  - 角色: 场景调度审查员\n"
            "    通过: true\n"
            "    发现: 群体调度合理\n"
            "    处理: 通过\n"
            "  - 角色: 冲突强度与画面冲击审查员\n"
            "    通过: true\n"
            "    发现: 快速排成迎接队列有动态压力\n"
            "    处理: 通过\n"
            "硬错误: 无\n"
            "评分:\n"
            "  施事逻辑: 5\n"
            "  道具连续性: 5\n"
            "  人物动机: 5\n"
            "  空间调度: 5\n"
            "  主线保护: 5\n"
            "  可拍性: 5\n"
            "  冲突强度: 5\n"
            "  画面冲击: 5\n"
            "逻辑审查: []\n"
            "最终处理:\n"
            "  是否返修: true\n"
            "  返修轮次: 2\n"
            "  采纳意见: []\n"
            "  剩余风险: 无\n"
            "增强依据: []\n"
            "主线保护: []\n"
            "节奏总控交接: []\n"
            "需用户确认: 无\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "秘书和主管们列队等候。",
            "original_script": "秘书和主管们列队等候。",
            "scene_context_brief": "",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    runtime = result["knowledge_metadata"]["director_showrunner"]["runtime"]["logic_review"]
    assert len(review_rounds) == 2
    assert runtime["verdict"] == "PASS"
    assert [item["verdict"] for item in runtime["rounds"]] == ["REPAIR_REQUIRED", "PASS"]
    assert runtime["rounds"][0]["reported_verdict"] == "PASS"
    assert runtime["rounds"][0]["gate_reason"] == "score_below_4:人物动机,冲突强度,画面冲击"
    assert "快速排成迎接队列" in result["enhanced_script"]


def test_director_showrunner_blocks_unapproved_enhancement_after_max_rounds(monkeypatch):
    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        agent_name = kwargs["agent_name"]
        if agent_name == "director_showrunner":
            return (
                "增强版剧本: |\n"
                "  乔熙压住小豆丁乱动的衣角。\n"
                "增强依据: []\n"
                "主线保护: []\n"
                "节奏总控交接: []\n"
                "需用户确认: 无\n"
            )
        return (
            "审查结论: PASS\n"
            "增强版剧本: |\n"
            "  乔熙压住小豆丁乱动的衣角。\n"
            "多维审查:\n"
            "  - 角色: 物理逻辑审查员\n"
            "    通过: false\n"
            "    发现: 施事错误仍未修复\n"
            "    处理: 需要阻断\n"
            "  - 角色: 冲突强度与画面冲击审查员\n"
            "    通过: true\n"
            "    发现: 本轮主要阻断点不是冲突强度\n"
            "    处理: 通过\n"
            "硬错误:\n"
            "  - 类型: 施事错误\n"
            "    原句: 乔熙压住小豆丁乱动的衣角。\n"
            "    问题: 衣角不能主动乱动。\n"
            "    严重级别: P0\n"
            "    必须修复: true\n"
            "    修复结果: 未修复\n"
            "评分:\n"
            "  施事逻辑: 2\n"
            "  道具连续性: 5\n"
            "  人物动机: 5\n"
            "  空间调度: 5\n"
            "  主线保护: 5\n"
            "  可拍性: 4\n"
            "  冲突强度: 4\n"
            "  画面冲击: 4\n"
            "逻辑审查: []\n"
            "最终处理:\n"
            "  是否返修: true\n"
            "  返修轮次: 1\n"
            "  采纳意见: []\n"
            "  剩余风险: 施事错误仍在\n"
            "增强依据: []\n"
            "主线保护: []\n"
            "节奏总控交接: []\n"
            "需用户确认: 施事错误两轮未修复\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "小豆丁扭来扭去，不肯配合。",
            "original_script": "小豆丁扭来扭去，不肯配合。",
            "scene_context_brief": "",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    runtime = result["knowledge_metadata"]["director_showrunner"]["runtime"]
    assert runtime["status"] == "blocked_original_script_kept"
    assert runtime["logic_review"]["verdict"] == "BLOCKED"
    assert result["enhanced_script"] == "小豆丁扭来扭去，不肯配合。"


def test_review_board_accepts_primary_output(monkeypatch):
    """Current shot_director_impl._run_shot_director_review_board is deterministic
    and always returns the primary output with no arbiter involvement."""
    captured: dict[str, object] = {}

    def fake_review_board(**kwargs):
        captured["kwargs"] = kwargs
        return (
            "- fragment_id: F01\n  main_shots: []\n",
            {"mode": "deterministic_guard", "status": "accepted_primary", "output_chars": 42},
            "accepted primary output",
        )

    monkeypatch.setattr(sdi, "_run_shot_director_review_board", fake_review_board)
    monkeypatch.setattr(sdi, "_persist_update", lambda state, update: {**state, **update})

    output, runtime, report = sdi._run_shot_director_review_board(
        script="A enters.",
        planner_output="- fragment_id: F01",
        director_brief="film_tone: restrained",
        primary_output="- fragment_id: F01\n  main_shots: []\n",
        images_base64=None,
    )

    assert output.startswith("- fragment_id: F01")
    assert runtime["status"] == "accepted_primary"
    assert "accepted" in report


def test_shot_director_node_runs_single_pass_and_stores_output(monkeypatch):
    """Current shot_director_impl.shot_director_node calls _run_shot_director_single_pass
    (not review_board) and stores the result. Guard-repair validation is bypassed via
    monkeypatch so this test is independent of the guard-contract implementation."""
    captured: dict[str, object] = {}

    def fake_single_pass(**kwargs):
        captured["planner_output"] = kwargs["planner_output"]
        captured["director_brief"] = kwargs["director_brief"]
        return (
            "- fragment_id: F01\n  main_shots:\n    - shot_id: F01-S01\n",
            {"elapsed_seconds": 0.1},
            {"final": {"retrieval_mode": "stub"}},
            {"final": "yaml"},
        )

    monkeypatch.setattr(sdi, "_run_shot_director_single_pass", fake_single_pass)
    monkeypatch.setattr(sdi, "_persist_update", lambda state, update: {**state, **update})
    monkeypatch.setattr(sdi, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(sdi, "_hard_shot_director_issues", lambda issues: [])

    result = sdi.shot_director_node(
        {
            "script": "A enters.",
            "director_brief": "film_tone: restrained",
            "aspect_ratio": "9:16",
            "agent_outputs": {"story_planner": "- fragment_id: F01\n"},
            "knowledge_metadata": {},
            "segment_names": ["F01"],
            "total_segments": 1,
        }
    )

    assert captured["planner_output"] == "- fragment_id: F01\n"
    assert captured["director_brief"] == "film_tone: restrained"
    assert "shot_director" in result["agent_outputs"]
    assert result["agent_outputs"]["shot_director"].startswith("- fragment_id: F01")


def test_human_review_pauses_after_story_enhancement(monkeypatch):
    saved: dict[str, object] = {}
    monkeypatch.setattr(runners, "_save_runner_state", lambda state: saved.update(state))

    state = runners._mark_human_review_state(
        {
            "agent_outputs": {"director_showrunner": "增强版剧本: |\n  A rushes in."},
            "step": "step_0_enhance",
        },
        ("rhythm_rewrite_director",),
    )

    assert state["status"] == "waiting_for_user_input"
    assert state["review_agent"] == "director_showrunner"
    assert state["review_title"] == "剧情增强"
    assert "A rushes in" in state["review_output"]
    assert saved["review_agent"] == "director_showrunner"


def test_scene_preanalysis_pauses_before_story_enhancement(monkeypatch):
    saved: dict[str, object] = {}
    monkeypatch.setattr(runners, "_save_runner_state", lambda state: saved.update(state))

    state = runners._mark_human_review_state(
        {
            "agent_outputs": {"scene_analyst": "人物占位:\n  - 乔熙站在床边"},
            "step": "step_0_scene",
        },
        ("director_showrunner",),
    )

    assert state["status"] == "waiting_for_user_input"
    assert state["step"] == "step_0_scene"
    assert state["review_agent"] == "scene_analyst"
    assert state["review_title"] == "场景预分析"
    assert "乔熙站在床边" in state["review_output"]
    assert saved["review_agent"] == "scene_analyst"


def test_scene_preanalysis_review_edit_updates_scene_context():
    edited = "人物占位:\n  - 乔熙站在门口\n场景母版图: |\n  - scene card"

    state = runners._apply_human_review_edit(
        {
            "script": "old",
            "scene_context_brief": "old context",
            "agent_outputs": {},
        },
        "scene_analyst",
        edited,
    )

    assert state["scene_context_brief"] == edited
    assert state["agent_outputs"]["scene_analyst"] == edited
    assert state["status"] == "running_phase_1"


def test_story_enhancement_review_edit_updates_script():
    edited = (
        "增强版剧本: |\n"
        "  乔熙急匆匆冲到公司门口。\n"
        "  苏小可：Sunny, big news—the company's been bought out. New boss is coming!\n"
        "增强依据:\n"
        "  - 原文锚点: 主管们列队等候\n"
        "    增强方式: 改成动态列队\n"
        "主线保护:\n"
        "  - 公司易主事实不变\n"
        "节奏总控交接:\n"
        "  - 公司门口段需要起速\n"
        "需用户确认: 无\n"
    )

    state = runners._apply_human_review_edit(
        {
            "original_script": "苏小可：Sunny, big news—the company's been bought out. New boss is coming!",
            "script": "old",
            "agent_outputs": {},
        },
        "director_showrunner",
        edited,
    )

    assert state["script"].startswith("乔熙急匆匆冲到公司门口。")
    assert state["enhanced_script"] == state["script"]
    assert "增强依据" in state["director_brief"]
    assert "增强版剧本" not in state["director_brief"]
    assert state["agent_outputs"]["director_showrunner"] == edited
