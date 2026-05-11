from __future__ import annotations

import base64
import sys
from io import BytesIO

from PIL import Image

from ui import app as ui_app


class _FakeEncoded:
    def __init__(self, payload: bytes):
        self._payload = payload

    def tobytes(self) -> bytes:
        return self._payload


class _FakeCapture:
    def __init__(self, _path: str):
        self.released = False

    def isOpened(self) -> bool:
        return True

    def get(self, _prop: int) -> int:
        return 3

    def set(self, _prop: int, _value: int) -> None:
        return None

    def read(self):
        return True, object()

    def release(self) -> None:
        self.released = True


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (18, 12), (18, 120, 210))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


def test_previous_segment_video_tail_frame_asset_registers_manifest(tmp_path, monkeypatch):
    jpeg_payload = _jpeg_bytes()

    class FakeCv2:
        CAP_PROP_FRAME_COUNT = 7
        CAP_PROP_POS_FRAMES = 1
        IMWRITE_JPEG_QUALITY = 1

        @staticmethod
        def VideoCapture(path: str):
            return _FakeCapture(path)

        @staticmethod
        def imencode(_extension: str, _frame: object, _params: list[int]):
            return True, _FakeEncoded(jpeg_payload)

    monkeypatch.setitem(sys.modules, "cv2", FakeCv2)
    monkeypatch.setattr(ui_app, "OUTPUT_DIR", str(tmp_path / "output"))

    video_path = tmp_path / "previous.mp4"
    video_path.write_bytes(b"fake video")

    asset = ui_app._build_previous_segment_video_tail_frame_asset(str(video_path), segment_index=2)

    assert asset is not None
    assert asset["source"] == "previous_segment_video_tail_frame"
    assert asset["image_data_url"].startswith("data:image/jpeg;base64,")
    assert base64.b64decode(asset["raw_b64"]) == jpeg_payload
    assert asset["saved_path"]
    assert (tmp_path / "output" / "auto_tail_frames").exists()

    manifest = asset["manifest_item"]
    assert manifest["role"] == "previous_segment_tail_frame"
    assert manifest["source"] == "previous_segment_video_tail_frame"
    assert manifest["previous_segment_index"] == "1"
    assert "not use this as a character, scene, or style master" in manifest["purpose"]

    state = {
        "reference_image_b64s": ["data:image/jpeg;base64,old"],
        "reference_image_manifest": [{"role": "character", "filename": "hero.jpg"}],
    }
    ui_app._apply_previous_continuity_asset_to_state(state, asset)

    assert state["reference_image_count"] == 2
    assert state["reference_image_manifest"][-1]["role"] == "previous_segment_tail_frame"
    assert state["reference_image_b64s"][-1].startswith("data:image/jpeg;base64,")


def test_previous_continuity_falls_back_to_storyboard_placeholder_then_out_state_text():
    storyboard_state = {"storyboard_images_by_segment": {"1": "output/storyboards/seg01.jpg"}}
    storyboard_asset = ui_app._select_previous_continuity_asset(storyboard_state, segment_index=2)

    assert storyboard_asset["source"] == "previous_storyboard_last_panel_placeholder"
    assert storyboard_asset["storyboard_image_path"] == "output/storyboards/seg01.jpg"
    assert "Crop the previous storyboard last panel" in storyboard_asset["todo"]

    text_state = {
        "agent_outputs": {
            "compiled_segment_1": "Previous out-state: character ends beside the elevator doors."
        }
    }
    text_asset = ui_app._select_previous_continuity_asset(text_state, segment_index=2)

    assert text_asset["source"] == "previous_out_state_text"
    assert "elevator doors" in text_asset["out_state_text"]
    assert "manifest_item" not in text_asset


def test_previous_continuity_without_video_or_history_returns_none():
    asset = ui_app._select_previous_continuity_asset({}, segment_index=1)

    assert asset["source"] == "none"
    assert asset["previous_segment_index"] == 0
