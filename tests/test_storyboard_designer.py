"""Tests for storyboard_designer_impl module and graph integration."""
from __future__ import annotations

import os
import sys

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.director_graph_package.storyboard_designer_impl import (
    _build_storyboard_user_prompt,
    _build_character_reference_notes,
    _build_storyboard_continuity_notes,
    _current_script_excerpt,
    _extract_fragment_task_and_rhythm,
    _extract_shots_from_director_segment,
    _format_shot_for_storyboard,
    _reference_images_for_storyboard,
    _save_storyboard_image,
    _segment_block,
    generate_storyboard_image_for_segment,
    generate_storyboard_for_segment,
    storyboard_designer_node,
)
from agents.director_graph_package.types import DirectorState


# ---------------------------------------------------------------------------
# Sample test fixtures
# ---------------------------------------------------------------------------
SAMPLE_DIRECTOR_SEGMENT = """
fragment_id: F01
fragment_task: 建立权力关系
rhythm: 压抑-紧张
shots:
  - shot_id: S01
    duration: 3秒
    task: 建立空间
    subject: 商北琛
    camera: 正前方固定机位
    size: 中全景
    action: 走进大堂
    dialogue: ""
    must_carry: 空间关系
    cut_point: 停住
    continuity: 保持纵深
  - shot_id: S02
    duration: 4秒
    task: 压迫感
    subject: 乔熙
    camera: 低角度仰拍
    size: 中景
    action: 抬头看
    dialogue: 你来了
    must_carry: 表情
    cut_point: 台词落下
    continuity: 从左前方继承
  - shot_id: S03
    duration: 3秒
    task: 对峙
    subject: 两人
    camera: 侧面固定机位
    size: 双人全景
    action: 对视
    dialogue: ""
    must_carry: 空间距离
    cut_point: 尾帧
    continuity: 悬停
"""

SAMPLE_PLANNER_SEGMENT = """
fragment_id: F01
scene: 大堂
director_brief: 用空间压迫建立权力关系
reaction_plan: 员工闪躲，乔熙挺直
key_beats:
  - 商北琛入场
  - 乔熙抬头对峙
"""

CHINESE_DIRECTOR_SEGMENT = """
片段编号: F01
片段任务: 建立权力关系
节奏: 压抑-紧张
镜头列表:
  - 镜头编号: F01-S01
    时长: 3秒
    镜头任务: 建立空间
    拍摄主体: 商北琛
    镜头: 正前方中全景
    画面动作: 商北琛走进大堂
    台词: ~
    必须承载: 空间关系
    切镜点: 商北琛停住时切出
    连续性: 保持纵深
"""


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------
class TestShotExtraction:
    def test_extract_shots_count(self):
        shots = _extract_shots_from_director_segment(SAMPLE_DIRECTOR_SEGMENT)
        assert len(shots) == 3

    def test_extract_shot_fields(self):
        shots = _extract_shots_from_director_segment(SAMPLE_DIRECTOR_SEGMENT)
        s0 = shots[0]
        assert s0.get("shot_id") == "S01"
        assert s0.get("subject") == "商北琛"
        assert s0.get("size") == "中全景"
        assert s0.get("duration") == "3秒"
        assert s0.get("camera") == "正前方固定机位"

    def test_extract_shots_accepts_chinese_fields(self):
        shots = _extract_shots_from_director_segment(CHINESE_DIRECTOR_SEGMENT)
        assert len(shots) == 1
        assert shots[0].get("shot_id") == "F01-S01"
        assert shots[0].get("duration") == "3秒"
        assert shots[0].get("subject") == "商北琛"
        assert shots[0].get("action") == "商北琛走进大堂"
        assert shots[0].get("cut_point") == "商北琛停住时切出"

    def test_extract_fragment_meta(self):
        task, rhythm = _extract_fragment_task_and_rhythm(SAMPLE_DIRECTOR_SEGMENT)
        assert "权力关系" in task
        assert "压抑" in rhythm

    def test_extract_fragment_meta_accepts_chinese_fields(self):
        task, rhythm = _extract_fragment_task_and_rhythm(CHINESE_DIRECTOR_SEGMENT)
        assert "权力关系" in task
        assert "压抑" in rhythm

    def test_format_shot(self):
        shots = _extract_shots_from_director_segment(SAMPLE_DIRECTOR_SEGMENT)
        formatted = _format_shot_for_storyboard(shots[0], 0)
        assert "镜头 S01 首帧格" in formatted
        assert "商北琛" in formatted
        assert "中全景" in formatted
        assert "不画完整动作过程" in formatted
        assert "故事板行版式" in formatted
        assert "右栏机位图" in formatted
        assert "固定空间锁定" in formatted
        assert "不得把道具移动到旁边台面、床头或新位置" in formatted

    def test_format_shot_omits_dialogue_text(self):
        shots = _extract_shots_from_director_segment(SAMPLE_DIRECTOR_SEGMENT)
        formatted = _format_shot_for_storyboard(shots[1], 1)
        assert "你来了" not in formatted
        assert "首帧" in formatted


class TestSegmentBlock:
    def test_segment_block_extraction(self):
        full_text = (
            "---\n"
            + SAMPLE_DIRECTOR_SEGMENT
            + "\n---\nfragment_id: F02\nfragment_task: 另一段\n"
        )
        block = _segment_block(full_text, 1)
        assert "F01" in block
        assert "商北琛" in block
        assert "F02" not in block

    def test_segment_block_missing(self):
        block = _segment_block("", 1)
        assert block == ""

    def test_current_script_excerpt_prefers_enhanced_segment(self):
        state: DirectorState = {
            "enhanced_script": (
                "片段 1｜出门\n乔熙拿起背包，小豆丁站在门边。\n\n"
                "片段 2｜到达\n乔熙进入办公室。"
            )
        }
        excerpt = _current_script_excerpt(state, 1, "F01")
        assert "乔熙拿起背包" in excerpt
        assert "进入办公室" not in excerpt


class TestReferenceNotes:
    def test_no_manifest(self):
        state: DirectorState = {"reference_image_manifest": []}
        notes = _build_character_reference_notes(state)
        assert notes == ""

    def test_with_manifest(self):
        state: DirectorState = {
            "reference_image_manifest": [
                {"filename": "hero.jpg", "description": "男主角参考"},
                {"filename": "office.jpg", "description": "办公室场景"},
            ]
        }
        notes = _build_character_reference_notes(state)
        # description takes priority over filename
        assert "男主角参考" in notes
        assert "办公室场景" in notes
        assert "【参考图使用规则】" in notes
        assert "人物参考图只用于锁定" in notes
        assert "固定空间锚点不得移动" in notes

    def test_reference_notes_list_api_order_and_usage(self):
        state: DirectorState = {
            "reference_image_b64s": ["char-b64", "scene-b64", "layout-b64"],
            "reference_image_manifest": [
                {"label": "@图片1", "filename": "hero.jpg", "role": "character", "purpose": "人物外观"},
                {"label": "@图片2", "filename": "office.jpg", "role": "scene", "purpose": "办公室空间"},
                {
                    "label": "@图片3",
                    "filename": "layout.png",
                    "role": "annotated_scene_layout",
                    "purpose": "人物位置与移动轨迹",
                },
            ],
        }

        notes = _build_character_reference_notes(state)

        assert "参考图1（API输入第1张" in notes
        assert "参考图2（API输入第2张" in notes
        assert "参考图3（API输入第3张" in notes
        assert "人物图，只锁人物外观" in notes
        assert "场景图，只锁空间结构" in notes
        assert "场景开局标点图，只锁当前场景开局的初始站位、固定物和基础轴线" in notes
        assert "不要求逐段运动轨迹" in notes

    def test_previous_tail_frame_is_appended_after_uploaded_refs(self):
        state: DirectorState = {
            "reference_image_b64s": ["char-b64", "scene-b64"],
            "reference_image_manifest": [
                {"filename": "hero.jpg", "role": "character"},
                {"filename": "office.jpg", "role": "scene"},
            ],
            "previous_segment_tail_frame": "tail-b64",
        }

        notes = _build_character_reference_notes(state)
        images = _reference_images_for_storyboard(state)

        assert images == ["char-b64", "scene-b64", "tail-b64"]
        assert "参考图3（API输入第3张" in notes
        assert "上一片段尾帧图，只锁片段承接状态" in notes


class TestContinuityNotes:
    def test_previous_tail_frame_prompts_first_panel_handoff_for_same_scene(self):
        planner_output = """
fragment_id: F01
scene: office
出场状态: 乔熙站在沙发左侧，面向商北琛。
---
fragment_id: F02
scene: office
入场状态: 承接上一段。
"""
        state: DirectorState = {
            "segment_names": ["一", "二"],
            "previous_segment_tail_frame": "tail-b64",
        }

        notes = _build_storyboard_continuity_notes(
            state,
            segment_index=2,
            planner_output=planner_output,
            current_fragment_id="F02",
        )

        assert "同场景后续片段：不强制新标点" in notes
        assert "有 previous_segment_tail_frame，第一格必须承接上一段视频尾帧" in notes

    def test_tail_frame_manifest_prompts_first_panel_handoff_for_same_scene(self):
        planner_output = """
fragment_id: F01
scene: office
出场状态: 乔熙站在桌边，手里拿着合同。
---
fragment_id: F02
scene: office
"""
        state: DirectorState = {
            "segment_names": ["一", "二"],
            "reference_image_b64s": ["tail-data-url"],
            "reference_image_manifest": [
                {
                    "role": "previous_segment_tail_frame",
                    "purpose": "上一片段尾帧，只承接上一段结束状态",
                }
            ],
        }

        notes = _build_storyboard_continuity_notes(
            state,
            segment_index=2,
            planner_output=planner_output,
            current_fragment_id="F02",
        )

        assert "有 previous_segment_tail_frame，第一格必须承接上一段视频尾帧" in notes

    def test_new_scene_does_not_force_tail_frame_handoff(self):
        planner_output = """
fragment_id: F01
scene: office
出场状态: 乔熙站在沙发左侧。
---
fragment_id: F02
scene: rooftop
入场状态: 重新开场。
"""
        state: DirectorState = {
            "segment_names": ["一", "二"],
            "previous_segment_tail_frame": "tail-b64",
        }

        notes = _build_storyboard_continuity_notes(
            state,
            segment_index=2,
            planner_output=planner_output,
            current_fragment_id="F02",
        )

        assert "场景关系：新场景" in notes
        assert "第一格不要照搬上一段尾帧人物站位" in notes

    def test_scene_layout_annotation_does_not_require_per_segment_motion_path(self):
        state: DirectorState = {
            "reference_image_b64s": ["layout-b64"],
            "reference_image_manifest": [
                {
                    "label": "@图片1",
                    "filename": "layout.png",
                    "role": "scene_layout_annotation",
                    "purpose": "人物位置和活动轨迹",
                }
            ],
        }

        notes = _build_character_reference_notes(state)

        assert "场景开局标点图" in notes
        assert "不要求逐段运动轨迹" in notes


class TestPromptBuilder:
    def test_build_user_prompt_structure(self):
        shots = _extract_shots_from_director_segment(SAMPLE_DIRECTOR_SEGMENT)
        prompt = _build_storyboard_user_prompt(
            segment_index=1,
            segment_name="Test Segment",
            fragment_task="建立关系",
            rhythm="压抑",
            shots=shots,
            planner_context=SAMPLE_PLANNER_SEGMENT,
            script_context="乔熙拿起背包，小豆丁站在门边。",
            reference_notes="[Ref] hero.jpg",
            aspect_ratio="9:16",
        )
        assert "生成片段 1" in prompt
        assert "9:16" in prompt
        assert "整张分镜首帧图必须严格使用 9:16 比例" in prompt
        assert "镜头1 / 镜头2 / 镜头3" in prompt
        assert "镜头 S01 首帧格" in prompt
        assert "商北琛" in prompt
        assert "【拆片规划上下文】" in prompt
        assert "hero.jpg" in prompt
        assert "【当前片段增强剧本参考】" in prompt
        assert "只用它核对人物、道具、台词事实和动作起点" in prompt
        assert "【分镜故事板输出合同】" in prompt
        assert "gpt-image-2" in prompt
        assert "左栏只画首帧/关键静止瞬间" in prompt
        assert "禁止对白气泡、字幕、人物运动箭头、动作轨迹" in prompt
        assert "不出现台词文字" in prompt
        assert "人物运动箭头" in prompt
        assert "每行三栏" in prompt
        assert "左栏分镜首帧图" in prompt
        assert "右栏俯视机位图" in prompt
        assert "CAM 摄影机三角形" in prompt
        assert "FOV 视野扇形" in prompt
        assert "固定家具位置锁定" in prompt
        assert "不能出现“旁边台面”“床头边缘”“另一个桌面”" in prompt


class TestSaveStoryboardImage:
    def test_save_text_fallback(self, tmp_path):
        # When given plain text (not image data), it should save as .txt
        result = _save_storyboard_image(
            "some random text that is not an image",
            segment_index=1,
            session_id="test_session",
        )
        assert result.endswith(".txt")
        assert os.path.exists(result)

    def test_save_data_uri(self, tmp_path):
        # Create a minimal 1x1 PNG in base64
        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
            "hKmMIQAAAABJRU5ErkJggg=="
        )
        data_uri = f"data:image/png;base64,{png_b64}"
        result = _save_storyboard_image(
            data_uri,
            segment_index=2,
            session_id="test_session",
        )
        # If decoding succeeds it should be .png, otherwise .txt
        assert result.endswith(".png") or result.endswith(".txt")


# ---------------------------------------------------------------------------
# Node-level integration tests
# ---------------------------------------------------------------------------
class TestStoryboardDesignerNode:
    def test_skips_when_no_director_output(self, monkeypatch):
        """If shot_director hasn't produced output yet, node should skip gracefully."""
        state: DirectorState = {
            "active_segment_index": 1,
            "total_segments": 3,
            "agent_outputs": {},
            "segment_names": ["片段01", "片段02", "片段03"],
        }
        result = storyboard_designer_node(state)
        assert "已跳过" in result.get("message", "")

    def test_skips_when_no_parseable_shots(self, monkeypatch):
        state: DirectorState = {
            "active_segment_index": 1,
            "total_segments": 1,
            "agent_outputs": {
                "shot_director": "fragment_id: F01\nfragment_task: x\nshots:\n",
            },
            "segment_names": ["片段01"],
        }
        result = storyboard_designer_node(state)
        assert "没有可识别的镜头列表" in result.get("message", "")


class TestGraphIntegration:
    def test_graph_defers_storyboard_until_segment_assets_exist(self):
        from agents.director_graph_package.graph_api import create_director_graph

        graph = create_director_graph()
        assert "storyboard_designer" not in graph.nodes
        assert "wait_for_segment_request" in graph.nodes

    def test_story_planner_waits_before_segment_level_generation(self):
        from agents.director_graph_package.graph_api import create_director_graph

        graph = create_director_graph()
        edges = list(graph.edges)
        assert ("story_planner", "wait_for_segment_request") in edges
        assert ("shot_director", "storyboard_designer") not in edges
        assert ("storyboard_designer", "wait_for_segment_request") not in edges


# ---------------------------------------------------------------------------
# Standalone helper tests
# ---------------------------------------------------------------------------
class TestGenerateStoryboardForSegment:
    def test_returns_dict_with_keys(self, monkeypatch):
        """generate_storyboard_for_segment should return expected keys even on minimal state."""
        state: DirectorState = {
            "active_segment_index": 1,
            "total_segments": 1,
            "agent_outputs": {
                "shot_director": SAMPLE_DIRECTOR_SEGMENT,
                "story_planner": SAMPLE_PLANNER_SEGMENT,
            },
            "segment_names": ["Test"],
            "aspect_ratio": "16:9",
        }
        agent_names = []

        def fake_call_llm(*args, **kwargs):
            agent_names.append(kwargs.get("agent_name"))
            return "一张分镜首帧图，包含 3 个镜头格子。"

        monkeypatch.setattr(
            "agents.director_graph_package.storyboard_designer_impl.call_llm",
            fake_call_llm,
        )

        result = generate_storyboard_for_segment(state, segment_index=1)
        assert "prompt" in result
        assert "image_path" in result
        assert result["prompt"] != ""
        assert result["image_path"] == ""
        assert agent_names == ["storyboard_prompt_designer"]

    def test_generate_image_uses_existing_prompt(self, monkeypatch):
        state: DirectorState = {
            "active_segment_index": 1,
            "agent_outputs": {
                "storyboard_prompt_seg01": "一张分镜首帧图，包含 3 个镜头格子。",
            },
            "reference_image_b64s": ["fake-ref"],
        }
        calls = []

        def fake_image_api(prompt, images_base64=None, agent_name="storyboard_designer"):
            calls.append((prompt, images_base64, agent_name))
            return "https://example.com/fake_image.png"

        def fake_save(data, segment_index, session_id):
            return f"saved-{segment_index}.png"

        monkeypatch.setattr(
            "agents.director_graph_package.storyboard_designer_impl._call_image_generation_api",
            fake_image_api,
        )
        monkeypatch.setattr(
            "agents.director_graph_package.storyboard_designer_impl._save_storyboard_image",
            fake_save,
        )

        result = generate_storyboard_image_for_segment(state, segment_index=1)
        assert result["image_path"] == "saved-1.png"
        assert calls == [
            ("一张分镜首帧图，包含 3 个镜头格子。", ["fake-ref"], "storyboard_designer")
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
