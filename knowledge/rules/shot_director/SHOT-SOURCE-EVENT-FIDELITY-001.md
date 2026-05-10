---
rule_id: SHOT-SOURCE-EVENT-FIDELITY-001
title: shot_director 只能继承 source_script_events
doc_type: rule_card
rule_type: fidelity
owner_agent: shot_director
agent_scope:
- shot_director
- quality_inspector
- prompt_compiler
priority: P0
status: active
pipeline_stage: source_fidelity_guard
runtime_retrieval: true
retrieval_key:
- shot-source-event-fidelity-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.door_state
- risks.script_invention_risk
- risks.blood_avoidance
- dialogue_types.long_dialogue_compression
- scene_types.dialogue
- scene_types.action
applies_when:
- 镜头设计
- 剧本忠实度
- 道具连续性
avoid_when:
- "no_source_script_events_available"
- "explicit_user_authorized_adaptation"
failure_mode:
- "invented_scene_event_or_prop_state"
output_contract: "Translate only source_script_events into shots; preserve character names, space, props, and visible states."
example_good: "乔熙在公寓回神，照片在桌上，小豆丁背书包站门口。"
example_bad: "Sunny 睡在床上，伴侣在床边叫醒她。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
events:
- collision
- door_state
risks:
- script_invention_risk
- blood_avoidance
dialogue_types:
- long_dialogue_compression
applies_to:
- 镜头设计
- 剧本忠实度
- 道具连续性
- 低歧义画面
source_files:
- knowledge/00_知识库优先级与冲突裁决规则.md
- knowledge/06_连续性与安全规则.md
conflicts_with: []
supersedes: []
---

# shot_director 只能继承 source_script_events

## 规则

`shot_director` 只能把 `story_planner.source_script_events` 翻译成镜头、景别、运镜、受击落点和子分镜重音。

不得重新解释剧本前提，不得把英文台词或 OS 中的词义联想改造成新的画面事件。

## 硬边界

- 场次标题、人物行、`source_script_events` 的可见事实优先级高于英文台词里的词义联想。
- 场景空间必须继承场次标题和 `source_script_events`；公寓不能改成车内，门口不能改成大堂，集团门口不能改成办公室。
- `subject` 只能来自当前片段的人物行、`source_script_events` 中的可见人物、群体、道具或车辆。
- OS/台词里的昵称或英文名不能替换人物行中的角色名。
- 不得新增睡醒、床边、伴侣、车内、保镖、记者、闪光灯、鞠躬、员工低语等剧本外前提。
- 必须继承上游道具状态和空间状态；不得为了情绪镜头改写照片、书包、车门、咖啡杯等道具归属。

## 低歧义画面优先

优先使用稳定可见动作：

- 放到桌上
- 站在门口
- 停住动作
- 看向某处
- 车辆到达
- 助理开门
- 队列后收

避免把简单动作改成模型容易误画的微观状态：

- 攥进掌心
- 指尖摩挲
- 掌心收紧
- 指节泛白
- 发丝、衣角、杯沿等无连续性必要的局部细节

## 示例

当原剧本写：

> ▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。  
> ▲小豆丁已经站在门口，单肩背着书包等她。  
> 乔熙OS：It's been four years. He's married with a kid now. Sunny, wake up.

`shot_director` 必须理解为：

- 乔熙在公寓现实场景中回神。
- 照片已经在桌上。
- 小豆丁背着书包站在门口。
- “Sunny, wake up” 是乔熙自我提醒，不是睡醒戏。

禁止输出：

- Sunny 睡在床上
- 伴侣在床边叫醒她
- 乔熙睁眼
- 乔熙把照片攥进掌心
- 乔熙把照片塞回小豆丁的书包

## Agent 执行

- `shot_director`：把 source_script_events 转成镜头，不补剧情。
- `prompt_compiler`：继承 shot_director 的道具与人物状态，不再二次发明动作。
- `quality_inspector`：发现剧本外前提、昵称替换主体、道具归属跳变时必须判为 fail。
