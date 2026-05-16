---
rule_id: PROMPT-TIMELINE-SHOT-BASE-001
title: 时间段必须先立分镜基底
doc_type: rule_card
rule_type: prompt_timeline
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: timeline_shot_basis
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
avoid_when:
- "当前时间段已经先建立分镜基底。"
failure_mode:
- "时间段先写动作后补镜头，导致模型不知道主体、景别、角度或运动方式。"
output_contract: "每个镜头句按【主体】景别，简洁视角/观看位置，人物动作/台词/反应（切镜触发）输出。"
example_good: "镜头3【2秒】【乔熙】中近景，从商北琛肩后看向乔熙，乔熙眼神停住，听见后半句压过来（反应出现后→镜头4）。"
example_bad: "乔熙抬头愣住，镜头随后切近。"
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

每个镜头句的第一分句，必须先让模型知道这是怎么拍的，再进入动作。

至少明确以下四项：

- 当前主体。
- 主体景别。
- 简洁视角/观看位置。
- 人物动作、台词或反应落点。

静态镜头也要写清基底，例如双人中景、半身中景、中近景、同侧过肩视角、同侧固定视角、办公桌侧面固定视角。

## 正确

```text
镜头1【2秒】【商北琛、乔熙】双人中景，办公桌侧面固定视角，两人隔着办公桌对峙。
镜头3【2秒】【乔熙】中近景，从商北琛肩后看向乔熙，乔熙眼神停住，听见后半句压过来。
```

## 错误

```text
乔熙眼神停住，镜头随后切近。
空间方位和景别硬拼成一个抽象短语。
```

