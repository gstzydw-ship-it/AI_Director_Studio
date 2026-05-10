---
rule_id: SHOT-MOVEMENT-BEAT-001
title: 运镜介入服从节拍功能
doc_type: rule_card
rule_type: camera_movement
owner_agent: shot_director
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P3
status: active
pipeline_stage: movement_rhythm
runtime_retrieval: true
retrieval_key:
- shot-movement-beat-001
- signals.action_coverage
- events.collision
- events.reaction
- risks.blood_avoidance
- dialogue_types.reaction_beat
- scene_types.action
applies_when:
- 运镜
- 节拍
- 停顿
avoid_when:
- "static_pause"
- "movement_has_no_rhythm_function"
failure_mode:
- "camera_more_emotional_than_character"
output_contract: "Choose camera movement by beat function; pauses stay fixed, impact favors cut or hold."
example_good: "逼近段固定到慢推；停顿段固定不漂移。"
example_bad: "炸点时机械推脸，停顿时无动机漂移。"
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
- reaction_beat
applies_to:
- 运镜
- 节拍
- 停顿
- 炸点
source_files:
- knowledge/20_镜头库与机位库.md
conflicts_with: []
supersedes: []
---

# 运镜介入服从节拍功能

## 规则

运镜不是默认加戏，而是服从当前节拍功能。

- 建立：固定优先，可极轻微带动。
- 预压：固定优先，可轻推半步。
- 逼近：固定到慢推，或受控切近。
- 炸点：固定优先，允许切主体，禁止机械推脸。
- 受击：固定优先，之后可逼近。
- 停顿：固定，不加任何运镜。
- 收束：固定或缓退，轻收势。

## 禁止

镜头比人物更激动；停顿段出现无动机漂移；炸点段机械推脸。

