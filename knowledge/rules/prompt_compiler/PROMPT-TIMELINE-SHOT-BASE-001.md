---
rule_id: PROMPT-TIMELINE-SHOT-BASE-001
title: 时间段必须先立分镜基底
doc_type: rule_card
rule_type: prompt_timeline
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- prompt-timeline-shot-base-001
- signals.action_coverage
- events.reaction
- scene_types.action
applies_when:
- 时间轴
- 分镜基底
- 景别显式化
avoid_when: []
signals:
- action_coverage
scene_types:
- action
events:
- reaction
applies_to:
- 时间轴
- 分镜基底
- 景别显式化
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 时间段必须先立分镜基底

## 规则

每个时间段的第一句或第一分句，必须先让模型知道这是怎么拍的，再进入动作。

至少明确以下四项中的三项：

- 当前主体。
- 主体景别。
- 机位高度。
- 拍摄角度。
- 镜头运动方式。

静态镜头也要写清基底，例如固定机位、稳定观察、守住双人关系、越肩观察。

## 正确

```text
商北琛中景，平视 3/4 角度，稳定后退跟拍，他迈步走进大堂。
乔熙胸部以上中近景，平视，轻微推近，她抬头愣住。
```

## 错误

```text
商北琛迈步走进大堂，镜头稳定后退。
乔熙抬头愣住，镜头随后切近。
```

