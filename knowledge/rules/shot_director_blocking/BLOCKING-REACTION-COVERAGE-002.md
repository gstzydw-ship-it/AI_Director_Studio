---
rule_id: BLOCKING-REACTION-COVERAGE-002
title: reaction_coverage 必须明确落到主镜头或子镜头
rule_type: hard_constraint
agent_scope:
  - shot_director_blocking
priority: P2
status: active
runtime_retrieval: true
applies_to:
  - reaction_coverage
  - 受击落点
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
