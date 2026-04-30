---
rule_id: SHOT-DIALOGUE-PAUSE-001
title: 长对白必须切出气口
doc_type: rule_card
rule_type: dialogue_rhythm
agent_scope:
  - shot_director
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/04_对白与表演镜头规则.md
  - knowledge/15_故事节奏控制规则.md
conflicts_with: []
supersedes: []
applies_to:
  - 长对白
  - 语言对峙
  - 反应镜头
  - 微停顿
---

# 长对白必须切出气口

## 规则

当单句对白超过 15 个中文字符、预计发音超过 4 秒，或 10 秒内连续出现 3 句以上高压对白时，`shot_director` 必须切出无台词气口。

推荐结构：

- 讲话者半身或中近景承接第一段台词。
- 听者反应镜头或关键道具插入，1.0-2.5 秒，无嘴部说话动作。
- 回到讲话者更近景别或更稳定构图，承接后半段台词。

对白可以拆分给不同镜头，但只能在原文已有标点、语气停顿或完整短语边界处切分。所有 `assigned_dialogue` 按时间顺序拼回后，必须与原始对白一字不差。

## 禁止

- 不得删字、换词、润色、概括或改写对白。
- 不得把一个完整词组从中间切断。
- 不得让同一镜头承载长对白、复杂动作和大幅运镜。
- 不得用无意义走路、转身、低头填满气口；气口必须是反应、线索、停顿或关系压力。
