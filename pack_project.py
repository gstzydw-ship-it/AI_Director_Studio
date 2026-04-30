#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包 AI Director Studio 项目 + 会话记录
排除 dist/（exe可重新打包）、视频文件、__pycache__、.pyc
"""

import os
import zipfile
from datetime import datetime

PROJECT_DIR = r"E:\AI_Director_Studio_Pack_20260416\AI_Director_Studio"
SESSION_DIR = r"C:\Users\gstzy\.gemini\antigravity\brain\cb59f882-a053-434e-a4e0-c0f6ea0d4315"

OUTPUT_ZIP = os.path.join(
    os.path.dirname(PROJECT_DIR),
    f"AI_Director_Studio_Pack_{datetime.now().strftime('%Y%m%d')}.zip"
)

# 排除规则
EXCLUDE_DIRS = {
    "dist",           # exe打包目录，128MB，可重新生成
    "__pycache__",    # Python缓存
    ".git",           # Git目录
    "node_modules",   # Node模块
    "midscene_run",   # 中间文件
}

EXCLUDE_EXTENSIONS = {
    ".mp4",           # 视频文件 ~24MB
    ".pyc",           # 编译文件
    ".sqlite",        # SQLite数据库（运行时生成）
    ".sqlite-wal",
    ".sqlite-shm",
}

EXCLUDE_FILES = {
    "pipeline_state.json",  # 运行时状态（每次运行会重新生成）
    "ui_server.out.log",    # 日志
}


def should_exclude(filepath, relpath):
    """判断是否排除此文件"""
    parts = relpath.split(os.sep)
    
    # 排除指定目录
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    
    # 排除指定扩展名
    _, ext = os.path.splitext(filepath)
    if ext.lower() in EXCLUDE_EXTENSIONS:
        return True
    
    # 排除指定文件名
    basename = os.path.basename(filepath)
    if basename in EXCLUDE_FILES:
        return True
    
    return False


def main():
    print(f"Packing project to: {OUTPUT_ZIP}")
    print(f"Project: {PROJECT_DIR}")
    print(f"Session: {SESSION_DIR}")
    print()

    file_count = 0
    total_size = 0
    skipped_count = 0
    skipped_size = 0

    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. 打包项目目录
        for root, dirs, files in os.walk(PROJECT_DIR):
            # 过滤掉排除的目录（原地修改 dirs 列表）
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for filename in files:
                filepath = os.path.join(root, filename)
                relpath = os.path.relpath(filepath, PROJECT_DIR)
                
                if should_exclude(filepath, relpath):
                    fsize = os.path.getsize(filepath)
                    skipped_count += 1
                    skipped_size += fsize
                    continue
                
                arcname = os.path.join("AI_Director_Studio", relpath)
                zf.write(filepath, arcname)
                fsize = os.path.getsize(filepath)
                file_count += 1
                total_size += fsize

        # 2. 打包会话记录（implementation_plan, task, walkthrough）
        session_files = [
            "implementation_plan.md",
            "task.md",
            "walkthrough.md",
        ]
        for fn in session_files:
            fpath = os.path.join(SESSION_DIR, fn)
            if os.path.exists(fpath):
                arcname = os.path.join("AI_Director_Studio", "_session_artifacts", fn)
                zf.write(fpath, arcname)
                fsize = os.path.getsize(fpath)
                file_count += 1
                total_size += fsize
                print(f"  + session: {fn}")

    print()
    print(f"Done!")
    print(f"  Packed: {file_count} files, {total_size/1024/1024:.1f} MB")
    print(f"  Skipped: {skipped_count} files, {skipped_size/1024/1024:.1f} MB")
    print(f"  Output: {OUTPUT_ZIP}")
    print(f"  ZIP size: {os.path.getsize(OUTPUT_ZIP)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
