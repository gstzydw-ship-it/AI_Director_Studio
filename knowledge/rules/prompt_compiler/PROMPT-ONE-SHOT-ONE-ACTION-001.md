---
rule_id: PROMPT-ONE-SHOT-ONE-ACTION-001
title: 一镜一主动作
doc_type: rule_card
rule_type: prompt_timeline
owner_agent: prompt_compiler
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: action_density_control
runtime_retrieval: true
retrieval_key:
- prompt-one-shot-one-action-001
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.reaction
- risks.blood_avoidance
- scene_types.action
applies_when:
- 时间轴
- 动作描述
- 可生成性
avoid_when:
- "当前时间段只有一个核心动作且已清晰可执行。"
failure_mode:
- "单一时间段并列塞入多个主驱动动作，导致模型无法连续生成。"
output_contract: "每个时间段只保留一个主动作，其余信息降为表情、视线、局部动作或反应。"
example_good: "她先停住脚步，手指慢慢松开西装前襟。"
example_bad: "她起身、奔跑、回头、挥手、推门、坐下并抢走文件。"
signals:
- action_coverage
- continuity_lock
scene_types:
- action
events:
- collision
- reaction
risks:
- blood_avoidance
applies_to:
- 时间轴
- 动作描述
- 可生成性
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 一镜一主动作

## 规则

一个时间段只能有一个主驱动动作。

其他信息只能作为：

- 表情承接。
- 视线变化。
- 局部动作。
- 受击反应。
- 机位调整。

## 禁止

不要把起身、奔跑、回头、挥手、推门、坐下、抢东西并列塞进同一句主镜头里。

## 正确方向

主动作先成立，其他动作作为承接节拍或局部落点补充。

