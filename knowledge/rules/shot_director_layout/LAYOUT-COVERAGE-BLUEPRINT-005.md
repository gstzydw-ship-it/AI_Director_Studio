---
rule_id: LAYOUT-COVERAGE-BLUEPRINT-005
title: 主分镜必须先给镜头覆盖蓝图
doc_type: rule_card
rule_type: coverage_blueprint
agent_scope:
  - shot_director_layout
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/25_镜头摆位主分镜骨架规则.md
  - knowledge/02_焦段景深与景别画幅策略.md
  - knowledge/03_镜头切换与推进规则.md
  - knowledge/20_镜头库与机位库.md
  - knowledge/19_Gold_Standard_Prompt范例.md
conflicts_with: []
supersedes: []
applies_to:
  - main_shots
  - coverage_role
  - over_the_shoulder
  - reverse_shot
  - relationship_reset
---

# 主分镜必须先给镜头覆盖蓝图

## 规则

一号镜头摆位导演输出 `main_shots` 时，不能只写主体、景别、角度。每个主镜头必须写清：

- `coverage_role`：它在覆盖链条里的职责
- `cut_reason`：为什么从上一镜头切到这里
- `companion_visibility`：同场关键人物如何保留或离开
- `tailframe_role`：是否承担尾帧复位

## 推荐覆盖链

双人压迫、冷处理、误会撞见、封闭空间对话优先使用：

1. 施压者过肩或纵深中近景
2. 受击者反打中近景
3. 双人半身关系景
4. 手部/道具/身体接触插入的父镜头
5. 尾帧关系复位镜头

## 禁止

- 只写“半身中景、平视、固定”但不写镜头职责
- 单人镜头不交代另一人在前景、边缘、画外哪一侧
- 切镜理由写成“表现情绪”或“更有电影感”
- 最后停在局部特写而没有关系景复位
