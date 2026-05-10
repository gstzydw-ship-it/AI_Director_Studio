---
rule_id: PROMPT-EXECUTABLE-STRUCTURE-001
title: Prompt必须像可直接执行的导演指令
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: prompt_structure
runtime_retrieval: true
retrieval_key:
- prompt-executable-structure-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- signals.reference_binding
- events.cut
- events.reference_binding
- risks.reference_misuse
- scene_types.dialogue
- scene_types.action
applies_when:
- Seedance Prompt
- 输出结构
- 可执行性
avoid_when:
- "当前不是最终 prompt 结构输出。"
failure_mode:
- "输出关键词串、概念标签或表格，缺少可直接生成的导演指令。"
output_contract: "最终 prompt 用完整自然句承载空间、人物位置、动作、台词落点、镜头变化和约束。"
example_good: "乔熙胸部以上中近景，平视固定机位，她听到后半句时嘴唇停住。"
example_bad: "冷白灯，近景，悲伤，压迫，电影感。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
- reference_binding
scene_types:
- dialogue
- action
events:
- cut
- reference_binding
risks:
- reference_misuse
applies_to:
- Seedance Prompt
- 输出结构
- 可执行性
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# Prompt必须像可直接执行的导演指令

## 规则

最终 Seedance prompt 应优先追求结构清楚、句子完整、信息足够、可直接执行，而不是越短越好。

每个片段至少应承载：

- 场面空间。
- 人物位置。
- 动作推进。
- 台词落点。
- 主分镜切换。
- 子分镜变化。
- 表情细节。
- 光线关系。
- 连续性约束。
- 参考图继承关系。

## 禁止

- 只输出关键词串。
- 只输出概念标签。
- 用技术表格替代自然导演句。

