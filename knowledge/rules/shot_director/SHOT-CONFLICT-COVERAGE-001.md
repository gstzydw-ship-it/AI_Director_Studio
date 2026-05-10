---
rule_id: SHOT-CONFLICT-COVERAGE-001
title: 冲突戏必须覆盖施压与受击
doc_type: rule_card
rule_type: shot_calling
owner_agent: shot_director
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: conflict_coverage
runtime_retrieval: true
retrieval_key:
- shot-conflict-coverage-001
- signals.action_coverage
- events.collision
- events.reaction
- risks.privacy_body
- risks.blood_avoidance
- dialogue_types.argument_escalation
- dialogue_types.reaction_beat
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- 冲突戏
- 信息炸点
- 受击反应
avoid_when:
- "no_pressure_or_impact_beat"
- "pure_exposition_without_reaction_need"
failure_mode:
- "pressure_only_without_hit_reaction"
output_contract: "Cover pressure source, visible hit reaction, and short aftermath pause."
example_good: "施压者说出炸点，切受击者反应，再留半拍停顿。"
example_bad: "施压者一直说，受击者没有镜头。"
signals:
- action_coverage
scene_types:
- action
- intimacy_privacy
events:
- collision
- reaction
risks:
- privacy_body
- blood_avoidance
dialogue_types:
- argument_escalation
- reaction_beat
applies_to:
- 冲突戏
- 信息炸点
- 受击反应
source_files:
- knowledge/20_镜头库与机位库.md
conflicts_with: []
supersedes: []
---

# 冲突戏必须覆盖施压与受击

## 规则

情绪冲突和重大炸点必须同时覆盖：

- 施压者说出或执行冲击动作的画面。
- 受击者被命中的可见反应。
- 炸点后的短暂停顿或身体反应。

推荐组合：

- 情绪递进中近景。
- 情绪顶点特写。
- 受击反应特写或半身受击。
- 必要时补局部特写。

## 风险

双重炸点必须分两次落点。第二炸点必须给第二次受击反应，不得只让施压者一直说。

