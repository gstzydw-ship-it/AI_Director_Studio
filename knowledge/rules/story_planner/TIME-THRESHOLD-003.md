---
rule_id: TIME-THRESHOLD-003
title: 阈值段主动做减法
doc_type: rule_card
rule_type: segment_planning
owner_agent: story_planner
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: threshold_segment_planning
runtime_retrieval: true
retrieval_key:
- time-threshold-003
- signals.tailframe_lock
- signals.action_coverage
- signals.continuity_lock
- events.rush_in
- events.collision
- events.door_state
- events.reaction
- events.tailframe
- risks.reference_misuse
- scene_types.action
applies_when:
- 电梯
- 门口
- 新人物冲入
avoid_when:
- "原剧本明确写阻门、按键重开或阈值外人物继续行动。"
failure_mode:
- "保留无叙事增量的走路和群演反应。"
- "让门状态反复开合。"
output_contract: "输出减法后的片段计划，保留核心动作、门状态、进入触发点和尾帧状态。"
example_good: "只保留门未合拢、人物进入、门继续合拢。"
example_bad: "进入后又写门重新打开制造热闹。"
signals:
- tailframe_lock
- action_coverage
- continuity_lock
scene_types:
- action
events:
- rush_in
- collision
- door_state
- reaction
- tailframe
risks:
- reference_misuse
applies_to:
- 电梯
- 门口
- 新人物冲入
- 尾帧续接
source_files:
- knowledge/05_剧本拆分与15秒片段规划规则.md
conflicts_with: []
supersedes: []
---

# 阈值段主动做减法

## 规则

如果一个片段同时包含到达阈值、门状态变化、新人物冲入/撞入、尾帧续接，拆片规划必须主动做减法。

优先保留：

- 当前片段必须发生的核心动作。
- 门状态的单向推进。
- 新人物进入或撞入的物理触发点。
- 尾帧需要留下的状态。

主动舍弃：

- 无关人物残留。
- 多余问候或背景群演反应。
- 已在上一段完成的入场、转身、让路。
- 会让门状态反复开合的额外动作。

