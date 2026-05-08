from __future__ import annotations

from pathlib import Path
import sys


ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
from agents.director_graph_package import planning_context_impl as pci
from agents.director_graph_package import shot_director_impl as sdi


def test_director_showrunner_node_writes_brief(monkeypatch):
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
        assert "必须输出的 YAML 字段" in user_prompt
        assert "英文字段名" in user_prompt
        return (
            "film_tone: 克制\n"
            "shot_priority:\n"
            "  - 剧本忠实\n"
            "handoff_notes:\n"
            "  scene_analyst: 保留事实\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci.director_showrunner_node(
        {
            "script": "A enters the room.",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    assert result["director_brief"].startswith("影片气质: 克制")
    assert "镜头优先级:" in result["director_brief"]
    assert "下游交接:" in result["director_brief"]
    assert "场景分析师:" in result["director_brief"]
    assert result["agent_outputs"]["director_showrunner"] == result["director_brief"]


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
