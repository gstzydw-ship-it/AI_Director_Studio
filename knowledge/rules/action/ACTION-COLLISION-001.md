---
rule_id: ACTION-COLLISION-001
title: 意外碰撞不得浪漫化
doc_type: rule_card
rule_type: action_safety
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
- shot_director_blocking
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- action-collision-001
- signals.action_coverage
- signals.continuity_lock
- events.rush_in
- events.collision
- events.reaction
- risks.romanticize_collision
- risks.privacy_body
- dialogue_types.reaction_beat
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- 冲入
- 撞上
- 扶稳
avoid_when: []
signals:
- action_coverage
- continuity_lock
scene_types:
- action
- intimacy_privacy
events:
- rush_in
- collision
- reaction
risks:
- romanticize_collision
- privacy_body
dialogue_types:
- reaction_beat
applies_to:
- 冲入
- 撞上
- 扶稳
- 身体接触
source_files:
- knowledge/06_连续性与安全规则.md
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 意外碰撞不得浪漫化

## 规则

冲入、撞上、扑到等动作如果在剧本中是意外或阻拦，不得被写成恋爱化拥抱。

正确方向：

- 短促失衡。
- 冷静稳住。
- 身体接触有明确物理目的。
- 接触后快速进入新的对峙或停顿状态。

## 禁止

- 扑进怀里。
- 拥抱。
- 贴身。
- 亲密对视。
- 慢动作恋爱化凝视。

