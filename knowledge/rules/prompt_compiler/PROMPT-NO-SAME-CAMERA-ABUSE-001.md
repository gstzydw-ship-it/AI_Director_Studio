---
rule_id: PROMPT-NO-SAME-CAMERA-ABUSE-001
title: PROMPT-NO-SAME-CAMERA-ABUSE-001
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P3
status: active
pipeline_stage: hidden_cut_detection
runtime_retrieval: true
retrieval_key:
- prompt-no-same-camera-abuse-001
- signals.action_coverage
- events.cut
- scene_types.elevator
- scene_types.action
applies_when:
- "同一机位继续"
- "隐性切镜"
- "主体或景别变化"
avoid_when:
- "没有使用同一机位继续或隐性切镜。"
failure_mode:
- "滥用同一机位继续掩盖主体变化、景别变化或画面中心变化。"
output_contract: "仅在同主体、同景别基底或固定场景机位真延续时使用同一机位继续。"
example_good: "镜头保持在乔熙身上，她从低头停住到慢慢抬头。"
example_bad: "同一机位继续，严飞胸部以上中近景落在画面中心。"
signals:
- action_coverage
scene_types:
- elevator
- action
events:
- cut
conflicts_with: []
supersedes: []
---

# PROMPT-NO-SAME-CAMERA-ABUSE-001

## 规则标题
禁止滥用“同一机位继续”

## 规则内容
1. “同一机位继续”不是通用衔接词，不能用来掩盖主体变化、景别变化或新的画面中心。
2. 若“同一机位继续”后 50-60 字内出现新主体 + 新景别 / 新构图中心，应视为隐性切镜。
3. 出现隐性切镜时，必须改写为真正的切镜句，或回退到上游拆镜/拆段。
4. 固定场景机位场景优先写“电梯口固定机位保持”“办公室门口固定机位保持”“双人关系景保持”。

## 为什么
“同一机位继续”被滥用时，模型会把它同时理解成“不要切”和“画面已经切了”，最终生成出假连续、背景漂移、人物跳位。

## 允许场景
- 同一主体继续动作。
- 双人关系景继续推进，人物距离不变。
- 固定机位保持，人物进入或离开画面。

## 禁止场景
- A 说完后直接变成 B 的中近景。
- 同主体突然从半身景跳成手部特写却不说明切近。
- 空间锚点从大堂变电梯口但还写“同一机位继续”。

## 质检要点
- 是否出现“同一机位继续 + 新主体 + 新景别”的隐性切镜。
- 是否用“固定机位保持 / 镜头保持在A身上”替代了模糊表达。
