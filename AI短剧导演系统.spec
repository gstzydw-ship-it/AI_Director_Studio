# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('knowledge', 'knowledge'),
        ('config', 'config'),
        ('ui/templates', 'ui/templates'),
        ('ui/static', 'ui/static'),
    ],
    hiddenimports=[
        'tiktoken_ext.openai_public', 'tiktoken_ext',
        'langgraph', 'langgraph.checkpoint.sqlite', 'langgraph.checkpoint', 'langgraph.graph',
        'langgraph.types', 'bm25s', 'httpx', 'openai', 'aiosqlite', 'sqlite_vec', 'ui.app',
        'fastapi', 'uvicorn', 'jinja2', 'multipart', 'cv2'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI短剧导演系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI短剧导演系统',
)
