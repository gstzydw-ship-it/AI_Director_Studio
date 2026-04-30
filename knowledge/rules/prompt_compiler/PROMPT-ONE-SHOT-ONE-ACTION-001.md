---
rule_id: PROMPT-ONE-SHOT-ONE-ACTION-001
title: 一镜一主动作
doc_type: rule_card
rule_type: prompt_timeline
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
  - 时间轴
  - 动作描述
  - 可生成性
---

# 一镜一主动作

## 规则

一个时间段只能有一个主驱动动作。

其他信息只能作为：

- 表情承接。
- 视线变化。
- 局部动作。
- 受击反应。
- 机位调整。

## 禁止

不要把起身、奔跑、回头、挥手、推门、坐下、抢东西并列塞进同一句主镜头里。

## 正确方向

主动作先成立，其他动作作为承接节拍或局部落点补充。

