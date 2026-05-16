import json
import os
import time


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_knowledge_index_status_marks_newer_knowledge_as_stale(monkeypatch, tmp_path):
    import agents.knowledge_base as kb

    knowledge_dir = tmp_path / "knowledge"
    db_dir = tmp_path / "runtime-vectordb"
    db_path = db_dir / "vectordb.json"
    _write(knowledge_dir / "rules" / "director_showrunner" / "fresh.md", "# fresh")
    _write(db_path, "{}")

    old = time.time() - 120
    new = time.time()
    os.utime(db_path, (old, old))
    os.utime(knowledge_dir / "rules" / "director_showrunner" / "fresh.md", (new, new))

    monkeypatch.setattr(kb, "get_knowledge_dir", lambda: str(knowledge_dir))
    monkeypatch.setattr(kb, "load_config", lambda: {"vectordb": {"persist_directory": str(db_dir)}})

    status = kb.knowledge_index_status()

    assert status["status"] == "stale"
    assert status["needs_rebuild"] is True
    assert status["newer_file_count"] == 1
    assert status["newer_files"][0]["path"] == "rules/director_showrunner/fresh.md"
    assert status["vectordb_path"] == str(db_path)


def test_knowledge_index_status_reports_legacy_root_vectordb(monkeypatch, tmp_path):
    import agents.knowledge_base as kb

    project_root = tmp_path / "project"
    knowledge_dir = project_root / "knowledge"
    runtime_dir = tmp_path / "cache" / "vectordb" / "chroma_data"
    legacy_path = project_root / "vectordb" / "chroma_data" / "vectordb.json"
    runtime_path = runtime_dir / "vectordb.json"
    _write(knowledge_dir / "rule.md", "# rule")
    _write(runtime_path, "{}")
    _write(legacy_path, "{}")

    now = time.time()
    os.utime(knowledge_dir / "rule.md", (now - 20, now - 20))
    os.utime(runtime_path, (now, now))
    os.utime(legacy_path, (now - 60, now - 60))

    monkeypatch.setattr(kb, "get_knowledge_dir", lambda: str(knowledge_dir))
    monkeypatch.setattr(kb, "load_config", lambda: {"vectordb": {"persist_directory": str(runtime_dir)}})

    status = kb.knowledge_index_status()

    assert status["status"] == "fresh"
    assert status["legacy_vectordb"]["exists"] is True
    assert status["legacy_vectordb"]["path"] == str(legacy_path)
    assert "不是当前运行路径" in status["legacy_vectordb"]["message"]


def test_build_vectordb_writes_source_freshness_metadata(monkeypatch, tmp_path):
    import agents.knowledge_base as kb

    knowledge_dir = tmp_path / "knowledge"
    db_dir = tmp_path / "db"
    _write(
        knowledge_dir / "rule.md",
        """---
agent_scope: director_showrunner
owner_agent: director_showrunner
pipeline_stage: story
failure_mode: weak conflict
output_contract: scene beats
example_good: strong choice
example_bad: vague choice
---
# Rule
Use stronger conflict.
""",
    )

    monkeypatch.setattr(kb, "get_knowledge_dir", lambda: str(knowledge_dir))
    monkeypatch.setattr(kb, "_load_session_model_profile", lambda: {})
    monkeypatch.setattr(kb, "load_config", lambda: {
        "vectordb": {
            "persist_directory": str(db_dir),
            "embedding_model": "fake-embedding",
            "chunk_size": 1000,
            "chunk_overlap": 0,
        }
    })
    monkeypatch.setattr(kb, "_embed_texts", lambda texts, model=None, batch_size=20: [[1.0, 0.0] for _ in texts])

    kb.build_vectordb(force_rebuild=True)

    data = json.loads((db_dir / "vectordb.json").read_text(encoding="utf-8"))
    assert data["knowledge_dir"] == str(knowledge_dir)
    assert data["knowledge_file_count"] == 1
    assert data["knowledge_latest_file"] == "rule.md"
    assert data["built_at"]
    metadata = data["metadatas"][0]
    assert metadata["owner_agent"] == "director_showrunner"
    assert metadata["pipeline_stage"] == "story"
    assert metadata["failure_mode"] == "weak conflict"
    assert metadata["output_contract"] == "scene beats"
    assert metadata["example_good"] == "strong choice"
    assert metadata["example_bad"] == "vague choice"
