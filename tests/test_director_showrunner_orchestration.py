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
                "增强版剧本: |\n"
                "  A rushes into the room.\n"
                "  A: Hello.\n"
                "逻辑审查:\n"
                "  - 未发现硬逻辑错误\n"
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
    assert "辩论审查清单" in captured["review_user"]
    assert "施事逻辑" in captured["review_user"]
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
            "增强版剧本: |\n"
            "  小豆丁坐在沙发边扭动，衣摆被她攥皱。乔熙按住她的手，继续给她扣衣服。\n"
            "逻辑审查:\n"
            "  - 问题: 衣角不能主动乱动。\n"
            "    判断: 施事错误。\n"
            "    修正方式: 改为小豆丁身体和手在动。\n"
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
