---
rule_id: PROMPT-NOSUBTITLE-001
title: 含对白必须禁止字幕与屏幕文字
doc_type: rule_card
rule_type: prompt_constraint
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- prompt-nosubtitle-001
- signals.dialogue_coverage
- scene_types.dialogue
applies_when:
- 对白
- 字幕
- 屏幕文字
avoid_when: []
signals:
- dialogue_coverage
scene_types:
- dialogue
applies_to:
- 对白
- 字幕
- 屏幕文字
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
- knowledge/08_错误纠偏与判例库.md
conflicts_with: []
supersedes: []
---

# 含对白必须禁止字幕与屏幕文字

## 规则

只要 prompt 中包含台词、口型或画外音，就必须在【约束】中写明：

```text
禁止字幕、屏幕文字、英文字幕和文字浮层，台词只作为声音或口型存在。
```

## 禁止

- `字幕显示`
- `画面出现文字`
- `英文字幕`
- `屏幕文字浮层`
- 会诱发模型生成乱码、水印、假品牌或假界面字的表达。

