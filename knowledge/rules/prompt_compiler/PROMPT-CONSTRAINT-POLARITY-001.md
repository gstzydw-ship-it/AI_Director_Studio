---
rule_id: PROMPT-CONSTRAINT-POLARITY-001
title: 约束集中写入且时间轴正向表达
doc_type: rule_card
rule_type: prompt_constraint
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: constraint_formatting
runtime_retrieval: true
retrieval_key:
- prompt-constraint-polarity-001
- signals.dialogue_coverage
- signals.continuity_lock
- events.waist_support
- events.door_state
- risks.door_state_jump
- risks.romanticize_collision
- risks.axis_confusion
- dialogue_types.argument_escalation
- scene_types.elevator
- scene_types.dialogue
- scene_types.intimacy_privacy
applies_when:
- 硬约束
- 时间轴
- 否定词污染
avoid_when:
- "当前输出没有硬约束或禁忌约束。"
failure_mode:
- "把禁忌串反复贴入时间轴，或用否定句污染画面描述。"
output_contract: "硬约束集中写在约束区；时间轴内使用正向可见状态。"
example_good: "电梯门保持闭合；画面仅保留商北琛与乔熙。"
example_bad: "每段末尾都写无字幕、门不打开、严飞不出现。"
signals:
- dialogue_coverage
- continuity_lock
scene_types:
- elevator
- dialogue
- intimacy_privacy
events:
- waist_support
- door_state
risks:
- door_state_jump
- romanticize_collision
- axis_confusion
dialogue_types:
- argument_escalation
applies_to:
- 硬约束
- 时间轴
- 否定词污染
- 禁止字幕
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 约束集中写入且时间轴正向表达

## 规则

`prompt_compiler` 必须把硬约束集中放在【核心禁忌】或【约束】中，不得在每个时间轴段落末尾重复粘贴同一组禁忌。

时间轴内部优先写可见、可执行、正向的画面状态：

- 用“电梯门保持闭合”替代反复写“电梯门不打开”。
- 用“画面仅保留商北琛与乔熙”替代反复写“严飞不出现”。
- 用“两人保持半步距离，胸前留有可见空隙”替代亲密接触否定堆叠。
- 用“台词只作为声音或口型存在”承接无字幕规则。

`PROMPT-NOSUBTITLE-001` 仍然有效；含对白时最终【约束】必须保留禁止字幕与屏幕文字的硬句，但不得污染每一个时间轴镜头。

## 禁止

- 在时间轴每一段重复“无字幕无屏幕文字；零亲密接触；轴线不变；严飞不出现”等完整禁忌串。
- 一边写“零亲密接触”，一边在时间轴中写“扶腰、贴身、胸膛、怀里、极近脸距”等冲突词。
- 用大量否定句替代可执行画面状态，导致视频模型注意力被禁忌词吸走。
