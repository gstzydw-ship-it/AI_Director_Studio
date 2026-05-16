---
rule_id: SHOT-ACTION-GROUP-BUDGET-031
title: 动作群戏预算与跨片段节奏
doc_type: rule_card
rule_type: action_group_budget_rhythm
owner_agent: shot_director
agent_scope:
  - shot_director
  - shot_director_layout
  - shot_director_blocking
  - shot_director_guard
  - prompt_compiler
  - quality_inspector
priority: P1
status: active
pipeline_stage: coverage_rhythm_guard
runtime_retrieval: true
retrieval_key:
  - 动作戏专项规则
  - 群戏镜头调度
  - 跨片段景别节奏
  - 预算降级
  - 程序化镜头表
applies_when:
  - 动作戏
  - 四人以上群戏
  - 同一场景连续多个片段
  - 模型可生成性或切镜预算超载
avoid_when:
  - 纯静态单人镜头
  - 不存在动作、群戏或跨片段节奏问题
scene_types:
  - action_scene
  - group_dialogue
  - multi_character_scene
events:
  - action_peak
  - reaction
  - beat_change
risks:
  - same_scale_repetition
  - poor_model_generability
  - schema_violation
aspect_ratios:
  - "9:16"
  - "16:9"
source_files:
  - knowledge/31_程序化镜头表结构与跨片段节奏规则.md
---

# 动作群戏预算与跨片段节奏

动作戏必须按“前摇、切点、受击、结果”拆镜，优先让观众看懂动作，不追求复杂炫技。一个镜头最多承担一个主动作。

四人以上场面先分区：主动作区、受击区、旁观区、出入口区。只给有信息变化的人反应镜头。

跨片段要检查最近三到五个片段的景别和开尾镜头。上一段以强特写结束，下一段优先关系复位或半身中景；连续同类中近景后，下一段应换成关系、动作、纵深或不同观看位置。

三快叠加禁止：快速运镜、快速动作、快速切镜同镜最多同时出现两项。

预算降级时先删复杂运镜和多人同时动作，保留关系、受击和结果回收。

程序化表结构只用于内部检索。最终输出必须把“镜头类型、景别、观看位置、任务”翻译成自然中文镜头句。
