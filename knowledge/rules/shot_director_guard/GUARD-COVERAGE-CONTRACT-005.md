---
rule_id: GUARD-COVERAGE-CONTRACT-005
title: 最终镜头方案必须具备覆盖合同
doc_type: rule_card
rule_type: coverage_contract_guard
owner_agent: shot_director_guard
agent_scope:
- shot_director_guard
- quality_inspector
priority: P0
status: active
pipeline_stage: guard
runtime_retrieval: true
retrieval_key:
- guard-coverage-contract-005
- signals.tailframe_lock
- signals.continuity_lock
- events.cut
- events.tailframe
- risks.reference_misuse
applies_when:
- coverage_role
- cut_reason
- companion_visibility
avoid_when:
- "最终 YAML 已具备 coverage_role、cut_reason、companion_visibility、state_delta、tailframe_role"
- "需要的是重新设计镜头，而非最小补字段"
failure_mode:
- "最终方案缺覆盖合同字段，prompt_compiler 被迫猜测机位功能和尾帧状态。"
output_contract: "只给已有镜头补缺失合同字段；不得重写全段。"
example_good: "在 S04 追加 tailframe_role=最后 0.8 秒回到双人半身关系景。"
example_bad: "发现缺字段后删除原方案，重新设计整组镜头。"
signals:
- tailframe_lock
- continuity_lock
events:
- cut
- tailframe
risks:
- reference_misuse
applies_to:
- coverage_role
- cut_reason
- companion_visibility
- state_delta
- tailframe_role
source_files:
- knowledge/27_规则守门与最小修复规则.md
- knowledge/06_连续性与安全规则.md
- knowledge/rules/prompt_compiler/TAILFRAME-RELATIONSHOT-001.md
conflicts_with: []
supersedes: []
---

# 最终镜头方案必须具备覆盖合同

## 规则

三号规则守门导演必须检查最终 YAML 是否具备可编译合同：

- `coverage_role`
- `cut_reason`
- `companion_visibility`
- `state_delta`
- `tailframe_role`

缺这些字段时，prompt_compiler 会被迫猜测机位功能、切镜原因、同场人物位置和尾帧状态，容易退化成旧错误。

## 最小修复

只给已有镜头补字段，不重写全段。

如果尾镜头是局部或单人，必须把最后 0.5-1 秒拉回可继承关系景，或在 `tailframe_role` 中明确下一段可以继承的空间、人物距离、门/道具状态。
