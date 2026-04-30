---
rule_id: GUARD-COVERAGE-CONTRACT-005
title: 最终镜头方案必须具备覆盖合同
doc_type: rule_card
rule_type: coverage_contract_guard
agent_scope:
  - shot_director_guard
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/27_规则守门与最小修复规则.md
  - knowledge/06_连续性与安全规则.md
  - knowledge/rules/prompt_compiler/TAILFRAME-RELATIONSHOT-001.md
conflicts_with: []
supersedes: []
applies_to:
  - coverage_role
  - cut_reason
  - companion_visibility
  - state_delta
  - tailframe_role
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
