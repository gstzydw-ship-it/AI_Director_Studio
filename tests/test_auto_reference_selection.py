from __future__ import annotations

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui import app as ui_app


def _write_image(path):
    image = Image.new("RGB", (24, 16), (32, 80, 160))
    image.save(path)


def test_auto_reference_matches_script_entities(tmp_path, monkeypatch):
    ref_dir = tmp_path / "reference_images"
    ref_dir.mkdir()
    for name in ["乔熙.png", "商北琛.png", "集团大堂.png", "集团门口.png", "儿童房.png", "手机.png"]:
        _write_image(ref_dir / name)
    monkeypatch.setattr(ui_app, "REFERENCE_IMAGES_DIR", str(ref_dir))

    script = "乔熙冲进集团大堂，商北琛扶住她。她的手机掉在地上。"

    matches = ui_app._build_auto_reference_matches(script)
    filenames = [item["filename"] for item in matches]

    assert "乔熙.png" in filenames
    assert "商北琛.png" in filenames
    assert "集团大堂.png" in filenames
    assert "集团门口.png" not in filenames
    assert "手机.png" in filenames
    assert "儿童房.png" not in filenames
    assert next(item for item in matches if item["filename"] == "集团大堂.png")["asset_type"] == "scene"
    assert next(item for item in matches if item["filename"] == "手机.png")["asset_type"] == "prop"


def test_auto_reference_encodes_and_skips_existing_manifest(tmp_path, monkeypatch):
    ref_dir = tmp_path / "reference_images"
    ref_dir.mkdir()
    for name in ["乔熙.png", "集团大堂.png"]:
        _write_image(ref_dir / name)
    monkeypatch.setattr(ui_app, "REFERENCE_IMAGES_DIR", str(ref_dir))

    images, manifest, selected = ui_app._auto_select_reference_images(
        "乔熙站在集团大堂。",
        existing_manifest=[{"filename": "乔熙.png"}],
    )

    assert [item["filename"] for item in selected] == ["集团大堂.png"]
    assert len(images) == 1
    assert images[0].startswith("data:image/jpeg;base64,")
    assert manifest[0]["label"] == "@图片2"
    assert manifest[0]["asset_type"] == "scene"
    assert manifest[0]["selected_by"] == "auto_reference_matcher"
