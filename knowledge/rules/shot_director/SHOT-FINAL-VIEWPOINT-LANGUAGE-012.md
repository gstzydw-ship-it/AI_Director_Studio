---
rule_id: SHOT-FINAL-VIEWPOINT-LANGUAGE-012
title: 最终镜头字段必须用视角语言
doc_type: rule_card
rule_type: final_shot_language
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
pipeline_stage: final_handoff
runtime_retrieval: true
retrieval_key:
- shot-final-viewpoint-language-012
- signals.final_prompt_language
- signals.viewpoint_translation
- risks.camera_jargon_leak
- risks.prompt_ambiguity
applies_when:
- 最终镜头字段
- prompt_compiler 输入
- Seedance prompt
avoid_when:
- internal_camera_planning_only
failure_mode:
- "把内部机位术语原样输出给视频模型，例如固定机位、侧面机位、摄影机位于。"
output_contract: "最终 shot/镜头字段必须把内部机位翻译为视角或观看位置。"
example_good: "乔熙和小豆丁双人半身关系景，侧面视角。"
example_bad: "乔熙和小豆丁双人半身关系景，沙发侧面固定机位。"
signals:
- final_prompt_language
- viewpoint_translation
risks:
- camera_jargon_leak
- prompt_ambiguity
---

# 最终镜头字段必须用视角语言

## 核心规则

内部可以用机位做规划，但最终交给 `prompt_compiler` 和视频模型的 `镜头` 字段必须写成“视角/观看位置”。

## 翻译表

- 固定机位 → 固定视角
- 侧面机位 → 侧面视角
- 正面机位 → 正面视角
- 背后机位 → 背后跟随视角
- 同侧过肩机位 → 从某人肩后看向某人
- 场景固定机位 → 固定视角，空间关系稳定
- 略低机位 → 略低视角
- 略高机位 → 略高视角
- 主观 POV → 某人的主观视角
- 半主观 → 靠近某人视线的半主观视角

## 禁止

- 沙发侧面固定机位。
- 茶几侧面固定机位。
- 摄影机位于某人正前方。
- 同侧固定机位。
- 右前方 30 度、左后方 45 度等坐标式机位。

## 正确

- 乔熙和小豆丁双人半身关系景，侧面视角。
- 小豆丁胸部以上中近景，略低视角，乔熙手臂保留在画面边缘。
- 乔熙胸部以上中近景，从小豆丁肩后看向乔熙。
- 书包局部近景，固定视角，书包从沙发边被拿起。

## 自检

如果一句镜头字段里出现“机位”，还没有完成最终翻译。
