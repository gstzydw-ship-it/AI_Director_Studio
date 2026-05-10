---
rule_id: REFERENCE-ROLE-STRICT-001
title: 参考图职责边界必须严格
doc_type: rule_card
rule_type: reference_control
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: reference_role_validation
runtime_retrieval: true
retrieval_key:
- reference-role-strict-001
- signals.tailframe_lock
- signals.continuity_lock
- signals.reference_binding
- events.tailframe
- events.reference_binding
- risks.axis_confusion
- risks.reference_misuse
- dialogue_types.argument_escalation
applies_when:
- 参考图
- 人物身份
- 场景空间
avoid_when:
- "没有任何参考图进入 prompt。"
failure_mode:
- "人物参考图、场景参考图与尾帧图职责互相污染。"
output_contract: "每张参考图进入 prompt 前必须绑定职责；当前无戏份人物不得被保留。"
example_good: "人物参考图只用于身份、五官、发型、体态、服装和年龄气质。"
example_bad: "用人物参考图背景覆盖当前场景，并把图中无戏份人物写入时间轴。"
signals:
- tailframe_lock
- continuity_lock
- reference_binding
events:
- tailframe
- reference_binding
risks:
- axis_confusion
- reference_misuse
dialogue_types:
- argument_escalation
applies_to:
- 参考图
- 人物身份
- 场景空间
- 尾帧
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 参考图职责边界必须严格

## 规则

每张参考图进入 prompt 前必须先绑定职责，不允许让人物参考图、场景参考图、尾帧图互相污染。

职责边界：

- 人物参考图只用于身份、五官、发型、体态、服装和年龄气质。
- 场景参考图只用于空间、轴线、光线、材质和场景基底。
- 上一段尾帧图优先用于首帧连续、人物站位、道具状态和光线继承。
- 当前无戏份人物不得因为出现在参考图或尾帧里被保留到当前片段。

## 禁止

- 用人物参考图背景覆盖当前场景。
- 在时间轴每段重复调用同一张参考图。
- 把当前片段不需要的人物参考图写入参考绑定。
- 尾帧与剧本冲突时反向改剧本，应由质检提示用户重跑或修正上段。
