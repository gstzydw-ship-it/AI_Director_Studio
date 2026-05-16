---
rule_id: SHOWRUNNER-REQUIRED-PROP-HANDOFF-002
title: 场景缺失的剧本关键道具必须合理补入可见空间
doc_type: rule_card
rule_type: story_conflict_enhancement
owner_agent: director_showrunner
agent_scope:
- director_showrunner
- scene_analyst
- story_planner
- shot_director_layout
- quality_inspector
priority: P0
status: active
pipeline_stage: story_conflict_enhancement
runtime_retrieval: true
retrieval_key:
- showrunner-required-prop-handoff-002
- signals.reference_binding
- signals.continuity_lock
- risks.missing_required_prop
- risks.spatial_jump
applies_when:
- 场景预分析有关键道具缺口
- 剧本关键道具在参考图缺失
- 道具触发动作或尾帧继承
avoid_when:
- "该道具不在原剧本、台词暗示或用户补充要求中。"
- "补入道具会改变主线因果、制造新证据或新增反转。"
failure_mode:
- "剧情增强把剧本关键道具留给 prompt 临时补，导致闹钟、书包、照片等道具位置漂移。"
output_contract: "增强版剧本必须写清缺失关键道具的合理可见起始位置、使用者、状态变化和去向。"
example_good: "沙发旁小台面上放着剧本已要求的闹钟；乔熙伸手拍停后转向小豆丁。"
example_bad: "乔熙拍停闹钟，但前文没有任何闹钟位置或可触达空间。"
signals:
- reference_binding
- continuity_lock
scene_types:
- interior
- domestic_scene
- constrained_space
events:
- object_handoff
- action_peak
risks:
- missing_required_prop
- spatial_jump
applies_to:
- 剧情增强
- 关键道具
- 首帧前置状态
source_files:
- knowledge/rules/scene_analyst/SCENE-REQUIRED-PROP-GAP-002.md
- knowledge/rules/director_showrunner/SHOWRUNNER-STORY-ENHANCE-001.md
conflicts_with: []
supersedes: []
---

# 场景缺失的剧本关键道具必须合理补入可见空间

## 规则

当 `scene_analyst` 输出“关键道具缺口”时，`director_showrunner` 必须把它当作“剧本已有但参考图未显示”的施工缺口，而不是当成新增剧情。

增强版剧本必须补清：

- 道具在动作开始前位于哪个合理可见空间。
- 谁能触到它。
- 它如何参与动作。
- 动作后它的状态或去向。

## 可补范围

允许补入的位置必须满足：

- 依附当前场景内合理家具或台面。
- 不改变既有固定物体和入口、沙发、茶几等相对关系。
- 不制造新剧情线索。
- 不把补道具写成镜头语言或特写方案。

## 禁止

- 禁止新增剧本外关键道具。
- 禁止把缺失道具交给最终 prompt 临时脑补。
- 禁止只在台词或动作里突然使用道具，却没有前置可见位置。
- 禁止把“关键道具缺口”展开成新事件、新台词或新反转。

## 交接

`节奏总控交接` 必须提醒下游：该道具是剧本关键道具，参考图缺失但已按合理空间补入；后续拆片、镜头摆位和 prompt 编译必须继承它的起始位置和状态变化。
