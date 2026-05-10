---
rule_id: SHOT-COMPLEX-ACTION-DEGRADE-001
title: 复杂物理动作必须蒙太奇降级
doc_type: rule_card
rule_type: action_safety
owner_agent: shot_director
agent_scope:
- shot_director
- quality_inspector
- prompt_compiler
priority: P0
status: active
pipeline_stage: action_safety_degrade
runtime_retrieval: true
retrieval_key:
- shot-complex-action-degrade-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.reaction
- risks.romanticize_collision
- risks.axis_confusion
- risks.privacy_body
- risks.blood_avoidance
- scene_types.dialogue
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- 打脸
- 推搡
- 抢夺
avoid_when:
- "simple_low_risk_action"
- "explicit_no_contact_contract"
failure_mode:
- "unsafe_full_contact_physics_in_one_shot"
output_contract: "Degrade complex contact into 2-4 safe montage shots: setup, pre-impact cutout, reaction, result hint."
example_good: "手部前摇后在接触前切走，再给受击反应和散落道具。"
example_bad: "一个全景完整展示击打、倒地和多人推搡。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- intimacy_privacy
events:
- collision
- reaction
risks:
- romanticize_collision
- axis_confusion
- privacy_body
- blood_avoidance
applies_to:
- 打脸
- 推搡
- 抢夺
- 撞击
- 群体冲突
- 高风险身体接触
source_files:
- knowledge/14_动作描述精细化控制规则.md
- knowledge/21_镜头调用规则与多机位模板.md
conflicts_with:
- ACTION-COLLISION-001
supersedes: []
---

# 复杂物理动作必须蒙太奇降级

## 规则

当剧本出现击打、推搡、抢夺、多人混乱、倒地、强拉强拽、贴身碰撞等复杂物理交互时，`shot_director` 不得把完整交互塞进一个镜头。

必须拆成 2-4 个安全镜头：

- 动作前摇：发起者手、肩、脚步、道具或面部决心，1-2 秒。
- 冲击切出：在接触点前或动作顶点前切走，避免生成真实碰撞。
- 受击反应：承受者面部、身体重心或眼神受击，1.5-3 秒。
- 结果暗示：散落道具、门声、碎杯、衣角晃动、旁观者反应或空间静默，1-2 秒。

如果剧本要求轻微身体接触，只描述已稳定后的状态，不放大接触过程；若存在“零亲密接触”或“保持物理距离”契约，必须服从距离契约。

## 禁止

- 一个镜头内同时写两人完成高密度身体碰撞、长台词、倒地、落泪和关系变化。
- 用全景完整展示击打、扭打、拥挤推搡或多人混战。
- 把意外碰撞拍成拥抱、怀里、贴身暧昧或亲密对视。
- 为了追求完整动作而牺牲人物稳定性、空间轴线和可生成性。

