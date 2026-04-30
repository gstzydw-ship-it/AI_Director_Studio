#!/usr/bin/env python3
"""
导演流水线监控运行脚本
直接在Python中运行导演流程，无需WebUI
"""
import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("导演流水线监控运行")
print("=" * 80)

# 测试剧本
test_script = """2-1 日/内/咖啡厅
人物：男主角、女主角
▲男主角坐在窗边，看向窗外。
女主角走过来，坐在对面。
女主角：好久不见。
男主角：是啊，三年了。
▲两人相视而笑。"""

print("\n测试剧本:")
print("-" * 40)
print(test_script)
print("-" * 40)

# 导入导演系统
print("\n[1] 导入导演系统...")
from agents.director_graph import (
    run_phase_1_planning,
    run_phase_2_compile_segment,
    clear_state,
    _state_file
)
print("   [OK]")

# 清理状态
print("\n[2] 清理之前的状态...")
clear_state()
print("   [OK]")

# 创建模拟的参考图片数据（base64编码的小图片）
print("\n[3] 准备参考图片...")
# 使用最小的有效JPEG base64
MINIMAL_JPG_BASE64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAABAAEDAREAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwD3iAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//Z"

reference_images = [
    MINIMAL_JPG_BASE64,  # 主角
    MINIMAL_JPG_BASE64,  # 对手
    MINIMAL_JPG_BASE64,  # 场景
]
print(f"   准备了 {len(reference_images)} 张参考图片")
print("   [OK]")

# 运行 Phase 1
print("\n[4] 运行 Phase 1 (规划阶段)...")
print("   这可能需要一些时间，请等待...")
try:
    result = run_phase_1_planning(
        script=test_script,
        aspect_ratio="16:9",
        reference_images=None,
        reference_image_b64s=reference_images,
        speed_mode=False  # 使用真实LLM
    )
    print("   Phase 1 完成!")
    print(f"   状态: {result.get('status', 'unknown')}")
    print(f"   消息: {result.get('message', '无')}")
    print("   [OK]")
except Exception as e:
    print(f"   [ERROR] Phase 1 失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 读取状态
print("\n[5] 读取执行结果...")
try:
    state_file = _state_file()
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        print(f"   状态文件: {state_file}")
        print(f"   状态键: {list(state.keys())}")
        
        if 'outputs' in state:
            outputs = state['outputs']
            print("\n   各阶段输出:")
            for key in ['director_showrunner', 'scene_analyst', 'rhythm_rewrite_director', 
                        'story_planner']:
                if key in outputs:
                    content = outputs[key]
                    preview = str(content)[:100].replace('\n', ' ')
                    print(f"     - {key}: {preview}...")
                else:
                    print(f"     - {key}: (无输出)")
        
        # 检查是否有片段需要生成
        total_segments = state.get('total_segments', 0)
        print(f"\n   总片段数: {total_segments}")
        
        if total_segments > 0:
            print("\n[6] 生成片段 Prompt...")
            for i in range(1, total_segments + 1):
                print(f"\n   生成片段 {i}/{total_segments}...")
                try:
                    result = run_phase_2_compile_segment(segment_index=i)
                    print(f"   片段 {i} 完成")
                    
                    # 显示生成的Prompt
                    outputs = state.get('outputs', {})
                    prompt_key = f"compiled_segment_{i}"
                    if prompt_key in outputs:
                        prompt = outputs[prompt_key]
                        print(f"\n   Prompt {i} 预览:")
                        print(f"   {prompt[:300]}...")
                except Exception as e:
                    print(f"   [ERROR] 片段 {i} 失败: {e}")
    else:
        print(f"   [WARNING] 状态文件不存在: {state_file}")
except Exception as e:
    print(f"   [ERROR] 读取状态失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("导演流水线执行完成!")
print("=" * 80)
