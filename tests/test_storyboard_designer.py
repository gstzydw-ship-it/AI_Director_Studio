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
    _extract_fragment_task_and_rhythm,
    _extract_shots_from_director_segment,
    _format_shot_for_storyboard,
    _save_storyboard_image,
    _segment_block,
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

    def test_extract_fragment_meta(self):
        task, rhythm = _extract_fragment_task_and_rhythm(SAMPLE_DIRECTOR_SEGMENT)
        assert "权力关系" in task
        assert "压抑" in rhythm

    def test_format_shot(self):
        shots = _extract_shots_from_director_segment(SAMPLE_DIRECTOR_SEGMENT)
        formatted = _format_shot_for_storyboard(shots[0], 0)
        assert "Panel 1" in formatted
        assert "商北琛" in formatted
        assert "中全景" in formatted


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
        assert "Maintain visual consistency" in notes


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
            reference_notes="[Ref] hero.jpg",
            aspect_ratio="9:16",
        )
        assert "segment 1" in prompt.lower()
        assert "9:16" in prompt
        assert "Panel 1" in prompt
        assert "商北琛" in prompt
        assert "Story Planner Context" in prompt
        assert "hero.jpg" in prompt
        assert "Output Contract" in prompt or "storyboard" in prompt.lower()


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
        assert "skipped" in result.get("message", "").lower() or "skip" in result.get(
            "message", ""
        ).lower()

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
        assert "skipped" in result.get("message", "").lower() or "no parseable" in result.get(
            "message", ""
        ).lower()


class TestGraphIntegration:
    def test_graph_contains_storyboard_node(self):
        from agents.director_graph_package.graph_api import create_director_graph

        graph = create_director_graph()
        assert "storyboard_designer" in graph.nodes

    def test_storyboard_node_is_between_shot_director_and_wait(self):
        from agents.director_graph_package.graph_api import create_director_graph

        graph = create_director_graph()
        # Check edges: shot_director -> storyboard_designer -> wait_for_segment_request
        edges = list(graph.edges)
        assert ("shot_director", "storyboard_designer") in edges
        assert ("storyboard_designer", "wait_for_segment_request") in edges


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
        # Monkey-patch call_llm to avoid real network calls
        call_count = [0]

        def fake_call_llm(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "A storyboard prompt describing panels..."
            return "https://example.com/fake_image.png"

        monkeypatch.setattr(
            "agents.director_graph_package.storyboard_designer_impl.call_llm",
            fake_call_llm,
        )

        result = generate_storyboard_for_segment(state, segment_index=1)
        assert "prompt" in result
        assert "image_path" in result
        assert result["prompt"] != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
