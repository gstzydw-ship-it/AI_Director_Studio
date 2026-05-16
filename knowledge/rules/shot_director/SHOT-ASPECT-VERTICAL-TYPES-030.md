---
rule_id: SHOT-ASPECT-VERTICAL-TYPES-030
title: 画幅映射与竖屏专用镜头类型
doc_type: rule_card
rule_type: aspect_ratio_mapping
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
pipeline_stage: aspect_framing
runtime_retrieval: true
retrieval_key:
  - 画幅镜头映射
  - 竖屏正反切
  - 纵深前后
  - 竖屏分屏
  - 景别适配
applies_when:
  - 9:16 竖屏
  - 16:9 横屏
  - 1:1 方画幅
  - 2.39:1 宽画幅
  - 需要把抽象镜头词改写成自然画面语
avoid_when:
  - 未识别到画幅且用户不要求画幅推断
  - 剧本明确要求非写实实验影像
scene_types:
  - vertical_screen_scene
  - dialogue_scene
  - action_scene
events:
  - reaction
  - entrance_exit
  - reveal
risks:
  - aspect_ratio_mismatch
  - vertical_closeup_overuse
  - abstract_prompt
aspect_ratios:
  - "9:16"
  - "16:9"
  - "1:1"
  - "2.39:1"
source_files:
  - knowledge/30_画幅镜头映射与竖屏专用镜头规则.md
---

# 画幅映射与竖屏专用镜头类型

镜头导演必须按画幅选择镜头语言。竖屏主力不是连续脸部特写，而是半身中景、七分身景、中近景、肩后关系、纵深前后和分区群像。

竖屏可用类型：

- 竖屏正反切：同侧轴线内按台词和反应切换观看对象，必须写清从谁看向谁。
- 竖屏纵深前后：写清近处主体、远处目标和真实环境锚点。
- 竖屏分层过肩：肩线只作为边缘，目标人物和视线对象必须明确。
- 竖屏双层关系景：用前后距离表现关系变化。
- 竖屏分区群像：四人以上先分区，不横向硬塞。
- 竖屏分屏：除非剧本明确要求真实分屏，否则最终改写为同一竖屏画面里的前后或上下分层。

禁止输出抽象组合名，例如“门框侧斜向纵深双人中景”。必须写成可见画面，例如“从乔熙肩后看向门口，小豆丁站在门边，半个身子探进来”。
