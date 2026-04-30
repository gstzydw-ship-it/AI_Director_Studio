---
rule_id: BLOCKING-CUT-ANCHOR-TIMING-004
title: 子分镜切镜必须有动作或信息锚点
doc_type: rule_card
rule_type: blocking_cut_timing
agent_scope:
  - shot_director_blocking
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/26_动作调度与受击覆盖规则.md
  - knowledge/28_全场景分镜与转场案例库.md
conflicts_with: []
supersedes: []
applies_to:
  - sub_shots
  - reaction_coverage
  - dialogue_coverage
  - match_on_action
---

# 子分镜切镜必须有动作或信息锚点

## 规则

二号动作调度导演新增任何 `sub_shot` 时，必须至少命中一个锚点：

- 动作锚点：转身、落脚、手碰道具、停步、出画、入画
- 视线锚点：看向新对象，或被看对象进入画面
- 信息锚点：文件、手机、门、空间变化、群体反应
- 权力锚点：压制者占位变化，受压者退让或失语
- 声音锚点：对白落点、脚步炸开、环境瞬间安静

没有锚点的表情插切，不应成为子分镜。

## 切镜时机

动作匹配剪辑要切在动作中间态，不要等动作完成后再切。

- 上一镜在动作完成约 50% 到 70% 时切出
- 下一镜从动作完成约 30% 到 50% 接上
- 出画入画可以压缩无叙事增量的位移

## 对白完整性

一句台词承担命令、威胁、揭示、冷处理时，优先用稳定关系镜头或半身中景完整承接。不要为了“有电影感”在一句话中间插入无信息增量的脸部特写。

切到单人镜头时，必须交代其他角色的处理方式：继续可见、边缘虚化、前景肩影、画外左侧、画外右侧、已经出画。不能让刚刚同场的人物在下一秒无解释消失。
