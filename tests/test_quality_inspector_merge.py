from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package import quality_inspector_impl as qi
from agents.director_graph_package.quality_inspector_impl import (
    _normalise_llm_quality_issues,
    _normalise_merged_quality_report,
)


def test_agent_configured_uses_package_llm_config(monkeypatch):
    monkeypatch.setattr(
        qi,
        "load_config",
        lambda: {
            "agent_models": {
                "quality_inspector_llm_a": {"model": "gpt-test"},
                "quality_inspector_llm_b": {},
                "quality_inspector_llm_c": "disabled",
            }
        },
    )

    assert qi._agent_configured("quality_inspector_llm_a") is True
    assert qi._agent_configured("quality_inspector_llm_b") is False
    assert qi._agent_configured("quality_inspector_llm_c") is False


def test_qc_router_delegates_retry_instruction_to_package_state_store(monkeypatch):
    captured = {}

    def fake_persist_update(state, update):
        captured["state"] = state
        captured["update"] = update
        return update

    monkeypatch.setattr(qi, "_persist_update", fake_persist_update)
    state = {
        "last_qc_status": "fail",
        "qc_retry_count": 0,
        "agent_outputs": {"quality_inspector": "retry this segment"},
    }

    update = qi.qc_router_node(state)

    assert update["qc_retry_count"] == 1
    assert update["revision_instruction"] == "retry this segment"
    assert update["step"] == "step_2_compile"
    assert captured["state"] is state


def test_route_after_qc_keeps_revision_compatibility_path_clear():
    assert qi.route_after_qc({"revision_instruction": "fix prompt"}) == "prompt_compiler"
    assert qi.route_after_qc({"revision_instruction": ""}) == "segment_complete"
    assert qi.route_after_qc({}) == "segment_complete"


def test_merged_quality_warn_report_keeps_optional_items_soft():
    report = """总体评级：warn

【严重问题（需返修）】
- 无

【次要提示（可选优化）】
- 员工冻结反应略重复。
- 主管四散动作可见性不足。
"""

    assert _normalise_merged_quality_report(report) == (
        "warn",
        [
            "- [warn] 员工冻结反应略重复。",
            "- [warn] 主管四散动作可见性不足。",
        ],
    )


def test_warn_llm_quality_issues_do_not_become_hard_failures():
    issues = ["- 可选优化：压缩重复反应。", "- [warn] 已经是软提示。"]

    assert _normalise_llm_quality_issues("warn", issues) == [
        "- [warn] 可选优化：压缩重复反应。",
        "- [warn] 已经是软提示。",
    ]
