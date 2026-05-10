---
rule_id: GUARD-STRUCTURE-PRESERVE-002
title: 优先保留主结构与编号
doc_type: rule_card
rule_type: hard_constraint
owner_agent: shot_director_guard
agent_scope:
- shot_director_guard
- quality_inspector
priority: P2
status: active
pipeline_stage: guard
runtime_retrieval: true
retrieval_key:
- guard-structure-preserve-002
- dialogue_types.argument_escalation
applies_when:
- fragment_id
- shot_id
- main_shots 保留
avoid_when:
- "shot_id 存在真实重复、指向错误或结构冲突，必须最小范围重编"
- "当前不是 guard 修复阶段"
failure_mode:
- "守门修复时无故合并 fragment、重排 shot_id、删除无问题 main_shots。"
output_contract: "fragment_id 顺序不变；shot_id 不无故重排；只在真实编号冲突时最小重编。"
example_good: "保留 F02-S01 到 F02-S04，仅把重复的 F02-S03b 改为 F02-S03a。"
example_bad: "为了更整齐，把所有 shot_id 从 S01 重新编号。"
dialogue_types:
- argument_escalation
applies_to:
- fragment_id
- shot_id
- main_shots 保留
conflicts_with: []
supersedes: []
---

# GUARD-STRUCTURE-PRESERVE-002：优先保留主结构与编号

## 适用场景

规则守门导演修复镜头方案时，需要决定是否改动 fragment_id、shot_id 或 main_shots 结构。

## 执行指令

1. `fragment_id` 顺序不变、不合并、不跳号。
2. `shot_id` 保持前两位导演给出的编号，不无故重排。
3. 已有的 `main_shots` 除非存在严重结构错误，否则保留。
4. 不删除没有问题的主分镜。
5. 不把修复当作机会来重新设计镜头层级。

## 例外边界

只有当 shot_id 存在真正冲突（重复编号、指向错误）时，才允许最小范围重编。
