---
rule_id: PROMPT-CURRENT-SEGMENT-ONLY-001
title: Prompt只输出当前片段
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
  - 多段流程
  - 当前片段
  - 历史片段污染
---

# Prompt只输出当前片段

## 规则

Prompt Compiler 只能输出当前正在编译的片段，不得把片段 1、片段 2 的完整 prompt 或动作时间轴复制进片段 3。

允许读取历史片段的目的只有：

- 理解上一段尾帧状态。
- 避免人物、门、道具状态断裂。
- 保持角色身份和空间轴线连续。

## 禁止

- 在当前片段输出中带入其他片段标题。
- 把历史片段时间轴拼接进当前输出。
- 因 `state.result` 或 `prompt_compiler` 旧别名残留而展示旧片段。

