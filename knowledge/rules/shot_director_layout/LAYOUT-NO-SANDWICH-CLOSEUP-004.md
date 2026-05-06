---
rule_id: LAYOUT-NO-SANDWICH-CLOSEUP-004
title: 主分镜禁止中景特写中景碎切
doc_type: rule_card
rule_type: shot_scale_cadence
agent_scope:
- shot_director_layout
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- layout-no-sandwich-closeup-004
- signals.vertical_framing
- signals.action_coverage
- signals.continuity_lock
- risks.vertical_closeup_overuse
- risks.script_invention_risk
- scene_types.action
applies_when:
- 9:16竖屏
- 主分镜骨架
- 景别递进
avoid_when: []
signals:
- vertical_framing
- action_coverage
- continuity_lock
scene_types:
- action
risks:
- vertical_closeup_overuse
- script_invention_risk
aspect_ratios:
- '9:16'
applies_to:
- 9:16竖屏
- 主分镜骨架
- 景别递进
- 情绪表演
source_files:
- knowledge/25_镜头摆位主分镜骨架规则.md
- knowledge/28_全场景分镜与转场案例库.md
conflicts_with: []
supersedes: []
---

# 主分镜禁止中景特写中景碎切

## 规则

一号镜头摆位导演搭主分镜骨架时，禁止把同一主体写成：

- 半身中景
- 脸部或眼神特写
- 回到同一角度半身中景

这种结构通常没有新增空间信息，会把节奏切碎，并诱导视频模型把特写拖成整张大头。

## 9:16 表情处理

竖屏里表现表情变化，默认使用：

- 半身中景
- 胸口以上中近景
- 肩部以上特写

不要使用整张脸贴满画面的“大头”作为常规情绪镜头。眼神、眉头、呼吸等微表情可以在主镜头内完成，只有真正承担新信息或强心理压迫时才允许短暂切近。

## 允许切近的条件

只有满足至少一个条件，才允许从关系镜头切近：

- 出现新的视线目标
- 出现新的动作锚点
- 出现新的权力关系变化
- 出现必须被观众识别的物件或信息
- 情绪已经到达不能用当前景别承接的顶点

如果只是“眉头微皱”“目光变冷”“表情变化”，不要把它升成主镜头特写。
