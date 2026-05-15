---
rule_id: SHOT-TAILFRAME-ACTION-CARRY-011
title: 相邻镜头必须承接尾帧动作状态
doc_type: rule_card
rule_type: continuity
owner_agent: shot_director
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: continuity_guard
runtime_retrieval: true
retrieval_key:
- shot-tailframe-action-carry-011
- signals.tailframe_lock
- signals.continuity_lock
- signals.action_coverage
- events.tailframe
- events.cut
- risks.action_discontinuity
- risks.teleport
applies_when:
- 相邻镜头
- 尾帧继承
- 动作状态链
avoid_when:
- metadata_only_task
failure_mode:
- "人物或道具在下一镜凭空换位置、换坐站状态、换穿戴完成度或换归属。"
output_contract: "S02 及以后必须说明如何承接上一镜尾帧；状态变化必须在画面动作、切镜点或连续性中可追踪。"
example_good: "连续性: 承接上一镜尾帧，小豆丁仍坐在沙发边，乔熙从她身前起身去拿书包。"
example_bad: "S01 两人坐在沙发边；S02 小豆丁突然站在茶几旁，衣服已经穿好。"
signals:
- tailframe_lock
- continuity_lock
- action_coverage
events:
- tailframe
- cut
risks:
- action_discontinuity
- teleport
---

# 相邻镜头必须承接尾帧动作状态

## 核心规则

每一镜的首帧必须能从上一镜尾帧自然长出来。
如果人物、道具或空间状态发生变化，变化必须满足三种方式之一：

- 在上一镜尾帧已经开始。
- 在本镜画面动作里看见过渡。
- 在切镜点写明动作中段匹配剪辑。

## 必须追踪的状态

- 人物坐/站/躺/蹲。
- 人物在沙发、茶几、门口、车内等空间位置。
- 道具归属：谁拿着、放在哪、是否掉落、是否收起。
- 穿戴完成度：衣服、鞋、项链、外套是否已经穿好/戴好。
- 身体接触：抓住、抱住、扶住、松开、躲避。

## 禁止

- 上一镜人物坐在沙发边，下一镜没有起身过程就站到茶几旁。
- 上一镜孩子还没穿好衣服，下一镜直接已经穿戴整齐。
- 上一镜书包没出现，下一镜突然在人物手里。
- 上一镜手机在耳边，下一镜没有放下就变成双手套衣服。

## 修复方式

- 保持上一镜状态，不让人物换位。
- 在本镜开头写“承接上一镜尾帧，谁仍在哪里”。
- 把无信息位移压进一个关系镜头内完成。
- 需要切换景别时，用动作中段匹配剪辑，而不是跳到动作完成后。
