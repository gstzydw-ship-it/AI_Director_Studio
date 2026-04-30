#!/usr/bin/env python3
"""
简化版导演流水线测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("导演流水线测试 (简化版)")
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
print(test_script)

# 导入
print("\n[1] 导入模块...")
try:
    from agents.director_graph import run_phase_1_planning, clear_state
    print("   [OK]")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# 清理状态
print("\n[2] 清理状态...")
clear_state()
print("   [OK]")

# 准备参考图片
print("\n[3] 准备参考图片...")
MINIMAL_JPG = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAABAAEDAREAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwD3iAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//Z"
reference_images = [MINIMAL_JPG, MINIMAL_JPG, MINIMAL_JPG]
print(f"   准备了 {len(reference_images)} 张图片")

# 运行 Phase 1
print("\n[4] 运行 Phase 1...")
print("   正在调用 LLM，请等待...")
try:
    result = run_phase_1_planning(
        script=test_script,
        aspect_ratio="16:9",
        reference_images=None,
        reference_image_b64s=reference_images,
        speed_mode=False
    )
    print("   [OK] Phase 1 完成")
    print(f"   状态: {result.get('status')}")
    print(f"   消息: {result.get('message')}")
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
