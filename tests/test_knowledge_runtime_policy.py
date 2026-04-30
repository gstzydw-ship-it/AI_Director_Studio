from pathlib import Path
import re
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.knowledge_base import (  # noqa: E402
    _runtime_retrieval_enabled,
    get_agent_knowledge_files,
    get_full_knowledge_for_agent,
    get_rule_registry_context,
    load_knowledge_documents,
    preferred_sources_from_registry_results,
    query_rule_registry,
)
from agents import knowledge_base as kb  # noqa: E402
from tools.check_knowledge_policy import run_checks  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"


def _knowledge_name(pattern: str) -> str:
    return next(KNOWLEDGE_DIR.glob(pattern)).name


def _frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8").lstrip("\ufeff")
    if not content.startswith("---"):
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.S)
    if not match:
        return {}
    parsed = yaml.safe_load(match.group(1)) or {}
    return parsed if isinstance(parsed, dict) else {}


def _runtime_disabled_names() -> list[str]:
    names = []
    for path in KNOWLEDGE_DIR.glob("*.md"):
        if _frontmatter(path).get("runtime_retrieval") is False:
            names.append(path.name)
    return names


def test_runtime_disabled_source_docs_are_skipped():
    disabled_names = _runtime_disabled_names()
    assert _knowledge_name("23_*.md") in disabled_names
    assert len(disabled_names) >= 3

    for filename in disabled_names:
        content = (KNOWLEDGE_DIR / filename).read_text(encoding="utf-8")
        assert _runtime_retrieval_enabled(content) is False
        assert load_knowledge_documents("shot_director", [filename]) == []


def test_common_policy_files_are_first_for_runtime_agents():
    priority_doc = _knowledge_name("00_*.md")
    agents = [
        "scene_analyst",
        "story_planner",
        "rhythm_rewrite_director",
        "shot_director",
        "shot_director_layout",
        "shot_director_blocking",
        "shot_director_guard",
        "prompt_compiler",
        "quality_inspector",
    ]

    for agent_name in agents:
        assert get_agent_knowledge_files(agent_name)[0] == priority_doc
        assert get_agent_knowledge_files(agent_name, critical_only=True)[0] == priority_doc
        assert "rule_registry.yaml" not in get_agent_knowledge_files(agent_name)
        assert "rule_registry.yaml" not in get_agent_knowledge_files(agent_name, critical_only=True)


def test_dramatic_signal_doc_is_loaded_for_rhythm_agents():
    signal_doc = _knowledge_name("24_*.md")

    assert signal_doc in get_agent_knowledge_files("rhythm_rewrite_director")
    assert signal_doc in get_agent_knowledge_files("story_planner")
    assert signal_doc in get_agent_knowledge_files("quality_inspector")

    assert signal_doc in get_agent_knowledge_files("rhythm_rewrite_director", critical_only=True)
    assert signal_doc in get_agent_knowledge_files("story_planner", critical_only=True)
    assert signal_doc in get_agent_knowledge_files("quality_inspector", critical_only=True)


def test_story_planner_does_not_load_rhythm_rewrite_doc():
    rewrite_doc = _knowledge_name("09_*.md")

    assert rewrite_doc not in get_agent_knowledge_files("story_planner")
    assert rewrite_doc not in get_agent_knowledge_files("story_planner", critical_only=True)


def test_vector_retrieval_respects_current_agent_file_scope(monkeypatch):
    rewrite_doc = _knowledge_name("09_*.md")
    planner_doc = _knowledge_name("05_*.md")

    monkeypatch.setattr(
        kb,
        "_load_vectordb",
        lambda: {
            "documents": ["stale rewrite doc", "planner doc"],
            "metadatas": [
                {
                    "source_file": rewrite_doc,
                    "agents": "story_planner",
                    "title": "stale",
                },
                {
                    "source_file": planner_doc,
                    "agents": "story_planner",
                    "title": "planner",
                },
            ],
            "embeddings": kb.np.array([[1.0, 0.0], [0.9, 0.1]], dtype=kb.np.float32),
        },
    )
    monkeypatch.setattr(kb, "_embed_texts", lambda *_a, **_kw: [[1.0, 0.0]])

    results = kb.query_knowledge("节奏 拆片", "story_planner", n_results=5)
    sources = {item["source"] for item in results}

    assert rewrite_doc not in sources
    assert planner_doc in sources


def test_rhythm_rewrite_rule_card_is_loaded_critically():
    rule_card = "rules/rhythm_rewrite_director/RHYTHM-SIGNAL-REWRITE-001.md"

    critical_files = get_agent_knowledge_files("rhythm_rewrite_director", critical_only=True)

    assert rule_card in critical_files


def test_shot_director_layout_loads_layout_scope_docs_and_rules():
    layout_doc = _knowledge_name("25_*.md")
    lens_doc = _knowledge_name("02_*.md")
    acting_doc = _knowledge_name("04_*.md")
    files = get_agent_knowledge_files("shot_director_layout")
    critical_files = get_agent_knowledge_files("shot_director_layout", critical_only=True)

    assert layout_doc in files
    assert lens_doc in files
    assert acting_doc not in files
    assert "rules/shot_director_layout/LAYOUT-MAINSHOT-ONLY-001.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-SHOTID-STABILITY-001.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-VERTICAL-RELATION-FIRST-001.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-COVERAGE-BLUEPRINT-005.md" in critical_files


def test_full_fallback_keeps_raw_source_and_full_registry_out():
    priority_doc = _knowledge_name("00_*.md")
    raw_name = _knowledge_name("23_*.md")
    text = get_full_knowledge_for_agent("shot_director", critical_only=True)

    assert f"--- {priority_doc} ---" in text
    assert "--- rule_registry.yaml ---" not in text
    assert f"--- {raw_name} ---" not in text


def test_knowledge_policy_checker_has_no_errors():
    errors, _warnings = run_checks()
    assert errors == []


def test_rule_registry_core_coverage_targets_are_satisfied():
    registry = yaml.safe_load((KNOWLEDGE_DIR / "rule_registry.yaml").read_text(encoding="utf-8"))
    rules = registry["rules"]
    source_counts = {}
    for rule in rules:
        for source_file in rule.get("source_files", []):
            source_counts[source_file] = source_counts.get(source_file, 0) + 1

    assert len(rules) >= 70
    for target in registry["coverage_targets"]:
        assert source_counts.get(target["file"], 0) >= target["min_rules"]


def test_rule_registry_routes_owner_specific_rules():
    shot_results = query_rule_registry("AI 多机位 单段 一个机位 连续拍摄", "shot_director", n_results=3)
    shot_rule_ids = {item["rule_id"] for item in shot_results}
    assert "MULTICAM-MULTISHOT-002" in shot_rule_ids

    layout_results = query_rule_registry("主分镜骨架 shot_id continuity_anchor 不要 sub_shots", "shot_director_layout", n_results=5)
    layout_rule_ids = {item["rule_id"] for item in layout_results}
    assert "LAYOUT-CONTRACT-001" in layout_rule_ids
    assert "LAYOUT-SHOTID-002" in layout_rule_ids

    prompt_results = query_rule_registry("一镜一主动作 提示词 关键动作 表情锚点", "prompt_compiler", n_results=5)
    prompt_rule_ids = {item["rule_id"] for item in prompt_results}
    assert "PROMPT-ACTION-006" in prompt_rule_ids

    shot_prompt_results = query_rule_registry("一镜一主动作 提示词 关键动作 表情锚点", "shot_director", n_results=5)
    shot_prompt_rule_ids = {item["rule_id"] for item in shot_prompt_results}
    assert "PROMPT-ACTION-006" not in shot_prompt_rule_ids


def test_rule_registry_global_safety_rules_are_visible_cross_agent():
    results = query_rule_registry("私密场景 身体部位 情绪 不看身体", "shot_director", n_results=5)
    rule_ids = {item["rule_id"] for item in results}
    assert "SAFETY-INTIMACY-001" in rule_ids


def test_rule_registry_context_formats_cards():
    text, results = get_rule_registry_context("反应镜头 信息揭示 停留 1.5 秒", "rhythm_rewrite_director", n_results=3)

    assert results
    assert text.startswith("--- rule_registry.yaml")
    assert any(item["rule_id"] == "RHYTHM-REACTION-MIN-001" for item in results)
    assert "执行指令:" in text


def test_smart_knowledge_prepends_registry_context(monkeypatch):
    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "bm25",
                "final_top_k": 1,
                "min_chunks_fallback": 0,
                "registry_top_k": 2,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    text, meta = kb.get_smart_knowledge("shot_director", "AI 多机位 单段 一个机位 连续拍摄")

    assert text.startswith("--- rule_registry.yaml")
    assert "MULTICAM-MULTISHOT-002" in meta["registry_rule_ids"]
    assert meta["registry_result_count"] >= 1
    assert "rule_registry.yaml" in meta["matched_sources"]


def test_registry_results_expose_preferred_source_files():
    results = query_rule_registry("AI 多机位 单段 一个机位 连续拍摄", "shot_director", n_results=3)
    preferred_sources = preferred_sources_from_registry_results(results)

    assert _knowledge_name("22_*.md") in preferred_sources
    assert all((KNOWLEDGE_DIR / source).exists() for source in preferred_sources)


def test_registry_preferred_sources_exclude_runtime_disabled_docs():
    results = query_rule_registry("动作匹配剪辑 手触碰门把 动作锚点", "shot_director", n_results=8)
    preferred_sources = preferred_sources_from_registry_results(results)

    assert _knowledge_name("21_*.md") in preferred_sources
    assert _knowledge_name("23_*.md") not in preferred_sources


def test_smart_knowledge_passes_preferred_sources_to_hybrid(monkeypatch):
    captured = {}
    source_21 = _knowledge_name("21_*.md")

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "hybrid",
                "final_top_k": 1,
                "min_chunks_fallback": 0,
                "registry_top_k": 2,
                "bm25_top_k": 3,
                "vector_top_k": 3,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_hybrid(query, agent_name, n_results, bm25_k, vector_k, preferred_sources=None):
        captured["preferred_sources"] = set(preferred_sources or [])
        return [{
            "text": "match-on-action source body",
            "source": source_21,
            "title": "fake",
            "relevance": 1.0,
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_hybrid", fake_hybrid)

    _text, meta = kb.get_smart_knowledge("shot_director", "动作匹配剪辑 手触碰门把 动作锚点")

    assert source_21 in captured["preferred_sources"]
    assert source_21 in meta["registry_preferred_sources"]
    assert source_21 in meta["matched_sources"]


def test_shot_director_blocking_loads_blocking_scope_docs_and_rules():
    blocking_doc = _knowledge_name("26_*.md")
    layout_doc = _knowledge_name("25_*.md")
    acting_doc = _knowledge_name("04_*.md")
    files = get_agent_knowledge_files("shot_director_blocking")
    critical_files = get_agent_knowledge_files("shot_director_blocking", critical_only=True)

    # 二号必须加载自己的职责文档
    assert blocking_doc in files
    assert blocking_doc in critical_files
    # 二号必须加载对白规则
    assert acting_doc in files
    # 二号不应加载一号的骨架文档
    assert layout_doc not in files
    assert layout_doc not in critical_files
    # 二号的规则卡必须被加载
    assert "rules/shot_director_blocking/BLOCKING-PARENT-SUBSHOT-001.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-REACTION-COVERAGE-002.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-DIALOGUE-FIDELITY-003.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-STATE-DELTA-005.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-ACTION-FLOW-006.md" in critical_files


def test_shot_director_guard_loads_guard_scope_docs_and_rules():
    guard_doc = _knowledge_name("27_*.md")
    layout_doc = _knowledge_name("25_*.md")
    blocking_doc = _knowledge_name("26_*.md")
    files = get_agent_knowledge_files("shot_director_guard")
    critical_files = get_agent_knowledge_files("shot_director_guard", critical_only=True)

    # 三号必须加载自己的职责文档
    assert guard_doc in files
    assert guard_doc in critical_files
    # 三号不应加载一号/二号的专属文档
    assert layout_doc not in files
    assert blocking_doc not in files
    # 三号的规则卡必须被加载
    assert "rules/shot_director_guard/GUARD-MINIMAL-REPAIR-001.md" in critical_files
    assert "rules/shot_director_guard/GUARD-STRUCTURE-PRESERVE-002.md" in critical_files
    assert "rules/shot_director_guard/GUARD-FIDELITY-VERTICAL-003.md" in critical_files
    assert "rules/shot_director_guard/GUARD-COVERAGE-CONTRACT-005.md" in critical_files


def test_rule_registry_routes_blocking_and_guard_rules():
    blocking_results = query_rule_registry(
        "reaction_coverage 受击落在哪个 shot_id 子分镜 parent_shot_id 挂靠 对白落点",
        "shot_director_blocking",
        n_results=6,
    )
    blocking_rule_ids = {item["rule_id"] for item in blocking_results}
    assert "BLOCKING-PARENT-SUBSHOT-001" in blocking_rule_ids
    assert "BLOCKING-REACTION-COVERAGE-002" in blocking_rule_ids
    assert "BLOCKING-ACTION-FLOW-006" in blocking_rule_ids

    guard_results = query_rule_registry(
        "最小修复 结构保留 fragment_id 剧本忠实度 竖屏纪律",
        "shot_director_guard",
        n_results=5,
    )
    guard_rule_ids = {item["rule_id"] for item in guard_results}
    assert "GUARD-MINIMAL-REPAIR-001" in guard_rule_ids
    assert "GUARD-FIDELITY-VERTICAL-003" in guard_rule_ids


def test_blocking_rules_not_visible_to_guard():
    guard_results = query_rule_registry(
        "sub_shots parent_shot_id 挂靠 漂浮子分镜",
        "shot_director_guard",
        n_results=5,
    )
    guard_rule_ids = {item["rule_id"] for item in guard_results}
    assert "BLOCKING-PARENT-SUBSHOT-001" not in guard_rule_ids


def test_three_stage_coverage_contract_rules_route():
    layout_results = query_rule_registry(
        "过肩 反打 前景肩线 coverage_role cut_reason companion_visibility 尾帧复位",
        "shot_director_layout",
        n_results=6,
    )
    assert "LAYOUT-COVERAGE-BLUEPRINT-005" in {item["rule_id"] for item in layout_results}

    blocking_results = query_rule_registry(
        "state_delta cut_point blocking_plan state_chain event_coverage duration_hint action_phase 手部状态 单向变化 台词落点 动作中间态",
        "shot_director_blocking",
        n_results=6,
    )
    assert "BLOCKING-STATE-DELTA-005" in {item["rule_id"] for item in blocking_results}
    assert "BLOCKING-ACTION-FLOW-006" in {item["rule_id"] for item in blocking_results}

    guard_results = query_rule_registry(
        "覆盖合同 tailframe_role state_delta companion_visibility 最终 YAML 尾镜头 关系景",
        "shot_director_guard",
        n_results=6,
    )
    assert "GUARD-COVERAGE-CONTRACT-005" in {item["rule_id"] for item in guard_results}
