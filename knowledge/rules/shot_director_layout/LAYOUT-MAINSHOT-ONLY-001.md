---
rule_id: LAYOUT-MAINSHOT-ONLY-001
title: 主分镜骨架阶段只输出主镜头合同
doc_type: rule_card
rule_type: shot_layout_contract
owner_agent: shot_director_layout
agent_scope:
- shot_director_layout
- quality_inspector
priority: P0
status: active
pipeline_stage: layout
runtime_retrieval: true
retrieval_key:
- layout-mainshot-only-001
- signals.action_coverage
- events.collision
- events.reaction
- risks.blood_avoidance
- dialogue_types.long_dialogue_compression
- dialogue_types.reaction_beat
- scene_types.action
applies_when:
- 主分镜骨架
- main_shots
- 输出合同
avoid_when:
- "当前阶段是 shot_director_blocking，需要补 reaction_coverage 或 sub_shots"
- "当前阶段是 shot_director_guard，只允许最小修复既有方案"
failure_mode:
- "layout 阶段抢先输出 reaction_coverage、sub_shots 或解释散文。"
output_contract: "只输出 fragment_id、fragment_intent、continuity_anchor、main_shots。"
example_good: "fragment_id、fragment_intent、continuity_anchor、main_shots 齐全；受击点留给 blocking。"
example_bad: "在 main_shots 后继续补 sub_shots、reaction_coverage。"
signals:
- action_coverage
scene_types:
- action
events:
- collision
- reaction
risks:
- blood_avoidance
dialogue_types:
- long_dialogue_compression
- reaction_beat
applies_to:
- 主分镜骨架
- main_shots
- 输出合同
source_files:
- knowledge/25_镜头摆位主分镜骨架规则.md
- knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes: []
---

# 主分镜骨架阶段只输出主镜头合同

## 规则

镜头摆位阶段只允许输出：

- `fragment_id`
- `fragment_intent`
- `continuity_anchor`
- `main_shots`

不允许提前输出：

- `reaction_coverage`
- `sub_shots`
- 任何自由解释文字

如果某个信息更像“反应点”“受击点”“停顿重音”“局部细节”，应留给下一位动作调度导演处理，不要在本阶段提前展开。

## 禁止

- 把局部重音误抬成新的主镜头
- 把未来属于 `sub_shots` 的内容提前写进主镜头骨架
- 一边做摆位，一边把整段动作调度抢先做完
