from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.knowledge_base import AGENT_KNOWLEDGE_MAP, get_agent_knowledge_files


def test_teaching_case_library_belongs_to_shot_director_stages_not_compiler():
    compiler_files = AGENT_KNOWLEDGE_MAP["prompt_compiler"]

    assert "06_连续性与安全规则.md" in compiler_files
    assert "07_Seedance输出词典与模型适配.md" in compiler_files
    assert "21_镜头调用规则与多机位模板.md" not in compiler_files
    assert "28_全场景分镜与转场案例库.md" not in compiler_files

    for agent_name in ("shot_director", "shot_director_layout", "shot_director_blocking"):
        assert "28_全场景分镜与转场案例库.md" in AGENT_KNOWLEDGE_MAP[agent_name]


def test_dialogue_performance_rules_are_available_to_camera_planning_stages():
    for agent_name in ("shot_director", "shot_director_layout", "shot_director_blocking", "shot_director_guard"):
        assert "04_对白与表演镜头规则.md" in AGENT_KNOWLEDGE_MAP[agent_name]


def test_dialogue_performance_rules_are_critical_for_camera_planning_stages():
    for agent_name in ("shot_director", "shot_director_layout", "shot_director_blocking", "shot_director_guard"):
        assert "04_对白与表演镜头规则.md" in get_agent_knowledge_files(agent_name, critical_only=True)


def test_frontmatter_agent_scope_rule_cards_are_critical_for_scoped_agents():
    rule_card = "rules/prompt_compiler/PROMPT-AXIS-LOCK-PER-SEGMENT-001.md"

    assert rule_card in get_agent_knowledge_files("shot_director", critical_only=True)
    assert rule_card in get_agent_knowledge_files("prompt_compiler", critical_only=True)
    assert rule_card in get_agent_knowledge_files("quality_inspector", critical_only=True)
