---
rule_id: PROMPT-HARD-CONSTRAINT-DEDUP-001
title: 硬约束去重与集中收束
doc_type: rule_card
rule_type: prompt_constraint
agent_scope:
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
applies_to:
  - 硬约束
  - 时间轴
  - prompt清洗
---

# 硬约束去重与集中收束

## 规则

硬约束只能集中写在【核心禁忌】或【约束】中。时间轴段落只写当前镜头可见的正向状态，不逐段重复同一串禁止项。

必须去重的约束包括：

- 禁止字幕、屏幕文字、英文字幕和文字浮层。
- 仅保留当前戏份角色。
- 轴线、门状态、物理距离和尾帧继承。
- 禁止亲密化、拥抱、怀里、贴身暧昧。

## 禁止

- 每个时间段末尾重复粘贴同一组禁忌。
- 把“严飞不出现”等负面约束写进每个镜头主体动作。
- 用禁忌堆叠替代清楚的画面状态。
