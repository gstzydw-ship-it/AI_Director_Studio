@echo off
chcp 65001 >nul
echo [1/4] Installing dependencies...
D:\Python311-64\python.exe -m pip install -r requirements.txt pyinstaller

echo [2/4] Building the Web UI executable...
D:\Python311-64\python.exe -m PyInstaller --noconfirm --onedir --console ^
  --name "AI_Director_Studio" ^
  --add-data "knowledge;knowledge" ^
  --add-data "config;config" ^
  --add-data "ui\templates;ui\templates" ^
  --add-data "ui\static;ui\static" ^
  --hidden-import "langgraph" ^
  --hidden-import "langgraph.checkpoint.sqlite" ^
  --hidden-import "langgraph.checkpoint" ^
  --hidden-import "langgraph.graph" ^
  --hidden-import "langgraph.types" ^
  --hidden-import "bm25s" ^
  --hidden-import "httpx" ^
  --hidden-import "openai" ^
  --hidden-import "aiosqlite" ^
  --hidden-import "sqlite_vec" ^
  --hidden-import "ui.app" ^
  --hidden-import "fastapi" ^
  --hidden-import "uvicorn" ^
  --hidden-import "jinja2" ^
  --hidden-import "multipart" ^
  --hidden-import "cv2" ^
  main.py

echo [3/4] Build Complete!
echo [4/4] Results are in: dist\AI_Director_Studio\
pause
