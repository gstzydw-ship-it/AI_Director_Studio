---
rule_id: GLOBAL-ASPECT-001
title: 画幅 9:16 刚性锁定
doc_type: rule_card
rule_type: global_constraint
owner_agent: story_planner
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
- shared
priority: P0
status: active
pipeline_stage: global_constraint
runtime_retrieval: true
retrieval_key:
- global-aspect-001
- signals.vertical_framing
- risks.vertical_closeup_overuse
applies_when:
- 画幅
- aspect_ratio
- 竖屏
avoid_when:
- "用户在输入中显式指定 16:9。"
failure_mode:
- "Agent 自行改画幅。"
- "竖屏片段按横屏构图设计。"
output_contract: "输出并继承 aspect_ratio，默认锁定 9:16。"
example_good: "aspect_ratio: 9:16，构图以纵深调度为主。"
example_bad: "未确认就改成 16:9 横屏。"
signals:
- vertical_framing
risks:
- vertical_closeup_overuse
aspect_ratios:
- '9:16'
- '16:9'
applies_to:
- 画幅
- aspect_ratio
- 竖屏
source_files:
- external:交付物六
conflicts_with: []
supersedes: []
---

# 画幅 9:16 刚性锁定

## 规则

所有输出的 Seedance prompt 必须锁定画幅为 9:16 竖屏（除非用户在输入时显式指定 16:9）。

画幅是全局刚性约束，不允许任何 Agent 在执行过程中自行修改画幅设定。

## 约束

- 竖屏构图必须以 Z 轴纵深调度为主。
- 所有景别、机位、运镜方案必须基于 9:16 竖屏画幅设计。
- prompt_compiler 输出时必须在画幅锚点段明确写出 9:16。
