---
rule_id: PROMPT-TIME-INHERIT-UPSTREAM-001
title: PROMPT-TIME-INHERIT-UPSTREAM-001
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P3
status: active
pipeline_stage: upstream_timing_inheritance
runtime_retrieval: true
retrieval_key:
- prompt-time-inherit-upstream-001
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.reaction
- events.cut
- events.tailframe
- risks.script_invention_risk
- risks.reference_misuse
- dialogue_types.argument_escalation
- dialogue_types.reaction_beat
- scene_types.action
applies_when:
- "上游时间段"
- "duration_hint"
- "cut_point"
- "节奏继承"
avoid_when:
- "无上游时间结构，仅生成草案且明确允许临时估算。"
failure_mode:
- "编译阶段擅自重切时间、合并镜头、压缩反应或重排节奏。"
output_contract: "严格继承上游 shot duration、duration_hint、cut_point、rhythm、tailframe_role 与 state_chain。"
example_good: "上游 0-4/4-7/7-9 秒，prompt 保留三段时长并翻译。"
example_bad: "为了顺口，把三段并成一段长描述。"
signals:
- tailframe_lock
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- action
events:
- reaction
- cut
- tailframe
risks:
- script_invention_risk
- reference_misuse
dialogue_types:
- argument_escalation
- reaction_beat
conflicts_with: []
supersedes: []
---

# PROMPT-TIME-INHERIT-UPSTREAM-001

## 规则标题
Prompt 时间段必须继承上游镜头时长

## 适用范围
- owner_agent: `prompt_compiler`
- 联动 agent: `story_planner` / `rhythm_rewrite_director` / `shot_director` / `quality_inspector`
- 适用于将 shot_director 施工单翻译为 Seedance / 即梦 2.0 可执行 prompt 的所有片段。

## 规则内容
1. `prompt_compiler` 不能重新切时间，也不能重新决定镜头时长。
2. 最终 prompt 的每个时间段必须继承上游已经确定的 `shot duration`、`duration_hint`、`cut_point`、`rhythm`、`tailframe_role`、`state_chain`。
3. `prompt_compiler` 的职责是翻译镜头施工单，不是二次导演；禁止在编译阶段重新拆镜头、重排主体、重写节奏。
4. 如果上游时长设计不足以承载信息，`prompt_compiler` 必须暴露冲突并请求上游重排，而不是偷偷压缩、拉长或改写时间结构。
5. 片段内时间段应做到“文字和画面一一对应”：每一段都能回答拍谁、在哪里、做什么、怎么拍。

## 为什么
Seedance 2.0 更吃分镜脚本和时间切片。时间切片来自上游节奏设计，不来自编译器。编译器一旦重切时间，就会破坏上游节奏、动作承接和尾帧继承，导致连续性和可控性一起下降。

## 正例
- 上游 shot 规定 0-4 秒为人物起句，4-7 秒为听者反应，7-9 秒为关系景复位；编译时忠实保留三段时长，只翻译成自然镜头语言。
- sub_shot 已标明 `duration_hint: 0.8s`、`action_phase: impact`；编译时把它写成 0.8 秒左右的短重音，不扩成新主镜头。

## 反例
- 为了让 prompt 更顺口，擅自把 3 段并成 1 段长描述。
- 为了减少切镜数，把 2 秒反应镜头塞回上一个说话镜头。
- 为了规避切镜预算，偷偷缩短时长或删除上游节奏段。

## 质检要点
- 是否继承了上游时间长度。
- 是否保留了 `duration_hint` / `cut_point` / `tailframe_role` / `state_chain` 所表达的切点与尾态。
- 是否出现编译器自行重切、重排、重定节奏的行为。
