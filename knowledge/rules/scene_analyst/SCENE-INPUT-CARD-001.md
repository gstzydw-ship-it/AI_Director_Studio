---
rule_id: SCENE-INPUT-CARD-001
title: 场景分析九层输入卡必填
doc_type: rule_card
rule_type: scene_analysis
owner_agent: scene_analyst
agent_scope:
- scene_analyst
- story_planner
priority: P0
status: active
pipeline_stage: scene_input_card
runtime_retrieval: true
retrieval_key:
- scene-input-card-001
- signals.tailframe_lock
- signals.action_coverage
- signals.continuity_lock
- signals.reference_binding
- events.cut
- events.tailframe
- events.reference_binding
- risks.privacy_body
- scene_types.action
- scene_types.suspense
- scene_types.intimacy_privacy
applies_when:
- 任务层
- 戏剧层
- 动作层
avoid_when:
- "需要直接设计景别、机位或运镜时交给 shot_director。"
failure_mode:
- "九层输入卡缺层或缺字段。"
- "未声明 segment_function 就给主分镜建议。"
output_contract: "输出九层输入卡，并用 unresolved 列出 unknown 或 null 字段。"
example_good: "任务层到约束层齐全，未知字段显式写 null。"
example_bad: "跳过输入卡，直接给中景和推镜建议。"
signals:
- tailframe_lock
- action_coverage
- continuity_lock
- reference_binding
scene_types:
- action
- suspense
- intimacy_privacy
events:
- cut
- tailframe
- reference_binding
risks:
- privacy_body
applies_to:
- 任务层
- 戏剧层
- 动作层
- 运镜层
- 空间层
- 状态层
- 光线与风格层
- 参考资产层
- 约束层
source_files:
- knowledge/11_场景分析输入卡与导演意图提取.md
conflicts_with: []
supersedes: []
---

# 场景分析九层输入卡必填

## 规则

`scene_analyst` 在输出任何下游字段之前，必须先产出一张完整的九层输入卡。每一层至少输出如下字段，缺失字段必须显式标记 `null` 或 `unknown`，不得默认缺省。

- **任务层**：`task_type`（新编分镜 / 重编 prompt / 审稿 / 最小修正）、`mode`（审稿 / 纯编译 / 风格记录）。
- **戏剧层**：`dramatic_task`、`primary_subject`、`speaker`、`receiver`、`info_bombs[]`、`bomb_order[]`、`segment_function`。
- **动作层**：`primary_action`、`action_completeness`、`must_keep_utterance`、`must_carry_reaction`、`local_action_or_prop_drop`、`needs_mid_sentence_cut`。
- **运镜层**：`shot_primary_goal`、`primary_camera_motion`、`motion_is_physical_or_optical`、`needs_composite_beat`、`stability_constraints`。
- **空间层**：`is_new_scene_or_continuation`、`position_map_ref`、`space_map_ref`、`prev_tailframe_ref`、`first_frame_source`、`segment_boundary_locked`、`axis_definition`、`gaze_and_target`、`blocking_changes`、`spatial_residue_to_keep`。
- **状态层**：`wardrobe_state`、`posture_state`、`hand_landing`、`prop_state`、`micro_physical_state`、`must_inherit_states`。
- **光线与风格层**：`lighting_base`、`time_weather_light_source`、`style_direction`、`style_light_match`、`style_anchor_visual_only`。
- **参考资产层**：`hero_id_images[]`、`rival_id_images[]`、`position_map_image`、`space_map_image`、`prev_tailframe_image`、`@image_to_call`、声明 `no_reference_video_or_audio`。
- **约束层**：`critical_constraints[]`、`private_safety_required`、`reference_only_reinforcement`。

## 禁止项

- 不得直接输出具体景别、机位或运镜——那是 `shot_director` 的职责。
- 不得把某一层缺字段悄悄补成空字符串而不告知下游。
- 不得在未声明 `segment_function` 的情况下输出主分镜建议。

## 正确写法

- 所有字段以结构化 JSON 或 YAML 输出，未知字段写 `null` 并同时在 `unresolved` 数组里列出，交给 `story_planner` 补全。
- `info_bombs[]` 与 `bomb_order[]` 必须同时给出，长度一致。
- 约束层的 `critical_constraints[]` 必须从项目约束白名单里取值（身份一致 / 空间稳定 / 守轴 / 身体完整 / 画面洁净 / …），不允许生造。

## Agent 执行

- `scene_analyst` 负责填入并校验九层；`story_planner` 在片段拆分前读取本输入卡，发现 `unresolved` 字段必须回追 `scene_analyst` 或显式跳过并记录原因。
