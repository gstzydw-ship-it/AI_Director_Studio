"""
测试脚本：优化后的 4 步流程
Step 1: 场景分析（模板化快速跳过） → 省~60秒
Step 2: 拆片（独立LLM调用，保证质量）
Step 3: 镜头导演（独立LLM调用，保证质量）
Step 4: Prompt编译 + 机械质检 → 省~30秒
"""
import os
import sys
import json
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1,localhost"

from agents.director_graph import (
    call_llm,
    build_system_prompt,
    _script_fidelity_rules,
    _subject_framing_rules,
    _prompt_guard_report,
    _extract_segments,
    OUTPUT_DIR,
)

SCRIPT = """2-1 日/内/天御集团大堂
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
▲乔熙瞬间回神，触电般松开手，尴尬地拨弄头发。"""

ASPECT_RATIO = "9:16"

def run_test():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_start = time.time()
    step_times = {}

    # ========== Step 1: 场景分析（快速模板） ==========
    print("\n" + "=" * 60)
    print("📋 Step 1/4: 场景分析（快速模板）...")
    print("=" * 60)
    t1 = time.time()
    scene_output = (
        f"mode: fast_local_scene_card\n"
        f"aspect_ratio: {ASPECT_RATIO}\n"
        "source: original_script_only\n"
        "notes:\n"
        "  - 快速模式跳过场景分析师LLM调用，后续节点直接以原始剧本为准。\n"
        "  - 禁止新增原剧本外人物、对白、事件、员工低语、旁白或解释性信息。\n"
    )
    step_times["场景分析"] = time.time() - t1
    print(f"✅ 场景分析完成 ({step_times['场景分析']:.1f}秒)")

    # ========== Step 2: 拆片（独立LLM） ==========
    print("\n" + "=" * 60)
    print("📐 Step 2/4: 结构拆片...")
    print("=" * 60)
    t2 = time.time()
    planner_system = build_system_prompt(
        "你是一位金牌连续剧结构规划师。负责将分析结果切分为一个个 15 秒以内的执行片段。",
        "story_planner",
    )
    planner_user = (
        f"基于以下【原始剧本】与【场景分析结果】，制定严格拆片方案。\n\n"
        f"【原始剧本】\n{SCRIPT}\n\n"
        f"【场景分析结果】\n{scene_output}\n\n"
        "【要求】\n"
        "1. 必须按剧本真实戏剧动作拆分，不按时间均分。\n"
        "2. 每段必须包含 fragment_id，格式为 F01、F02、F03。\n"
        "3. 每段必须包含 source_script_events，逐条引用该段覆盖的原剧本动作/台词；没有原文依据不得写入。\n"
        "4. 片段可以短于15秒；禁止为了凑满15秒添加剧本外员工低语、旁白、解释、额外走位或新情节。\n"
        "5. 第一段必须从原剧本第一个动作/台词开始，结束点必须落在真实动作单元或完整发言单元边界。\n"
        "6. 每个片段优先控制在 10-15 秒，不要拆得太碎（不要出现5秒以下的片段），否则实际生成视频时衔接困难。\n"
        "7. 【尾帧收束】每个片段的最后一个事件必须是可形成明确画面定格的动作（如进入电梯门将闭、转身离开、"
        "对视定住等），为下一片段提供衔接起点。禁止片段结尾悬在进行中的动作上而没有收束画面。\n"
        f"{_script_fidelity_rules()}"
        "8. 直接输出YAML拆片结果。"
    )
    planner_output = call_llm(planner_system, planner_user)
    total_segments, segment_names = _extract_segments(planner_output)
    with open(os.path.join(OUTPUT_DIR, f"{timestamp}_test_story_planner.md"), "w", encoding="utf-8") as f:
        f.write(planner_output)
    step_times["拆片"] = time.time() - t2
    print(f"✅ 拆片完成：共 {total_segments} 个片段 ({step_times['拆片']:.1f}秒)")

    # ========== Step 3: 镜头导演（独立LLM） ==========
    print("\n" + "=" * 60)
    print("🎬 Step 3/4: 镜头导演...")
    print("=" * 60)
    t3 = time.time()
    director_system = build_system_prompt(
        "你是一位大师级视觉镜头导演。负责为所有切好的片段赋予电影级的分镜主干。\n\n"
        "【绝对禁令】\n"
        "1. 你只能基于原始剧本中已有的人物、动作、台词和事件设计镜头。\n"
        "2. 禁止新增剧本中没有的台词、旁白、员工低语、群体反应、心理活动或解释性信息。\n"
        "3. 如果原剧本没有写员工说话，dialogue 字段中不得出现员工对白或低声确认。\n"
        "4. dialogue 字段的 content_intent 只能引用或概括原剧本中的台词原文，禁止臆想新台词。",
        "shot_director",
    )
    director_user = (
        f"基于以下【原始剧本】与【拆片方案】，为【所有】片段设计详细镜头方案。\n\n"
        f"【原始剧本】\n{SCRIPT}\n\n"
        f"【拆片方案】\n{planner_output}\n\n"
        "【重大约束】\n"
        "你必须为每个独立的片段分别设计独立的主分镜与子分镜。"
        "绝对禁止把整集凑进片段01。每个片段(F01, F02...)都必须独立展示骨架。\n\n"
        "【情绪锚点密度要求】\n"
        "每个时间段的 emotion_anchor 字段必须至少包含 2 个以上可见身体表现的描述，"
        "禁止只用一个空泛情绪词概括。\n\n"
        f"{_script_fidelity_rules()}\n"
        f"{_subject_framing_rules()}\n"
        f"【画幅】{ASPECT_RATIO}\n"
        "请直接输出YAML镜头方案。"
    )
    director_output = call_llm(director_system, director_user)
    with open(os.path.join(OUTPUT_DIR, f"{timestamp}_test_shot_director.md"), "w", encoding="utf-8") as f:
        f.write(director_output)
    step_times["镜头"] = time.time() - t3
    print(f"✅ 镜头导演完成 ({step_times['镜头']:.1f}秒)")

    # ========== Step 4: Prompt编译 + 机械质检 ==========
    print("\n" + "=" * 60)
    print("✍️  Step 4/4: Seedance编译 + 机械质检...")
    print("=" * 60)
    t4 = time.time()
    aspect_label = "9:16竖屏" if "9:16" in ASPECT_RATIO else "16:9横屏"

    compiler_system = build_system_prompt(
        "你是一位 Seedance 视觉模型提示词编译大师。\n\n"
        "你的唯一职责：读取上游骨架资产，针对指定片段编译出可直接放入 Seedance 模型的最终中文导演 Prompt。\n\n"
        "【语言风格硬约束——最重要】\n"
        "1. 用简洁的导演调度语言，不用文学化描写。'大步走进大堂'而不是'肩背挺直几乎无晃动'。\n"
        "2. 表情只写关键状态（1-2个），不堆砌微表情。\n"
        "3. 运镜用口语化调度：'镜头正前方中景后退跟着商北琛'而不是'平视3/4角度，稳定后退跟拍'。\n"
        "4. 一句一个动作，句子简短有力。\n\n"
        "【逻辑正确性——最高优先级】\n"
        "人物进出方向、空间位置、动作顺序、道具状态都不能出错。\n\n"
        "【节奏与事件覆盖】\n"
        "片段必须完整覆盖拆片方案中所有事件，剧情推进优先于表情堆砌。\n\n"
        "【禁止项】禁止YAML、教学标签、微表情堆砌、编造剧本外内容。\n\n"
        "你的知识库中有 Gold Standard 范例文档（19号文档），范例A经实际视频生成验证效果良好，"
        "你的输出必须在语言风格上对齐范例A——简洁、清晰、可执行。",
        "prompt_compiler",
    )
    compiler_user = (
        f"=== 前置骨架资产 ===\n\n"
        f"【原始剧本】\n{SCRIPT}\n\n"
        f"【拆片方案】\n{planner_output}\n\n"
        f"【镜头骨架】\n{director_output}\n\n"
        f"【上一段尾帧分析】\n无（第一段）\n\n"
        f"【参考图清单】\n无参考图\n\n"
        f"【当前任务】\n"
        f"请专门为【片段 1】编译最终 Seedance Prompt。\n\n"
        f"画幅为 {aspect_label}。\n"
        "严禁包含多段；只输出当前片段。\n\n"
        f"{_script_fidelity_rules()}\n"
        f"{_subject_framing_rules()}\n"
        "【输出前强制自检】\n"
        "1. 标题行是否为 '片段N｜场景名｜关键词｜~秒数秒' 格式？\n"
        "2. 是否包含【风格锚点】【画幅锚点】【空间与首帧总控】【时间轴】【约束】五个段落？\n"
        "3. 运镜是否用口语化调度？\n"
        "4. 表情是否只写关键状态（1-2个），没有堆砌微表情？\n"
        "5. 是否存在剧本外编造的台词或情节？\n"
        f"6. 末尾是否包含尾帧上传提示？\n"
        "7. 拆片方案中当前片段的 source_script_events 是否全部被覆盖？\n"
        "8. 人物空间位置、动作方向是否有逻辑错误？\n"
        "全部通过后再输出。"
    )
    compiler_output = call_llm(compiler_system, compiler_user)
    guard_report = _prompt_guard_report(compiler_output, SCRIPT)

    with open(os.path.join(OUTPUT_DIR, f"{timestamp}_test_prompt_seg1.md"), "w", encoding="utf-8") as f:
        f.write(compiler_output)
    step_times["编译+质检"] = time.time() - t4
    print(f"✅ 编译+机械质检完成 ({step_times['编译+质检']:.1f}秒)")

    if guard_report:
        print(f"⚠️  机械质检预警:\n{guard_report}")
    else:
        print("✅ 机械质检通过")

    # ========== 最终结果 ==========
    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"🎬 最终结果：片段1 Seedance Prompt")
    print("=" * 60)
    print(compiler_output)

    print("\n" + "=" * 60)
    print("⏱️  性能数据")
    print("=" * 60)
    for step, t in step_times.items():
        print(f"  {step}: {t:.1f}秒")
    print(f"  ────────────────")
    print(f"  总计: {total_time:.1f}秒")

    print(f"\n📁 所有输出已保存到: {OUTPUT_DIR}")
    print(f"   文件前缀: {timestamp}_test_*")


if __name__ == "__main__":
    run_test()
