from __future__ import annotations

from pathlib import Path
import sys

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg


def test_scene_analyst_uses_scene_vision_agent_for_reference_images(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(dg, "_should_send_reference_images_to_llm", lambda: False)
    monkeypatch.setattr(
        dg,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        dg,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(dg, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["agent_name"] = kwargs.get("agent_name")
        captured["images_base64"] = kwargs.get("images_base64")
        captured["user_prompt"] = user_prompt
        return "scene_id: test_scene"

    monkeypatch.setattr(dg, "call_llm", fake_call_llm)

    state = {
        "script": "商北琛走进大堂。",
        "aspect_ratio": "9:16",
        "reference_image_b64s": ["image-a"],
        "reference_image_manifest": [],
        "reference_images": "",
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    result = dg.scene_analyst_node(state)

    assert captured["agent_name"] == "scene_vision_analyst"
    assert captured["images_base64"] == ["image-a"]
    assert "五官" in str(captured["user_prompt"])
    assert "人物站位" in str(captured["user_prompt"])
    assert result["agent_outputs"]["scene_analyst"] == "scene_id: test_scene"


def test_scene_analyst_uses_text_agent_without_reference_images(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(dg, "_should_send_reference_images_to_llm", lambda: False)
    monkeypatch.setattr(
        dg,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        dg,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(dg, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["agent_name"] = kwargs.get("agent_name")
        captured["images_base64"] = kwargs.get("images_base64")
        return "scene_id: test_scene"

    monkeypatch.setattr(dg, "call_llm", fake_call_llm)

    state = {
        "script": "商北琛走进大堂。",
        "aspect_ratio": "9:16",
        "reference_image_b64s": [],
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    dg.scene_analyst_node(state)

    assert captured["agent_name"] == "scene_analyst"
    assert captured["images_base64"] is None


def test_run_pipeline_keeps_uploaded_reference_images_for_scene_vision(monkeypatch):
    monkeypatch.setattr(dg, "_should_send_reference_images_to_llm", lambda: False)
    monkeypatch.setattr(dg, "clear_state", lambda: None)
    monkeypatch.setattr(dg, "save_state", lambda state: None)
    monkeypatch.setattr(dg, "_invoke_graph", lambda state, thread_id: state)

    state = dg.run_phase_1_planning(
        script="test script",
        aspect_ratio="9:16",
        reference_images="",
        reference_image_b64s=["image-a", "image-b", "image-c"],
        reference_image_manifest=[],
        speed_mode=False,
    )

    assert state["reference_image_count"] == 3
    assert state["reference_image_b64s"] == ["image-a", "image-b", "image-c"]
