---
rule_id: PROMPT-DIRECTOR-JARGON-TRANSLATION-001
title: 导演调度口语必须翻译成可见画面语言
doc_type: rule_card
rule_type: prompt_language
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: language_downtranslation
runtime_retrieval: true
retrieval_key:
- prompt-director-jargon-translation-001
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.rush_in
- events.collision
- events.waist_support
- events.reaction
- events.cut
- events.tailframe
- risks.romanticize_collision
- risks.axis_confusion
- risks.reference_misuse
- risks.privacy_body
- dialogue_types.reaction_beat
- scene_types.elevator
- scene_types.dialogue
- scene_types.action
- scene_types.intimacy_privacy
applies_when:
- 导演调度
- Seedance Prompt
- 运镜
avoid_when:
- "文本不是模型 prompt 或可执行时间轴。"
failure_mode:
- "把导演口语、抽象情绪或幕后调度词原样输出给视频模型。"
output_contract: "将上游已定意图翻译为镜头序列句：主体、景别、简洁机位、动作、视线和切镜触发。"
example_good: "严飞微微低头，主管们肩膀收紧，视线避开商北琛。"
example_bad: "空气收紧，权力压住所有人。"
signals:
- tailframe_lock
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- elevator
- dialogue
- action
- intimacy_privacy
events:
- rush_in
- collision
- waist_support
- reaction
- cut
- tailframe
risks:
- romanticize_collision
- axis_confusion
- reference_misuse
- privacy_body
dialogue_types:
- reaction_beat
applies_to:
- 导演调度
- Seedance Prompt
- 运镜
- 受击反应
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
- knowledge/rules/prompt_compiler/PROMPT-NATURAL-SENTENCE-001.md
- knowledge/rules/shot_director/MOTION-MODALITY-001.md
conflicts_with: []
supersedes: []
---

# 导演调度口语必须翻译成可见画面语言

## 规则

`prompt_compiler` 不得把上游导演口语原样输出给 Seedance。最终 prompt 必须把调度意图翻译成模型可见的镜头序列句：主体、景别、简洁机位、人物动作、视线和切镜触发。

## 禁止

```text
稳定器在同一运动里带到严飞和主管胸部以上受压反应。
顺势带到众员工被权力压住。
空气收紧，沉默就是回应。
炸点后尾帧悬停，留足回味。
前慢后碎，电梯暧昧段保持凝滞和张力。
纵深中全景到商北琛半身中景，商北琛右前方眼平高度。
同一镜头内横移 truck right 到严飞反应，再 truck left 回到主位。
```

## 改写方向

```text
镜头切至严飞和几名主管胸部以上中近景，同侧固定机位；严飞微微低头，主管们肩膀收紧、屏住呼吸、避开商北琛视线。
```

## 翻译表

- `稳定器在同一运动里带到` -> `镜头切至同侧反应 / 平稳跟拍 / 同侧固定机位`
- `受压反应` -> `低头 / 屏住呼吸 / 肩膀收紧 / 眼神回避 / 身体僵住`
- `权力压住 / 空气收紧` -> `停顿 0.5-1 秒 / 无人说话 / 人群停步 / 让开通道`
- `压入 / 卡断 / 炸点 / 钩子` -> `台词说完后停0.8秒 / 手刚要抬起时切镜 / 门尚未完全闭合时冲入 / 画面停在身体接触瞬间`
- `凝滞 / 粘滞 / 暧昧感 / 张力` -> `两人相距半步 / 对视1秒 / 手停在腰侧不移动 / 乔熙嘴唇停住`
- `气口 / 留白 / 回味 / 泄压` -> `镜头保持固定0.5-1秒 / 无人说话 / 人物停在原位 / 呼吸放慢`
- `纵深中全景到半身中景 / 中景转关系景` -> `双人中景 / 商北琛半身中景 / 电梯口固定中景`
- `truck right/left / 同一镜头内横移到反应再回主位` -> `镜头切至同侧听者反应 / 镜头切回主角`
- `眼平高度 / 同轴线偏右 / 人物右前方` -> 通常删除或简化为 `正面固定机位 / 侧面固定机位 / 同侧过肩机位 / 办公桌侧面固定机位`
- `门窗框住人物 / 前景压线 / 框景压迫` -> `同侧过肩机位，从某人肩后看向门口，某人站在门口或门边做具体动作`
