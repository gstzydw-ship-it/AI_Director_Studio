---
rule_id: SHOT-SIMPLE-SEEDANCE-CAMERA-001
title: Seedance 镜头必须降级为单任务短句
doc_type: rule_card
rule_type: camera_language
agent_scope:
  - shot_director
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - 电影分镜、镜头语言与剪辑深度学习报告.md
  - knowledge/21_镜头调用规则与多机位模板.md
  - knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes: []
applies_to:
  - Seedance
  - 镜头导演
  - 运镜降级
  - 轴线连续
---

# Seedance 镜头必须降级为单任务短句

## 规则

`shot_director` 不能把实拍导演现场口令直接交给 Seedance。每个 shot 必须降级成：

- 一个主体焦点。
- 一个景别基底。
- 一个简洁机位。
- 最多一种镜头运动。
- 一个明确叙事任务。

如果一个镜头同时需要入场、说话、听者反应、群体散开、进入电梯或门状态变化，必须拆成多个镜头，用切镜完成减法。

## 禁止

- `纵深中全景到半身中景`
- `中景转电梯口关系景`
- `同轴线偏右/偏左`
- `眼平高度` 作为默认模板词
- `稳定器在人物前方同速后退`
- `稳定器在人物背后同速前进`
- `truck right / truck left`
- `同一镜头内横移到反应再横移回主位`
- `前后景关系/肩线侧身分布` 这类复杂空间说明

## 改写

- `纵深中全景到半身中景` -> `大堂全景` 或 `商北琛半身中景`
- `同一镜头内横移到严飞反应` -> `镜头切至严飞胸部以上中近景`
- `右后方中景转电梯口关系景` -> `电梯口固定中景`
- `稳定器在商北琛前方同速后退` -> `正面平稳跟拍`

## 依据

电影分镜报告强调镜头序列逻辑、动作剪辑和轴线同侧；多机位规则强调机位切换是减法，每段只描述 1-2 个简单动作。Seedance prompt 应优先服务稳定生成，而不是复刻复杂实拍运镜术语。
