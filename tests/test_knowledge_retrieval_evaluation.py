from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from tools.evaluate_knowledge_retrieval import evaluate_case, evaluate_cases, load_cases  # noqa: E402


def test_golden_knowledge_retrieval_cases_pass():
    report = evaluate_cases(load_cases())

    assert report["total"] >= 12
    assert report["failed"] == 0


def test_golden_retrieval_does_not_prefer_raw_sources():
    report = evaluate_cases(load_cases())
    raw_source = next((ROOT / "knowledge").glob("23_*.md")).name
    preferred_sources = {
        source
        for result in report["results"]
        for source in result["preferred_sources"]
    }

    assert raw_source not in preferred_sources


def test_retrieval_explain_reports_rule_rank_when_missing_from_top_k():
    case = {
        "id": "diagnostic_probe",
        "agent": "shot_director",
        "query": "MULTICAM-MULTISHOT-002 MULTICAM-ACTIONLIMIT-003",
        "top_k": 1,
        "must_match_rules": ["MULTICAM-ACTIONLIMIT-003"],
    }

    result = evaluate_case(case, explain=True, diagnostic_k=10)

    assert result["passed"] is False
    assert result["diagnostics"]
    assert "MULTICAM-ACTIONLIMIT-003" in result["diagnostics"][0]
    assert "ranked #" in result["diagnostics"][0]
