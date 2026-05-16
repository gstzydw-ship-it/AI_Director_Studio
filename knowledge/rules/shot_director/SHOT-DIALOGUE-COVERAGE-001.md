---
rule_id: SHOT-DIALOGUE-COVERAGE-001
title: 对话戏基础覆盖
doc_type: rule_card
rule_type: shot_calling
owner_agent: shot_director
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P3
status: active
pipeline_stage: dialogue_coverage
runtime_retrieval: true
retrieval_key:
- shot-dialogue-coverage-001
- signals.vertical_framing
- signals.dialogue_coverage
- signals.action_coverage
- events.collision
- events.reaction
- risks.vertical_closeup_overuse
- risks.blood_avoidance
- dialogue_types.long_dialogue_compression
- dialogue_types.reaction_beat
- scene_types.dialogue
- scene_types.action
applies_when:
- 双人对话
- OTS
- 正反切
avoid_when:
- "no_two_person_dialogue"
- "high_impact_conflict_requires_conflict_rule"
failure_mode:
- "static_talking_heads_without_listener_reaction"
output_contract: "Use relationship shot, OTS or reverse coverage, and listener reaction when information lands."
example_good: "双人中景建立关系，正反切承接对白，信息点给听者反应。"
example_bad: "整段解释型对白只拍说话者站桩。"
signals:
- vertical_framing
- dialogue_coverage
- action_coverage
scene_types:
- dialogue
- action
events:
- collision
- reaction
risks:
- vertical_closeup_overuse
- blood_avoidance
dialogue_types:
- long_dialogue_compression
- reaction_beat
aspect_ratios:
- '9:16'
applies_to:
- 双人对话
- OTS
- 正反切
source_files:
- knowledge/20_镜头库与机位库.md
conflicts_with: []
supersedes: []
---

# 对话戏基础覆盖

## 规则

低强度双人对话默认使用：

- 对白中景。
- OTS 过肩正反打。
- 关系中景建立空间。

竖屏时优先使用纵深机位和正反切，减少横向 OTS 的空间压力。

## 风险

不可长期站桩。即使是解释型对白，也要有子分镜变化、视线落点或受听者反应。

如果对白含信息炸点，必须给受击者反应镜头。

