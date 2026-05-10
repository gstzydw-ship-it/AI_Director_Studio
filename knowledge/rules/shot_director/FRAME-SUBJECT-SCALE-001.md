---
rule_id: FRAME-SUBJECT-SCALE-001
title: 切镜必须写清主体景别与看点
doc_type: rule_card
rule_type: framing
owner_agent: shot_director
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: framing_contract
runtime_retrieval: true
retrieval_key:
- frame-subject-scale-001
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.reaction
- events.cut
- risks.blood_avoidance
- dialogue_types.reaction_beat
- scene_types.action
applies_when:
- 景别显式化
- 切镜
- 时间轴
avoid_when:
- "no_cut_or_time_axis"
- "subject_scale_focus_already_explicit"
failure_mode:
- "ambiguous_cut_without_subject_scale_or_viewpoint"
output_contract: "Each cut names subject, shot size or body part, and visible focus."
example_good: "切至乔熙面部特写，看她把难堪压成反击。"
example_bad: "镜头切回乔熙。"
signals:
- action_coverage
- continuity_lock
scene_types:
- action
events:
- collision
- reaction
- cut
risks:
- blood_avoidance
dialogue_types:
- reaction_beat
applies_to:
- 景别显式化
- 切镜
- 时间轴
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 切镜必须写清主体景别与看点

## 规则

时间轴每个时间段都必须显式出现至少一次主体 + 景别锚点。

凡出现切镜、切回、转镜、切近、切受击者、切局部，都必须写清：

- 切到谁。
- 对应什么景别或局部。
- 切后具体看什么。

## 禁止

- 镜头切回商北琛。
- 镜头更近。
- 镜头切过去。
- 镜头转到乔熙。

## 正确

```text
镜头切至乔熙面部特写，看她把难堪硬说成武器。
画面转到乔熙手指与下颌的局部特写，承接那一下停顿。
```

