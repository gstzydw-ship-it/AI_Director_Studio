---
rule_id: TIME-THRESHOLD-003
title: 阈值段主动做减法
doc_type: rule_card
rule_type: segment_planning
agent_scope:
  - story_planner
  - shot_director
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/05_剧本拆分与15秒片段规划规则.md
conflicts_with: []
supersedes: []
applies_to:
  - 电梯
  - 门口
  - 新人物冲入
  - 尾帧续接
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

