#!/usr/bin/env python3
"""监控任务执行状态"""
import json
import os

state_file = 'K:/AI_Director_Studio_Pack_20260417/AI_Director_Studio/output/pipeline_state.json'
log_file = 'K:/AI_Director_Studio_Pack_20260417/AI_Director_Studio/output/ui.log'

print('=' * 70)
print('监控任务执行状态')
print('=' * 70)

# 读取状态文件
if os.path.exists(state_file):
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    print(f"\n[状态] {state.get('status', 'unknown')}")
    print(f"[步骤] {state.get('step', 'unknown')}")
    print(f"[消息] {state.get('message', '')}")
    error = state.get('error', '')
    print(f"[错误] {error if error else '无'}")
    print(f"[开始时间] {state.get('started_at', 'unknown')}")
    
    # 检查agent输出
    outputs = state.get('agent_outputs', {})
    print(f"\n[Agent输出状态]")
    for agent in ['rhythm_rewrite_director', 'scene_analyst', 'story_planner', 'shot_director']:
        status = '完成' if outputs.get(agent) else '未开始'
        print(f"  - {agent}: {status}")
    
    # 显示剧本前100字
    script = state.get('script', '')
    if script:
        print(f"\n[当前剧本前100字]")
        print(f"  {script[:100]}...")
else:
    print('\n[警告] 状态文件不存在')

# 读取日志文件最后30行
print('\n' + '=' * 70)
print('最近日志 (最后30行):')
print('=' * 70)
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for line in lines[-30:]:
            print(line.rstrip())
else:
    print('  日志文件不存在')
