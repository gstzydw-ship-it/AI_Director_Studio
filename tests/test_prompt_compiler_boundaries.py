from __future__ import annotations

from pathlib import Path

import pytest

from agents.director_graph_package import nodes
from agents.director_graph_package import helpers
from agents.director_graph_package import legacy_impl
from agents.director_graph_package import prompt_compiler_impl
from agents.director_graph_package import state_store


def test_prompt_compiler_uses_package_state_store_helpers() -> None:
    assert prompt_compiler_impl._agent_outputs is state_store._agent_outputs
    assert prompt_compiler_impl._persist_update is state_store._persist_update


def test_prompt_compiler_has_no_director_graph_reverse_import() -> None:
    source = Path(prompt_compiler_impl.__file__).read_text(encoding="utf-8")
    assert "agents.director_graph" not in source


def test_prompt_compiler_owns_segment_block_extraction() -> None:
    assert prompt_compiler_impl._segment_block is not legacy_impl._segment_block

    text = (
        "fragment_id: F01\n"
        "fragment_task: first\n"
        "shots:\n"
        "  - shot_id: S01\n"
        "fragment_id: F02\n"
        "fragment_task: second\n"
    )

    block = prompt_compiler_impl._segment_block(text, 1)

    assert "fragment_id: F01" in block
    assert "fragment_task: first" in block
    assert "fragment_id: F02" not in block


def test_segment_block_can_use_actual_fragment_id() -> None:
    text = (
        "fragment_id: F05\n"
        "fragment_task: selected\n"
        "shots:\n"
        "  - shot_id: F05-S01\n"
        "fragment_id: F06\n"
        "fragment_task: next\n"
    )

    assert helpers._fragment_id_for_segment_index(["F05"], 1) == "F05"
    assert helpers._fragment_id_for_segment_index(["Test"], 1) == "F01"
    block = prompt_compiler_impl._segment_block(text, 1, "F05")

    assert "fragment_id: F05" in block
    assert "fragment_task: selected" in block
    assert "fragment_id: F06" not in block


def test_segment_block_accepts_chinese_shot_director_fields() -> None:
    text = (
        "- 片段编号: F01\n"
        "  片段任务: 第一段\n"
        "  镜头列表:\n"
        "    - 镜头编号: F01-S01\n"
        "- 片段编号: F02\n"
        "  片段任务: 第二段\n"
    )

    block = prompt_compiler_impl._segment_block(text, 1, "F01")

    assert "片段编号: F01" in block
    assert "片段任务: 第一段" in block
    assert "片段编号: F02" not in block


def test_normalise_compiled_prompt_limits_jimeng_submit_length() -> None:
    long_shot_lines = "\n".join(
        f"镜头{i}【3秒】【乔熙】中近景，同侧固定机位，乔熙右手从桌边拿起外套，左手按住手机，视线看向小豆丁，动作落点清楚。"
        for i in range(1, 35)
    )
    prompt = f"""片段1｜客厅｜赶时间+孩子抗拒｜~12秒

【风格锚点】
都市生活现实风，动作清楚。

【画幅锚点】
9:16竖屏。

【空间与首帧总控】
客厅沙发与茶几固定，晨光从窗边进入，乔熙和小豆丁在同一空间里。

【人物】
- 乔熙：年轻母亲，穿通勤外套，焦急但克制。
- 小豆丁：孩子，坐在沙发边缘，抗拒上学。

【镜头序列】
{long_shot_lines}

【约束】
严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌。人物、空间、道具和尾帧状态必须连续。

片段1 prompt 已输出。
请生成视频后，上传：

片段1的尾帧截图
当前人物位置关系（若有变化）
"""

    cleaned = prompt_compiler_impl._normalise_compiled_prompt(prompt, 1)

    assert len(cleaned) <= prompt_compiler_impl.JIMENG_PROMPT_CHAR_LIMIT
    assert "请生成视频后" not in cleaned
    assert "尾帧截图" not in cleaned
    assert "【镜头序列】" in cleaned
    assert "严禁出现任何文字" in cleaned



def test_prompt_compiler_uses_segment_names_for_non_f01_fragment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_system_prompt(base_system, _agent_name, context_hint="", **_kwargs):
        captured["context_hint"] = context_hint
        return base_system, {"retrieval_mode": "stub"}

    def fake_call_llm(system_prompt, user_prompt, images_base64=None, agent_name=""):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["images_base64"] = images_base64
        captured["agent_name"] = agent_name
        return "LLM compiled prompt for F05"

    monkeypatch.setattr(prompt_compiler_impl, "build_system_prompt", fake_build_system_prompt)
    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fake_call_llm)

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "segment_names": ["F05"],
        "script": "Alex opens the door.",
        "aspect_ratio": "16:9",
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F05\n"
                "  source_script_events:\n"
                "    - Alex opens the door.\n"
            ),
            "shot_director": (
                "- fragment_id: F05\n"
                "  fragment_task: opening beat\n"
                "  rhythm: readable action\n"
                "  shots:\n"
                "    - shot_id: F05-S01\n"
                "      duration: 0-3s\n"
                "      task: carry the opening beat\n"
                "      subject: Alex\n"
                "      shot: stable medium shot\n"
                "      action: Alex opens the door.\n"
                "      dialogue: \"\"\n"
                "      must_carry: Alex opens the door.\n"
                "      cut_point: after the door opens\n"
                "      continuity: keep screen direction\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)
    compiled = result["agent_outputs"]["compiled_segment_1"]

    assert compiled == "LLM compiled prompt for F05"
    assert captured["agent_name"] == "prompt_compiler"
    assert captured["images_base64"] is None
    assert "fragment_id: F05" in str(captured["user_prompt"])


def test_prompt_compiler_uses_llm_shot_director_handoff(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_call_llm(system_prompt, user_prompt, images_base64=None, agent_name=""):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["images_base64"] = images_base64
        captured["agent_name"] = agent_name
        return "LLM compiled prompt with Alex looks at Blair"

    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fake_call_llm)
    monkeypatch.setattr(
        prompt_compiler_impl,
        "_persist_update",
        lambda state, update: {**dict(state), **dict(update)},
    )

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 2,
        "segment_names": ["F01"],
        "script": "Alex: Stay here.\nBlair steps back.",
        "aspect_ratio": "9:16",
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Alex says stay here.\n"
                "    - Blair steps back.\n"
            ),
            "shot_director": (
                "- fragment_id: F01\n"
                "  fragment_task: pressure beat\n"
                "  rhythm: dialogue then reaction\n"
                "  shots:\n"
                "    - shot_id: F01-S01\n"
                "      duration: 0-3s\n"
                "      task: carry the command beat\n"
                "      subject: Alex\n"
                "      shot: stable medium shot\n"
                "      action: Alex looks at Blair and gives the order.\n"
                "      dialogue: Stay here.\n"
                "      must_carry: Alex gives the order.\n"
                "      cut_point: after the order lands\n"
                "      continuity: keep the same eyeline\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)
    outputs = result["agent_outputs"]

    assert outputs["compiled_segment_1"] == "LLM compiled prompt with Alex looks at Blair"
    assert "prompt_compiler_fallback_seg01" not in outputs
    assert captured["agent_name"] == "prompt_compiler"
    assert captured["images_base64"] is None
    assert "Alex looks at Blair" in str(captured["user_prompt"])
    assert result["step"] == "step_5_inspect"



def test_seedance_reference_prompt_block_labels_reference_roles() -> None:
    block = prompt_compiler_impl._seedance_reference_prompt_block(
        {
            "reference_image_manifest": [
                {"label": "@图片1", "filename": "hero.png", "role": "character", "purpose": "乔熙人物参考"},
                {"label": "@图片2", "filename": "car.jpg", "role": "scene", "purpose": "车后排场景"},
                {
                    "label": "@图片3",
                    "filename": "tail.jpg",
                    "role": "previous_segment_tail_frame",
                    "purpose": "上一段尾帧",
                },
            ]
        }
    )

    assert "@图片1 是人物参考图" in block
    assert "面部形象、发型、服装" in block
    assert "@图片2 是场景参考图" in block
    assert "空间结构、固定家具/道具、光线方向" in block
    assert "@图片3 是上一段实际尾帧/抽帧参考图" in block
    assert "本段首帧承接" in block


def test_seedance_reference_prompt_block_does_not_treat_scene_layout_as_tail_frame() -> None:
    block = prompt_compiler_impl._seedance_reference_prompt_block(
        {
            "reference_image_manifest": [
                {
                    "label": "@图片12",
                    "filename": "scene_layout_01.png",
                    "role": "scene_layout",
                    "type": "scene_layout",
                    "purpose": "集团门口场景俯视布局图；运动过程由片段出入场状态和视频尾帧承接",
                },
            ]
        }
    )

    assert "@图片12 是场景参考图" in block
    assert "上一段实际尾帧/抽帧参考图" not in block


def test_seedance_reference_prompt_block_filters_to_current_segment_context() -> None:
    state = {
        "reference_image_manifest": [
            {"label": "@图片1", "filename": "集团门口.png", "role": "scene", "purpose": "自动匹配场景参考图：集团门口"},
            {"label": "@图片2", "filename": "乔熙公寓-客厅.png", "role": "scene", "purpose": "自动匹配场景参考图：乔熙公寓-客厅"},
            {"label": "@图片3", "filename": "商北琛.png", "role": "character", "purpose": "商北琛人物参考"},
            {
                "label": "@图片4",
                "filename": "scene_layout_02.png",
                "role": "scene_layout",
                "type": "scene_layout",
                "name": "@图片2｜乔熙公寓-客厅.png｜自动匹配场景参考图：乔熙公寓-客厅",
                "purpose": "乔熙公寓-客厅场景俯视布局图；运动过程由片段出入场状态和视频尾帧承接",
            },
            {
                "label": "@图片5",
                "filename": "seg01_tail.jpg",
                "role": "previous_segment_tail_frame",
                "purpose": "上一段尾帧",
            },
        ]
    }

    block = prompt_compiler_impl._seedance_reference_prompt_block(
        state,
        segment_index=1,
        current_context="片段1｜乔熙公寓｜闹钟铃响。场景：乔熙公寓-客厅。主体：闹钟。",
    )

    assert "@图片2 是场景参考图" in block
    assert "@图片4 是场景参考图" in block
    assert "集团门口" not in block
    assert "商北琛" not in block
    assert "上一段实际尾帧/抽帧参考图" not in block


def test_prompt_compiler_propagates_llm_failure_with_valid_shot_director_input(monkeypatch) -> None:
    def fail_call_llm(*_args, **_kwargs):
        raise RuntimeError("LLM gateway failed")

    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fail_call_llm)

    with pytest.raises(RuntimeError, match="LLM gateway failed"):
        prompt_compiler_impl.prompt_compiler_node(
            {
                "active_segment_index": 1,
                "current_segment_index": 1,
                "total_segments": 1,
                "segment_names": ["F01"],
                "script": "Alex opens the door.",
                "aspect_ratio": "9:16",
                "agent_outputs": {
                    "story_planner": (
                        "- fragment_id: F01\n"
                        "  source_script_events:\n"
                        "    - Alex opens the door.\n"
                    ),
                    "shot_director": (
                        "- fragment_id: F01\n"
                        "  fragment_task: opening beat\n"
                        "  rhythm: readable action\n"
                        "  shots:\n"
                        "    - shot_id: F01-S01\n"
                        "      duration: 0-3s\n"
                        "      task: carry the opening beat\n"
                        "      subject: Alex\n"
                        "      shot: stable medium shot\n"
                        "      action: Alex opens the door.\n"
                        "      dialogue: \"\"\n"
                        "      must_carry: Alex opens the door.\n"
                        "      cut_point: after the door opens\n"
                        "      continuity: keep screen direction\n"
                    ),
                },
            }
        )


def test_prompt_compiler_rejects_legacy_local_shot_fallback_marker_before_llm(monkeypatch) -> None:
    called = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal called
        called = True
        raise RuntimeError("LLM gateway should not be called")

    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fail_if_called)
    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "segment_names": ["F01"],
        "script": "Alex opens the door. Blair steps back.",
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Alex opens the door.\n"
            ),
            "shot_director": (
                "- fragment_id: F01\n"
                "  schema_version: shot_director_local_fallback_v1\n"
                "  fragment_task: local fallback beat\n"
                "  rhythm: readable action\n"
                "  shots:\n"
                "    - shot_id: F01-S01\n"
                "      duration: 0-3s\n"
                "      task: carry the door beat\n"
                "      subject: Alex\n"
                "      shot: stable medium shot\n"
                "      action: Alex opens the door.\n"
                "      dialogue: \"\"\n"
                "      must_carry: Alex opens the door.\n"
                "      cut_point: after the door opens\n"
                "      continuity: keep screen direction\n"
            ),
        },
    }

    with pytest.raises(RuntimeError, match="上游三段式镜头导演输出来自本地兜底"):
        prompt_compiler_impl.prompt_compiler_node(state)
    assert called is False

def test_nodes_prompt_compiler_node_delegates_to_package_impl(monkeypatch) -> None:
    sentinel_state = {"step": "compile"}
    sentinel_result = {"step": "inspect"}

    def fake_prompt_compiler_node(state):
        assert state is sentinel_state
        return sentinel_result

    monkeypatch.setattr(
        nodes._prompt_compiler_impl,
        "prompt_compiler_node",
        fake_prompt_compiler_node,
    )

    assert nodes.prompt_compiler_node(sentinel_state) is sentinel_result
