---
rule_id: MOTION-MODALITY-001
title: 运镜模态必须明确区分
doc_type: rule_card
rule_type: camera_movement
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- motion-modality-001
- signals.action_coverage
- events.collision
- risks.blood_avoidance
- scene_types.action
applies_when:
- 推镜
- 变焦
- 横移
avoid_when: []
signals:
- action_coverage
scene_types:
- action
events:
- collision
risks:
- blood_avoidance
applies_to:
- 推镜
- 变焦
- 横移
- 摇摄
- 俯仰
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 运镜模态必须明确区分

## 规则

Seedance 对不同摄影机运动的理解并不对称，写法必须明确：

- 推镜：机位物理推进，背景透视会变化。
- 变焦：焦距光学变化，机位本体不移动。
- 横移：机位平移，透视关系随位置变化。
- 摇摄：机位固定，只做水平扫视。
- 俯仰：机位固定，只做上下视角调整。

## 禁止

- 把推镜写成变焦。
- 把横移写成摇摄。
- 写成“镜头一边推近一边变焦一边横移一边扫过去”。

若必须叠加，改写成时间节拍：先固定，随后缓慢推近，最后轻微摇到受击者。

