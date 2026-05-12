from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
import agents.director_graph_package.prompt_compiler_impl as prompt_compiler_impl


def _patch_fast_prompt_builder(monkeypatch):
    def fake_build_system_prompt(base_system, agent_name, context_hint=""):
        return base_system, {
            "retrieval_mode": "stub",
            "matched_sources": [f"{agent_name}.stub.md"],
            "context_hint": context_hint,
        }

    monkeypatch.setattr(prompt_compiler_impl, "build_system_prompt", fake_build_system_prompt)


def test_scene_memory_card_keeps_spatial_facts_and_drops_appearance_noise():
    scene_output = "\n".join(
        [
            "外貌细节：GLOBAL_APPEARANCE_SHOULD_DROP，黑色西装、发型、五官。",
            "空间轴线：CURRENT_SCENE_SPATIAL_MARKER，大堂中轴直通纵深处电梯门。",
            "站位关系：商北琛位于中轴前段，面朝电梯方向。",
            "光线基底：冷白商务顶光稳定。",
        ]
    )

    card = dg._scene_memory_card(scene_output, 500)

    assert "CURRENT_SCENE_SPATIAL_MARKER" in card
    assert "站位关系" in card
    assert "GLOBAL_APPEARANCE_SHOULD_DROP" not in card


def test_prompt_compiler_uses_current_fragment_compressed_context(monkeypatch):
    captured: dict[str, object] = {}

    def fake_call_llm_with_mcp(system_prompt, user_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["images_base64"] = kwargs.get("images_base64")
        captured["agent_name"] = kwargs.get("agent_name")
        return (
            "片段1｜测试场景｜动作承接｜~8秒\n\n"
            "【风格锚点】\n现代都市写实，冷静克制。\n\n"
            "【画幅锚点】\n9:16竖屏。\n\n"
            "【空间与首帧总控】\n商北琛位于电梯轿厢内，面朝门口，电梯门框位于左右侧边缘。\n\n"
            "【时间轴】\n\n"
            "0-8秒：商北琛半身中景，摄影机位于人物正前方0度，眼平高度固定机位，商北琛保持站姿。\n\n"
            "【约束】\n主体锁定商北琛，空间锁定电梯内外轴线。\n\n"
            "片段1 prompt 已输出。\n"
            "请生成视频后，上传：\n\n"
            "片段1的尾帧截图\n"
            "当前人物位置关系（若有变化）\n\n"
            "我将基于实际尾帧继续输出片段2。"
        )

    def fake_persist_update(state, update):
        merged = dict(state)
        merged.update(update)
        return merged

    monkeypatch.setattr(prompt_compiler_impl, "call_llm_with_mcp", fake_call_llm_with_mcp)
    monkeypatch.setattr(prompt_compiler_impl, "_persist_update", fake_persist_update)
    _patch_fast_prompt_builder(monkeypatch)

    state = {
        "script": (
            "GLOBAL_SCRIPT_SHOULD_NOT_REACH_COMPILER\n"
            "CURRENT_EVENT_MARKER：商北琛进入电梯。\n"
            "OTHER_EVENT_SHOULD_NOT_REACH_COMPILER：乔熙冲入电梯。"
        ),
        "aspect_ratio": "9:16",
        "current_segment_index": 1,
        "total_segments": 2,
        "tail_frame_analysis": "TAIL_STATE_MARKER：上一段最终人物站在电梯内，面朝门外。",
        "reference_image_b64s": ["image-a"],
        "agent_outputs": {
            "scene_analyst": (
                "外貌细节：SCENE_APPEARANCE_SHOULD_DROP，五官、发型、服装。\n"
                "空间轴线：CURRENT_SCENE_SPATIAL_MARKER，电梯位于大堂纵深尽头。"
            ),
            "story_planner": (
                "- fragment_id: F01\n"
                "  duration_target: \"8秒\"\n"
                "  dramatic_unit: \"电梯收束\"\n"
                "  source_script_events:\n"
                "    - \"CURRENT_EVENT_MARKER：商北琛进入电梯。\"\n"
                "  cast:\n"
                "    active:\n"
                "      - 商北琛\n"
                "  continuity:\n"
                "    entry: \"商北琛位于电梯门外。\"\n"
                "    exit: \"商北琛位于电梯内。\"\n"
                "- fragment_id: F02\n"
                "  dramatic_unit: \"GLOBAL_PLANNER_SHOULD_NOT_REACH_COMPILER\"\n"
                "  source_script_events:\n"
                "    - \"OTHER_EVENT_SHOULD_NOT_REACH_COMPILER：乔熙冲入电梯。\"\n"
            ),
            "shot_director": (
                "- fragment_id: F01\n"
                "  fragment_task: \"CURRENT_DIRECTOR_MARKER\"\n"
                "  rhythm: \"稳住电梯内站位\"\n"
                "  shots:\n"
                "    - shot_id: \"F01-S01\"\n"
                "      duration: \"0-8秒\"\n"
                "      task: \"确认商北琛已经进入电梯\"\n"
                "      subject: \"商北琛\"\n"
                "      shot: \"正面半身中景\"\n"
                "      action: \"商北琛站在电梯轿厢内，面朝门口保持站姿。\"\n"
                "      dialogue: \"none\"\n"
                "      must_carry: \"商北琛已在电梯内，电梯门框位于左右侧边缘。\"\n"
                "      cut_point: \"站位稳定、尾帧状态清楚后切。\"\n"
                "      continuity: \"商北琛仍在电梯内，面朝门口，电梯内外轴线保持清楚。\"\n"
                "- fragment_id: F02\n"
                "  fragment_task: \"GLOBAL_DIRECTOR_SHOULD_NOT_REACH_COMPILER\"\n"
            ),
        },
        "knowledge_metadata": {},
    }

    result = dg.prompt_compiler_node(state)

    prompt = str(captured["user_prompt"])
    assert captured["agent_name"] == "prompt_compiler"
    assert captured["images_base64"] is None
    assert "CURRENT_EVENT_MARKER" in prompt
    assert "CURRENT_DIRECTOR_MARKER" in prompt
    assert "CURRENT_SCENE_SPATIAL_MARKER" in prompt
    assert "TAIL_STATE_MARKER" in prompt
    assert "GLOBAL_SCRIPT_SHOULD_NOT_REACH_COMPILER" not in prompt
    assert "GLOBAL_PLANNER_SHOULD_NOT_REACH_COMPILER" not in prompt
    assert "GLOBAL_DIRECTOR_SHOULD_NOT_REACH_COMPILER" not in prompt
    assert "OTHER_EVENT_SHOULD_NOT_REACH_COMPILER" not in prompt
    assert "SCENE_APPEARANCE_SHOULD_DROP" not in prompt
    assert result["agent_outputs"]["compiled_segment_1"].startswith("片段1｜测试场景")
