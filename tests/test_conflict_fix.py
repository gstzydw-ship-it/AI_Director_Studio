#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识库冲突修复效果
用包含双人对话+受击反应+多重炸点的剧本测试流水线
"""

import base64
import os
import sys
import io

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

# 设置代理
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1,localhost"

TEST_SCRIPT = """3-1 日/内/总裁办公室
人物：乔熙、商北琛
▲乔熙敲门进去，将咖啡小心翼翼地放在桌上。
乔熙：Mr. Pierce, your coffee.
▲商北琛端起来喝了一口。
商北琛：Your coffee's gotten better, but your brain clearly hasn't.
▲一叠报表扔到桌上。
商北琛：There are mistakes in this report. Double-check it and get it back to me.
乔熙：Mr. Pierce, could you point out which part is wrong?
商北琛：They're your mistakes. You expect me to fix them?
乔熙：Can I get this to you tomorrow?
商北琛：Sunny, if it's not done, you're not leaving.
乔熙：Nash, you're doing this on purpose.
商北琛：On purpose? You think you're that important?
▲乔熙无语。
商北琛：Go to the Sothebie's auction tomorrow and pick up a necklace for me. Don't lose it. You couldn't afford it even if you sold everything you had.
乔熙：Mr. Pierce, something that valuable... maybe you should go yourself.
商北琛：If I have to do everything myself, what do I need a secretary for? Just to get in the way?
"""


def make_placeholder_image():
    """生成1x1 PNG占位图的base64"""
    # Minimal valid 1x1 white PNG
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
        b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return "data:image/png;base64," + base64.b64encode(png_data).decode("ascii")


def main():
    from agents.director_graph import (
        run_phase_1_planning,
        run_phase_2_compile_segment,
        clear_state,
        _agent_outputs,
        _combined_prompt,
    )

    print("=" * 70)
    print("  Knowledge Base Conflict Fix Test")
    print("  Script: 3-1 CEO Office - Dual Dialogue + Reaction + Dominance")
    print("=" * 70)

    clear_state()

    # 生成3张占位图
    placeholder = make_placeholder_image()
    ref_images = [placeholder, placeholder, placeholder]
    ref_manifest = [
        {"label": "@pic1", "filename": "protagonist.png", "purpose": "protagonist Qiao Xi"},
        {"label": "@pic2", "filename": "antagonist.png", "purpose": "antagonist Shang Beichen / Nash Pierce"},
        {"label": "@pic3", "filename": "scene.png", "purpose": "CEO office scene"},
    ]

    print("\n[Phase 1] Running pipeline (speed_mode=True)...\n")

    try:
        state = run_phase_1_planning(
            script=TEST_SCRIPT,
            aspect_ratio="9:16",
            reference_images="pic1=protagonist Qiao Xi; pic2=antagonist Nash Pierce; pic3=CEO office",
            reference_image_b64s=ref_images,
            reference_image_manifest=ref_manifest,
            speed_mode=True,
        )
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return

    outputs = _agent_outputs(state)
    status = state.get("status", "unknown")

    print(f"\n{'='*70}")
    print(f"  Pipeline Status: {status}")
    print(f"{'='*70}")

    # 输出各节点结果
    for agent_name in ["scene_analyst", "story_planner", "shot_director"]:
        output = outputs.get(agent_name, "")
        if output:
            print(f"\n{'='*60}")
            print(f"  {agent_name} ({len(output)} chars)")
            print(f"{'='*60}")
            print(output[:4000])
            if len(output) > 4000:
                print(f"\n... ({len(output) - 4000} chars omitted)")

    # 如果需要Phase 2，自动运行
    if status == "waiting_for_user_input":
        total_segs = int(state.get("total_segments") or 1)
        print(f"\n[Phase 2] Compiling {total_segs} segments...\n")
        
        for seg_idx in range(1, total_segs + 1):
            print(f"  Compiling segment {seg_idx}/{total_segs}...")
            try:
                state = run_phase_2_compile_segment(seg_idx)
                outputs = _agent_outputs(state)
            except Exception as e:
                print(f"  Segment {seg_idx} failed: {e}")
                break

    # 输出编译好的Prompt
    compiled_keys = sorted(k for k in outputs if k.startswith("compiled_segment_"))
    if compiled_keys:
        for key in compiled_keys:
            print(f"\n{'='*60}")
            print(f"  {key} ({len(outputs[key])} chars)")
            print(f"{'='*60}")
            print(outputs[key])
    elif outputs.get("prompt_compiler"):
        print(f"\n{'='*60}")
        print(f"  prompt_compiler ({len(outputs['prompt_compiler'])} chars)")
        print(f"{'='*60}")
        print(outputs["prompt_compiler"])

    # 质检结果
    if outputs.get("quality_inspector"):
        print(f"\n{'='*60}")
        print(f"  quality_inspector")
        print(f"{'='*60}")
        print(outputs["quality_inspector"])

    # 保存完整结果
    output_path = os.path.join(ROOT_DIR, "output", "conflict_test_result.txt")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Test Time: {__import__('datetime').datetime.now()}\n")
        f.write(f"Status: {state.get('status', 'unknown')}\n\n")
        for k, v in sorted(outputs.items()):
            f.write(f"\n{'='*60}\n{k}\n{'='*60}\n{v}\n")
    print(f"\nFull results saved to: {output_path}")


if __name__ == "__main__":
    main()
