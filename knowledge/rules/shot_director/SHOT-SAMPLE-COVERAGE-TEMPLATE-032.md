---
rule_id: SHOT-SAMPLE-COVERAGE-TEMPLATE-032
title: 94集样片 coverage 镜头模板
doc_type: rule_card
rule_type: shot_coverage
owner_agent: shot_director
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: shot_director_generation
runtime_retrieval: true
retrieval_key:
- shot-sample-coverage-template-032
- signals.short_drama_samples
- signals.coverage_role
- signals.viewpoint_language
- signals.reaction_coverage
- signals.tailframe
- scene_types.domestic_scene
- scene_types.elevator
- scene_types.company_arrival
- events.reaction
- events.reveal
- events.prop_reveal
- risks.pseudo_viewpoint
- risks.overloaded_shot
applies_when:
- 需要按短剧样片设计镜头和机位
- 镜头导演输出过于复杂
- 出现关系景、反应、动作顶点、道具揭示、尾帧承接
avoid_when:
- 用户明确要求实验性长镜头或非短剧风格
- 当前阶段只做节奏拆片，不做镜头方案
failure_mode:
- "先编造抽象机位，再把动作、反应、道具和尾帧塞进同一镜头。"
output_contract: "镜头导演必须先给每个镜头标注 coverage_role，再用自然可拍视角表达；每镜只保留一个主动作或主反应，严禁伪视角和过载镜头。"
example_good: "乔熙胸部以上中近景，平视，从小豆丁肩后看向乔熙，乔熙说完电话后停半拍。"
example_bad: "沙发与地毯之间的关系视角，兼顾手机落点、孩子抗拒、乔熙安抚和尾帧承接。"
signals:
- short_drama_samples
- coverage_role
- viewpoint_language
- reaction_coverage
- tailframe
scene_types:
- domestic_scene
- elevator
- company_arrival
events:
- reaction
- reveal
- prop_reveal
risks:
- pseudo_viewpoint
- overloaded_shot
source_files:
- knowledge/external_sources/short_drama_samples/README.md
- knowledge/external_sources/short_drama_samples/shot_coverage_template_library_v1.yaml
- knowledge/external_sources/short_drama_samples/rhythm_control_template_library_v1.yaml
conflicts_with: []
supersedes: []
---

# 94集样片 coverage 镜头模板

## 核心结论

94集样片中，关系景、环境关系景、半身景占主导；CU/ECU只占约2.1%。短剧镜头导演的基本功不是堆复杂机位，而是判断每个镜头的 coverage 任务。

每个镜头必须先回答一个问题：

- 拍关系？
- 拍台词压力？
- 拍受击反应？
- 拍动作顶点？
- 拍信息揭示？
- 拍关系恢复？
- 拍尾帧承接？

## coverage 角色

### establish_relation

任务：建立人物、空间、道具位置。

推荐：双人中景或半身关系景，1.5-3.0秒。

句式：`双人中景，平视，固定视角，A与B在同一空间内，关键道具在画面边缘可见。`

### dialogue_pressure

任务：承载说话者台词和对方压力。

推荐：胸部以上中近景或双人半身景，2.0-4.0秒。

句式：`A胸部以上中近景，平视，从B肩后看向A，A看着B说出台词，B肩线虚在前景。`

### impact_reaction

任务：拍被击中的表情、停顿、视线变化。

推荐：胸部以上中近景，1.5-3.0秒。

句式：`B胸部以上中近景，平视，B抬眼或停住，表情变化清楚，没有新动作抢反应。`

### action_apex

任务：拍状态改变的动作顶点。

推荐：半身景或局部近景，0.7-1.5秒。

句式：`局部近景，固定视角，手刚松开/道具刚落下/衣服刚整理到位，动作只发生一次。`

### information_reveal

任务：道具、身份、车辆、照片、文件等信息爆点。

推荐：局部近景或主体中景，1.0-2.5秒。

句式：`道具局部近景，固定视角，道具从明确来源进入画面，停在明确落点。`

### relation_recover

任务：特写或反应后恢复空间关系，防止跳轴和丢人。

推荐：双人半身关系景，1.5-3.0秒。

句式：`双人半身关系景，平视，固定视角，两人仍在原空间内，上一镜变化后的状态清楚可见。`

### tailframe_hold

任务：给下一段承接帧。

推荐：双人关系景或关键主体半身景，0.5-1.0秒。

句式：`最后0.5秒回到关系景，人物位置、手部状态、道具落点和门/车/电梯状态清楚。`

## 场景模板

### domestic_morning_pressure

顺序：establish_relation -> dialogue_pressure -> action_apex -> impact_reaction -> relation_recover -> tailframe_hold。

执行：地毯、沙发、茶几只能作为空间锚点，不能生成“沙发与地毯之间的关系视角”。

### elevator_close_pressure

顺序：dialogue_pressure -> impact_reaction -> relation_recover -> action_apex -> tailframe_hold。

执行：平视、过肩、反打、双人半身关系景足够；不写拥抱、怀里、贴身亲密，除非剧本明确。

### company_arrival_reveal

顺序：establish_relation -> information_reveal -> dialogue_pressure -> information_reveal -> impact_reaction -> tailframe_hold。

执行：人群压力先用关系景建立，再用车门、腿部、人物抬头作为揭示链；主角受击反应必须留够0.6秒以上。

### prop_memory_trigger

顺序：action_apex -> information_reveal -> impact_reaction -> relation_recover -> tailframe_hold。

执行：道具从哪里来、落在哪里、谁先看见必须清楚；回忆触发前的现实尾帧要保留人物僵住状态。

## 禁止项

- 禁止“沙发与地毯之间的关系视角”。
- 禁止“空间关系视角”“尾帧承接视角”“覆盖职责视角”。
- 禁止一个镜头同时承担台词、反应、道具落点、起身、拿包、尾帧承接。
- 禁止用复杂坐标式机位替代自然视角。
- 禁止字幕、屏幕文字、英文字幕和文字浮层。
