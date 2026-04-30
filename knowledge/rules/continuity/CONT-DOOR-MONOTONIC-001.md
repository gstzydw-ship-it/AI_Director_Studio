---
rule_id: CONT-DOOR-MONOTONIC-001
title: 门状态单调推进
doc_type: rule_card
rule_type: continuity
agent_scope:
  - story_planner
  - shot_director
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/06_连续性与安全规则.md
  - knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
applies_to:
  - 电梯门
  - 门缝
  - 阈值动作
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

