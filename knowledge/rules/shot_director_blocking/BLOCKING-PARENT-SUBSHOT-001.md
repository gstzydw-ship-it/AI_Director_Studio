---
rule_id: BLOCKING-PARENT-SUBSHOT-001
title: 子分镜必须挂靠 parent_shot_id
doc_type: rule_card
rule_type: hard_constraint
owner_agent: shot_director_blocking
agent_scope:
- shot_director_blocking
- quality_inspector
priority: P2
status: active
pipeline_stage: blocking
runtime_retrieval: true
retrieval_key:
- blocking-parent-subshot-001
- signals.action_coverage
- events.collision
- events.reaction
- risks.blood_avoidance
- scene_types.action
applies_when:
- sub_shots
- parent_shot_id
avoid_when:
- "当前没有 sub_shots"
- "layout 阶段尚未生成可挂靠的 main_shots"
failure_mode:
- "子分镜没有 parent_shot_id，或 parent_shot_id 指向不存在的 shot_id。"
output_contract: "每个 sub_shot 必须包含 parent_shot_id，并指向当前 fragment 既有 main_shot。"
example_good: "sub_shot S02-a: parent_shot_id=S02，trigger=手松开门把。"
example_bad: "sub_shot C1: 手部特写，无 parent_shot_id。"
signals:
- action_coverage
scene_types:
- action
events:
- collision
- reaction
risks:
- blood_avoidance
applies_to:
- sub_shots
- parent_shot_id
conflicts_with: []
supersedes: []
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
