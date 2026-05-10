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


def test_append_scene_card_references_keeps_layout_and_grid(tmp_path):
    layout_path = tmp_path / "scene_layout_01.png"
    grid_path = tmp_path / "scene_grid_01.png"
    layout_path.write_bytes(b"layout")
    grid_path.write_bytes(b"grid")

    images, manifest = pci._append_scene_card_references(
        {
            "reference_image_b64s": ["person-ref"],
            "reference_image_manifest": [{"filename": "乔熙.png", "role": "character"}],
        },
        [
            {
                "scene_number": "1",
                "scene_title": "集团大堂",
                "layout_path": str(layout_path),
                "grid_path": str(grid_path),
                "image_path": str(grid_path),
            }
        ],
    )

    assert len(images) == 3
    assert images[1].startswith("data:image/png;base64,")
    assert images[2].startswith("data:image/png;base64,")
    assert [item.get("role") for item in manifest] == ["character", "scene_layout", "scene_card"]
    assert "用户标注" in manifest[1]["purpose"]
    assert "人物位置" in manifest[1]["purpose"]
    assert "移动轨迹" in manifest[1]["purpose"]

    rerun_images, rerun_manifest = pci._append_scene_card_references(
        {"reference_image_b64s": images, "reference_image_manifest": manifest},
        [
            {
                "scene_number": "1",
                "scene_title": "集团大堂",
                "layout_path": str(layout_path),
                "grid_path": str(grid_path),
                "image_path": str(grid_path),
            }
        ],
    )

    assert len(rerun_images) == 3
    assert [item.get("role") for item in rerun_manifest] == ["character", "scene_layout", "scene_card"]


def test_scene_layout_annotations_are_saved_as_annotated_references():
    state = {
        "reference_image_b64s": ["layout-a", "old-annotated", "person-a"],
        "reference_image_manifest": [
            {"label": "@图片1", "role": "scene_layout", "purpose": "场景俯视布局图"},
            {"label": "@图片2", "role": "annotated_scene_layout", "purpose": "旧标注图"},
            {"label": "@图片3", "role": "character", "purpose": "主角人物"},
        ],
        "agent_outputs": {},
    }

    saved_count = ui_app._upsert_scene_layout_annotations(
        state,
        [
            {
                "scene_number": 1,
                "image_path": "output/sessions/local/scene_cards/scene_layout_01.png",
                "annotations": {
                    "people": [{"label": "乔熙", "x": 0.3, "y": 0.5, "color": "#ef4444"}],
                    "arrows": [{"x1": 0.2, "y1": 0.3, "x2": 0.8, "y2": 0.7}],
                },
                "annotated_image": "data:image/png;base64,annotated",
            }
        ],
    )

    assert saved_count == 1
    assert state["scene_layout_annotations"][0]["summary"] == (
        "人物标点: 乔熙(0.30,0.50)；活动轨迹: (0.20,0.30)->(0.80,0.70)"
    )
    assert state["reference_image_b64s"] == ["layout-a", "person-a", "data:image/png;base64,annotated"]
    assert state["reference_image_manifest"][-1]["role"] == "annotated_scene_layout"
    assert "人物位置" in state["reference_image_manifest"][-1]["purpose"]
    assert "移动轨迹" in state["reference_image_manifest"][-1]["purpose"]
    assert "scene_layout_annotations" in state["agent_outputs"]


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
        return (
            "scene_id: test_scene\n"
            "调度待定: 人物站位和运动轨迹由用户在俯视图上手动标注；场景预分析不推导。\n"
            "场景信息: 大堂入口在北侧，前台在东侧。\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    def fake_scene_card_generate(overhead_prompt, card_prompt, scene_image, session_id, scene_number):
        captured["overhead_prompt"] = overhead_prompt
        captured["scene_card_prompt"] = card_prompt
        captured["scene_card_images"] = [scene_image]
        captured["scene_card_session_id"] = session_id
        captured["scene_card_scene_number"] = scene_number
        return "data:image/png;base64,iVBORw0KGgo=", rf"D:\tmp\scene_layout_{scene_number:02d}.png"

    monkeypatch.setattr(pci, "_generate_scene_card_with_overhead", fake_scene_card_generate)
    monkeypatch.setattr(pci, "_save_scene_card_image", lambda data, session_id, scene_number=1: rf"D:\tmp\scene_grid_{scene_number:02d}.png")
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
    assert "场景预分析卡" in str(captured["user_prompt"])
    assert "不从参考图固定人物站位、人物姿势、人物朝向、人物间距离或视线轴线" in str(captured["user_prompt"])
    assert "不推导人物站位和行动路径" in str(captured["user_prompt"])
    assert "调度待定" in str(captured["user_prompt"])
    assert "人物站位和运动轨迹由用户在俯视图上手动标注" in str(captured["user_prompt"])
    assert "场景信息" in str(captured["user_prompt"])
    assert "道具锚点" in str(captured["user_prompt"])
    assert "光线与材质" in str(captured["user_prompt"])
    assert "场景参考图需求" in str(captured["user_prompt"])
    assert "输出两张独立图片" in str(captured["user_prompt"])
    assert "第一张是俯视布局图" in str(captured["user_prompt"])
    assert "第二张是 16:9 的 3x3 九宫格机位图" in str(captured["user_prompt"])
    assert "不要要求生成左侧俯视图+右侧九宫格的十格场景卡" in str(captured["user_prompt"])
    assert "左侧俯视图，右侧" not in str(captured["user_prompt"])
    assert "人物占位" not in str(captured["user_prompt"])
    assert "站位姿势" not in str(captured["user_prompt"])
    assert "本场景在场人物" not in str(captured["user_prompt"])
    assert "左前方" not in str(captured["user_prompt"])
    assert "右前方" not in str(captured["user_prompt"])
    assert "第一步：只根据随请求发送的这一张场景参考图，生成一张独立的俯视布局图" in str(captured["overhead_prompt"])
    assert "输出只允许是一张俯视布局图" in str(captured["overhead_prompt"])
    assert "不要场景卡" in str(captured["overhead_prompt"])
    assert "不要九宫格" in str(captured["overhead_prompt"])
    assert "不要透视内景" in str(captured["overhead_prompt"])
    assert "严格依据当前随请求发送的唯一场景参考图推导" in str(captured["overhead_prompt"])
    assert "不可凭空新增对称大厅、停车区、水池、柱廊、沙发区、雕塑或绿化" in str(captured["overhead_prompt"])
    assert "房间/场地边界尽量贴近画布四边" in str(captured["overhead_prompt"])
    assert "禁止白边、留白、底板、图例、编号、箭头、机位点、站位点和人物" in str(captured["overhead_prompt"])
    assert "基于随请求上传的两张参考图，生成一张独立的 3x3 多机位参考图 / cinematic camera-angle coverage sheet" in str(captured["scene_card_prompt"])
    assert "参考图1：只用于锁定真实场景的材质、家具外观、色彩、光线、氛围和渲染风格" in str(captured["scene_card_prompt"])
    assert "参考图2：只用于锁定俯视空间布局、方向、门窗、入口、通道、家具和固定物体位置" in str(captured["scene_card_prompt"])
    assert "两张参考图都只是参考，不得被复制、裁切、拼贴或直接画进最终图" in str(captured["scene_card_prompt"])
    assert "禁止出现俯视图、说明卡、十格布局、海报拼贴、白边、留白、背景底色、标题栏或未绘制区域" in str(captured["scene_card_prompt"])
    assert "以参考图2为唯一布局依据，图上方=北，右侧=东，下方=南，左侧=西" in str(captured["scene_card_prompt"])
    assert "九宫格固定排列" in str(captured["scene_card_prompt"])
    assert "左上：北侧平视，看南" in str(captured["scene_card_prompt"])
    assert "上中：高位看全场" in str(captured["scene_card_prompt"])
    assert "右上：东侧平视，看西" in str(captured["scene_card_prompt"])
    assert "左中：西侧平视，看东" in str(captured["scene_card_prompt"])
    assert "中间：正对主墙看" in str(captured["scene_card_prompt"])
    assert "右中：南侧平视，看北" in str(captured["scene_card_prompt"])
    assert "左下：入口看里面" in str(captured["scene_card_prompt"])
    assert "下中：道具近景" in str(captured["scene_card_prompt"])
    assert "右下：里面看入口" in str(captured["scene_card_prompt"])
    assert "北侧平视：相机贴近俯视图北边界，眼平高度，水平看南" in str(captured["scene_card_prompt"])
    assert "东侧平视：相机贴近俯视图东边界，眼平高度，水平看西" in str(captured["scene_card_prompt"])
    assert "南侧平视：相机贴近俯视图南边界，眼平高度，水平看北" in str(captured["scene_card_prompt"])
    assert "西侧平视：相机贴近俯视图西边界，眼平高度，水平看东" in str(captured["scene_card_prompt"])
    assert "东侧和西侧必须有清晰的侧墙、侧立面或侧向通道透视，不能仍然正对主入口或主墙" in str(captured["scene_card_prompt"])
    assert "禁止用同一个入口、主墙、窗墙、沙发、电视墙、门头或主立面画面冒充多个方向" in str(captured["scene_card_prompt"])
    assert "正对主墙看：水平正对最重要的墙面、电视墙、柜体、门头或主背景面" in str(captured["scene_card_prompt"])
    assert "道具近景：靠近原图已有固定道具，如茶几、沙发、柜体、门把手、标志、台阶或水景边缘，近景中仍能看出周围空间" in str(captured["scene_card_prompt"])
    assert "里面看入口：位于空间内部、靠近核心家具或主活动区，水平看向入口、门、通道或来向，只画空景" in str(captured["scene_card_prompt"])
    assert "不要人物、人物肩背、视线轴线、箭头、点位标记、运动线、图例、新家具、新装饰、复制画面、镜像画面、鱼眼、超广角畸变或夸张透视" in str(captured["scene_card_prompt"])
    assert "斜向中景" not in str(captured["scene_card_prompt"])
    assert "空间纵深景" not in str(captured["scene_card_prompt"])
    assert "顶面灯光" not in str(captured["scene_card_prompt"])
    assert "仰视" not in str(captured["scene_card_prompt"])
    assert "反打关系" not in str(captured["scene_card_prompt"])
    assert "对向回看" not in str(captured["scene_card_prompt"])
    assert "coverage sheet" in str(captured["scene_card_prompt"])
    assert "正投影" not in str(captured["scene_card_prompt"])
    assert "【第1张原始场景图说明】" not in str(captured["scene_card_prompt"])
    assert "当前随请求发送的唯一参考图" not in str(captured["scene_card_prompt"])
    assert "【仅供锁定空间的文字摘要】" not in str(captured["scene_card_prompt"])
    assert "一次性生成完整" not in str(captured["scene_card_prompt"])
    assert "整张画布必须被十个图格全部占满" not in str(captured["scene_card_prompt"])
    assert "左侧俯视图必须复用" not in str(captured["scene_card_prompt"])
    assert "右侧约 72%" not in str(captured["scene_card_prompt"])
    assert "人物站位" not in str(captured["scene_card_prompt"])
    assert "女主根据剧本动作" not in str(captured["scene_card_prompt"])
    assert "本场景在场人物" not in str(captured["scene_card_prompt"])
    assert "人物占位" not in str(captured["scene_card_prompt"])
    assert "站位姿势" not in str(captured["scene_card_prompt"])
    assert "只用不同颜色的实心圆点标出在场人物占位" not in str(captured["scene_card_prompt"])
    assert "人物点位必须贴近剧本动作和场景预分析确定的位置" not in str(captured["scene_card_prompt"])
    assert "必须先读【戏剧动作关系】再放点" not in str(captured["scene_card_prompt"])
    assert "彩色圆点" not in str(captured["scene_card_prompt"])
    assert "相机点" not in str(captured["scene_card_prompt"])
    assert "四视图" not in str(captured["scene_card_prompt"])
    assert "2x2" not in str(captured["scene_card_prompt"])
    assert "机位1西北角" not in str(captured["scene_card_prompt"])
    assert "左前方视角" not in str(captured["scene_card_prompt"])
    assert "右前方视角" not in str(captured["scene_card_prompt"])
    assert "人物名文字" not in str(captured["scene_card_prompt"])
    assert captured["scene_card_images"] == ["image-a"]
    assert captured["scene_card_scene_number"] == 1
    assert "scene_id: test_scene" in result["agent_outputs"]["scene_analyst"]
    assert "调度待定" in result["agent_outputs"]["scene_analyst"]
    assert "3x3 九宫格机位图" in result["agent_outputs"]["scene_analyst"]
    assert "每个场景输出两张独立图片" in result["agent_outputs"]["scene_analyst"]
    assert "场景参考图" in result["agent_outputs"]["scene_analyst"]
    assert result["agent_outputs"]["scene_card_image"] == r"D:\tmp\scene_grid_01.png"
    assert result["agent_outputs"]["scene_grid_image"] == r"D:\tmp\scene_grid_01.png"
    assert result["agent_outputs"]["scene_layout_image"] == r"D:\tmp\scene_layout_01.png"
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
    def fake_scene_card_generate(overhead_prompt, card_prompt, scene_image, session_id, scene_number):
        scene_card_calls.append(
            {
                "scene_image": scene_image,
                "overhead_prompt": overhead_prompt,
                "card_prompt": card_prompt,
                "scene_number": scene_number,
            }
        )
        return "data:image/png;base64,iVBORw0KGgo=", rf"D:\tmp\scene_layout_{scene_number:02d}.png"

    monkeypatch.setattr(pci, "_generate_scene_card_with_overhead", fake_scene_card_generate)
    monkeypatch.setattr(pci, "_save_scene_card_image", lambda data, session_id, scene_number=1: rf"D:\tmp\scene_grid_{scene_number:02d}.png")
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
    assert [call["scene_image"] for call in scene_card_calls] == ["scene-a", "scene-b"]
    assert [call["scene_number"] for call in scene_card_calls] == [1, 2]
    assert all("第一步" in str(call["overhead_prompt"]) for call in scene_card_calls)
    assert all("基于随请求上传的两张参考图，生成一张独立的 3x3 多机位参考图" in str(call["card_prompt"]) for call in scene_card_calls)
    assert all("禁止出现俯视图、说明卡、十格布局、海报拼贴" in str(call["card_prompt"]) for call in scene_card_calls)


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


def test_scene_analyst_falls_back_to_text_agent_when_vision_fails(monkeypatch):
    calls: list[dict[str, object]] = []

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
        calls.append(
            {
                "agent_name": kwargs.get("agent_name"),
                "images_base64": kwargs.get("images_base64"),
                "user_prompt": user_prompt,
            }
        )
        if kwargs.get("agent_name") == "scene_vision_analyst":
            raise RuntimeError("vision gateway disconnected")
        return "scene_info: text fallback scene card"

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)
    monkeypatch.setattr(
        pci,
        "_generate_scene_card_with_overhead",
        lambda overhead_prompt, card_prompt, scene_image, session_id, scene_number: (
            "data:image/png;base64,iVBORw0KGgo=",
            rf"D:\tmp\scene_layout_{scene_number:02d}.png",
        ),
    )
    monkeypatch.setattr(pci, "_save_scene_card_image", lambda data, session_id, scene_number=1: rf"D:\tmp\scene_grid_{scene_number:02d}.png")
    monkeypatch.setattr(
        pci,
        "_append_scene_card_references",
        lambda state, scene_cards: (
            list(state.get("reference_image_b64s") or []) + ["data:image/png;base64,iVBORw0KGgo=" for _ in scene_cards],
            list(state.get("reference_image_manifest") or []) + [{"purpose": "scene_card", "type": "scene_card"} for _ in scene_cards],
        ),
    )

    state = {
        "script": "test script",
        "aspect_ratio": "9:16",
        "reference_image_b64s": ["image-a"],
        "reference_image_manifest": [{"label": "scene", "purpose": "scene space"}],
        "reference_images": "",
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    result = pci.scene_analyst_node(state)

    assert [call["agent_name"] for call in calls] == ["scene_vision_analyst", "scene_analyst"]
    assert calls[0]["images_base64"] == ["image-a"]
    assert calls[1]["images_base64"] is None
    assert "参考图网关连接失败" in str(calls[1]["user_prompt"])
    assert "text fallback scene card" in result["agent_outputs"]["scene_analyst"]


def test_scene_analyst_uses_local_scene_card_when_vision_and_text_fail(monkeypatch):
    calls: list[str] = []

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
        calls.append(str(kwargs.get("agent_name")))
        raise RuntimeError("gateway disconnected")

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)
    monkeypatch.setattr(
        pci,
        "_generate_scene_card_with_overhead",
        lambda overhead_prompt, card_prompt, scene_image, session_id, scene_number: (
            "data:image/png;base64,iVBORw0KGgo=",
            rf"D:\tmp\scene_layout_{scene_number:02d}.png",
        ),
    )
    monkeypatch.setattr(pci, "_save_scene_card_image", lambda data, session_id, scene_number=1: rf"D:\tmp\scene_grid_{scene_number:02d}.png")
    monkeypatch.setattr(
        pci,
        "_append_scene_card_references",
        lambda state, scene_cards: (
            list(state.get("reference_image_b64s") or []) + ["data:image/png;base64,iVBORw0KGgo=" for _ in scene_cards],
            list(state.get("reference_image_manifest") or []) + [{"purpose": "scene_card", "type": "scene_card"} for _ in scene_cards],
        ),
    )

    state = {
        "script": "test script",
        "aspect_ratio": "9:16",
        "reference_image_b64s": ["image-a"],
        "reference_image_manifest": [{"label": "scene", "purpose": "scene space"}],
        "reference_images": "",
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    result = pci.scene_analyst_node(state)

    assert calls == ["scene_vision_analyst", "scene_analyst"]
    assert "degraded_local_scene_card" in result["agent_outputs"]["scene_analyst"]
    assert "Do not invent visual details" in result["scene_context_brief"]


def test_director_showrunner_obeys_scene_standing_constraints(monkeypatch):
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
        captured["user_prompt"] = user_prompt
        return (
            "增强版剧本: |\n"
            "  商北琛从门口走进大堂。\n"
            "增强依据: []\n"
            "主线保护: []\n"
            "节奏总控交接: 无\n"
            "需用户确认: 无\n"
        )

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    state = {
        "script": "商北琛从门口走进大堂。",
        "aspect_ratio": "9:16",
        "scene_context_brief": (
            "场景信息: 大堂北侧为入口，核心通道通向大厅中心。\n"
            "人物站位: 商北琛从北侧入口进入，面向大堂中心。\n"
            "场景参考图需求: 生成俯视布局图和 3x3 九宫格机位图，这段不应交给剧情增强。\n"
            "光线与材质: 大面积玻璃幕墙，冷色光线，这段不应交给剧情增强。\n"
            "固定物体锁定: 入口和主通道不能移动。\n"
        ),
        "agent_outputs": {},
        "knowledge_metadata": {},
        "speed_mode": False,
    }

    result = pci.director_showrunner_node(state)

    assert captured["agent_name"] == "director_showrunner"
    assert "场景信息: 大堂北侧为入口" in str(captured["user_prompt"])
    assert "商北琛从北侧入口进入" not in str(captured["user_prompt"])
    assert "人物站位:" not in str(captured["user_prompt"])
    assert "入口和主通道不能移动" in str(captured["user_prompt"])
    assert "只遵守上方简表里的物理空间硬约束" in str(captured["user_prompt"])
    assert "不要推导或锁定人物站位、行动路径、运动轨迹" in str(captured["user_prompt"])
    assert "靠近、停下、退开、挡住、绕开、转身看向" in str(captured["user_prompt"])
    assert "不写“左侧/右侧/北侧/几米/从A点到B点”等精确调度" in str(captured["user_prompt"])
    assert "3x3 九宫格机位图" not in str(captured["user_prompt"])
    assert "光线与材质" not in str(captured["user_prompt"])
    assert result["step"] == "step_0_rhythm"


def test_compact_scene_context_for_showrunner_keeps_only_short_hard_constraints():
    compact = pci._compact_scene_context_for_showrunner(
        """scene_id: test_scene
场景信息: 客厅入口在西侧，沙发在东侧，电视墙在南侧。
人物站位:
  - 乔熙从入口走向沙发旁。
  - 小豆丁停在茶几附近。
道具锚点: 茶几在沙发前方。
光线与材质: 午后自然光，大量软装细节。
场景参考图需求: 输出俯视布局图和 3x3 九宫格机位图。
固定物体锁定: 沙发、茶几、电视墙不可移动。
增强约束: 剧情增强不得改入口和沙发相对位置。"""
    )

    assert "场景信息: 客厅入口在西侧" in compact
    assert "乔熙从入口走向沙发旁" not in compact
    assert "人物站位" not in compact
    assert "道具锚点: 茶几在沙发前方" in compact
    assert "固定物体锁定: 沙发、茶几、电视墙不可移动" in compact
    assert "增强约束: 剧情增强不得改入口和沙发相对位置" in compact
    assert "光线与材质" not in compact
    assert "场景参考图需求" not in compact
    assert "3x3 九宫格" not in compact
    assert len(compact) < 700


def test_scene_card_spatial_summary_strips_position_marker_sections():
    summary = pci._scene_card_spatial_summary(
        """本场景在场人物: 女主、孩子
人物站位:
  - 女主根据剧本动作站在入口旁
人物占位:
  - 女主在沙发旁
站位姿势:
  - 两人相邻
场景信息: 客厅，沙发在电视墙对侧，入口在左侧。
道具锚点: 茶几在沙发前方。
固定物体锁定: 沙发、茶几、电视墙不可移动。"""
    )

    assert "人物站位" not in summary
    assert "人物占位" not in summary
    assert "站位姿势" not in summary
    assert "女主" not in summary
    assert "场景信息" in summary
    assert "固定物体锁定" in summary


def test_scene_card_image_api_generates_standalone_grid(monkeypatch):
    calls: list[str] = []

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        calls.append(user_prompt)
        assert kwargs["agent_name"] == "scene_card_designer"
        assert kwargs["images_base64"] == ["scene-image"]
        assert "多机位场景参考图生成模型" in system_prompt
        assert "严格按用户提示生成一张独立 3x3 九宫格图" in system_prompt
        assert "输入图片顺序固定：参考图1为原始场景图，参考图2为俯视布局图" in system_prompt
        assert "不得复制、裁切、拼贴或直接画入任何参考图" in system_prompt
        assert "不得输出俯视图、十格布局、说明卡或海报拼贴" in system_prompt
        assert "只输出同一空间的九个透视机位空景" in system_prompt
        assert "必须依据参考图2反推相机位置" in system_prompt
        assert "斜向中景" not in system_prompt
        assert "空间纵深景" not in system_prompt
        assert "顶面灯光" not in system_prompt
        assert "反打关系" not in system_prompt
        assert "对向回看" not in system_prompt
        assert "base prompt" == user_prompt
        return "data:image/png;base64,single"

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci._call_scene_card_image_api("base prompt", ["scene-image"])

    assert result == "data:image/png;base64,single"
    assert len(calls) == 1


def test_scene_card_generation_uses_saved_overhead_as_second_reference(monkeypatch):
    captured: dict[str, object] = {}

    def fake_overhead_api(prompt, images_base64):
        captured["overhead_prompt"] = prompt
        captured["overhead_images"] = images_base64
        return "data:image/png;base64,layout"

    def fake_save_layout(data, session_id, scene_number):
        captured["saved_layout_data"] = data
        captured["saved_layout_session"] = session_id
        captured["saved_layout_scene"] = scene_number
        return rf"D:\tmp\scene_layout_{scene_number:02d}.png"

    def fake_file_to_data_uri(path):
        captured["layout_path_for_reference"] = path
        return "data:image/png;base64,saved-layout"

    def fake_card_api(prompt, images_base64):
        captured["card_prompt"] = prompt
        captured["card_images"] = images_base64
        return "data:image/png;base64,card"

    monkeypatch.setattr(pci, "_call_scene_card_overhead_api", fake_overhead_api)
    monkeypatch.setattr(pci, "_save_scene_card_layout_image", fake_save_layout)
    monkeypatch.setattr(pci, "_file_to_image_data_uri", fake_file_to_data_uri)
    monkeypatch.setattr(pci, "_call_scene_card_image_api", fake_card_api)

    card_result, layout_path = pci._generate_scene_card_with_overhead(
        "layout prompt",
        "card prompt",
        "scene-image",
        "session-x",
        3,
    )

    assert card_result == "data:image/png;base64,card"
    assert layout_path == r"D:\tmp\scene_layout_03.png"
    assert captured["overhead_images"] == ["scene-image"]
    assert captured["saved_layout_data"] == "data:image/png;base64,layout"
    assert captured["saved_layout_session"] == "session-x"
    assert captured["saved_layout_scene"] == 3
    assert captured["layout_path_for_reference"] == r"D:\tmp\scene_layout_03.png"
    assert captured["card_images"] == ["scene-image", "data:image/png;base64,saved-layout"]


def test_scene_card_overhead_api_reuses_scene_card_designer_config(monkeypatch):
    captured: dict[str, object] = {}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["agent_name"] = kwargs.get("agent_name")
        captured["images_base64"] = kwargs.get("images_base64")
        return "data:image/png;base64,layout"

    monkeypatch.setattr(pci, "call_llm", fake_call_llm)

    result = pci._call_scene_card_overhead_api("layout prompt", ["scene-image"])

    assert result == "data:image/png;base64,layout"
    assert captured["agent_name"] == "scene_card_designer"
    assert captured["images_base64"] == ["scene-image"]
    assert "只生成一张独立俯视图" in str(captured["system_prompt"])


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
    assert "人物" in ui_app._infer_reference_purpose(3, "商北琛.png")


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


def test_scene_reference_items_prefer_scene_filenames_over_stale_scene_metadata():
    state = {
        "reference_image_b64s": ["yanfei", "qiaoxi", "shangbeichen", "living-room", "gate"],
        "reference_image_manifest": [
            {"filename": "严飞.png", "purpose": "主角人物"},
            {"filename": "乔熙.png", "purpose": "对手角色"},
            {"filename": "商北琛.png", "purpose": "场景空间、轴线、光线与首帧环境基底锁定"},
            {"filename": "乔熙公寓-客厅.png", "purpose": "场景空间"},
            {"filename": "集团门口.png", "purpose": "补充参考图"},
        ],
    }

    items = pci._scene_reference_items(state)

    assert [item["image"] for item in items] == ["living-room", "gate"]
