from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.knowledge_base import AGENT_KNOWLEDGE_MAP, get_agent_knowledge_files
from agents.knowledge_base import _runtime_retrieval_enabled


def test_teaching_case_library_is_not_direct_runtime_context():
    compiler_files = AGENT_KNOWLEDGE_MAP["prompt_compiler"]

    assert "06_连续性与安全规则.md" not in compiler_files
    assert "07_Seedance输出词典与模型适配.md" not in compiler_files
    assert "21_镜头调用规则与多机位模板.md" not in compiler_files
    assert "28_全场景分镜与转场案例库.md" not in compiler_files

    for agent_name in ("shot_director", "shot_director_layout", "shot_director_blocking"):
        assert "28_全场景分镜与转场案例库.md" not in AGENT_KNOWLEDGE_MAP[agent_name]


def test_case_cards_are_not_default_runtime_retrieval():
    case_files = sorted((Path(ROOT) / "knowledge" / "cases").glob("CASE_*.md"))

    assert case_files
    for path in case_files:
        assert not _runtime_retrieval_enabled(path.read_text(encoding="utf-8"))


def test_dialogue_performance_long_doc_is_profiled_for_camera_planning_stages():
    for agent_name in ("shot_director", "shot_director_blocking", "shot_director_guard"):
        assert "04_对白与表演镜头规则.md" not in AGENT_KNOWLEDGE_MAP[agent_name]
    assert "04_对白与表演镜头规则.md" not in AGENT_KNOWLEDGE_MAP["shot_director_layout"]


def test_dialogue_performance_rule_cards_are_critical_for_camera_planning_stages():
    blocking_dialogue_rule = "rules/shot_director_blocking/BLOCKING-DIALOGUE-FIDELITY-003.md"
    prompt_dialogue_rule = "rules/prompt_compiler/PROMPT-SHOT-EXPRESSION-CORE-001.md"

    for agent_name in ("shot_director", "shot_director_layout", "shot_director_blocking", "shot_director_guard"):
        assert "04_对白与表演镜头规则.md" not in get_agent_knowledge_files(agent_name, critical_only=True)
    assert blocking_dialogue_rule in get_agent_knowledge_files("shot_director_blocking", critical_only=True)
    assert prompt_dialogue_rule in get_agent_knowledge_files("shot_director_guard", critical_only=True)


def test_frontmatter_agent_scope_rule_cards_are_critical_for_scoped_agents():
    rule_card = "rules/prompt_compiler/PROMPT-AXIS-LOCK-PER-SEGMENT-001.md"

    assert rule_card in get_agent_knowledge_files("shot_director", critical_only=True)
    assert rule_card in get_agent_knowledge_files("prompt_compiler", critical_only=True)
    assert rule_card in get_agent_knowledge_files("quality_inspector", critical_only=True)


def test_visual_language_translation_rule_is_shared_across_planning_and_prompt_agents():
    rule_card = "rules/prompt_compiler/PROMPT-DIRECTOR-JARGON-TRANSLATION-001.md"

    scoped_agents = (
        "director_showrunner",
        "rhythm_rewrite_director",
        "story_planner",
        "shot_director",
        "shot_director_layout",
        "shot_director_blocking",
        "shot_director_guard",
        "prompt_compiler",
        "quality_inspector",
    )
    for agent_name in scoped_agents:
        assert rule_card in get_agent_knowledge_files(agent_name, critical_only=True)


def test_shot_director_does_not_use_compiler_degrade_rule_as_runtime_contract():
    natural_language_rulebook = "07_Seedance输出词典与模型适配.md"
    degrade_rule = "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md"

    for agent_name in ("shot_director", "shot_director_layout", "shot_director_blocking", "shot_director_guard"):
        critical_files = get_agent_knowledge_files(agent_name, critical_only=True)
        runtime_files = get_agent_knowledge_files(agent_name)
        assert natural_language_rulebook not in AGENT_KNOWLEDGE_MAP[agent_name]
        assert natural_language_rulebook not in critical_files
        assert degrade_rule not in critical_files
        assert degrade_rule not in runtime_files

    compiler_critical = get_agent_knowledge_files("prompt_compiler", critical_only=True)
    assert degrade_rule in compiler_critical
