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

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        assert kwargs["agent_name"] == "director_showrunner"
        assert "剧情冲突增强导演" in system_prompt
        assert "必须输出的 YAML 字段" in user_prompt
        assert "增强版剧本" in user_prompt
        assert "不得新增台词" in user_prompt
        assert "禁止输出状态合同" in system_prompt
        assert "手机/电话尤其要谨慎" in system_prompt
        assert "每两句原台词之间最多补 1-2 个动作节拍" in user_prompt
        assert "通话结束后必须写清手机去向" in system_prompt
        assert "不要写“状态合同/入场状态/出场状态/道具状态变化/禁止连续性/特写/音效”" in user_prompt
        assert "【场景预分析约束】" in user_prompt
        assert "门在左侧，乔熙站在床边" in user_prompt
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
            "scene_context_brief": "人物占位: 乔熙和小豆丁\n站位姿势: 门在左侧，乔熙站在床边",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    assert result["script"].startswith("A rushes into the room.")
    assert result["enhanced_script"] == result["script"]
    assert result["original_script"] == "A enters the room."
    assert "增强版剧本" in result["agent_outputs"]["director_showrunner"]
    assert "增强版剧本" not in result["director_brief"]
    assert "增强依据" in result["director_brief"]
    assert "节奏总控交接" in result["director_brief"]


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


def test_scene_preanalysis_does_not_pause_before_story_enhancement(monkeypatch):
    saved: dict[str, object] = {}
    monkeypatch.setattr(runners, "_save_runner_state", lambda state: saved.update(state))

    state = runners._mark_human_review_state(
        {
            "agent_outputs": {"scene_analyst": "人物占位:\n  - 乔熙站在床边"},
            "step": "step_0_scene",
        },
        ("director_showrunner",),
    )

    assert state["step"] == "step_0_scene"
    assert "review_agent" not in state
    assert saved == {}


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
