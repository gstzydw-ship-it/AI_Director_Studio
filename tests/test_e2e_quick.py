"""
Quick E2E test: Hybrid retrieval + per-agent model routing
Runs scene_analyst -> story_planner -> shot_director on the test script.
"""
import os, sys, time
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except: pass
sys.path.insert(0, os.path.dirname(__file__))

import yaml, httpx

SCRIPT = """
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
""".strip()

CONFIG = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")

def load_cfg():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_llm_for_agent(agent_name):
    cfg = load_cfg()
    llm = cfg.get("llm", {})
    overrides = cfg.get("agent_models", {}).get(agent_name, {})
    return {
        "api_key": overrides.get("api_key", llm.get("api_key", "")),
        "base_url": overrides.get("base_url", llm.get("base_url", "")).rstrip("/"),
        "model": overrides.get("model", llm.get("model", "")),
    }

def call_llm(agent_name, system_prompt, user_prompt):
    s = get_llm_for_agent(agent_name)
    host = s["base_url"].split("//")[1].split("/")[0] if "//" in s["base_url"] else "?"
    print(f"  [LLM] {agent_name} -> {s['model']} @ {host}")

    headers = {"Authorization": f"Bearer {s['api_key']}", "Content-Type": "application/json"}
    payload = {
        "model": s["model"],
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
                resp = client.post(f"{s['base_url']}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < 2:
                print(f"    [RETRY {attempt+1}] {type(e).__name__}: {str(e)[:100]}")
                time.sleep(3)
            else:
                print(f"    [FAIL] {type(e).__name__}: {str(e)[:200]}")
                return f"ERROR: {e}"

def build_sys(role_desc, agent_name, hint=""):
    from agents.knowledge_base import get_smart_knowledge
    kb = get_smart_knowledge(agent_name, hint)
    return f"{role_desc}\n\n===== 规则 =====\n{kb}\n===== 规则结束 ====="

def main():
    print("=" * 60)
    print("  E2E Test: Hybrid + Multi-Model")
    print("=" * 60)
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    # 1. scene_analyst
    print("\n[1/3] scene_analyst")
    hint = f"场景分析 剧本拆解 核心动作 炸点 约束 导演意图 {SCRIPT[:200]}"
    sys_p = build_sys("你是一位顶尖短剧场景分析师。拆解剧本，提取核心动作、炸点和约束。", "scene_analyst", hint)
    usr_p = f"分析以下剧本场景。\n\n【剧本】\n{SCRIPT}\n\n【画幅】9:16\n\n请直接输出YAML分析卡片。"
    print(f"  sys_prompt: {len(sys_p):,} chars")
    t0 = time.time()
    scene = call_llm("scene_analyst", sys_p, usr_p)
    print(f"  done in {time.time()-t0:.1f}s, output: {len(scene):,} chars")
    with open(os.path.join(out_dir, "test_scene_analyst.md"), "w", encoding="utf-8") as f:
        f.write(scene)

    # 2. story_planner
    print("\n[2/3] story_planner")
    hint = f"剧本拆分 15秒片段规划 节奏控制 镜头切换 {SCRIPT[:200]}"
    sys_p = build_sys("你是一位金牌连续剧结构规划师。将分析结果切分为15秒以内的执行片段。", "story_planner", hint)
    usr_p = f"基于【原始剧本】与【场景分析】制定拆片方案。\n\n【原始剧本】\n{SCRIPT}\n\n【场景分析】\n{scene}\n\n直接输出YAML拆片结果。"
    print(f"  sys_prompt: {len(sys_p):,} chars")
    t0 = time.time()
    planner = call_llm("story_planner", sys_p, usr_p)
    print(f"  done in {time.time()-t0:.1f}s, output: {len(planner):,} chars")
    with open(os.path.join(out_dir, "test_story_planner.md"), "w", encoding="utf-8") as f:
        f.write(planner)

    # 3. shot_director
    print("\n[3/3] shot_director")
    hint = f"镜头导演 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制 {SCRIPT[:200]}"
    sys_p = build_sys("你是一位大师级视觉镜头导演。为片段赋予电影级分镜主干。", "shot_director", hint)
    usr_p = f"基于【原始剧本】与【拆片方案】设计镜头方案。\n\n【原始剧本】\n{SCRIPT}\n\n【拆片方案】\n{planner}\n\n【画幅】9:16\n请直接输出YAML镜头方案。"
    print(f"  sys_prompt: {len(sys_p):,} chars")
    t0 = time.time()
    director = call_llm("shot_director", sys_p, usr_p)
    print(f"  done in {time.time()-t0:.1f}s, output: {len(director):,} chars")
    with open(os.path.join(out_dir, "test_shot_director.md"), "w", encoding="utf-8") as f:
        f.write(director)

    print("\n" + "=" * 60)
    print("  Results saved to output/test_*.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
