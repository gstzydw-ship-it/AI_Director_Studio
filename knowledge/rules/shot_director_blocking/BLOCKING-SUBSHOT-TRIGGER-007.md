---
rule_id: BLOCKING-SUBSHOT-TRIGGER-007
title: 子镜头必须由信息增量触发
doc_type: rule_card
rule_type: subshot_trigger_strategy
agent_scope:
- shot_director_blocking
- shot_director_guard
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- blocking-subshot-trigger-007
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.door_state
- events.reaction
- events.cut
- risks.door_state_jump
- risks.privacy_body
- risks.blood_avoidance
- dialogue_types.reaction_beat
- scene_types.elevator
- scene_types.dialogue
- scene_types.action
- scene_types.suspense
- scene_types.intimacy_privacy
applies_when:
- sub_shots
- reaction_coverage
- action_insert_slot
avoid_when: []
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- elevator
- dialogue
- action
- suspense
- intimacy_privacy
events:
- collision
- door_state
- reaction
- cut
risks:
- door_state_jump
- privacy_body
- blood_avoidance
dialogue_types:
- reaction_beat
applies_to:
- sub_shots
- reaction_coverage
- action_insert_slot
- information_reveal
source_files:
- knowledge/28_全场景分镜与转场案例库.md
- knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes: []
---

# 子镜头必须由信息增量触发

## 规则

`shot_director_blocking` 不应随机添加子镜头，也不应因为害怕碎切而永远不添加子镜头。`sub_shots` 只能在出现明确的信息增量时使用。

允许触发 `sub_shots` 的情况：

- 关键道具改变剧情理解，例如手机、照片、合同、门缝、戒指、血迹、文件。
- 手部动作改变人物关系，例如抓住、松开、递出、收回、按住、推开。
- 反应比台词更重要，例如被命中后短暂停顿、失语、视线断开、身体重心后移。
- 动作需要桥接，例如人物过门槛、擦身、撞上、转身离开，主镜头无法同时看清起点和结果。
- 需要延迟或隐藏信息，例如先看角色发现，再看被发现物，而不是直接亮出答案。
- 声音落点需要视觉重音，例如门锁响、脚步停住、杯子落桌、手机震动。

## 禁止

- 不得为每个微表情单独开子镜头。
- 不得把没有新信息的眼神、嘴角、手指、衣角写成子镜头。
- 不得用子镜头替代主镜头必须承担的动作路径。
- 不得让 `sub_shot` 独立建立新场地、新人物或新事件。
- 不得为了“电影感”在完整台词中间插入无信息特写。

## 必填判断

当一个片段同时存在以下两类以上任务时，若完全没有 `sub_shots`，需要重新判断是否过度保守：

- 信息揭示
- 道具状态变化
- 身体接触
- 受击反应
- 动作过阈值
- 权力关系翻转

如果仍然决定不使用 `sub_shots`，必须在 `blocking_plan` 或 `reaction_coverage` 中说明原因：主镜头已经完整覆盖了信息、动作和反应，额外插入会破坏节奏。

## 执行格式

每个 `sub_shot` 必须挂靠一个既有 `parent_shot_id`，并写清：

- `trigger`: 为什么必须切入。
- `cut_point`: 切在台词落点、动作中段、触碰前、触碰后、视线命中还是声音落点。
- `action_phase`: 只能是 `pre_action`、`mid_action`、`impact`、`reaction`、`reset`。
- `duration_hint`: 默认 0.5-1.5 秒，除非它是唯一的信息揭示镜头。
- `state_delta`: 它改变了什么状态；若没有状态变化，通常不该存在。

