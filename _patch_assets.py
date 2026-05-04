from pathlib import Path
import os

p = Path(r"d:\AI_Director_Studio\ui\app.py")
text = p.read_text(encoding="utf-8")
original = text

# 1. Add hashlib import after shutil
if "import shutil" in text and "import hashlib" not in text:
    text = text.replace("import shutil\n", "import shutil\nimport hashlib\n", 1)

# 2. Add _file_sha256 and _dedupe_asset_path helpers before _safe_filename
helper_anchor = 'def _safe_filename(filename: str, fallback: str = "asset") -> str:\n'
if helper_anchor in text and "_file_sha256(" not in text:
    idx = text.index(helper_anchor)
    # find the blank line after _safe_filename's own def line + body
    end = text.index("\n\n", idx)
    insert_pos = end + 2
    helper = """def _file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _dedupe_asset_path(folder: str, original_filename: str, content: bytes) -> tuple[str, bool]:
    safe_name = _safe_filename(original_filename)
    stem, ext = os.path.splitext(safe_name)
    digest = _file_sha256(content)

    for existing in os.listdir(folder):
        existing_path = os.path.join(folder, existing)
        if not os.path.isfile(existing_path):
            continue
        try:
            with open(existing_path, "rb") as f:
                if _file_sha256(f.read()) == digest:
                    return existing_path, True
        except Exception:
            continue

    final_name = f"{stem}_{digest[:12]}{ext}"
    return os.path.join(folder, final_name), False


"""
    text = text[:insert_pos] + helper + text[insert_pos:]

# 3. Patch api_assets_import
old_single = '''    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_filename(file.filename)}"
    path = os.path.join(ASSET_LIBRARY_DIR, dirname, filename)
    with open(path, "wb") as output:
        output.write(await file.read())
    return {"asset": _scan_asset_library()["assets"][-1]}
'''
new_single = '''    content = await file.read()
    path, existed = _dedupe_asset_path(os.path.join(ASSET_LIBRARY_DIR, dirname), file.filename or "asset", content)
    if not existed:
        with open(path, "wb") as output:
            output.write(content)
    asset = next((item for item in _scan_asset_library()["assets"] if item.get("path") == path), None)
    return {"asset": asset, "deduplicated": existed}
'''
if old_single in text:
    text = text.replace(old_single, new_single)
else:
    print("WARN: single import pattern not found")

# 4. Patch api_assets_import_batch
old_batch = '''    for file in files:
        if not file.filename:
            continue
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_filename(file.filename)}"
        path = os.path.join(ASSET_LIBRARY_DIR, dirname, filename)
        with open(path, "wb") as output:
            output.write(await file.read())
        imported += 1
    return {"ok": True, "imported": imported, "library": _scan_asset_library()}
'''
new_batch = '''    skipped = 0
    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        path, existed = _dedupe_asset_path(os.path.join(ASSET_LIBRARY_DIR, dirname), file.filename or "asset", content)
        if existed:
            skipped += 1
            continue
        with open(path, "wb") as output:
            output.write(content)
        imported += 1
    return {"ok": True, "imported": imported, "skipped": skipped, "library": _scan_asset_library()}
'''
if old_batch in text:
    text = text.replace(old_batch, new_batch)
else:
    print("WARN: batch import pattern not found")

if text != original:
    p.write_text(text, encoding="utf-8")
    print("SUCCESS: ui/app.py patched")
else:
    print("NO CHANGE: ui/app.py was already patched or patterns not found")
