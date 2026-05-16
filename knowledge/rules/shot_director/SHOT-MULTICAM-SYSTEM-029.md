---
rule_id: SHOT-MULTICAM-SYSTEM-029
title: 多机位体系强制调用规则
doc_type: rule_card
rule_type: multicam_system
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
pipeline_stage: shot_language_selection
runtime_retrieval: true
retrieval_key:
  - 多机位体系
  - 二机位模板
  - 三机位模板
  - 四机位模板
  - 群戏调度
applies_when:
  - 双人对白
  - 三人冲突
  - 四人以上群戏
  - 动作或反应覆盖
avoid_when:
  - 单人静态独白且无反应对象
  - 用户明确要求单镜头连续拍摄
scene_types:
  - dialogue_scene
  - group_dialogue
  - action_scene
  - multi_character_scene
events:
  - reaction
  - action_peak
  - reveal
risks:
  - shot_monotony
  - axis_confusion
  - poor_model_generability
aspect_ratios:
  - "9:16"
  - "16:9"
source_files:
  - knowledge/29_多机位体系与预算降级规则.md
---

# 多机位体系强制调用规则

镜头导演遇到对白、冲突、动作、群戏或反应覆盖时，必须先判断二机、三机或四机覆盖，而不是默认同侧固定机位和中近景。

二机位用于简单双人关系：一个关系镜头加一个发言或反应镜头。

三机位用于冲突升级、三角关系、旁观者打断或动作前摇：关系、发言、受击三类镜头各司其职。

四机位用于四人以上群戏或高压动作：总关系、核心发言、受击反应、游动补偿。群戏先分区，再切人。

最终输出必须是自然中文，例如“从乔熙肩后看向商北琛，商北琛半身入画”，不得输出二号机、三号机、反打机、内部编码或英文缩写。

如果模型风险升高，优先降级复杂运镜和多人同时动作，不得删掉必要的关系交代和受击反应。
