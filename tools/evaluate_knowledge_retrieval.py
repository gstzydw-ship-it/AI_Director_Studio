from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "tests" / "knowledge_retrieval_cases.yaml"

sys.path.insert(0, str(ROOT))

from agents.knowledge_base import (  # noqa: E402
    preferred_sources_from_registry_results,
    query_rule_registry,
)


def _basename(value: str) -> str:
    return os.path.basename(str(value))


def _ranked_rule_ids(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(item.get("rule_id", "")): rank
        for rank, item in enumerate(results, start=1)
        if item.get("rule_id")
    }


def load_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Retrieval cases file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("knowledge retrieval cases file must contain a 'cases' list")
    return cases


def _diagnose_rule(
    rule_id: str,
    diagnostic_results: list[dict[str, Any]],
    top_k: int,
) -> str:
    ranked = _ranked_rule_ids(diagnostic_results)
    rank = ranked.get(rule_id)
    if rank is None:
        return f"{rule_id}: not in diagnostic candidates; check query wording, owner_agent visibility, and registry fields."
    if rank <= top_k:
        return f"{rule_id}: ranked #{rank} inside top_k={top_k}; check evaluator expectations."

    suppressors = [
        item.get("rule_id", "")
        for item in diagnostic_results[max(0, rank - 6): rank - 1]
        if item.get("rule_id")
    ]
    return f"{rule_id}: ranked #{rank}, outside top_k={top_k}; nearest higher rules: {', '.join(suppressors)}"


def _diagnose_source(
    source: str,
    diagnostic_results: list[dict[str, Any]],
    top_k: int,
) -> str:
    source_name = _basename(source)
    for rank, item in enumerate(diagnostic_results, start=1):
        item_sources = {_basename(value) for value in item.get("source_files", []) or []}
        if source_name in item_sources:
            return (
                f"{source_name}: first appears via {item.get('rule_id', '')} "
                f"at rank #{rank}; top_k={top_k}"
            )
    return f"{source_name}: not present in diagnostic source candidates."


def _build_diagnostics(
    case: dict[str, Any],
    results: list[dict[str, Any]],
    errors: list[str],
    diagnostic_k: int,
) -> list[str]:
    if not errors:
        return []

    agent = str(case.get("agent", "")).strip()
    query = str(case.get("query", "")).strip()
    top_k = int(case.get("top_k", 8))
    diagnostic_results = query_rule_registry(query, agent_name=agent, n_results=diagnostic_k)
    ranked = _ranked_rule_ids(results)
    diagnostics: list[str] = []

    for rule_id in case.get("must_match_rules", []) or []:
        if rule_id not in ranked:
            diagnostics.append(_diagnose_rule(rule_id, diagnostic_results, top_k))

    for rule_id in case.get("must_not_match_rules", []) or []:
        if rule_id in ranked:
            diagnostics.append(f"{rule_id}: forbidden rule matched at rank #{ranked[rule_id]} inside top_k={top_k}.")

    preferred_sources = preferred_sources_from_registry_results(results)
    for source in case.get("must_match_sources", []) or []:
        if _basename(source) not in preferred_sources:
            diagnostics.append(_diagnose_source(source, diagnostic_results, top_k))

    return diagnostics


def evaluate_case(
    case: dict[str, Any],
    default_top_k: int = 8,
    explain: bool = False,
    diagnostic_k: int = 50,
) -> dict[str, Any]:
    case_id = str(case.get("id", "")).strip() or "<missing-id>"
    agent = str(case.get("agent", "")).strip()
    query = str(case.get("query", "")).strip()
    top_k = int(case.get("top_k", default_top_k))

    errors: list[str] = []
    if not agent:
        errors.append("case missing agent")
    if not query:
        errors.append("case missing query")

    results = [] if errors else query_rule_registry(query, agent_name=agent, n_results=top_k)
    matched_rules = {str(item.get("rule_id", "")) for item in results if item.get("rule_id")}
    preferred_sources = preferred_sources_from_registry_results(results)

    for rule_id in case.get("must_match_rules", []) or []:
        if rule_id not in matched_rules:
            errors.append(f"missing rule: {rule_id}")

    for rule_id in case.get("must_not_match_rules", []) or []:
        if rule_id in matched_rules:
            errors.append(f"forbidden rule matched: {rule_id}")

    for source in case.get("must_match_sources", []) or []:
        if _basename(source) not in preferred_sources:
            errors.append(f"missing preferred source: {_basename(source)}")

    diagnostics = _build_diagnostics(case, results, errors, diagnostic_k) if explain else []

    return {
        "id": case_id,
        "agent": agent,
        "passed": not errors,
        "errors": errors,
        "diagnostics": diagnostics,
        "matched_rules": sorted(matched_rules),
        "preferred_sources": sorted(preferred_sources),
        "top_k": top_k,
    }


def evaluate_cases(
    cases: list[dict[str, Any]],
    default_top_k: int = 8,
    explain: bool = False,
    diagnostic_k: int = 50,
) -> dict[str, Any]:
    results = [
        evaluate_case(case, default_top_k=default_top_k, explain=explain, diagnostic_k=diagnostic_k)
        for case in cases
    ]
    failures = [result for result in results if not result["passed"]]
    return {
        "passed": not failures,
        "total": len(results),
        "failed": len(failures),
        "results": results,
    }


def _print_report(report: dict[str, Any]) -> None:
    print(f"[knowledge-retrieval] total: {report['total']}  failed: {report['failed']}")
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['id']} ({result['agent']})")
        print(f"    rules: {', '.join(result['matched_rules'])}")
        print(f"    sources: {', '.join(result['preferred_sources'])}")
        for error in result["errors"]:
            print(f"    ERROR: {error}")
        for diagnostic in result.get("diagnostics", []):
            print(f"    EXPLAIN: {diagnostic}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate rule-registry retrieval quality against golden cases.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="Path to knowledge retrieval cases YAML.")
    parser.add_argument("--top-k", type=int, default=8, help="Default number of registry rules to retrieve per case.")
    parser.add_argument("--explain", action="store_true", help="Explain failed expectations with rule ranks.")
    parser.add_argument("--diagnostic-k", type=int, default=50, help="Candidate depth used for failure explanation.")
    parser.add_argument("--json", action="store_true", help="Print JSON report instead of a text report.")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    report = evaluate_cases(
        cases,
        default_top_k=args.top_k,
        explain=args.explain,
        diagnostic_k=args.diagnostic_k,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
