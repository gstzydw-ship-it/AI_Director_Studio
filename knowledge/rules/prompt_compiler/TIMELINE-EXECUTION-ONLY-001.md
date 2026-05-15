---
rule_id: TIMELINE-EXECUTION-ONLY-001
title: 时间轴纯净执行规则
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: timeline_purity_validation
runtime_retrieval: true
retrieval_key:
- timeline-execution-only-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.cut
- risks.romanticize_collision
- risks.axis_confusion
- dialogue_types.long_dialogue_compression
- scene_types.dialogue
- scene_types.action
- scene_types.intimacy_privacy
applies_when: 编写 Prompt 时间轴段落时
avoid_when:
- "编写约束区、说明区或非时间轴元信息时。"
failure_mode:
- "时间轴混入规则复读、禁忌强调或幕后解释，污染可执行画面指令。"
output_contract: "时间轴只写画面内可见动作、运镜、调度、表情变化和对白声音。"
example_good: "乔熙半身中景，她听到声音后抬头，视线对上商北琛。"
example_bad: "这体现了她紧张退无可退的心理。无字幕无屏幕文字。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- intimacy_privacy
events:
- cut
risks:
- romanticize_collision
- axis_confusion
dialogue_types:
- long_dialogue_compression
conflicts_with: []
supersedes: []
instruction: 时间轴内仅允许描写画面内的可见动作、运镜和调度，严禁混入任何幕后解释、禁忌强调或规则复读。
---

# 时间轴纯净执行规则

## 核心规则
1. **只写执行**：【时间轴】的每一句都应当直接映射为画面内发生的事件，包含：镜头运动、景别变化、人物视角/观看位置、物理动作、表情变化和对白声音。
2. **禁止禁忌复读**：像“禁止字幕”、“保持轴线不变”、“不能生成其他人”这样的禁令或负向约束，必须全部移动到【全段硬约束】中集中管理。绝对禁止在每一个时间节点末尾反复唠叨。
3. **禁止导演场外音**：时间轴是给视觉模型直接生成画面的指令，禁止加入解释性文字（如“这里展现了紧张感”、“为了承接下一段”）。模型看不懂导演意图，只看得懂可见的物理改变。

## 反例（污染了禁忌和解释的时间轴）
```
3.1-5.3秒：乔熙半身中景，画面右侧位置不变。这体现了她紧张退无可退的心理。无字幕无屏幕文字。
5.3-7.8秒：回到商北琛半身景。保持零亲密接触。严飞不可出现。
```

## 正例（纯粹执行动作）
```
3.1-5.3秒：乔熙半身中景，画面右侧位置不变。她听到声音后抬头，视线对上商北琛，呼吸短促停一拍。
5.3-7.8秒：回到商北琛半身景或双人半身关系景，商北琛仍在画面左侧，声音更轻地说第二句台词。
```
