import base64
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

import agents.director_graph as dg


def test_extract_tail_frame_from_video_uses_last_frame(tmp_path, monkeypatch):
    cv2 = pytest.importorskip("cv2")
    monkeypatch.setattr(dg, "OUTPUT_DIR", str(tmp_path / "output"))

    video_path = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        1.0,
        (48, 32),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV video writer is unavailable in this environment")

    try:
        # BGR frames: red, green, then blue. The extracted tail should be blue.
        for color in [(0, 0, 255), (0, 255, 0), (255, 0, 0)]:
            frame = np.full((32, 48, 3), color, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()

    encoded, output_path, error = dg._extract_tail_frame_from_video(str(video_path), segment_index=2)

    assert error is None
    assert encoded
    assert output_path

    image = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGB")
    pixels = np.asarray(image, dtype=np.float32)
    red = pixels[:, :, 0].mean()
    green = pixels[:, :, 1].mean()
    blue = pixels[:, :, 2].mean()

    assert blue > red
    assert blue > green
