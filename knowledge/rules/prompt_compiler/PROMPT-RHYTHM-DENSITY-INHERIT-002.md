---
rule_id: PROMPT-RHYTHM-DENSITY-INHERIT-002
title: Prompt 编译必须继承节奏密度矩阵而不是临时加切镜
doc_type: rule_card
rule_type: prompt_output
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: prompt_compilation
runtime_retrieval: true
retrieval_key:
- prompt-rhythm-density-inherit-002
- signals.final_prompt
- signals.pace
- signals.action_density
- risks.too_many_cuts
- risks.prompt_ambiguity
applies_when:
- 最终 prompt
- 节奏密度
- 镜头时长
- 切镜预算
avoid_when:
- "上游没有节奏密度信息且片段是单镜连续动作。"
failure_mode:
- "编译器为了可读性临时补镜头、补特写或改变镜头时长，破坏上游节奏判断。"
output_contract: "Prompt 只翻译已批准的节奏档位、镜头数、时长和切点；缺失时请求上游补齐，不自行发明。"
example_good: "按上游紧凑档写 4 镜，总时长 10 秒，每镜时长在 1-3 秒内。"
example_bad: "上游 3 镜，编译时为了强调细节改成 6 个镜头。"
signals:
- final_prompt
- pace
- action_density
scene_types:
- any
events:
- cut
- action_peak
risks:
- too_many_cuts
- prompt_ambiguity
applies_to:
- Seedance Prompt
- 镜头时长
- 切镜预算
source_files:
- knowledge/rules/rhythm_rewrite_director/RHYTHM-SHOT-DENSITY-MATRIX-003.md
- knowledge/rules/prompt_compiler/PROMPT-CUT-BUDGET-001.md
- knowledge/rules/shot_director/SHOT-MOTIVATED-CUT-ACTION-DENSITY-002.md
external_sources:
- https://cursa.app/en/page/pacing-and-structure-making-cuts-feel-invisible-and-intentional
conflicts_with: []
supersedes: []
---

# Prompt 编译必须继承节奏密度矩阵而不是临时加切镜

## 规则

`prompt_compiler` 不做新的镜头导演判断。它必须继承上游已经批准的：

- 节奏档位。
- 每 5 秒镜头数。
- 目标 ASL。
- 单镜时长范围。
- 允许短插入数量。
- 必拍动作、可压缩动作、可省略动作。

如果上游缺失这些信息，编译器只能保守处理：减少切镜、保持关系景、提示上游补齐。不得自己新增特写或拆镜头。

## 编译自检

输出前必须检查：

- 最终镜头数是否符合当前片段时长和节奏档位。
- 任何低于 1 秒的镜头是否有状态改变。
- 每句台词是否有可见说话者或明确画外声承接。
- 首帧是否建立人物和关键道具关系。
- 尾帧是否可继承。

## 禁止

- 禁止用“局部近景、再切回、再切至”临时强化上游没有批准的动作。
- 禁止把可省略动作写成独立镜头。
- 禁止为了追求紧凑，把情绪反应压到不可读。
