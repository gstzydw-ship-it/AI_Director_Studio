from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"
REGISTRY_PATH = KNOWLEDGE_DIR / "rule_registry.yaml"


def _load_agent_maps() -> tuple[dict[str, list[str]], dict[str, list[str]], list[str]]:
    sys.path.insert(0, str(ROOT))
    from agents.knowledge_base import (  # noqa: WPS433
        AGENT_KNOWLEDGE_MAP,
        COMMON_KNOWLEDGE_FILES,
        CRITICAL_KNOWLEDGE_MAP,
    )

    return AGENT_KNOWLEDGE_MAP, CRITICAL_KNOWLEDGE_MAP, COMMON_KNOWLEDGE_FILES


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(content: str) -> dict[str, Any]:
    if not content.startswith("---"):
        return {}

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.DOTALL)
    if not match:
        return {}

    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}

    return metadata if isinstance(metadata, dict) else {}


def _runtime_enabled(path: Path) -> bool:
    return _frontmatter(_read_text(path)).get("runtime_retrieval") is not False


def _knowledge_path(filename: str) -> Path:
    return KNOWLEDGE_DIR / filename


def _load_registry(errors: list[str]) -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        errors.append("Missing knowledge/rule_registry.yaml")
        return {}

    try:
        registry = yaml.safe_load(_read_text(REGISTRY_PATH))
    except yaml.YAMLError as exc:
        errors.append(f"rule_registry.yaml is not valid YAML: {exc}")
        return {}

    if not isinstance(registry, dict):
        errors.append("rule_registry.yaml must contain a mapping at the top level")
        return {}

    return registry


def _check_registry(registry: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    rules = registry.get("rules")
    owner_agents = registry.get("owner_agents", {})
    priority_legend = registry.get("priority_legend", {})
    coverage_targets = registry.get("coverage_targets", [])

    if not isinstance(rules, list) or not rules:
        errors.append("rule_registry.yaml must define a non-empty rules list")
        return

    rule_ids: set[str] = set()
    required = {"id", "title", "owner_agent", "priority", "applies_when", "instruction", "source_files"}

    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            errors.append(f"Registry rule #{index} must be a mapping")
            continue

        missing = sorted(required - set(rule))
        if missing:
            errors.append(f"Registry rule #{index} missing fields: {', '.join(missing)}")

        rule_id = str(rule.get("id", "")).strip()
        if not rule_id:
            continue
        if rule_id in rule_ids:
            errors.append(f"Duplicate registry rule id: {rule_id}")
        rule_ids.add(rule_id)

        owner = rule.get("owner_agent")
        if owner not in owner_agents:
            errors.append(f"{rule_id}: owner_agent '{owner}' is not listed in owner_agents")

        priority = rule.get("priority")
        if priority not in priority_legend:
            errors.append(f"{rule_id}: priority '{priority}' is not listed in priority_legend")

        source_files = rule.get("source_files", [])
        if not isinstance(source_files, list) or not source_files:
            errors.append(f"{rule_id}: source_files must be a non-empty list")
            continue

        for source_file in source_files:
            source_path = ROOT / str(source_file)
            if not source_path.exists():
                errors.append(f"{rule_id}: source file does not exist: {source_file}")

        if not rule.get("avoid_when"):
            warnings.append(f"{rule_id}: avoid_when is empty; consider adding an exception boundary")

    _check_registry_coverage_targets(rules, coverage_targets, errors)


def _check_registry_coverage_targets(
    rules: list[dict[str, Any]],
    coverage_targets: Any,
    errors: list[str],
) -> None:
    if coverage_targets is None:
        return
    if not isinstance(coverage_targets, list):
        errors.append("coverage_targets must be a list")
        return

    source_counts: dict[str, int] = defaultdict(int)
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        for source_file in rule.get("source_files", []) or []:
            source_counts[str(source_file)] += 1

    for target in coverage_targets:
        if not isinstance(target, dict):
            errors.append("Each coverage_targets item must be a mapping")
            continue

        file_name = str(target.get("file", "")).strip()
        min_rules = int(target.get("min_rules", 1))
        if not file_name:
            errors.append("coverage_targets item missing file")
            continue

        target_path = ROOT / file_name
        if not target_path.exists():
            errors.append(f"coverage target does not exist: {file_name}")
            continue

        actual = source_counts.get(file_name, 0)
        if actual < min_rules:
            errors.append(f"coverage target {file_name} has {actual} registered rules, expected at least {min_rules}")


def _check_agent_mappings(errors: list[str]) -> None:
    agent_map, critical_map, common_files = _load_agent_maps()

    for map_name, mapping in (("AGENT_KNOWLEDGE_MAP", agent_map), ("CRITICAL_KNOWLEDGE_MAP", critical_map)):
        for agent_name, files in mapping.items():
            for common_file in common_files:
                if common_file not in files:
                    errors.append(f"{map_name}.{agent_name} missing common file: {common_file}")

            for filename in files:
                path = _knowledge_path(filename)
                if not path.exists():
                    errors.append(f"{map_name}.{agent_name} references missing file: {filename}")
                    continue
                if not _runtime_enabled(path):
                    errors.append(f"{map_name}.{agent_name} references runtime disabled file: {filename}")


def _check_raw_sources(errors: list[str]) -> None:
    for path in KNOWLEDGE_DIR.glob("*"):
        if path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        metadata = _frontmatter(_read_text(path))
        if metadata.get("status") in {"raw_source", "extraction_test"} and metadata.get("runtime_retrieval") is not False:
            errors.append(f"{path.name}: {metadata.get('status')} files must set runtime_retrieval: false")


def _check_case_cards_are_not_runtime(errors: list[str]) -> None:
    for path in sorted((KNOWLEDGE_DIR / "cases").glob("*.md")):
        metadata = _frontmatter(_read_text(path))
        if metadata.get("doc_type") == "case_card" and metadata.get("runtime_retrieval") is not False:
            errors.append(f"cases/{path.name}: case_card files must set runtime_retrieval: false")


def _check_reference_docs_are_not_runtime(errors: list[str]) -> None:
    non_runtime_doc_types = {"casebook", "case_library", "reference_library", "research_report", "raw_source"}
    for path in sorted(KNOWLEDGE_DIR.rglob("*")):
        if path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        metadata = _frontmatter(_read_text(path))
        doc_type = str(metadata.get("doc_type", "")).strip()
        if doc_type in non_runtime_doc_types and metadata.get("runtime_retrieval") is not False:
            relpath = path.relative_to(KNOWLEDGE_DIR).as_posix()
            errors.append(f"{relpath}: {doc_type} files must set runtime_retrieval: false")


def _check_duplicate_local_rules(warnings: list[str]) -> None:
    rule_heading = re.compile(r"^###\s*规则\s+(R-\d+)[：:]\s*(.*)$")

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        seen: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
            match = rule_heading.match(line.strip())
            if match:
                seen[match.group(1)].append((line_number, match.group(2).strip()))

        for rule_id, occurrences in seen.items():
            if len(occurrences) <= 1:
                continue
            locations = ", ".join(f"L{line}:{title}" for line, title in occurrences)
            warnings.append(f"{path.name}: duplicate local rule number {rule_id} ({locations})")


def _check_duplicate_h2_sections(warnings: list[str]) -> None:
    h2_heading = re.compile(r"^##\s+(.+)$", flags=re.MULTILINE)

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = _read_text(path)
        matches = list(h2_heading.finditer(text))
        sections_by_heading: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = match.group(1).strip()
            line_number = text[:match.start()].count("\n") + 1
            normalized_body = text[match.start():end].strip()
            sections_by_heading[heading][normalized_body].append(line_number)

        for heading, bodies in sections_by_heading.items():
            for lines in bodies.values():
                if len(lines) > 1:
                    joined = ", ".join(f"L{line}" for line in lines)
                    warnings.append(f"{path.name}: duplicate H2 section '{heading}' ({joined})")


def run_checks(strict_duplicates: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    registry = _load_registry(errors)
    if registry:
        _check_registry(registry, errors, warnings)
    _check_agent_mappings(errors)
    _check_raw_sources(errors)
    _check_case_cards_are_not_runtime(errors)
    _check_reference_docs_are_not_runtime(errors)
    _check_duplicate_local_rules(warnings)
    _check_duplicate_h2_sections(warnings)

    if strict_duplicates:
        duplicate_warnings = [warning for warning in warnings if "duplicate " in warning]
        errors.extend(duplicate_warnings)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AI Director Studio knowledge-base policy.")
    parser.add_argument(
        "--strict-duplicates",
        action="store_true",
        help="Treat duplicate local rule numbers as errors instead of warnings.",
    )
    args = parser.parse_args()

    errors, warnings = run_checks(strict_duplicates=args.strict_duplicates)

    print("[knowledge-policy] errors:", len(errors))
    for error in errors:
        print("  ERROR:", error)

    print("[knowledge-policy] warnings:", len(warnings))
    for warning in warnings:
        print("  WARN:", warning)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
