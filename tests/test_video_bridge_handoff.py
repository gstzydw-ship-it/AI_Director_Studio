from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph_package import segment_flow_impl, state_store  # noqa: E402


def test_next_segment_bridge_context_uses_requested_segment_assets():
    state = {
        "agent_outputs": {
            "scene_analyst": "scene_id: apartment\nspace: door left, table center",
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Previous segment event.\n"
                "- fragment_id: F02\n"
                "  source_script_events:\n"
                "    - Qiao Xi puts the photo back into the schoolbag.\n"
            ),
            "shot_director": (
                "- fragment_id: F01\n"
                "  shots:\n"
                "    - shot_id: F01-S01\n"
                "- fragment_id: F02\n"
                "  shots:\n"
                "    - shot_id: F02-S01\n"
                "      tailframe_role: space_reset\n"
            ),
        }
    }

    context = segment_flow_impl._next_segment_bridge_context(state, 2)

    assert "[Next Segment Bridge Target]" in context
    assert "segment_index: 2" in context
    assert "Qiao Xi puts the photo back" in context
    assert "F02-S01" in context


def test_tail_frame_without_image_defaults_to_direct_cut_with_next_context():
    analysis = segment_flow_impl._analyze_tail_frame(
        None,
        2,
        "[Next Segment Bridge Target]\nsegment_index: 2",
    )

    assert "next_segment_start_mode:" in analysis
    assert "mode: direct_cut" in analysis
    assert "usable_as_start_image: false" in analysis


def test_video_bridge_prompt_requires_image_start_or_direct_cut_decision():
    prompt = segment_flow_impl._video_bridge_user_prompt(
        3,
        "[Next Segment Bridge Target]\nsegment_index: 3\nflashback starts under ginkgo tree",
        "candidate_01: time=9.20s path=tail.jpg",
    )

    assert "image_start" in prompt
    assert "direct_cut" in prompt
    assert "selected_candidate" in prompt
    assert "flashback starts" in prompt


def test_prepare_phase_2_passes_next_segment_context_to_video_analysis(monkeypatch, tmp_path):
    captured: dict[str, str] = {}
    video_path = tmp_path / "previous.mp4"
    video_path.write_bytes(b"placeholder")

    def fake_analyze_video(path, segment_index, next_segment_context=""):
        captured["path"] = path
        captured["segment_index"] = str(segment_index)
        captured["next_segment_context"] = next_segment_context
        return "bridge_frame:\n  selected: false\nnext_segment_start_mode:\n  mode: direct_cut\n"

    monkeypatch.setattr(segment_flow_impl, "_analyze_video_segment", fake_analyze_video)
    monkeypatch.setattr(state_store, "save_state", lambda state: None)

    state = {
        "total_segments": 2,
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Previous event.\n"
                "- fragment_id: F02\n"
                "  source_script_events:\n"
                "    - Next segment begins in a new location.\n"
            ),
            "shot_director": "- fragment_id: F02\n  shots:\n    - shot_id: F02-S01\n",
        },
    }

    update = state_store._prepare_phase_2_compile_state(state, 2, video_path=str(video_path))

    assert captured["path"] == str(video_path)
    assert captured["segment_index"] == "2"
    assert "Next segment begins in a new location" in captured["next_segment_context"]
    assert "mode: direct_cut" in update["tail_frame_analysis"]
