---
rule_id: BLOCKING-PARENT-SUBSHOT-001
title: 子分镜必须挂靠 parent_shot_id
rule_type: hard_constraint
agent_scope:
  - shot_director_blocking
priority: P2
status: active
runtime_retrieval: true
applies_to:
  - sub_shots
  - parent_shot_id
---

# BLOCKING-PARENT-SUBSHOT-001：子分镜必须挂靠 parent_shot_id

## 适用场景

动作调度导演在已有主分镜骨架上补充子分镜时。

## 执行指令

1. 每个 `sub_shot` 必须包含 `parent_shot_id` 字段。
2. `parent_shot_id` 必须指向当前片段内已存在的 `shot_id`。
3. 不允许出现没有挂靠的"漂浮子分镜"。
4. 如果某个受击反应无法自然挂靠到任何现有主镜头，优先考虑是否真的需要这个子分镜，而不是凭空新建主镜头。

## 例外边界

无例外。漂浮子分镜在下游编译和质检中会被视为结构错误。
