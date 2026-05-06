---
rule_id: SHOT-ACTION-COVERAGE-001
title: 动作戏先保全貌再拆冲击
doc_type: rule_card
rule_type: shot_calling
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- shot-action-coverage-001
- signals.vertical_framing
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.reaction
- events.tailframe
- risks.vertical_closeup_overuse
- risks.reference_misuse
- risks.privacy_body
- dialogue_types.argument_escalation
- dialogue_types.reaction_beat
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- 动作戏
- 爆发戏
- 竖屏动作
avoid_when: []
signals:
- vertical_framing
- tailframe_lock
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- action
- intimacy_privacy
events:
- reaction
- tailframe
risks:
- vertical_closeup_overuse
- reference_misuse
- privacy_body
dialogue_types:
- argument_escalation
- reaction_beat
aspect_ratios:
- '9:16'
applies_to:
- 动作戏
- 爆发戏
- 竖屏动作
source_files:
- knowledge/20_镜头库与机位库.md
conflicts_with: []
supersedes: []
---

# 动作戏先保全貌再拆冲击

## 规则

动作/爆发戏要先用较完整景别保住动作全貌，再用近景或局部特写拆解冲击瞬间。

推荐顺序：

- 全景或中全景建立动作编舞。
- 关键冲击点切近。
- 手、脚、道具、身体接触点作为局部落点。
- 回到人物关系或尾帧状态。

## 竖屏差异

竖屏动作优先沿纵深或对角线方向，不要长时间横向追拍；可用局部特写和反应镜头替代复杂全景编舞。

## 禁止

大范围动作不宜使用长焦压缩镜头；禁止三快叠加。

