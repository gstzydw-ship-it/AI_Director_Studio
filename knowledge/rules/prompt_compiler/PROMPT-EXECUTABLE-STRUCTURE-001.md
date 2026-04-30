---
rule_id: PROMPT-EXECUTABLE-STRUCTURE-001
title: Prompt必须像可直接执行的导演指令
doc_type: rule_card
rule_type: prompt_compilation
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
  - Seedance Prompt
  - 输出结构
  - 可执行性
---

# Prompt必须像可直接执行的导演指令

## 规则

最终 Seedance prompt 应优先追求结构清楚、句子完整、信息足够、可直接执行，而不是越短越好。

每个片段至少应承载：

- 场面空间。
- 人物位置。
- 动作推进。
- 台词落点。
- 主分镜切换。
- 子分镜变化。
- 表情细节。
- 光线关系。
- 连续性约束。
- 参考图继承关系。

## 禁止

- 只输出关键词串。
- 只输出概念标签。
- 用技术表格替代自然导演句。

