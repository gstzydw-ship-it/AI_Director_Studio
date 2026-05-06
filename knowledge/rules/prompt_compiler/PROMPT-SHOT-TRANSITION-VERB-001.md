---
rule_id: PROMPT-SHOT-TRANSITION-VERB-001
title: PROMPT-SHOT-TRANSITION-VERB-001
doc_type: rule_card
rule_type: prompt_compilation
agent_scope:
- prompt_compiler
- quality_inspector
priority: P3
status: active
runtime_retrieval: true
retrieval_key:
- prompt-shot-transition-verb-001
- signals.action_coverage
- events.rush_in
- events.door_state
- events.cut
- risks.door_state_jump
- scene_types.elevator
- scene_types.action
applies_when: []
avoid_when: []
signals:
- action_coverage
scene_types:
- elevator
- action
events:
- rush_in
- door_state
- cut
risks:
- door_state_jump
conflicts_with: []
supersedes: []
---

# PROMPT-SHOT-TRANSITION-VERB-001

## 规则标题
镜头衔接词必须按主体变化准确选择

## 适用范围
- owner_agent: `prompt_compiler`
- 联动 agent: `shot_director` / `quality_inspector`

## 规则内容
将镜头衔接词严格分成四类：
1. **镜头保持在 A 身上**：同主体、同景别基底或同机位、动作继续。
2. **镜头切至 B**：主体变化，必须显式切镜。
3. **镜头切近 / 拉开至 A 的某个景别**：同主体，但景别变化。
4. **固定机位保持，A/B 进入或离开画面**：场景机位不变，人物在画内运动。

## 硬规则
1. 主体变化必须明确写“镜头切至/镜头切到/镜头转向”新主体，不能拿笼统话术糊过去。
2. “同一机位继续”只适用于极少数真延续：同主体动作续接、固定场景机位保持、双人关系景保持。
3. 即使是延续，也优先写“镜头保持在A身上”“双人关系景保持”“电梯口固定机位保持”，少写泛泛的“同一机位继续”。
4. 同主体换景别时，要明确写“切近至 / 拉开至 / 切至A手部短切 / 切至A肩部以上特写”。

## 为什么
Seedance 会把主体变化理解为真实切镜。如果文案还写“同一机位继续”，模型会出现假连续、隐性硬切、主体错乱、空间漂移。

## 正例
- 镜头保持在乔熙身上，她从低头停住到慢慢抬头。
- 镜头切至严飞胸部以上中近景，严飞低头，肩膀收紧。
- 镜头切近至乔熙肩部以上特写，她嘴唇停住，眼神回避。
- 电梯口固定机位保持，乔熙从画面左侧冲入门缝。

## 反例
- 同一机位继续，严飞低头。
- 同一机位继续，镜头里忽然变成 B 的中近景。
- 同主体换成特写却不说明景别变化。

## 质检要点
- 主体变化时是否明确写切镜。
- 同主体换景别时是否明确写切近/拉开。
- 固定机位场景是否写出空间锚点。
- 是否滥用了“同一机位继续”。
