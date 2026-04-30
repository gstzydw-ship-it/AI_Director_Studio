#!/usr/bin/env python3
"""
构建向量知识库脚本
用法: python build_vectordb.py [--rebuild]
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_base import build_vectordb

if __name__ == "__main__":
    force = "--rebuild" in sys.argv
    print("=" * 60)
    print("开始构建向量知识库...")
    print(f"强制重建: {force}")
    print("=" * 60)

    try:
        build_vectordb(force_rebuild=force)
        print("\n" + "=" * 60)
        print("✅ 向量知识库构建完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
