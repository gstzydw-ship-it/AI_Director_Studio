---
rule_id: BLOCKING-ACTION-FLOW-006
title: 动作导演必须交付动作流程表与事件覆盖表
doc_type: rule_card
rule_type: blocking_flow_contract
agent_scope:
- shot_director_blocking
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- blocking-action-flow-006
- signals.tailframe_lock
- signals.action_coverage
- signals.continuity_lock
- events.tailframe
- risks.reference_misuse
- scene_types.elevator
- scene_types.action
applies_when:
- blocking_plan
- state_chain
- event_coverage
avoid_when: []
signals:
- tailframe_lock
- action_coverage
- continuity_lock
scene_types:
- elevator
- action
events:
- tailframe
risks:
- reference_misuse
applies_to:
- blocking_plan
- state_chain
- event_coverage
- duration_hint
- action_phase
source_files:
- knowledge/26_动作调度与受击覆盖规则.md
- knowledge/28_全场景分镜与转场案例库.md
- knowledge/06_连续性与安全规则.md
conflicts_with: []
supersedes: []
---

# 动作导演必须交付动作流程表与事件覆盖表

## 规则

二号动作调度导演的输出不能只是在骨架上补几个局部字段，还必须把片段动作流程写成可执行合同。每个 fragment 至少补齐：

- `blocking_plan`
- `state_chain`
- `event_coverage`

如果存在 `sub_shots`，还必须补齐：

- `duration_hint`
- `action_phase`

## blocking_plan

用一句到两句说清当前片段的动作推进顺序：谁先动、谁承接、哪一镜负责完整发言、哪一镜只做短重音、何时回到关系景或尾帧复位。

## state_chain

把最容易跳变的状态写成单向链，优先覆盖：

- 手部接触
- 门/电梯/车门
- 道具拿放
- 双人距离
- 站位关系
- 群体聚散

即使状态不变，也要写“保持”。

## event_coverage

必须逐条挂住当前 fragment 的 `source_script_events`。每条至少写：

- `source_event`
- `covered_by`

`covered_by` 必须落到已有 `main_shot` 或 `sub_shot`，不能出现只说“已覆盖”但不给镜头编号的空话。

## sub_shot 执行约束

`duration_hint` 用来约束它只是短重音，不是新的主镜头；`action_phase` 只能写：

- `pre_action`
- `mid_action`
- `impact`
- `reaction`
- `reset`
