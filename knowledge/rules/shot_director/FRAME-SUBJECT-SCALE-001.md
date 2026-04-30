---
rule_id: FRAME-SUBJECT-SCALE-001
title: 切镜必须写清主体景别与看点
doc_type: rule_card
rule_type: framing
agent_scope:
  - shot_director
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
  - 景别显式化
  - 切镜
  - 时间轴
---

# 切镜必须写清主体景别与看点

## 规则

时间轴每个时间段都必须显式出现至少一次主体 + 景别锚点。

凡出现切镜、切回、转镜、切近、切受击者、切局部，都必须写清：

- 切到谁。
- 对应什么景别或局部。
- 切后具体看什么。

## 禁止

- 镜头切回商北琛。
- 镜头更近。
- 镜头切过去。
- 镜头转到乔熙。

## 正确

```text
镜头切至乔熙面部特写，看她把难堪硬说成武器。
画面转到乔熙手指与下颌的局部特写，承接那一下停顿。
```

