from pathlib import Path
import re
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.knowledge_base import (  # noqa: E402
    build_retrieval_profile_query,
    get_agent_wiki_files,
    _runtime_retrieval_enabled,
    get_agent_knowledge_files,
    get_full_knowledge_for_agent,
    get_rule_registry_context,
    load_knowledge_documents,
    preferred_sources_from_registry_results,
    query_rule_registry,
    source_basenames_from_registry_results,
)
from agents import knowledge_base as kb  # noqa: E402
from agents import utils as agent_utils  # noqa: E402
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


def test_common_policy_files_are_profiled_not_direct_runtime_context():
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
        assert priority_doc not in get_agent_knowledge_files(agent_name)
        assert priority_doc not in get_agent_knowledge_files(agent_name, critical_only=True)
        assert "rule_registry.yaml" not in get_agent_knowledge_files(agent_name)
        assert "rule_registry.yaml" not in get_agent_knowledge_files(agent_name, critical_only=True)


def test_get_knowledge_dir_respects_settings_directory(tmp_path, monkeypatch):
    project_root = tmp_path / "studio"
    config_dir = project_root / "config"
    configured_dir = project_root / "runtime_knowledge"
    config_dir.mkdir(parents=True)
    configured_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "knowledge:\n  directory: ./runtime_knowledge\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(agent_utils, "get_base_dir", lambda: str(project_root))
    monkeypatch.setattr(agent_utils.sys, "frozen", False, raising=False)

    assert Path(agent_utils.get_knowledge_dir()) == configured_dir


def test_agent_wiki_context_files_are_agent_scoped():
    planner_files = get_agent_wiki_files("story_planner")
    compiler_files = get_agent_wiki_files("prompt_compiler")
    storyboard_files = get_agent_wiki_files("storyboard_designer")

    assert "wiki/agents/story_planner.md" in planner_files
    assert "wiki/contracts/story_to_shot_contract.md" in planner_files
    assert "wiki/README.md" not in planner_files
    assert "wiki/index.md" not in planner_files
    assert "wiki/failure_modes/prompt_too_abstract.md" in compiler_files
    assert "wiki/playbooks/nine_panel_storyboard.md" in storyboard_files


def test_dramatic_signal_doc_is_profiled_and_rule_cards_cover_runtime():
    signal_doc = _knowledge_name("24_*.md")

    assert signal_doc not in get_agent_knowledge_files("rhythm_rewrite_director")
    assert signal_doc not in get_agent_knowledge_files("story_planner")
    assert signal_doc not in get_agent_knowledge_files("quality_inspector")

    assert signal_doc not in get_agent_knowledge_files("rhythm_rewrite_director", critical_only=True)
    assert signal_doc not in get_agent_knowledge_files("story_planner", critical_only=True)
    assert signal_doc not in get_agent_knowledge_files("quality_inspector", critical_only=True)
    assert "rules/rhythm_rewrite_director/RHYTHM-CUTTING-TEMPO-HANDOFF-002.md" in get_agent_knowledge_files(
        "rhythm_rewrite_director", critical_only=True
    )
    assert "rules/story_planner/RHYTHM-SIGNAL-TAXONOMY-001.md" in get_agent_knowledge_files(
        "story_planner", critical_only=True
    )


def test_story_planner_does_not_load_rhythm_rewrite_doc():
    rewrite_doc = _knowledge_name("09_*.md")

    assert rewrite_doc not in get_agent_knowledge_files("story_planner")
    assert rewrite_doc not in get_agent_knowledge_files("story_planner", critical_only=True)


def test_vector_retrieval_respects_current_agent_file_scope(monkeypatch):
    rewrite_doc = _knowledge_name("09_*.md")
    planner_doc = "rules/shared/CONT-STATE-CONTRACT-001.md"

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

    assert layout_doc not in files
    assert layout_doc not in critical_files
    assert lens_doc not in files
    assert lens_doc not in critical_files
    assert acting_doc not in files
    assert acting_doc not in critical_files
    assert "rules/shot_director_layout/LAYOUT-MAINSHOT-ONLY-001.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-SHOTID-STABILITY-001.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-VERTICAL-RELATION-FIRST-001.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-COVERAGE-BLUEPRINT-005.md" in critical_files
    assert "rules/shot_director_layout/LAYOUT-FIRST-FRAME-SPATIAL-ANCHOR-006.md" in critical_files


def test_full_fallback_keeps_raw_source_and_full_registry_out():
    priority_doc = _knowledge_name("00_*.md")
    raw_name = _knowledge_name("23_*.md")
    text = get_full_knowledge_for_agent("shot_director", critical_only=True)

    assert f"--- {priority_doc} ---" not in text
    assert "--- rules/shot_director/SHOT-DIRECTOR-STEPWISE-PIPELINE-001.md ---" in text
    assert "--- rule_registry.yaml ---" not in text
    assert f"--- {raw_name} ---" not in text


def test_knowledge_policy_checker_has_no_errors():
    errors, _warnings = run_checks()
    assert errors == []


def test_rule_cards_have_profile_frontmatter():
    required = {"agent_scope", "priority", "retrieval_key", "applies_when", "avoid_when"}
    rule_files = list((KNOWLEDGE_DIR / "rules").rglob("*.md"))

    assert len(rule_files) >= 70
    for path in rule_files:
        metadata = _frontmatter(path)
        missing = {field for field in required if field not in metadata}
        assert missing == set(), f"{path} missing {missing}"
        assert str(metadata["priority"]).startswith("P")


def test_case_cards_have_director_pattern_frontmatter():
    case_files = [path for path in (KNOWLEDGE_DIR / "cases").rglob("*.md") if not path.name.startswith("_")]

    assert len(case_files) >= 40
    for path in case_files:
        metadata = _frontmatter(path)
        assert metadata.get("doc_type") == "case_card"
        assert metadata.get("case_title")
        assert metadata.get("served_agents")
        assert metadata.get("scene_types")
        assert metadata.get("events")
        assert "aspect_ratio" in metadata


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


def test_rule_registry_strictly_filters_by_owner_or_agent_scope():
    shot_results = query_rule_registry("SAFETY INTIMACY private body emotion", "shot_director", n_results=5)
    shot_rule_ids = {item["rule_id"] for item in shot_results}
    assert "SAFETY-INTIMACY-001" not in shot_rule_ids

    quality_results = query_rule_registry("SAFETY INTIMACY private body emotion", "quality_inspector", n_results=5)
    quality_rule_ids = {item["rule_id"] for item in quality_results}
    assert "SAFETY-INTIMACY-001" in quality_rule_ids

    rhythm_results = query_rule_registry("PROMPT AXIS LOCK 180 reaction beat", "rhythm_rewrite_director", n_results=8)
    assert all(item["owner_agent"] == "rhythm_rewrite_director" for item in rhythm_results)
    assert "PROMPT-AXIS-LOCK-PER-SEGMENT-001" not in {item["rule_id"] for item in rhythm_results}


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

    assert text.startswith("--- wiki/agents/shot_director.md (agent_wiki_context) ---")
    assert "--- rule_registry.yaml" in text
    assert meta["used_wiki_context"] is True
    assert "MULTICAM-MULTISHOT-002" in meta["registry_rule_ids"]
    assert meta["registry_result_count"] >= 1
    assert "rule_registry.yaml" in meta["matched_sources"]


def test_registry_results_expose_preferred_source_files():
    results = query_rule_registry("AI 多机位 单段 一个机位 连续拍摄", "shot_director", n_results=3)
    preferred_sources = preferred_sources_from_registry_results(results)
    registry_sources = source_basenames_from_registry_results(results)

    assert _knowledge_name("22_*.md") in registry_sources
    assert _knowledge_name("22_*.md") not in preferred_sources
    assert _knowledge_name("00_*.md") in registry_sources
    assert _knowledge_name("00_*.md") not in preferred_sources
    assert all((KNOWLEDGE_DIR / source).exists() for source in preferred_sources)


def test_registry_preferred_sources_exclude_runtime_disabled_docs():
    results = query_rule_registry("动作匹配剪辑 手触碰门把 动作锚点", "shot_director", n_results=8)
    preferred_sources = preferred_sources_from_registry_results(results)
    registry_sources = source_basenames_from_registry_results(results)

    assert _knowledge_name("21_*.md") in registry_sources
    assert _knowledge_name("21_*.md") not in preferred_sources
    assert _knowledge_name("23_*.md") not in preferred_sources


def test_smart_knowledge_passes_preferred_sources_to_hybrid(monkeypatch):
    captured = {}
    profiled_source = _knowledge_name("22_*.md")
    result_source = "rules/shot_director/SHOT-MULTICAM-SYSTEM-029.md"

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
            "source": result_source,
            "title": "fake",
            "relevance": 1.0,
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_hybrid", fake_hybrid)

    _text, meta = kb.get_smart_knowledge("shot_director", "AI 多机位 单段 一个机位 连续拍摄")

    assert profiled_source not in captured["preferred_sources"]
    assert profiled_source not in meta["registry_preferred_sources"]
    assert profiled_source in meta["registry_source_files"]
    assert result_source in meta["matched_sources"]


def test_smart_knowledge_prepends_agent_wiki_context(monkeypatch):
    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "hybrid",
                "final_top_k": 1,
                "min_chunks_fallback": 0,
                "registry_top_k": 0,
                "bm25_top_k": 3,
                "vector_top_k": 3,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_hybrid(query, agent_name, n_results, bm25_k, vector_k, preferred_sources=None):
        return [{
            "text": "retrieved rule body",
            "source": "rules/story_planner/TIME-SEGMENT-MULTISHOT-001.md",
            "title": "fake",
            "relevance": 1.0,
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_hybrid", fake_hybrid)

    text, meta = kb.get_smart_knowledge("story_planner", "15 seconds door conflict")

    assert text.startswith("--- wiki/agents/story_planner.md (agent_wiki_context) ---")
    assert "retrieved rule body" in text
    assert meta["used_wiki_context"] is True
    assert "wiki/agents/story_planner.md" in meta["wiki_sources"]
    assert "wiki/agents/story_planner.md" in meta["matched_sources"]


def test_agent_retrieval_contracts_are_bootstrap_profile_only():
    kb._retrieval_contracts_cache = None

    profile = kb.build_agent_bootstrap_retrieval_profile("shot_director")

    assert "deprecated" in profile["exclude_status"]
    assert profile["case_card_limits"]["require_rule_anchor"] is True
    assert "camera" in profile["signals"]
    assert "shot_language" in profile["tags"]
    assert "agent_retrieval_contracts.yaml" not in get_agent_knowledge_files("shot_director")
    assert load_knowledge_documents("shot_director", ["agent_retrieval_contracts.yaml"]) == []


def test_default_config_uses_profiled_retrieval(monkeypatch):
    captured = {}

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "profiled",
                "final_top_k": 2,
                "min_chunks_fallback": 0,
                "registry_top_k": 0,
                "bm25_top_k": 12,
                "vector_top_k": 12,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_profiled(**kwargs):
        captured.update(kwargs)
        return [{
            "text": "profiled default match",
            "source": "rules/shot_director/SHOT-DIALOGUE-COVERAGE-001.md",
            "title": "dialogue coverage",
            "relevance": 1.0,
            "metadata": {"status": "active"},
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_profiled", fake_profiled)

    text, meta = kb.get_smart_knowledge("shot_director", "dialogue coverage")

    assert "profiled default match" in text
    assert captured["n_results"] == 2
    assert captured["bm25_k"] == 12
    assert captured["vector_k"] == 12
    assert meta["retrieval_mode"] == "profiled"
    assert meta["used_full_fallback"] is False


def test_profiled_retrieval_expands_registry_budget_to_final_top_k(monkeypatch):
    captured = {}

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "profiled",
                "final_top_k": 6,
                "min_chunks_fallback": 0,
                "registry_top_k": 4,
                "bm25_top_k": 12,
                "vector_top_k": 12,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_registry(query, agent_name, n_results):
        captured["registry_top_k"] = n_results
        return "", []

    def fake_profiled(**kwargs):
        return [{
            "text": "profiled match",
            "source": "rules/story_planner/SEG-LAYER-001.md",
            "title": "segment layer",
            "relevance": 1.0,
            "metadata": {"status": "active"},
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "get_rule_registry_context", fake_registry)
    monkeypatch.setattr(kb, "query_knowledge_profiled", fake_profiled)

    _text, meta = kb.get_smart_knowledge("story_planner", "segment boundary")

    assert captured["registry_top_k"] == 6
    assert "registry_top_k" not in meta["retrieval_profile"]


def test_smart_knowledge_applies_contract_profile_filters(monkeypatch):
    captured = {}

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "profiled",
                "final_top_k": 4,
                "min_chunks_fallback": 0,
                "registry_top_k": 0,
                "bm25_top_k": 3,
                "vector_top_k": 3,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_profiled(**kwargs):
        captured["query"] = kwargs["query"]
        return [
            {
                "text": "active case one",
                "source": "cases/one.md",
                "title": "case one",
                "relevance": 1.0,
                "metadata": {"doc_type": "case_card", "status": "active"},
            },
            {
                "text": "active case two",
                "source": "cases/two.md",
                "title": "case two",
                "relevance": 0.9,
                "metadata": {"doc_type": "case_card", "status": "active"},
            },
            {
                "text": "draft rule",
                "source": "rules/shot_director/draft.md",
                "title": "draft",
                "relevance": 0.8,
                "metadata": {"status": "draft"},
            },
            {
                "text": "active rule",
                "source": "rules/shot_director/active.md",
                "title": "active",
                "relevance": 0.7,
                "metadata": {"status": "active"},
            },
        ]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_profiled", fake_profiled)

    text, meta = kb.get_smart_knowledge("shot_director", "coverage")

    assert "signals: shot camera angle coverage reaction transition axis composition" in captured["query"]
    assert "active case one" in text
    assert "active case two" not in text
    assert "draft rule" not in text
    assert "active rule" in text
    assert meta["result_count"] == 2
    assert meta["retrieval_profile"]["case_card_limits"]["max_share_of_context"] == 0.35


def test_profiled_retrieval_reranks_with_rule_metadata(monkeypatch):
    def fake_hybrid(query, agent_name, n_results, bm25_k, vector_k, preferred_sources=None, metadata_profile=False):
        return [
            {
                "text": "generic camera language",
                "source": "knowledge/21_镜头调用规则与多机位模板.md",
                "title": "generic",
                "relevance": 1.0,
                "metadata": {"agent_scope": ["shot_director"], "priority": "P4"},
            },
            {
                "text": "door state must move monotonically",
                "source": "knowledge/rules/continuity/CONT-DOOR-MONOTONIC-001.md",
                "title": "door",
                "relevance": 0.8,
                "metadata": {
                    "agent_scope": ["shot_director"],
                    "priority": "P0",
                    "signals": ["电梯门", "门缝", "冲入"],
                    "risks": ["door_state_jump"],
                },
            },
        ]

    monkeypatch.setattr(kb, "query_knowledge_hybrid", fake_hybrid)

    results = kb.query_knowledge_profiled(
        "电梯门 门缝 冲入 door_state_jump",
        "shot_director",
        n_results=2,
    )

    assert results[0]["title"] == "door"
    assert results[0]["metadata_score"] > results[1]["metadata_score"]


def test_retrieval_profile_query_adds_structured_tags():
    query = build_retrieval_profile_query(
        "shot director",
        {
            "scene_type": "elevator",
            "events": ["rush_in", "collision"],
            "risks": ["door_state_jump", "romanticize_collision"],
            "dialogue_type": "teasing",
            "aspect_ratio": "9:16",
        },
    )

    assert "scene_types: elevator" in query
    assert "events: rush_in collision" in query
    assert "risks: door_state_jump romanticize_collision" in query
    assert "dialogue_types: teasing" in query
    assert "aspect_ratios: 9:16" in query


def test_smart_knowledge_passes_structured_profile_to_profiled_search(monkeypatch):
    captured = {}

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "profiled",
                "final_top_k": 1,
                "min_chunks_fallback": 0,
                "registry_top_k": 1,
                "bm25_top_k": 3,
                "vector_top_k": 3,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_registry(query, agent_name, n_results):
        captured["registry_query"] = query
        return "", []

    def fake_profiled(**kwargs):
        captured["profiled_query"] = kwargs["query"]
        return [{
            "text": "door rule",
            "source": "rules/continuity/CONT-DOOR-MONOTONIC-001.md",
            "title": "door",
            "relevance": 1.0,
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "get_rule_registry_context", fake_registry)
    monkeypatch.setattr(kb, "query_knowledge_profiled", fake_profiled)

    _text, meta = kb.get_smart_knowledge(
        "shot_director",
        "elevator scene",
        retrieval_profile={
            "scene_type": "elevator",
            "events": ["rush_in", "collision", "waist_support"],
            "risks": ["door_state_jump", "romanticize_collision"],
            "dialogue_type": "teasing",
            "aspect_ratio": "9:16",
        },
    )

    assert "scene_types: elevator" in captured["registry_query"]
    assert "events: rush_in collision waist_support" in captured["profiled_query"]
    assert "risks: door_state_jump romanticize_collision" in captured["profiled_query"]
    assert meta["retrieval_profile"]["scene_type"] == "elevator"


def test_smart_knowledge_uses_profile_retrieval_budget(monkeypatch):
    captured = {}

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "profiled",
                "final_top_k": 8,
                "min_chunks_fallback": 0,
                "registry_top_k": 4,
                "bm25_top_k": 12,
                "vector_top_k": 12,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_registry(query, agent_name, n_results):
        captured["registry_top_k"] = n_results
        return "", []

    def fake_profiled(**kwargs):
        captured["final_top_k"] = kwargs["n_results"]
        captured["bm25_top_k"] = kwargs["bm25_k"]
        captured["vector_top_k"] = kwargs["vector_k"]
        return [
            {"text": "first rhythm chunk", "source": "15.md", "title": "a", "relevance": 1.0},
            {"text": "duplicate rhythm chunk", "source": "15.md", "title": "b", "relevance": 0.9},
            {"text": "signal chunk", "source": "24.md", "title": "c", "relevance": 0.8},
        ]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "get_rule_registry_context", fake_registry)
    monkeypatch.setattr(kb, "query_knowledge_profiled", fake_profiled)

    text, meta = kb.get_smart_knowledge(
        "rhythm_rewrite_director",
        "节奏总控",
        retrieval_profile={
            "registry_top_k": 2,
            "final_top_k": 6,
            "bm25_top_k": 7,
            "vector_top_k": 8,
            "max_chunks_per_source": 1,
        },
    )

    assert captured["registry_top_k"] == 2
    assert captured["final_top_k"] == 6
    assert captured["bm25_top_k"] == 7
    assert captured["vector_top_k"] == 8
    assert "duplicate rhythm chunk" not in text
    assert meta["raw_result_count"] == 3
    assert meta["result_count"] == 2


def test_structured_aspect_ratio_query_does_not_force_vertical(monkeypatch):
    captured = {}

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "hybrid",
                "final_top_k": 1,
                "min_chunks_fallback": 0,
                "registry_top_k": 0,
                "bm25_top_k": 3,
                "vector_top_k": 3,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_hybrid(query, agent_name, n_results, bm25_k, vector_k, preferred_sources=None):
        captured["query"] = query
        return [{
            "text": "wide composition rule",
            "source": "rules/shared/GLOBAL-ASPECT-001.md",
            "title": "aspect",
            "relevance": 1.0,
        }]

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_hybrid", fake_hybrid)

    _text, meta = kb.get_smart_knowledge(
        "shot_director",
        "shot director composition",
        retrieval_profile={"aspect_ratio": "16:9"},
    )

    assert "aspect_ratios: 16:9" in captured["query"]
    assert "9:16" not in captured["query"]
    assert meta["query_hint"] == captured["query"]


def test_profiled_smart_knowledge_uses_critical_fallback_not_full(monkeypatch):
    calls = []

    def fake_load_config():
        return {
            "knowledge": {
                "retrieval_mode": "profiled",
                "final_top_k": 1,
                "min_chunks_fallback": 3,
                "registry_top_k": 0,
                "bm25_top_k": 3,
                "vector_top_k": 3,
            },
            "vectordb": {
                "chunk_size": 800,
                "chunk_overlap": 100,
            },
        }

    def fake_profiled(**_kwargs):
        return [{
            "text": "profiled match",
            "source": "rules/shot_director/SHOT-SOURCE-EVENT-FIDELITY-001.md",
            "title": "fidelity",
            "relevance": 1.0,
        }]

    def fake_full(agent_name, critical_only=False):
        calls.append((agent_name, critical_only))
        return "CRITICAL ONLY" if critical_only else "FULL SHOULD NOT BE USED"

    monkeypatch.setattr(kb, "load_config", fake_load_config)
    monkeypatch.setattr(kb, "query_knowledge_profiled", fake_profiled)
    monkeypatch.setattr(kb, "get_full_knowledge_for_agent", fake_full)

    text, meta = kb.get_smart_knowledge("shot_director", "电梯门冲入")

    assert "profiled match" in text
    assert "CRITICAL ONLY" in text
    assert "FULL SHOULD NOT BE USED" not in text
    assert meta["retrieval_mode"] == "profiled"
    assert meta["used_full_fallback"] is False
    assert meta["used_critical_fallback"] is True
    assert calls == [("shot_director", True)]


def test_shot_director_blocking_loads_blocking_scope_docs_and_rules():
    blocking_doc = _knowledge_name("26_*.md")
    layout_doc = _knowledge_name("25_*.md")
    acting_doc = _knowledge_name("04_*.md")
    files = get_agent_knowledge_files("shot_director_blocking")
    critical_files = get_agent_knowledge_files("shot_director_blocking", critical_only=True)

    # 二号职责由规则卡覆盖，长文档不再直接注入运行时
    assert blocking_doc not in files
    assert blocking_doc not in critical_files
    # 二号的对白约束由规则卡覆盖，长文档不再直接注入
    assert acting_doc not in files
    assert acting_doc not in critical_files
    # 二号不应加载一号的骨架文档
    assert layout_doc not in files
    assert layout_doc not in critical_files
    # 二号的规则卡必须被加载
    assert "rules/shot_director_blocking/BLOCKING-PARENT-SUBSHOT-001.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-REACTION-COVERAGE-002.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-DIALOGUE-FIDELITY-003.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-STATE-DELTA-005.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-ACTION-FLOW-006.md" in critical_files
    assert "rules/shot_director_blocking/BLOCKING-FAST-CUT-LEGIBILITY-008.md" in critical_files


def test_shot_director_guard_loads_guard_scope_docs_and_rules():
    guard_doc = _knowledge_name("27_*.md")
    layout_doc = _knowledge_name("25_*.md")
    blocking_doc = _knowledge_name("26_*.md")
    files = get_agent_knowledge_files("shot_director_guard")
    critical_files = get_agent_knowledge_files("shot_director_guard", critical_only=True)

    # 三号职责由规则卡覆盖，长文档不再直接注入
    assert guard_doc not in files
    assert guard_doc not in critical_files
    # 三号不应加载一号/二号的专属文档
    assert layout_doc not in files
    assert blocking_doc not in files
    # 三号的规则卡必须被加载
    assert "rules/shot_director_guard/GUARD-MINIMAL-REPAIR-001.md" in critical_files
    assert "rules/shot_director_guard/GUARD-STRUCTURE-PRESERVE-002.md" in critical_files
    assert "rules/shot_director_guard/GUARD-FIDELITY-VERTICAL-003.md" in critical_files
    assert "rules/shot_director_guard/GUARD-COVERAGE-CONTRACT-005.md" in critical_files
    assert "rules/shot_director_guard/GUARD-FIRST-FRAME-PROP-CUT-BUDGET-006.md" in critical_files


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
