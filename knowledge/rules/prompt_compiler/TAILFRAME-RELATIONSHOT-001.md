---
rule_id: TAILFRAME-RELATIONSHOT-001
title: 尾帧连续性与空间关系收束规则
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- shot_director
- quality_inspector
priority: P0
status: active
pipeline_stage: tailframe_closure
runtime_retrieval: true
retrieval_key:
- tailframe-relationshot-001
- signals.tailframe_lock
- signals.action_coverage
- signals.continuity_lock
- events.door_state
- events.tailframe
- risks.door_state_jump
- risks.reference_misuse
- scene_types.elevator
- scene_types.action
applies_when: 设计当前片段的最后一个镜头（尾帧）
avoid_when:
- "下一段剧本明确要求从特定局部特写或道具特写开始接续。"
failure_mode:
- "以局部特写收尾，下一段失去空间和人物站位锚点。"
output_contract: "片段最终尾帧默认回到双人/多人关系景或建立镜头，保留位置、朝向、距离与道具状态。"
example_good: "最后0.5秒切回双人半身关系景收束，电梯门在背景中闭合。"
example_bad: "片段最后停在乔熙手指拨弄头发的局部特写。"
signals:
- tailframe_lock
- action_coverage
- continuity_lock
scene_types:
- elevator
- action
events:
- door_state
- tailframe
risks:
- door_state_jump
- reference_misuse
conflicts_with: []
supersedes: []
instruction: 片段最终尾帧默认必须是双人/多人关系景，局部特写绝对不能作为尾帧，必须为下一片段留下可见的构图和场景锚点。
---

# 尾帧连续性与空间关系收束规则

## 核心痛点
由于多 Agent 视频生成管线强依赖上一段尾帧作为下一段的首帧约束，如果上一段以“眼神特写”、“发梢细节”、“手指按键”等局部特写收尾，下一片段将失去所有的场景结构、人物站位和光线锚点，导致严重的空间漂移和环境突变。

## 核心规则：尾帧优先级
1. **最高优先级**：双人中景 / 双人半身关系景 / 全景建立镜头。
2. **基本要求**：必须能看清主要人物的左右位置、朝向、物理距离，以及场景的核心空间状态（墙面、背景门窗）。
3. **空间锚点可见**：如果本段围绕某个核心道具（如电梯门、办公桌、车门），尾帧中必须能看到该道具的当前状态（如门已闭合）。
4. **禁止截断收尾**：禁止用手部特写、眼神特写、发梢特写、脚步特写或道具局部特写作为片段的最终尾帧。
5. **强制拉回机制**：如果在片段末尾因为情绪或动作表达必须切入局部特写，那么在时间轴的最后 0.5-1 秒，必须加一句“最后切回双人半身关系景收束”来重新建立空间坐标。

## 正确范例
```
7.8-11秒：乔熙仰拍特写，尴尬收回手拨弄头发。最后0.5秒必须切回双人半身关系景收束，商北琛仍在画面左侧，乔熙在右侧，电梯门在背景中完全闭合，两人距离清楚可见。
```
