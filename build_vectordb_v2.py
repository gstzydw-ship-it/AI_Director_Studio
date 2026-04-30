#!/usr/bin/env python3
"""
构建向量知识库脚本（带详细日志）
用法: python build_vectordb_v2.py [--rebuild]
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_base import (
    build_vectordb, _iter_knowledge_files, get_knowledge_dir,
    _runtime_retrieval_enabled, _frontmatter_metadata, chunk_markdown,
    AGENT_KNOWLEDGE_MAP, _normalise_agent_scope
)

def main():
    force = "--rebuild" in sys.argv
    print("=" * 60)
    print("开始构建向量知识库...")
    print(f"强制重建: {force}")
    print("=" * 60)

    # 首先列出所有找到的文件
    knowledge_dir = get_knowledge_dir()
    print(f"\n[INFO] 知识库目录: {knowledge_dir}")
    print("[INFO] 扫描到的文件:")

    all_files = list(_iter_knowledge_files(knowledge_dir))
    print(f"  总共找到 {len(all_files)} 个文件")

    # 分类统计
    rules_files = [f for f in all_files if "rules/" in f[0]]
    cases_files = [f for f in all_files if "cases/" in f[0]]
    root_files = [f for f in all_files if "/" not in f[0]]

    print(f"  - 根目录文件: {len(root_files)}")
    print(f"  - cases/ 文件: {len(cases_files)}")
    print(f"  - rules/ 文件: {len(rules_files)}")

    if rules_files:
        print("\n  rules/ 文件列表:")
        for relpath, _ in rules_files[:10]:  # 只显示前10个
            print(f"    - {relpath}")
        if len(rules_files) > 10:
            print(f"    ... 还有 {len(rules_files) - 10} 个文件")

    print("\n" + "=" * 60)
    print("开始构建...")
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

if __name__ == "__main__":
    main()
