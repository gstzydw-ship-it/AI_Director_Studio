from __future__ import annotations

from pathlib import Path
import sys


ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg


def test_director_showrunner_node_writes_brief(monkeypatch):
    monkeypatch.setattr(
        dg,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        dg,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(dg, "_persist_update", lambda state, update: {**state, **update})
    monkeypatch.setattr(
        dg,
        "_agent_runtime_trace",
        lambda *args, **kwargs: {"agent_name": args[0], "status": kwargs.get("status", "success")},
    )

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        assert kwargs["agent_name"] == "director_showrunner"
        assert "Required YAML Fields" in user_prompt
        return "film_tone: restrained\nshot_priority:\n  - script fidelity\n"

    monkeypatch.setattr(dg, "call_llm", fake_call_llm)

    result = dg.director_showrunner_node(
        {
            "script": "A enters the room.",
            "aspect_ratio": "9:16",
            "agent_outputs": {},
            "knowledge_metadata": {},
            "speed_mode": False,
        }
    )

    assert result["director_brief"].startswith("film_tone: restrained")
    assert result["agent_outputs"]["director_showrunner"] == result["director_brief"]


def test_shot_director_review_board_uses_arbiter_packet(monkeypatch):
    monkeypatch.setattr(dg, "_agent_configured", lambda agent_name: agent_name in {"shot_director_critic", "shot_director_arbiter"})
    monkeypatch.setattr(
        dg,
        "_agent_runtime_trace",
        lambda agent_name, **kwargs: {"agent_name": agent_name, "status": kwargs.get("status", "success")},
    )

    calls: list[tuple[str, str]] = []

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        agent_name = kwargs["agent_name"]
        calls.append((agent_name, user_prompt))
        if agent_name == "shot_director_critic":
            assert "Director Showrunner Brief" in user_prompt
            return "decision: revise\nscore: 72\nrevision_instruction: simplify camera move\n"
        if agent_name == "shot_director_arbiter":
            return (
                "decision: revise\n"
                "score: 88\n"
                "accepted_parts:\n"
                "  - clear geography\n"
                "rejected_parts:\n"
                "  - over-complex motion\n"
                "revision_instruction: keep geography, simplify motion\n"
                "final_output: |\n"
                "  - fragment_id: F01\n"
                "    main_shots:\n"
                "      - shot_id: F01-S01\n"
            )
        raise AssertionError(agent_name)

    monkeypatch.setattr(dg, "call_llm", fake_call_llm)

    output, runtime, report = dg._run_shot_director_review_board(
        script="A enters.",
        planner_output="- fragment_id: F01",
        director_brief="film_tone: restrained",
        primary_output="- fragment_id: F01\n  main_shots: []\n",
        images_base64=None,
    )

    assert output.startswith("- fragment_id: F01")
    assert runtime["final_source"] == "arbiter"
    assert runtime["arbiter_packet"]["decision"] == "revise"
    assert "simplify camera move" in report
    assert [name for name, _prompt in calls] == ["shot_director_critic", "shot_director_arbiter"]


def test_shot_director_node_passes_director_brief_to_stage_and_review(monkeypatch):
    captured: dict[str, str] = {}

    def fake_run_three_stage(**kwargs):
        captured["stage_brief"] = kwargs["director_brief"]
        return (
            "- fragment_id: F01\n  main_shots: []\n",
            {"final_source": "guard"},
            {"guard": {"retrieval_mode": "stub"}},
            {"layout": "layout", "blocking": "blocking", "guard": "guard"},
        )

    def fake_review_board(**kwargs):
        captured["review_brief"] = kwargs["director_brief"]
        return "reviewed-yaml", {"final_source": "primary"}, "review-report"

    monkeypatch.setattr(dg, "_run_shot_director_three_stage", fake_run_three_stage)
    monkeypatch.setattr(dg, "_run_shot_director_review_board", fake_review_board)
    monkeypatch.setattr(dg, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(dg, "_record_knowledge_metadata", lambda state, agent_name, context_hint, retrieval_meta: {})
    monkeypatch.setattr(dg, "_persist_update", lambda state, update: {**state, **update})

    result = dg.shot_director_node(
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

    assert captured["stage_brief"] == "film_tone: restrained"
    assert captured["review_brief"] == "film_tone: restrained"
    assert result["agent_outputs"]["shot_director"] == "reviewed-yaml"
    assert result["agent_outputs"]["shot_director_review"] == "review-report"
