from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from tools import evaluate_knowledge_retrieval as eval_knowledge  # noqa: E402
from tools.evaluate_knowledge_retrieval import evaluate_case, evaluate_cases, load_cases  # noqa: E402


def test_golden_knowledge_retrieval_cases_pass():
    report = evaluate_cases(load_cases())

    assert report["total"] >= 12
    assert report["failed"] == 0
    assert report["mode"] == "profiled"


def test_golden_retrieval_does_not_prefer_raw_sources():
    report = evaluate_cases(load_cases())
    raw_source = next((ROOT / "knowledge").glob("23_*.md")).name
    preferred_sources = {
        source
        for result in report["results"]
        for source in result["preferred_sources"]
    }

    assert raw_source not in preferred_sources


def test_registry_mode_remains_available_for_fast_rule_checks():
    report = evaluate_cases(load_cases(), mode="registry")

    assert report["total"] >= 12
    assert report["failed"] == 0
    assert report["mode"] == "registry"


def test_retrieval_explain_reports_rule_rank_when_missing_from_top_k():
    case = {
        "id": "diagnostic_probe",
        "agent": "shot_director",
        "query": "MULTICAM-MULTISHOT-002 MULTICAM-ACTIONLIMIT-003",
        "top_k": 1,
        "must_match_rules": ["MULTICAM-ACTIONLIMIT-003"],
    }

    result = evaluate_case(case, explain=True, diagnostic_k=10, mode="registry")

    assert result["passed"] is False
    assert result["diagnostics"]
    assert "MULTICAM-ACTIONLIMIT-003" in result["diagnostics"][0]
    assert "ranked #" in result["diagnostics"][0]


def test_smart_mode_checks_final_context_without_real_embedding(monkeypatch):
    def fake_smart(agent_name, context_hint, retrieval_mode=None, retrieval_profile=None):
        assert agent_name == "shot_director"
        assert context_hint == "door match action"
        assert retrieval_mode is None
        assert retrieval_profile["final_top_k"] == 2
        return (
            "--- rules/shot_director/example.md ---\n[ACT-MATCH-001] Match-on-Action",
            {
                "retrieval_mode": "profiled",
                "matched_sources": ["rules/shot_director/example.md"],
                "registry_rule_ids": [],
                "registry_preferred_sources": ["21_镜头调用规则与多机位模板.md"],
                "result_count": 1,
            },
        )

    monkeypatch.setattr(eval_knowledge, "get_smart_knowledge", fake_smart)

    result = evaluate_case(
        {
            "id": "smart_probe",
            "agent": "shot_director",
            "query": "door match action",
            "top_k": 2,
            "must_match_rules": ["ACT-MATCH-001"],
            "must_match_sources": ["21_镜头调用规则与多机位模板.md"],
        },
        mode="smart",
    )

    assert result["passed"] is True
    assert result["mode"] == "smart"
    assert result["retrieval_mode"] == "profiled"
