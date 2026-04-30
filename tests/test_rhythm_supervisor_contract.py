from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_rhythm_supervisor_does_not_replace_source_script(monkeypatch):
    from agents.director_graph_package import legacy_impl, nodes

    original_script = "乔熙：Wait a second!\n商北琛扶住她。"

    monkeypatch.setattr(
        legacy_impl,
        "build_system_prompt",
        lambda prompt, agent_name, context_hint="": (prompt, {"retrieval_mode": "test"}),
    )
    monkeypatch.setattr(
        legacy_impl,
        "call_llm",
        lambda *args, **kwargs: "rhythm_diagnosis: F01 保持快速进入；construction_notes: 普通反应留在片段内部。",
    )
    monkeypatch.setattr(legacy_impl, "_record_knowledge_metadata", lambda *args, **kwargs: {})

    def fake_persist(state, payload):
        merged = dict(state)
        merged.update(payload)
        return merged

    monkeypatch.setattr(legacy_impl, "_persist_update", fake_persist)

    result = nodes.rhythm_rewrite_director_node(
        {
            "script": original_script,
            "aspect_ratio": "9:16",
            "speed_mode": False,
            "agent_outputs": {},
        }
    )

    assert result["script"] == original_script
    assert "普通反应留在片段内部" in result["atmosphere_strategy"]
    assert "改写后剧本" not in result["agent_outputs"]["rhythm_rewrite_director"]
