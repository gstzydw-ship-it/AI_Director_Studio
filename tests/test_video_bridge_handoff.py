from pathlib import Path
import sys
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph_package import legacy_impl, segment_flow_impl, state_store  # noqa: E402
from agents.request_context import request_scope  # noqa: E402


class _FakeFrame:
    shape = (16, 16, 3)


class _FakeEncoded:
    def __init__(self, payload: bytes = b"jpg-bytes"):
        self._payload = payload

    def tobytes(self):
        return self._payload


class _FakeCapture:
    def __init__(self, _path):
        self.positions: list[int] = []

    def isOpened(self):
        return True

    def get(self, prop):
        if prop == 7:
            return 4
        if prop == 5:
            return 24.0
        return 0

    def set(self, _prop, value):
        self.positions.append(int(value))

    def read(self):
        return True, _FakeFrame()

    def release(self):
        pass


def _install_fake_cv2(monkeypatch):
    fake_cv2 = SimpleNamespace(
        CAP_PROP_FRAME_COUNT=7,
        CAP_PROP_FPS=5,
        CAP_PROP_POS_FRAMES=1,
        IMWRITE_JPEG_QUALITY=95,
        VideoCapture=_FakeCapture,
        imencode=lambda *_args, **_kwargs: (True, _FakeEncoded()),
        resize=lambda frame, _size: frame,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)


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


def test_prepare_phase_2_persists_tail_analysis_to_request_session(monkeypatch, tmp_path):
    captured: dict[str, str] = {}
    video_path = tmp_path / "previous.mp4"
    video_path.write_bytes(b"placeholder")
    monkeypatch.setattr(state_store, "OUTPUT_DIR", str(tmp_path))

    def fake_analyze_video(path, segment_index, next_segment_context=""):
        captured["path"] = path
        captured["segment_index"] = str(segment_index)
        captured["next_segment_context"] = next_segment_context
        return "bridge_frame:\n  selected: false\nnext_segment_start_mode:\n  mode: direct_cut\n"

    monkeypatch.setattr(segment_flow_impl, "_analyze_video_segment", fake_analyze_video)
    state = {
        "total_segments": 2,
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Previous event.\n"
                "- fragment_id: F02\n"
                "  source_script_events:\n"
                "    - Target segment starts in the corridor.\n"
            ),
            "shot_director": "- fragment_id: F02\n  shots:\n    - shot_id: F02-S01\n",
        },
    }

    with request_scope(session_id="web_bridge_a"):
        state_store._prepare_phase_2_compile_state(state, 2, video_path=str(video_path))
        saved = state_store.load_state()

    with request_scope(session_id="web_bridge_b"):
        other_saved = state_store.load_state()

    assert captured["path"] == str(video_path)
    assert captured["segment_index"] == "2"
    assert "Target segment starts in the corridor" in captured["next_segment_context"]
    assert saved["active_segment_index"] == 2
    assert "mode: direct_cut" in saved["tail_frame_analysis"]
    assert other_saved == {}
    assert (tmp_path / "sessions" / "web_bridge_a" / "pipeline_state.json").exists()
    assert not (tmp_path / "sessions" / "web_bridge_b" / "pipeline_state.json").exists()
    assert not (tmp_path / "pipeline_state.json").exists()


def test_auto_tail_frame_is_written_inside_request_session(monkeypatch, tmp_path):
    _install_fake_cv2(monkeypatch)
    monkeypatch.setattr(legacy_impl, "OUTPUT_DIR", str(tmp_path))
    video_path = tmp_path / "previous.mp4"
    video_path.write_bytes(b"placeholder")

    with request_scope(session_id="web_tail"):
        _b64, output_path, error = legacy_impl._extract_tail_frame_from_video(str(video_path), 2)

    assert error is None
    assert output_path is not None
    path = Path(output_path)
    assert path.exists()
    assert path.parent == tmp_path / "sessions" / "web_tail" / "agents" / "segment_flow" / "auto_tail_frames"
    assert not (tmp_path / "auto_tail_frames").exists()


def test_bridge_frame_candidates_are_written_inside_request_session(monkeypatch, tmp_path):
    _install_fake_cv2(monkeypatch)
    monkeypatch.setattr(state_store, "OUTPUT_DIR", str(tmp_path))
    video_path = tmp_path / "previous.mp4"
    video_path.write_bytes(b"placeholder")

    with request_scope(session_id="web_bridge"):
        candidates, error = segment_flow_impl._extract_bridge_frame_candidates(
            str(video_path),
            2,
            max_candidates=2,
        )

    assert error is None
    assert len(candidates) == 2
    expected_dir = tmp_path / "sessions" / "web_bridge" / "agents" / "segment_flow" / "auto_bridge_frames"
    assert all(Path(candidate["path"]).parent == expected_dir for candidate in candidates)
    assert all(Path(candidate["path"]).exists() for candidate in candidates)
    assert not (tmp_path / "auto_bridge_frames").exists()
