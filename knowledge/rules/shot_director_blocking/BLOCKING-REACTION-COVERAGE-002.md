---
rule_id: BLOCKING-REACTION-COVERAGE-002
title: reaction_coverage 必须明确落到主镜头或子镜头
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
- blocking-reaction-coverage-002
- signals.action_coverage
- events.collision
- events.reaction
- risks.blood_avoidance
- scene_types.action
applies_when:
- reaction_coverage
- 受击落点
avoid_when:
- "当前片段是纯环境建立且已显式声明无需受击覆盖"
- "layout 阶段尚未进入反应落点补齐"
failure_mode:
- "reaction_coverage 只写有反应或情绪传递，没有落到具体镜头编号。"
output_contract: "reaction_coverage 必须写明受击或信息冲击落在哪个 shot_id；无需要时显式说明。"
example_good: "reaction_coverage: 受击停顿落在 S02-a；本段无额外独立受击镜头。"
example_bad: "reaction_coverage: 这里要表现她被击中的复杂情绪。"
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
- reaction_coverage
- 受击落点
conflicts_with: []
supersedes: []
---

# BLOCKING-REACTION-COVERAGE-002：reaction_coverage 必须明确落到主镜头或子镜头

## 适用场景

动作调度导演为每个片段补齐 `reaction_coverage` 时。

## 执行指令

1. `reaction_coverage` 必须明确写出受击或信息冲击落在当前片段的哪个 `shot_id`（主分镜或子分镜）。
2. 不允许写"有受击反应"而不给出具体落点。
3. 不允许写"情绪传递"而不挂靠到可见的镜头。
4. 如果本段确实没有高冲击信息，必须显式写明"本段无需独立受击镜头"。
5. `reaction_coverage` 应当是短合同句，不允许发展成段落散文。

## 例外边界

纯环境交代或空间建立片段可以写"无需受击覆盖"，但必须显式声明。
