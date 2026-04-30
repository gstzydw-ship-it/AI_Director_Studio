"""
端到端质量对比测试：Full vs Hybrid 模式
不依赖 langgraph，直接调用 LLM 和知识库模块。
"""

import os
import sys
import json
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))

import yaml
import httpx

SCRIPT = """
【02集】
2-1 日/内/天御集团大堂
人物：乔熙、商北琛、苏小可、严飞、众员工
▲商北琛迈步走进大堂，锐利的眸子淡淡扫过两边的人群。
严飞：Welcome, Mr. Pierce.
▲商北琛没说话，眉头微皱。
商北琛：Meeting in ten minutes. Directors and above, be there.
▲主管们瞬间四散。
▲商北琛转身进入电梯，就在电梯门即将关闭之际——
乔熙：Wait a second!
▲乔熙像风一般冲进电梯，一个刹不住，整个人直扑到商北琛身上。
▲男人西装布料下的胸膛，坚实滚烫。
▲商北琛下意识伸手，稳稳扶住她的腰。
商北琛：Long time no see—since when did you start throwing yourself at people?
▲乔熙寻声抬头，撞进一双深不见底的眼眸里。
商北琛：You gonna keep holding on or what?
▲乔熙瞬间回神，触电般松开手，尴尬地拨弄头发。

2-2 日/内/天御集团顶层
人物：乔熙、商北琛、苏小可、秦悦
▲电梯门开，苏小可与秦悦早已等候，标准九十度鞠躬。
苏小可/秦悦：Hello, Mr. Pierce.
▲乔熙心头狠狠一震。
乔熙OS：Is this the guy who left our marriage with nothing and gave me everything? And now, just four years later, he bought a multi-billion-dollar company like Celestial Group?
▲商北琛冷眼一睨，目光落在乔熙身上。
商北琛：I am Nash Pierce. As of today, I'm the new CEO of Celestial Group. I take my coffee black, I hate the smell of perfume, and I don't tolerate tardiness. Remember that.
众人：Yes, Mr. Pierce.
▲商北琛看着乔熙，目光不善。
商北琛：You are Sunny Reid?
乔熙：Don't know my name? Is he serious?
乔熙：Yes, Mr. Pierce.
▲商北琛看了一下腕表。
商北琛：You're one minute late. No perfect attendance award, no performance pay this month.
乔熙OS：Is he making an example of me? Using me to show off?
乔熙：Understood.
商北琛：The records say you're divorced?
乔熙：Yes.
商北琛：What was the reason?
乔熙：We weren't compatible.
▲现场所有人惊了。商北琛眸色闪了一下。
商北琛OS：Not compatible? Five times a day and you call that not compatible?
商北琛：Any kids?
乔熙：No.
商北琛：Good.
乔熙OS：Good? My ass!
""".strip()

ASPECT_RATIO = "9:16"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def set_retrieval_mode(mode: str):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config.setdefault("knowledge", {})["retrieval_mode"] = mode
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    print(f"  [CONFIG] retrieval_mode = {mode}")


def call_llm(system_prompt: str, user_prompt: str) -> str:
    config = load_config()
    llm = config.get("llm", {})
    api_key = llm.get("api_key", "")
    base_url = llm.get("base_url", "").rstrip("/")
    model = llm.get("model", "claude-3-5-sonnet-20240620")
    if model.startswith("openai/"):
        model = model.replace("openai/", "", 1)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }
    timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=60.0)

    for attempt in range(3):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except (httpx.RemoteProtocolError, httpx.TimeoutException) as e:
            if attempt < 2:
                print(f" [RETRY {attempt+1}]", end="", flush=True)
                time.sleep(5)
            else:
                raise RuntimeError(f"LLM call failed after 3 attempts: {e}") from e


def build_system_prompt(role_description: str, agent_name: str, context_hint: str = ""):
    from agents.knowledge_base import get_smart_knowledge
    kb_text = get_smart_knowledge(agent_name, context_hint)
    return (
        f"{role_description}\n\n"
        f"===== 以下是你必须遵守的约束规则 =====\n"
        f"{kb_text}\n"
        f"===== 规则结束 =====\n"
        f"请严格遵守上述规则，并直接输出结果，不要包含寒暄或无关内容。"
    )


def run_pipeline(mode_label: str):
    from agents import knowledge_base
    knowledge_base._bm25_index_cache.clear()
    knowledge_base._vectordb_cache = None

    results = {}
    sys_sizes = {}

    fidelity = (
        "【剧本忠实度硬规则】\n"
        "1. 只能使用原剧本已经出现的人物、场景、动作、台词和信息点，禁止补写剧本外新事件。\n"
        "2. 禁止新增剧本中没有的台词、旁白、员工低语、心理活动或解释性信息；凡带引号的台词必须能在原剧本中找到。\n"
        "3. 若原剧本没有写员工说话，就不能写员工低声确认、新CEO到了、议论等补戏。\n"
        "4. 片段不足15秒时允许短于15秒，禁止为了凑时长添加新情节。\n"
    )

    # --- scene_analyst ---
    print(f"\n  [{mode_label}] scene_analyst ...", end="", flush=True)
    hint = f"场景分析 剧本拆解 核心动作 炸点 约束 导演意图 {SCRIPT[:200]}"
    sys_p = build_system_prompt(
        "你是一位顶尖短剧场景分析师。你需要拆解用户提供的剧本，提取核心动作、炸点和约束。\n\n"
        "【绝对禁令】你只能提取剧本原文中明确存在的信息。\n"
        "禁止推测、补充或扩展剧本中没有出现的内容。",
        "scene_analyst", context_hint=hint,
    )
    usr_p = f"分析以下剧本场景，填充完整的场景分析输入卡。\n\n【剧本】\n{SCRIPT}\n\n【画幅】{ASPECT_RATIO}\n\n{fidelity}\n请直接输出YAML分析卡片。"
    sys_sizes["scene_analyst"] = len(sys_p)
    t0 = time.time()
    scene_out = call_llm(sys_p, usr_p)
    print(f" {time.time()-t0:.0f}s, sys={len(sys_p):,}c, out={len(scene_out):,}c")
    results["scene_analyst"] = scene_out

    # --- story_planner ---
    print(f"  [{mode_label}] story_planner ...", end="", flush=True)
    hint = f"剧本拆分 15秒片段规划 节奏控制 镜头切换 {SCRIPT[:200]}"
    sys_p = build_system_prompt(
        "你是一位金牌连续剧结构规划师。负责将分析结果切分为一个个 15 秒以内的执行片段。",
        "story_planner", context_hint=hint,
    )
    usr_p = f"基于以下【原始剧本】与【场景分析结果】，制定严格拆片方案。\n\n【原始剧本】\n{SCRIPT}\n\n【场景分析结果】\n{scene_out}\n\n{fidelity}\n直接输出YAML拆片结果。"
    sys_sizes["story_planner"] = len(sys_p)
    t0 = time.time()
    planner_out = call_llm(sys_p, usr_p)
    print(f" {time.time()-t0:.0f}s, sys={len(sys_p):,}c, out={len(planner_out):,}c")
    results["story_planner"] = planner_out

    # --- shot_director ---
    print(f"  [{mode_label}] shot_director ...", end="", flush=True)
    hint = f"镜头导演 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制 {SCRIPT[:200]}"
    sys_p = build_system_prompt(
        "你是一位大师级视觉镜头导演。负责为所有切好的片段赋予电影级的分镜主干。\n\n"
        "【绝对禁令】\n"
        "1. 你只能基于原始剧本中已有的人物、动作、台词和事件设计镜头。\n"
        "2. 禁止新增剧本中没有的台词、旁白、员工低语、群体反应、心理活动或解释性信息。",
        "shot_director", context_hint=hint,
    )
    usr_p = (
        f"基于以下【原始剧本】与【拆片方案】，为【所有】片段设计详细镜头方案。\n\n"
        f"【原始剧本】\n{SCRIPT}\n\n【拆片方案】\n{planner_out}\n\n{fidelity}\n"
        f"【画幅】{ASPECT_RATIO}\n请直接输出YAML镜头方案。"
    )
    sys_sizes["shot_director"] = len(sys_p)
    t0 = time.time()
    director_out = call_llm(sys_p, usr_p)
    print(f" {time.time()-t0:.0f}s, sys={len(sys_p):,}c, out={len(director_out):,}c")
    results["shot_director"] = director_out

    return results, sys_sizes


def save_results(results, sys_sizes, mode):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for agent, output in results.items():
        fp = os.path.join(OUTPUT_DIR, f"compare_{mode}_{agent}.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"# {agent} ({mode} mode)\n\nSystem prompt: {sys_sizes.get(agent, 0):,} chars\n\n---\n\n")
            f.write(output)
    print(f"  Saved to output/compare_{mode}_*.md")


def main():
    print("=" * 70)
    print("  E2E Quality Comparison: Full vs Hybrid")
    print("  Script: 02 episode, 9:16, 2 scenes")
    print("=" * 70)

    # --- Compute FULL mode system prompt sizes (no LLM call) ---
    print("\n[PHASE 1] Computing FULL mode system prompt sizes (no LLM call) ...")
    set_retrieval_mode("full")
    from agents import knowledge_base
    knowledge_base._bm25_index_cache.clear()
    knowledge_base._vectordb_cache = None

    fidelity = (
        "【剧本忠实度硬规则】\n"
        "1. 只能使用原剧本已经出现的人物、场景、动作、台词和信息点，禁止补写剧本外新事件。\n"
    )
    full_sizes = {}
    for agent, hint in [
        ("scene_analyst", f"场景分析 剧本拆解 核心动作 炸点 约束 导演意图 {SCRIPT[:200]}"),
        ("story_planner", f"剧本拆分 15秒片段规划 节奏控制 镜头切换 {SCRIPT[:200]}"),
        ("shot_director", f"镜头导演 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制 {SCRIPT[:200]}"),
    ]:
        sp = build_system_prompt("role desc placeholder", agent, context_hint=hint)
        full_sizes[agent] = len(sp)
        print(f"  {agent:20s}: {len(sp):>6,} chars")
    print("  [NOTE] Full mode LLM calls skipped (API disconnects with oversized prompts)")

    # --- Run HYBRID mode ---
    print("\n[PHASE 2] HYBRID mode (actually calling LLM)")
    set_retrieval_mode("hybrid")
    knowledge_base._bm25_index_cache.clear()
    knowledge_base._vectordb_cache = None
    hybrid_r, hybrid_s = run_pipeline("HYBRID")
    save_results(hybrid_r, hybrid_s, "hybrid")

    # --- Compare ---
    print("\n" + "=" * 70)
    print("  System Prompt Size Comparison (chars)")
    print("=" * 70)
    for agent in ["scene_analyst", "story_planner", "shot_director"]:
        fs = full_sizes.get(agent, 0)
        hs = hybrid_s.get(agent, 0)
        sv = (1 - hs / max(fs, 1)) * 100
        print(f"  {agent:20s}: full={fs:>6,} → hybrid={hs:>6,}  saving={sv:.0f}%")

    print("\n  Hybrid outputs saved to output/compare_hybrid_*.md")
    set_retrieval_mode("hybrid")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
