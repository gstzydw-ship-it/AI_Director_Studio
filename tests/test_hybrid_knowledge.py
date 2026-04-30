"""
混合知识检索测试脚本
验证 BM25、向量检索和混合检索的返回结果，
对比 full/hybrid 两种模式的 token 节省量。

使用方法:
  python test_hybrid_knowledge.py              # 运行全部测试
  python test_hybrid_knowledge.py --bm25-only  # 仅测 BM25（不需要向量库）
"""

import os
import sys

# Fix Windows console encoding for Chinese text
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 确保能导入 agents 模块
sys.path.insert(0, os.path.dirname(__file__))

from agents.knowledge_base import (
    AGENT_KNOWLEDGE_MAP,
    get_full_knowledge_for_agent,
    chunk_markdown,
)


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文约 1.5 字符/token）"""
    return max(1, int(len(text) / 1.5))


def test_full_knowledge_baseline():
    """测试全文注入的 token 消耗"""
    print("=" * 60)
    print("[BASELINE] Full-text injection Token stats")
    print("=" * 60)
    total = 0
    for agent_name in AGENT_KNOWLEDGE_MAP:
        full_text = get_full_knowledge_for_agent(agent_name)
        tokens = estimate_tokens(full_text)
        file_count = len(AGENT_KNOWLEDGE_MAP[agent_name])
        print(f"  {agent_name:20s}: {len(full_text):>6,} chars, ~{tokens:>5,} tokens ({file_count} files)")
        total += tokens
    print(f"  {'TOTAL':20s}: ~{total:>5,} tokens")
    print()
    return total


def test_bm25_retrieval():
    """测试 BM25 检索"""
    try:
        from agents.knowledge_base import query_knowledge_bm25, _HAS_BM25S
    except ImportError:
        print("[WARN] Cannot import BM25 module")
        return

    if not _HAS_BM25S:
        print("[WARN] bm25s not installed, skip BM25 test. Run: pip install bm25s")
        return

    print("=" * 60)
    print("[BM25] Keyword retrieval test")
    print("=" * 60)

    test_queries = {
        "scene_analyst": "场景分析 剧本拆解 核心动作 炸点 约束 导演意图",
        "story_planner": "剧本拆分 15秒片段规划 节奏控制 镜头切换",
        "shot_director": "镜头导演 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制",
        "prompt_compiler": "Seedance提示词编译 输出词典 模型适配 动作描述精细化 故事节奏 Gold Standard范例",
        "quality_inspector": "质检 错误纠偏 判例 回溯修正",
    }

    for agent_name, query in test_queries.items():
        print(f"\n  Agent: {agent_name}")
        print(f"  Query: {query[:60]}...")
        results = query_knowledge_bm25(query, agent_name, n_results=5)
        total_chars = sum(len(r["text"]) for r in results)
        print(f"  结果: {len(results)} 片段, {total_chars:,} chars, ~{estimate_tokens(str(total_chars)):,} tokens")
        for i, r in enumerate(results[:3]):
            print(f"    [{i+1}] score={r['relevance']:.4f} source={r['source']} title={r['title'][:30]}")
            print(f"        {r['text'][:80]}...")
    print()


def test_hybrid_retrieval():
    """测试混合检索"""
    try:
        from agents.knowledge_base import query_knowledge_hybrid, _HAS_BM25S
    except ImportError:
        print("[WARN] Cannot import hybrid retrieval module")
        return

    print("=" * 60)
    print("[HYBRID] BM25 + Vector retrieval test")
    print("=" * 60)

    if not _HAS_BM25S:
        print("  [WARN] bm25s not installed, hybrid will use vector-only")

    test_queries = {
        "prompt_compiler": "Seedance提示词编译 输出词典 动作描述 Gold Standard范例 尾帧收束",
        "shot_director": "焦段景深 景别画幅 仰拍限制 情绪锚点",
    }

    for agent_name, query in test_queries.items():
        print(f"\n  Agent: {agent_name}")
        print(f"  Query: {query[:60]}")
        try:
            results = query_knowledge_hybrid(query, agent_name, n_results=8)
            total_chars = sum(len(r["text"]) for r in results)
            print(f"  结果: {len(results)} 片段, {total_chars:,} chars, ~{estimate_tokens(str(total_chars)):,} tokens")
            for i, r in enumerate(results[:5]):
                print(f"    [{i+1}] rrf_score={r['relevance']:.4f} source={r['source']}")
                print(f"        {r['text'][:80]}...")
        except Exception as e:
            print(f"  [ERROR] {e}")
    print()


def test_smart_knowledge_comparison():
    """对比 full vs hybrid 的 token 消耗"""
    try:
        from agents.knowledge_base import get_smart_knowledge
    except ImportError:
        print("[WARN] Cannot import get_smart_knowledge")
        return

    print("=" * 60)
    print("[COMPARE] Full vs Hybrid Token comparison")
    print("=" * 60)

    test_hints = {
        "scene_analyst": "场景分析 剧本拆解 核心动作 炸点 约束",
        "story_planner": "剧本拆分 15秒片段 节奏控制",
        "shot_director": "镜头导演 焦段景深 景别画幅 连续性",
        "prompt_compiler": "Seedance提示词 输出词典 模型适配 Gold Standard",
        "quality_inspector": "质检 错误纠偏 判例 回溯修正",
    }

    total_full = 0
    total_hybrid = 0

    for agent_name, hint in test_hints.items():
        full_text = get_full_knowledge_for_agent(agent_name)
        full_tokens = estimate_tokens(full_text)
        total_full += full_tokens

        hybrid_text = get_smart_knowledge(agent_name, hint)
        hybrid_tokens = estimate_tokens(hybrid_text)
        total_hybrid += hybrid_tokens

        saving = (1 - hybrid_tokens / max(full_tokens, 1)) * 100
        mode = "FULL" if hybrid_tokens >= full_tokens * 0.95 else "HYBRID"
        print(f"  {agent_name:20s}: full={full_tokens:>5,}t → hybrid={hybrid_tokens:>5,}t  [{mode}] 节省 {saving:.0f}%")

    overall_saving = (1 - total_hybrid / max(total_full, 1)) * 100
    print(f"\n  {'TOTAL':20s}: full={total_full:>5,}t → hybrid={total_hybrid:>5,}t  节省 {overall_saving:.0f}%")
    print()


if __name__ == "__main__":
    bm25_only = "--bm25-only" in sys.argv

    # 1. 基线
    test_full_knowledge_baseline()

    # 2. BM25
    test_bm25_retrieval()

    if not bm25_only:
        # 3. 混合
        test_hybrid_retrieval()

        # 4. 对比
        test_smart_knowledge_comparison()

    print("[OK] All tests completed")
