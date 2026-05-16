from __future__ import annotations

from ui import app as web_app


def test_runtime_event_view_exposes_knowledge_sources_and_rules() -> None:
    view = web_app._runtime_event_view(
        {
            "event": "knowledge_retrieval_completed",
            "agent_name": "shot_director",
            "result_count": 7,
            "matched_sources": [
                "rules/shot_director/PROMPT-SHOT-EXPRESSION-CORE-001.md",
                "rules/shared/vertical_shot_language.md",
            ],
            "registry_rule_ids": ["SHOT_CORE", "VERTICAL_FRAMING"],
        }
    )

    assert view["phase"] == "knowledge"
    assert view["status"] == "done"
    assert view["title"] == "🎥 镜头设计 知识库命中"
    assert "来源：rules/shot_director/PROMPT-SHOT-EXPRESSION-CORE-001.md" in view["detail"]
    assert "规则：SHOT_CORE、VERTICAL_FRAMING" in view["detail"]
    assert view["sources"] == [
        "rules/shot_director/PROMPT-SHOT-EXPRESSION-CORE-001.md",
        "rules/shared/vertical_shot_language.md",
    ]
    assert view["rules"] == ["SHOT_CORE", "VERTICAL_FRAMING"]


def test_knowledge_metadata_snapshot_exposes_latest_sources() -> None:
    events = web_app._knowledge_metadata_event_views(
        {
            "knowledge_metadata": {
                "shot_director": {
                    "retrieval_mode": "profiled",
                    "matched_sources": ["rules/shot_director/camera_language.md"],
                    "registry_rule_ids": ["SHOT_LANGUAGE"],
                }
            }
        }
    )

    assert len(events) == 1
    assert events[0]["title"] == "🎥 镜头设计 已记录知识库/规则"
    assert events[0]["sources"] == ["rules/shot_director/camera_language.md"]
    assert events[0]["rules"] == ["SHOT_LANGUAGE"]
