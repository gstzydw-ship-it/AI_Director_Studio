---
rule_id: QC-DIRECTOR-TASTE-SCORE-002
title: 质检必须评估镜头是否有导演选择
doc_type: rule_card
rule_type: director_taste_quality
agent_scope:
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- qc-director-taste-score-002
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- events.collision
- events.reaction
- events.tailframe
- risks.axis_confusion
- risks.reference_misuse
- risks.privacy_body
- risks.blood_avoidance
- scene_types.dialogue
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- quality_review
- shot_director
- layout
avoid_when: []
signals:
- tailframe_lock
- dialogue_coverage
- action_coverage
scene_types:
- dialogue
- action
- intimacy_privacy
events:
- collision
- reaction
- tailframe
risks:
- axis_confusion
- reference_misuse
- privacy_body
- blood_avoidance
applies_to:
- quality_review
- shot_director
- layout
- blocking
source_files:
- knowledge/17_结果质检与回溯修正规则.md
- knowledge/28_全场景分镜与转场案例库.md
conflicts_with: []
supersedes: []
---

# 质检必须评估镜头是否有导演选择

## 规则

`quality_inspector` 不只检查漏事件、越轴、景别不匹配，也必须判断镜头是否像专业导演做出的选择。

每段至少评估四项：

- `attention_clarity`: 观众此刻该看谁是否清楚。
- `emotional_progression`: 镜头顺序是否让情绪逐步升级或降温。
- `shot_irreplaceability`: 每个主镜头是否有不可替代的职责，而不是安全但平庸的重复覆盖。
- `stronger_angle_opportunity`: 是否存在更强的视角、遮挡、前景、反打或关系复位方案。

## 评分要求

如果输出含 LLM 深度质检，请给每项 1-10 分，并说明扣分原因。低于 7 分时必须给出可执行修正建议。

示例：

```yaml
director_taste_score:
  attention_clarity: 8
  emotional_progression: 6
  shot_irreplaceability: 5
  stronger_angle_opportunity: "F03-S02 可从正面中近景改为门框外窥视机位，让观众先看到女主迟疑再看到男主反应。"
```

## 必须指出的问题

- 镜头类型正确，但没有信息增量。
- 每个镜头都安全，但节奏缺少重音。
- 受击反应被台词镜头吞掉。
- 动作路径清楚，但没有情绪落点。
- 全段没有子镜头，且同时存在道具、身体接触、受击或权力翻转。
- 结尾没有关系复位或可继承尾帧。

## 禁止

- 不得只写“通过”“整体合理”。
- 不得只抓格式错而忽略导演选择质量。
- 不得提出抽象建议，如“更电影化”“更有冲击力”；必须说明改哪个 shot、改成什么视角、解决什么观众信息问题。

