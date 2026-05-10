---
rule_id: BLOCKING-DIALOGUE-FIDELITY-003
title: 对白只允许引用原剧本，不得补写
doc_type: rule_card
rule_type: hard_constraint
owner_agent: shot_director_blocking
agent_scope:
- shot_director_blocking
- quality_inspector
priority: P1
status: active
pipeline_stage: blocking
runtime_retrieval: true
retrieval_key:
- blocking-dialogue-fidelity-003
- signals.dialogue_coverage
- signals.action_coverage
- risks.script_invention_risk
- scene_types.dialogue
- scene_types.action
applies_when:
- dialogue_coverage
- 剧本忠实度
avoid_when:
- "当前片段没有 dialogue_coverage"
- "字段只描述动作状态，不引用或覆盖台词"
failure_mode:
- "dialogue_coverage 改写、缩写、合并或新增原剧本没有的台词。"
output_contract: "dialogue_coverage 只能逐字引用原剧本台词；无台词覆盖时写 none。"
example_good: "dialogue_coverage: \"你别过来。\""
example_bad: "dialogue_coverage: \"她低声说自己害怕，让对方不要再逼近。\""
signals:
- dialogue_coverage
- action_coverage
scene_types:
- dialogue
- action
risks:
- script_invention_risk
applies_to:
- dialogue_coverage
- 剧本忠实度
conflicts_with: []
supersedes: []
---

# BLOCKING-DIALOGUE-FIDELITY-003：对白只允许引用原剧本，不得补写

## 适用场景

动作调度导演在补齐对白落点和 `dialogue_coverage` 时。

## 执行指令

1. `dialogue_coverage` 只能引用原始剧本中的台词原文。
2. 不允许缩写、改写、意译或合并原文台词。
3. 不允许新增剧本中没有出现过的台词、旁白、低语、员工议论或心理活动。
4. 如果某个主镜头不覆盖任何台词，`dialogue_coverage` 写 `none`。
5. 不允许把属于其他片段的台词挪到当前片段。

## 例外边界

无例外。凡带引号的台词都必须能在原剧本中逐字找到。
