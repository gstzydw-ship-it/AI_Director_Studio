---
rule_id: GUARD-MINIMAL-REPAIR-001
title: 只修硬伤，不重写方案
doc_type: rule_card
rule_type: hard_constraint
owner_agent: shot_director_guard
agent_scope:
- shot_director_guard
- quality_inspector
priority: P2
status: active
pipeline_stage: guard
runtime_retrieval: true
retrieval_key:
- guard-minimal-repair-001
- risks.script_invention_risk
applies_when:
- 最小修复
- 守门原则
avoid_when:
- "前两位导演的方案没有会导致下游报错或质检 fail 的硬伤"
- "修改目的只是更好看、更有戏或个人偏好"
failure_mode:
- "守门导演把审查当成重写机会，新增内容、改创意或另起炉灶。"
output_contract: "只修复硬伤，不重写镜头创意，不新增非必要内容。"
example_good: "仅补缺失 parent_shot_id 和 tailframe_role，其余镜头顺序保持不变。"
example_bad: "为了更有戏，新增两个特写并重排所有 shot_id。"
risks:
- script_invention_risk
applies_to:
- 最小修复
- 守门原则
conflicts_with: []
supersedes: []
---

# GUARD-MINIMAL-REPAIR-001：只修硬伤，不重写方案

## 适用场景

规则守门导演审查前两位导演的产出，决定是否修改时。

## 执行指令

1. 只修复会导致下游报错或质检 fail 的硬伤。
2. 不重写镜头创意、不另起炉灶。
3. 不为了"更好看"或"更有戏"而新增内容。
4. 修复前必须确认：如果不改这个地方，下游能不能正常工作？
5. 如果下游能正常工作，不改。

## 例外边界

无例外。如果前两位导演的方案没有硬伤，守门导演的输出应当与输入几乎一致。
