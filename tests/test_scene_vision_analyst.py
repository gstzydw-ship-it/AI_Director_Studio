from __future__ import annotations

from pathlib import Path
import sys

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
from agents.director_graph_package import planning_context_impl as pci
from agents.director_graph_package import runners as package_runners
from ui import app as ui_app


def test_scene_analyst_uses_scene_vision_agent_for_reference_images(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["agent_name"] = kwargs.get("agent_name")
        captured["images_base64"] = kwargs.get("images_base64")
        captured["user_prompt"] = user_prompt
        return "scene_id: test_scene"

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    def fake_scene_card_api(prompt, images_base64):
        captured["scene_card_prompt"] = prompt
        captured["scene_card_images"] = images_base64
        return "data:image/png;base64,iVBORw0KGgo="

    monkeypatch.setattr(pci, "_call_scene_card_image_api", fake_scene_card_api)
    monkeypatch.setattr(pci, "_save_scene_card_image", lambda data, session_id, scene_number=1: rf"D:\tmp\scene_card_{scene_number:02d}.png")
    monkeypatch.setattr(
        pci,
        "_append_scene_card_references",
        lambda state, scene_cards: (
            list(state.get("reference_image_b64s") or []) + ["data:image/png;base64,iVBORw0KGgo=" for _ in scene_cards],
            list(state.get("reference_image_manifest") or []) + [{"purpose": "场景母版图", "type": "scene_card"} for _ in scene_cards],
        ),
    )

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

    result = pci.scene_analyst_node(state)

    assert captured["agent_name"] == "scene_vision_analyst"
    assert captured["images_base64"] == ["image-a"]
    assert "五官" in str(captured["user_prompt"])
    assert "人物站位" in str(captured["user_prompt"])
    assert "场景预分析卡" in str(captured["user_prompt"])
    assert "站位姿势" in str(captured["user_prompt"])
    assert "道具锚点" in str(captured["user_prompt"])
    assert "场景母版图" in str(captured["user_prompt"])
    assert "左前方" not in str(captured["user_prompt"])
    assert "右前方" not in str(captured["user_prompt"])
    assert "四个正面内景固定视角" in str(captured["user_prompt"])
    assert "俯视布局图" in str(captured["scene_card_prompt"])
    assert "四个固定视角" in str(captured["scene_card_prompt"])
    assert "房间四面墙壁位置看向房间内景象" in str(captured["scene_card_prompt"])
    assert "左前方视角" not in str(captured["scene_card_prompt"])
    assert "右前方视角" not in str(captured["scene_card_prompt"])
    assert captured["scene_card_images"] == ["image-a"]
    assert "scene_id: test_scene" in result["agent_outputs"]["scene_analyst"]
    assert "场景母版图" in result["agent_outputs"]["scene_analyst"]
    assert result["agent_outputs"]["scene_card_image"] == r"D:\tmp\scene_card_01.png"
    assert result["reference_image_count"] == 2
    assert "scene_id: test_scene" in result["scene_context_brief"]
    assert result["step"] == "step_0_enhance"


def test_scene_analyst_sends_all_scene_reference_images(monkeypatch):
    captured: dict[str, object] = {}
    scene_card_calls: list[list[str]] = []

    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["agent_name"] = kwargs.get("agent_name")
        captured["images_base64"] = kwargs.get("images_base64")
        return "scene_id: test_scene"

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)
    def fake_scene_card_api(prompt, images_base64):
        scene_card_calls.append(images_base64)
        return "data:image/png;base64,iVBORw0KGgo="

    monkeypatch.setattr(pci, "_call_scene_card_image_api", fake_scene_card_api)
    monkeypatch.setattr(pci, "_save_scene_card_image", lambda data, session_id, scene_number=1: rf"D:\tmp\scene_card_{scene_number:02d}.png")
    monkeypatch.setattr(
        pci,
        "_append_scene_card_references",
        lambda state, scene_cards: (
            list(state.get("reference_image_b64s") or []) + ["data:image/png;base64,iVBORw0KGgo=" for _ in scene_cards],
            list(state.get("reference_image_manifest") or []) + [{"purpose": "场景母版图", "type": "scene_card"} for _ in scene_cards],
        ),
    )

    state = {
        "script": "商北琛走进大堂。",
        "aspect_ratio": "9:16",
        "reference_image_b64s": ["person-a", "scene-a", "person-b", "scene-b"],
        "reference_image_manifest": [
            {"label": "A", "purpose": "主角人物"},
            {"label": "B", "purpose": "场景空间"},
            {"label": "C", "purpose": "对手人物"},
            {"label": "D", "purpose": "公司大堂场景"},
        ],
        "reference_images": "",
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    pci.scene_analyst_node(state)

    assert captured["agent_name"] == "scene_vision_analyst"
    assert captured["images_base64"] == ["scene-a", "scene-b"]
    assert scene_card_calls == [["scene-a"], ["scene-b"]]


def test_scene_analyst_uses_text_agent_without_reference_images(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        pci,
        "build_system_prompt",
        lambda base_system, agent_name, context_hint="": (base_system, {"retrieval_mode": "stub"}),
    )
    monkeypatch.setattr(
        pci,
        "_record_knowledge_metadata",
        lambda state, agent_name, context_hint, retrieval_meta: dict(state.get("knowledge_metadata") or {}),
    )
    monkeypatch.setattr(pci, "_persist_update", lambda state, update: {**state, **update})

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["agent_name"] = kwargs.get("agent_name")
        captured["images_base64"] = kwargs.get("images_base64")
        return "scene_id: test_scene"

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    state = {
        "script": "商北琛走进大堂。",
        "aspect_ratio": "9:16",
        "reference_image_b64s": [],
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    pci.scene_analyst_node(state)

    assert captured["agent_name"] == "scene_analyst"
    assert captured["images_base64"] is None


def test_run_pipeline_keeps_uploaded_reference_images_for_scene_vision(monkeypatch):
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


def test_run_phase_1_accepts_single_scene_reference_image(monkeypatch):
    monkeypatch.setattr(package_runners, "clear_state", lambda: None)
    monkeypatch.setattr(package_runners, "save_state", lambda state: None)
    monkeypatch.setattr(package_runners, "_invoke_graph", lambda state, thread_id: state)

    state = package_runners.run_phase_1_planning(
        script="test script",
        aspect_ratio="9:16",
        reference_images="",
        reference_image_b64s=["scene-a"],
        reference_image_manifest=[{"label": "scene", "purpose": "场景空间"}],
        speed_mode=False,
    )

    assert state["reference_image_count"] == 1
    assert state["reference_image_b64s"] == ["scene-a"]


def test_reference_purpose_infers_scene_from_filename():
    assert ui_app._infer_reference_purpose(1, "乔熙公寓-客厅.png").startswith("场景空间")
    assert ui_app._infer_reference_purpose(6, "集团门口.png").startswith("场景空间")
    assert ui_app._infer_reference_purpose(1, "乔熙.png").startswith("主角人物")


def test_scene_reference_items_accept_scene_filename_even_if_purpose_is_wrong():
    state = {
        "reference_image_b64s": ["apartment", "hero", "gate"],
        "reference_image_manifest": [
            {"filename": "乔熙公寓-客厅.png", "purpose": "主角人物身份"},
            {"filename": "乔熙.png", "purpose": "对手角色"},
            {"filename": "集团门口.png", "purpose": "补充参考图"},
        ],
    }

    items = pci._scene_reference_items(state)

    assert [item["image"] for item in items] == ["apartment", "gate"]
