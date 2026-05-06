---
rule_id: CONT-STATE-CONTRACT-001
title: 状态合同优先
doc_type: rule_card
rule_type: continuity
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
- shared
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- cont-state-contract-001
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.door_state
- events.reaction
- events.tailframe
- risks.axis_confusion
- risks.reference_misuse
- risks.privacy_body
- scene_types.dialogue
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- active_cast
- offscreen_cast
- state_contract
avoid_when: []
signals:
- tailframe_lock
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- intimacy_privacy
events:
- door_state
- reaction
- tailframe
risks:
- axis_confusion
- reference_misuse
- privacy_body
applies_to:
- active_cast
- offscreen_cast
- state_contract
source_files:
- knowledge/05_剧本拆分与15秒片段规划规则.md
- knowledge/06_连续性与安全规则.md
conflicts_with: []
supersedes: []
---

# 状态合同优先

## 规则

每个片段必须显式携带并继承状态合同：

- `active_cast`：当前片段允许可见并发生动作/台词的人物。
- `offscreen_cast`：上一段可能出现过，但当前片段必须退出或不可见的人物。
- `state_contract.entry_state`：本段首帧的人物位置、空间轴线、门/车/道具初始状态。
- `state_contract.exit_state`：本段尾帧必须留下的状态。
- `state_contract.object_state_transitions`：门、车、道具、身体接触等状态如何单向变化。
- `state_contract.forbidden_continuity`：禁止复活的人、禁止回弹的门状态、禁止偷跑的反应。

## Agent 执行

- `story_planner` 必须在片段规划里生成这些字段。
- `shot_director` 必须继承这些字段，不得用镜头调度改写人物生命周期。
- `prompt_compiler` 只能翻译状态合同，不能因为尾帧可见而增加人物。
- `quality_inspector` 必须把缺失或违反状态合同判为 fail。

