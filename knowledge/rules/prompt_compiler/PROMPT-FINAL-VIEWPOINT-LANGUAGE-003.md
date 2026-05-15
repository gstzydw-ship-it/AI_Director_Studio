---
rule_id: PROMPT-FINAL-VIEWPOINT-LANGUAGE-003
title: 最终 Prompt 用视角替代机位
doc_type: rule_card
rule_type: final_prompt_language
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
- shot_director
- shot_director_guard
priority: P0
status: active
pipeline_stage: final_prompt_compile
runtime_retrieval: true
retrieval_key:
- prompt-final-viewpoint-language-003
- signals.viewpoint_translation
- signals.seedance_prompt
- risks.camera_jargon_leak
applies_when:
- Seedance 最终 prompt
- 镜头序列输出
- shot 字段翻译
avoid_when:
- internal_camera_planning_only
failure_mode:
- "最终 prompt 保留固定机位、侧面机位、摄影机位于等内部摄影术语。"
output_contract: "最终镜头行只写视角/观看位置，不写机位。"
example_good: "镜头1【3秒】【乔熙和小豆丁】双人半身关系景，侧面视角。"
example_bad: "镜头1【3秒】【乔熙和小豆丁】双人半身关系景，沙发侧面固定机位。"
signals:
- viewpoint_translation
- seedance_prompt
risks:
- camera_jargon_leak
---

# 最终 Prompt 用视角替代机位

## 规则

`prompt_compiler` 接到上游 shot 字段后，必须把内部摄影术语翻译成视频模型更容易理解的“视角/观看位置”。

最终 Prompt 禁止出现：

- 固定机位
- 侧面机位
- 同侧固定机位
- 摄影机位于
- 机位在
- 左前方 / 右前方 / 左后方 / 右后方
- 数字角度

## 翻译

- 固定机位 → 固定视角
- 侧面固定机位 → 侧面视角
- 同侧过肩机位 → 从某人肩后看向某人
- 同侧固定机位 → 同侧固定视角
- 低机位 → 略低视角
- 高机位 → 略高视角
- 场景固定机位 → 固定视角，空间关系稳定

## 输出句式

```text
镜头1【3秒】【乔熙和小豆丁】双人半身关系景，侧面视角。乔熙坐在沙发边给小豆丁套衣服，小豆丁缩腿抗拒。（切镜时机：孩子抗拒反应出现后切至镜头2）
```

不要写：

```text
镜头1【3秒】【乔熙和小豆丁】双人半身关系景，沙发侧面固定机位。
```
