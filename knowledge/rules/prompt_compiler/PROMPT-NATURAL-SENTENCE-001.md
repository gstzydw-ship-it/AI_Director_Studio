---
rule_id: PROMPT-NATURAL-SENTENCE-001
title: 时间轴不是关键词串也不是表单
doc_type: rule_card
rule_type: prompt_language
agent_scope:
  - prompt_compiler
  - quality_inspector
priority: medium
status: active
runtime_retrieval: true
source_files:
  - knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
applies_to:
  - 时间轴
  - 自然中文
  - 表单化防止
---

# 时间轴不是关键词串也不是表单

## 规则

时间轴必须用完整中文句把主体、动作、空间、光线、镜头与落点写在一起。

镜头变化要体现在自然句里，不写成技术表头，也不写成教学标签。

## 禁止

```text
冷白灯，近景，悲伤，电影感，压迫，镜头推进。
主分镜 2，焦段 85mm，机位平视，景别近景，镜头切受击者。
```

## 正确方向

```text
乔熙胸部以上中近景，平视固定机位，她听到后半句时嘴唇停住，视线从商北琛脸上掉到地面。
```

