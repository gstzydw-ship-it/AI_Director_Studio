---
rule_id: LAYOUT-FIRST-FRAME-SPATIAL-ANCHOR-006
title: 首帧必须先建立人物和关键道具关系
doc_type: rule_card
rule_type: layout_continuity
owner_agent: shot_director_layout
agent_scope:
- shot_director_layout
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: layout
runtime_retrieval: true
retrieval_key:
- layout-first-frame-spatial-anchor-006
- signals.continuity_lock
- signals.reference_binding
- events.action_peak
- events.object_handoff
- risks.spatial_jump
- risks.missing_required_prop
applies_when:
- 首帧
- 双人同场
- 关键道具动作
avoid_when:
- "片段只有单人、无同场关系、无关键道具，且上一段尾帧已经清楚继承。"
failure_mode:
- "直接从单人或局部动作开始，缺少同场人物和关键道具位置，导致人物突然出现或道具跳出。"
output_contract: "main_shots 必须先给首帧关系锚点：在场人物、关键道具、固定物体、可继承尾帧。"
example_good: "首帧同屏建立乔熙在沙发旁台面、闹钟在手边、小豆丁在沙发边、书包在沙发右侧地面。"
example_bad: "首帧只有乔熙拿手机，2 秒后小豆丁突然出现在沙发上。"
signals:
- continuity_lock
- reference_binding
scene_types:
- interior
- domestic_scene
- multi_character_scene
events:
- action_peak
- object_handoff
risks:
- spatial_jump
- missing_required_prop
applies_to:
- 首帧空间锚点
- 人物同场关系
- 关键道具可见
source_files:
- knowledge/rules/scene_analyst/SCENE-REQUIRED-PROP-GAP-002.md
- knowledge/rules/shot_director_layout/LAYOUT-COVERAGE-BLUEPRINT-005.md
- knowledge/rules/shot_director_guard/GUARD-SPATIAL-RESET-BUDGET-004.md
conflicts_with: []
supersedes: []
---

# 首帧必须先建立人物和关键道具关系

## 规则

`shot_director_layout` 在每个片段的第一个主镜头里，必须先建立可继承的空间关系，再允许进入局部动作或单人镜。

首帧关系锚点至少包含：

- 当前片段所有必须同场的人物。
- 会在本片段被触碰、拿起、滑落、递交或揭示的关键道具。
- 一到两个固定物体锚点，例如沙发、茶几、门、柜台、车门。
- 尾帧要继承的状态。

如果关键动作需要局部特写，例如拍闹钟、抓书包提带、照片滑落，局部镜必须挂在首帧关系锚点之后，不能替代首帧。

## 禁止

- 禁止首镜只拍单人，随后让同场人物无解释出现。
- 禁止首镜只拍局部道具，随后让人物关系重置。
- 禁止把“单人镜/局部镜”误写成另一人在场关系消失。
- 禁止参考图没有关键道具时不说明补入位置。

## 输出要求

主镜头列表中第一个镜头必须写清：

- `首帧关系锚点`
- `同场人物位置`
- `关键道具可见性`
- `尾帧职责`

如果做不到，必须在 `需用户确认` 或 `风险` 中阻断，而不是继续输出可生成但会跳位的镜头骨架。
