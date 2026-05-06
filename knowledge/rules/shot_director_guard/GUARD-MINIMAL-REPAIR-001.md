---
rule_id: GUARD-MINIMAL-REPAIR-001
title: 只修硬伤，不重写方案
doc_type: rule_card
rule_type: hard_constraint
agent_scope:
- shot_director_guard
- quality_inspector
priority: P2
status: active
runtime_retrieval: true
retrieval_key:
- guard-minimal-repair-001
- risks.script_invention_risk
applies_when:
- 最小修复
- 守门原则
avoid_when: []
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
