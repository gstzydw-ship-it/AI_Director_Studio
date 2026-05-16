---
rule_id: PROMPT-REFERENCE-BINDING-001
title: 参考图先绑定职责再进入时间轴
doc_type: rule_card
rule_type: reference_control
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: reference_binding
runtime_retrieval: true
retrieval_key:
- prompt-reference-binding-001
- signals.reference_binding
- events.reference_binding
- risks.axis_confusion
- risks.reference_misuse
applies_when:
- 参考图
- 人物身份
- 场景参考
avoid_when:
- "没有使用任何人物、场景或尾帧参考图。"
failure_mode:
- "参考图职责未绑定，人物图背景污染场景，或同一时间段反复调用图片。"
output_contract: "先写清每张参考图职责，再进入时间轴；人物图只管身份外观，场景图只管空间光线。"
example_good: "@图片1 仅用于商北琛的人物身份、五官、发型、身形、服装一致性。"
example_bad: "反复在每个时间段调用 @图片1，并继承人物参考图里的背景。"
signals:
- reference_binding
events:
- reference_binding
risks:
- axis_confusion
- reference_misuse
applies_to:
- 参考图
- 人物身份
- 场景参考
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 参考图先绑定职责再进入时间轴

## 规则

使用参考图时，必须先写清每张图的职责，再进入时间轴。

人物参考图只负责：

- 人物身份。
- 五官。
- 发型。
- 体态。
- 服装一致性。
- 年龄感与气质基底。

场景图只负责场景空间、轴线、光线基底。人物图不得污染场景主体，人物图背景不得直接带入当前场景。

## 推荐写法

```text
@图片1 仅用于商北琛的人物身份、五官、发型、身形、服装一致性。
@图片4 仅用于集团大堂空间、轴线、冷白商务光线基底。
```

## 禁止

- 无节制堆叠参考图。
- 同一时间段反复调用 `@图片`。
- 用人物参考图背景覆盖当前场景。

