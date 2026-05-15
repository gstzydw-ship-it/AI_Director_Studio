---
rule_id: PROMPT-SMALL-ACTION-STABILITY-001
title: PROMPT-SMALL-ACTION-STABILITY-001
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P3
status: active
pipeline_stage: action_stabilization
runtime_retrieval: true
retrieval_key:
- prompt-small-action-stability-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.rush_in
- events.collision
- events.waist_support
- events.door_state
- events.reaction
- risks.door_state_jump
- risks.privacy_body
- dialogue_types.argument_escalation
- scene_types.elevator
- scene_types.dialogue
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- "复杂动作"
- "小动作链"
- "动作稳定性"
avoid_when:
- "上游已提供稳定小动作链且无需重写。"
failure_mode:
- "复杂动作未拆链，时间片同时承担过多事件、对白、反应和运镜。"
output_contract: "将上游动作翻译为小幅连续动作链，写清起点、路径、接触点、终点与结束状态。"
example_good: "她双手仍抓住西装前襟，手指慢慢松开，再落回身体两侧。"
example_bad: "她情绪爆发，猛烈转身冲过去又突然停住。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- elevator
- dialogue
- action
- intimacy_privacy
events:
- rush_in
- collision
- waist_support
- door_state
- reaction
risks:
- door_state_jump
- privacy_body
dialogue_types:
- argument_escalation
conflicts_with: []
supersedes: []
---

# PROMPT-SMALL-ACTION-STABILITY-001

## 规则标题
小幅动作优先，复杂动作拆链

## 规则内容
1. 每个时间片只承担一个核心画面任务。
2. 动作优先写小幅、可连续生成的动作：缓步前行、轻轻抬手、微微仰头、下颌收紧、手指松开。
3. 大动作必须拆成连续小动作链，并继承上一个动作的余势。
4. 一个动作链必须写出起点、路径、接触点、终点、结束状态。
5. 人物动作复杂时，镜头语言要收敛：固定视角、简单跟拍或单一缓推即可。

## 正例
- 她双手仍抓住西装前襟，手指先慢慢松开，双手向自己胸前收回，再自然落回身体两侧。
- 乔熙从门外向电梯门缝冲入，右肩先穿过门缝，脚步没刹住，撞到商北琛胸前，商北琛右手扶住她腰侧，两人停住。

## 反例
- 她情绪爆发。
- 她猛烈转身冲过去又停住。
- 同一时间段同时写入场、对白、群体反应、道具动作、空间变化、情绪特写。

## 质检要点
- 是否把复杂动作拆成小时间段或小动作链。
- 是否写出动作承接与结束状态。
- 人物动作复杂时，镜头是否仍堆叠多个运镜。
