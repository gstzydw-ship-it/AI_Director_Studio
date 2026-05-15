---
rule_id: PROMPT-CINEMATIC-DOWNTRANSLATION-002
title: 复杂分镜必须降维成视频模型可执行动作
doc_type: rule_card
rule_type: prompt_compiler_translation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: prompt_downtranslation
runtime_retrieval: true
retrieval_key:
- prompt-cinematic-downtranslation-002
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.reaction
- events.cut
- events.tailframe
- risks.reference_misuse
- risks.privacy_body
- risks.blood_avoidance
- dialogue_types.argument_escalation
- dialogue_types.reaction_beat
- scene_types.dialogue
- scene_types.action
- scene_types.suspense
- scene_types.intimacy_privacy
applies_when:
- seedance_prompt
- prompt_compiler
- main_shots
avoid_when:
- "输入不是最终模型 prompt 编译任务。"
failure_mode:
- "逐字保留复杂导演术语、密集分镜或抽象节奏。"
output_contract: "只把已定导演决策翻译为主体、视角/观看位置、路径、动作、视线、切入点与尾帧状态。"
example_good: "镜头从桌侧固定视角的中景开始，台词落点后短切到严飞中近景。"
example_bad: "过肩、反打、特写、推轨、荷兰角快速交替。"
signals:
- tailframe_lock
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- suspense
- intimacy_privacy
events:
- collision
- reaction
- cut
- tailframe
risks:
- reference_misuse
- privacy_body
- blood_avoidance
dialogue_types:
- argument_escalation
- reaction_beat
applies_to:
- seedance_prompt
- prompt_compiler
- main_shots
- sub_shots
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
- knowledge/19_Gold_Standard_Prompt范例.md
- knowledge/28_全场景分镜与转场案例库.md
conflicts_with: []
supersedes: []
---

# 复杂分镜必须降维成视频模型可执行动作

## 规则

电影分镜可以复杂，但 Seedance Prompt 必须克制、连续、可执行。`prompt_compiler` 的任务不是把所有导演术语逐字翻译，而是保留对视频模型最有用的信息：

- 主体是谁。
- 观看视角在哪里。
- 人物从哪里到哪里。
- 镜头何时切近、切回或保持固定。
- 哪个动作、视线、道具或声音是信息重音。
- 尾帧停在什么可继承状态。

## 降维策略

当上游有多个 `main_shots` 与 `sub_shots` 时：

- 主镜头负责空间、人物关系、动作路径和尾帧。
- 子镜头只翻译为短暂插入、反应重音或细节桥接。
- 每个 3 秒以内片段最多保留 1 个明确切入点。
- 每个 6-12 秒片段最多保留 2-4 个有效镜头变化。
- 如果电影分镜过密，优先保留信息揭示、身体接触、受击反应和关系复位，删除无信息的装饰性切镜。

## 翻译顺序

Prompt 时间轴应按这个顺序写：

1. 片段开始的空间与人物关系。
2. 主体动作推进。
3. 必要的切入或反打。
4. 回到关系镜头或明确尾帧状态。

## 禁止

- 不得把 `scene_map` 的所有字段机械塞进 prompt。
- 不得写模型难执行的抽象词，如“导演感更强”“权力结构压迫观众”。
- 不得同时写多个冲突视角，例如同一秒既正面、背面、侧面又俯拍。
- 不得把子镜头写成新场景。
- 不得为了保留全部分镜而牺牲动作连续性。

## 正确写法

```text
镜头从桌侧固定视角的中景开始，商北琛在画面左前方压住桌沿，严飞在桌对面抬头。台词落点后，镜头短切到严飞胸部以上中近景，他停顿半秒，视线没有避开；随后回到桌侧双人关系景，严飞起身，商北琛后退半步，尾帧保留两人隔桌对峙。
```

这比下面的写法更适合视频模型：

```text
过肩、反打、特写、推轨、荷兰角、快速切手部、再回到广角，形成高级电影节奏。
```

