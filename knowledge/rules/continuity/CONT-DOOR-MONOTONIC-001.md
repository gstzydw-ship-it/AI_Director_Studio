---
rule_id: CONT-DOOR-MONOTONIC-001
title: 门状态单调推进
doc_type: rule_card
rule_type: continuity
owner_agent: quality_inspector
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: continuity_qc
runtime_retrieval: true
retrieval_key:
- cont-door-monotonic-001
- signals.action_coverage
- signals.continuity_lock
- events.door_state
- risks.door_state_jump
- scene_types.elevator
- scene_types.action
applies_when:
- 电梯门
- 门缝
- 阈值动作
avoid_when:
- "原剧本明确写阻门、按开门键、门被挡住或重开。"
failure_mode:
- "门已合拢后再次打开。"
- "门缝收窄后又被冲开。"
output_contract: "检查 state_contract.object_state_transitions 中门状态单向推进。"
example_good: "门未合拢 -> 人进入 -> 门继续合拢 -> 关闭。"
example_bad: "人物进入后电梯门又打开。"
signals:
- action_coverage
- continuity_lock
scene_types:
- elevator
- action
events:
- door_state
risks:
- door_state_jump
applies_to:
- 电梯门
- 门缝
- 阈值动作
source_files:
- knowledge/06_连续性与安全规则.md
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 门状态单调推进

## 规则

电梯门、房门、车门、闸门等阈值物体在同一片段内必须按一个物理方向推进。

合法状态链：

```text
门尚未合拢 -> 人物从将合未合的门缝进入 -> 门继续合拢 -> 门关闭
```

## 禁止

- 人物已进入电梯后，电梯门又打开。
- 门缝已经收窄后，又被冲开。
- 同一片段中写“门合拢”和“重新打开/再次打开/被冲开”。

若剧本确实要求门被重开，必须在 `state_contract` 中明确写出重开的动作原因和人物触发点。

