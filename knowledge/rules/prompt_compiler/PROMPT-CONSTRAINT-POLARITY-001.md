---
rule_id: PROMPT-CONSTRAINT-POLARITY-001
title: 约束集中写入且时间轴正向表达
doc_type: rule_card
rule_type: prompt_constraint
agent_scope:
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
applies_to:
  - 硬约束
  - 时间轴
  - 否定词污染
  - 禁止字幕
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
