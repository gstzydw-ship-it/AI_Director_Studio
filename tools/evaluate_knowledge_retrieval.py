from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "tests" / "knowledge_retrieval_cases.yaml"
DEFAULT_CASES_GLOB = ROOT / "tests" / "knowledge_retrieval_cases*.yaml"

sys.path.insert(0, str(ROOT))

from agents.knowledge_base import (  # noqa: E402
    get_smart_knowledge,
    preferred_sources_from_registry_results,
    query_rule_registry,
    source_basenames_from_registry_results,
)


def _basename(value: str) -> str:
    return os.path.basename(str(value))


def _ranked_rule_ids(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(item.get("rule_id", "")): rank
        for rank, item in enumerate(results, start=1)
        if item.get("rule_id")
    }


def _rule_ids_from_text(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+\b", text or ""))


def _load_cases_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Retrieval cases file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError(f"{path} must contain a 'cases' list")
    for case in cases:
        if isinstance(case, dict):
            case.setdefault("_case_file", str(path.relative_to(ROOT)))
    return cases


def load_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    return _load_cases_file(path)


def discover_case_paths(pattern: str | Path = DEFAULT_CASES_GLOB) -> list[Path]:
    pattern_text = str(pattern)
    paths = sorted(Path().glob(pattern_text) if not os.path.isabs(pattern_text) else Path(pattern_text).parent.glob(Path(pattern_text).name))
    if not paths:
        raise FileNotFoundError(f"No retrieval case files matched: {pattern}")
    return [path.resolve() for path in paths]


def load_cases_from_paths(paths: list[Path]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in paths:
        cases.extend(_load_cases_file(path))
    return cases


def _case_list(case: dict[str, Any], name: str, *aliases: str) -> list[str]:
    for key in (name, *aliases):
        value = case.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value]
    return []


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

    for rule_id in _case_list(case, "must_match_rules", "expected_rules"):
        if rule_id not in ranked:
            diagnostics.append(_diagnose_rule(rule_id, diagnostic_results, top_k))

    for rule_id in _case_list(case, "must_not_match_rules", "forbidden_rules"):
        if rule_id in ranked:
            diagnostics.append(f"{rule_id}: forbidden rule matched at rank #{ranked[rule_id]} inside top_k={top_k}.")

    preferred_sources = source_basenames_from_registry_results(results)
    for source in _case_list(case, "must_match_sources", "expected_sources"):
        if _basename(source) not in preferred_sources:
            diagnostics.append(_diagnose_source(source, diagnostic_results, top_k))

    return diagnostics


def evaluate_case(
    case: dict[str, Any],
    default_top_k: int = 8,
    explain: bool = False,
    diagnostic_k: int = 50,
    mode: str = "profiled",
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

    results = []
    context_text = ""
    metadata: dict[str, Any] = {}
    source_provenance: set[str] = set()
    if not errors and mode == "registry":
        results = query_rule_registry(query, agent_name=agent, n_results=top_k)
        matched_rules = {str(item.get("rule_id", "")) for item in results if item.get("rule_id")}
        preferred_sources = preferred_sources_from_registry_results(results)
        source_provenance = source_basenames_from_registry_results(results)
    elif not errors and mode in {"smart", "profiled"}:
        retrieval_mode = "profiled" if mode == "profiled" else None
        context_text, metadata = get_smart_knowledge(
            agent,
            query,
            retrieval_mode=retrieval_mode,
            retrieval_profile={
                "final_top_k": top_k,
                "min_chunks_fallback": 0,
            },
        )
        matched_rules = _rule_ids_from_text(context_text)
        matched_rules.update(str(rule_id) for rule_id in metadata.get("registry_rule_ids", []) if rule_id)
        preferred_sources = {_basename(source) for source in metadata.get("matched_sources", []) or []}
        preferred_sources.update(_basename(source) for source in metadata.get("registry_preferred_sources", []) or [])
        source_provenance = set(preferred_sources)
        source_provenance.update(_basename(source) for source in metadata.get("registry_source_files", []) or [])
    else:
        matched_rules = set()
        preferred_sources = set()
        source_provenance = set()
        if not errors:
            errors.append(f"unsupported mode: {mode}")

    for rule_id in _case_list(case, "must_match_rules", "expected_rules"):
        if rule_id not in matched_rules:
            errors.append(f"missing rule: {rule_id}")

    for rule_id in _case_list(case, "must_not_match_rules", "forbidden_rules"):
        if rule_id in matched_rules:
            errors.append(f"forbidden rule matched: {rule_id}")

    for source in _case_list(case, "must_match_sources", "expected_sources"):
        if _basename(source) not in source_provenance:
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
        "source_provenance": sorted(source_provenance),
        "top_k": top_k,
        "mode": mode,
        "retrieval_mode": metadata.get("retrieval_mode", mode),
        "result_count": metadata.get("result_count"),
        "case_file": case.get("_case_file", ""),
    }


def _build_agent_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for result in results:
        agent = result["agent"] or "<missing-agent>"
        item = summary.setdefault(agent, {"total": 0, "failed": 0, "missing_rules": [], "failed_cases": []})
        item["total"] += 1
        if result["passed"]:
            continue
        item["failed"] += 1
        item["failed_cases"].append(result["id"])
        for error in result["errors"]:
            if error.startswith("missing rule: "):
                item["missing_rules"].append(error.removeprefix("missing rule: "))

    for item in summary.values():
        item["missing_rules"] = sorted(set(item["missing_rules"]))
    return dict(sorted(summary.items()))


def evaluate_cases(
    cases: list[dict[str, Any]],
    default_top_k: int = 8,
    explain: bool = False,
    diagnostic_k: int = 50,
    mode: str = "profiled",
) -> dict[str, Any]:
    results = [
        evaluate_case(case, default_top_k=default_top_k, explain=explain, diagnostic_k=diagnostic_k, mode=mode)
        for case in cases
    ]
    failures = [result for result in results if not result["passed"]]
    return {
        "passed": not failures,
        "total": len(results),
        "failed": len(failures),
        "mode": mode,
        "agent_summary": _build_agent_summary(results),
        "results": results,
    }


def _print_agent_matrix(report: dict[str, Any]) -> None:
    print("[agent-matrix]")
    for agent, item in report.get("agent_summary", {}).items():
        passed = item["total"] - item["failed"]
        print(f"  {agent}: {passed}/{item['total']} pass")
        if item["failed_cases"]:
            print(f"    failed_cases: {', '.join(item['failed_cases'])}")
        if item["missing_rules"]:
            print(f"    missing_rules: {', '.join(item['missing_rules'])}")


def _print_report(report: dict[str, Any], agent_matrix: bool = False) -> None:
    print(f"[knowledge-retrieval] total: {report['total']}  failed: {report['failed']}")
    if agent_matrix:
        _print_agent_matrix(report)
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['id']} ({result['agent']})")
        if result.get("case_file"):
            print(f"    file: {result['case_file']}")
        print(f"    rules: {', '.join(result['matched_rules'])}")
        print(f"    sources: {', '.join(result['preferred_sources'])}")
        for error in result["errors"]:
            print(f"    ERROR: {error}")
        for diagnostic in result.get("diagnostics", []):
            print(f"    EXPLAIN: {diagnostic}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate knowledge retrieval quality against golden cases.")
    parser.add_argument(
        "--cases",
        type=Path,
        action="append",
        default=None,
        help="Path to a knowledge retrieval cases YAML. Repeat to load multiple files.",
    )
    parser.add_argument(
        "--case-glob",
        type=str,
        default=None,
        help="Glob of retrieval case YAML files. Used by --agent-matrix when --cases is omitted.",
    )
    parser.add_argument("--top-k", type=int, default=8, help="Default number of registry rules to retrieve per case.")
    parser.add_argument(
        "--mode",
        choices=("registry", "smart", "profiled"),
        default="profiled",
        help="profiled checks final get_smart_knowledge context; registry checks rule_registry only.",
    )
    parser.add_argument("--explain", action="store_true", help="Explain failed expectations with rule ranks.")
    parser.add_argument("--diagnostic-k", type=int, default=50, help="Candidate depth used for failure explanation.")
    parser.add_argument("--agent-matrix", action="store_true", help="Load case shards and summarize pass/fail by agent.")
    parser.add_argument("--json", action="store_true", help="Print JSON report instead of a text report.")
    args = parser.parse_args()

    if args.cases:
        case_paths = [path.resolve() for path in args.cases]
    elif args.agent_matrix or args.case_glob:
        case_paths = discover_case_paths(args.case_glob or DEFAULT_CASES_GLOB)
    else:
        case_paths = [DEFAULT_CASES_PATH]
    cases = load_cases_from_paths(case_paths)
    report = evaluate_cases(
        cases,
        default_top_k=args.top_k,
        explain=args.explain,
        diagnostic_k=args.diagnostic_k,
        mode=args.mode,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report, agent_matrix=args.agent_matrix)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
