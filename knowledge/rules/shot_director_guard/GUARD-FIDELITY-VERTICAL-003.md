---
rule_id: GUARD-FIDELITY-VERTICAL-003
title: 优先修复剧本忠实度与竖屏纪律
doc_type: rule_card
rule_type: hard_constraint
agent_scope:
- shot_director_guard
- quality_inspector
priority: P1
status: active
runtime_retrieval: true
retrieval_key:
- guard-fidelity-vertical-003
- signals.vertical_framing
- signals.dialogue_coverage
- signals.action_coverage
- risks.vertical_closeup_overuse
- risks.script_invention_risk
- scene_types.dialogue
- scene_types.action
applies_when:
- 剧本忠实度
- 竖屏纪律
- 9:16 特写限频
avoid_when: []
signals:
- vertical_framing
- dialogue_coverage
- action_coverage
scene_types:
- dialogue
- action
risks:
- vertical_closeup_overuse
- script_invention_risk
aspect_ratios:
- '9:16'
- '16:9'
applies_to:
- 剧本忠实度
- 竖屏纪律
- 9:16 特写限频
conflicts_with: []
supersedes: []
---

# GUARD-FIDELITY-VERTICAL-003：优先修复剧本忠实度与竖屏纪律

## 适用场景

规则守门导演发现多类问题时，需要决定修复优先级。

## 执行指令

1. 剧本外元素（虚构台词、虚构人物、虚构动作）必须立即删除，优先级最高。
2. 9:16 竖屏画幅下，一个片段内不允许所有主镜头都是面部特写。
3. 特写型主镜头在一个片段内最多 1 个。
4. 修复竖屏纪律时，优先把多余特写改为半身中景或中近景，而不是全部删除。
5. `fragment_intent` 和 `reaction_coverage` 如果写成了段落散文，缩短为合同句。

## 例外边界

16:9 横屏画幅下，特写限频规则可适当放宽，但剧本忠实度规则无例外。
