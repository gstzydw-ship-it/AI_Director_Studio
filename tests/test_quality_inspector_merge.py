from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package.quality_inspector_impl import (
    _normalise_llm_quality_issues,
    _normalise_merged_quality_report,
)


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
