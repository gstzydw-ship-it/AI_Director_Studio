---
rule_id: PROMPT-AXIS-LOCK-PER-SEGMENT-001
title: 单片段内摄影机必须始终在轴线同侧
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: camera_axis_validation
runtime_retrieval: true
retrieval_key:
- prompt-axis-lock-per-segment-001
- signals.tailframe_lock
- signals.action_coverage
- signals.continuity_lock
- events.tailframe
- risks.axis_confusion
- risks.reference_misuse
- scene_types.elevator
- scene_types.action
applies_when:
- 180度轴线
- 跨轴
- 反打
avoid_when:
- "当前片段没有轴线或反打描述。"
failure_mode:
- "单个 segment 使用人物相对的左前方、右前方、左后方、右后方或反打词，造成左右翻面。"
output_contract: "每个 segment 使用同侧轴线表达：同侧过肩视角、同侧固定视角、同侧正面微侧视角或场景侧面固定视角。"
example_good: "商北琛半身中景，同侧正面微侧视角；乔熙中近景，从商北琛肩后看向乔熙。"
example_bad: "摄影机位于商北琛右前方，随后反打至乔熙左前方。"
signals:
- tailframe_lock
- action_coverage
- continuity_lock
scene_types:
- elevator
- action
events:
- tailframe
risks:
- axis_confusion
- reference_misuse
applies_to:
- 180度轴线
- 跨轴
- 反打
- 同侧轴线
- 简洁视角
- 人物相对左右
- 单片段视角
source_files:
- knowledge/06_连续性与安全规则.md
- knowledge/07_Seedance输出词典与模型适配.md
- knowledge/21_镜头调用规则与多机位模板.md
- knowledge/rules/scene_analyst/SCENE-CONSISTENCY-LOCK-001.md
conflicts_with: []
supersedes: []
---

# 单片段内摄影机必须始终在轴线同侧

## 背景

Seedance 2.0 是单镜头连续生成模型。大模型尤其不稳定的一点是：它分不清“人物左侧”和“画面左侧”，而人物从正面转到背面后，人物自己的左侧会变成画面另一侧。一个 segment 里只要使用“商北琛左前方、乔熙右前方、人物左后方”这类人物相对左右视角，模型就容易把空间翻面、人物左右颠倒、背景错乱。

## 规则

每个 prompt segment 必须保持同侧轴线。最终 prompt 优先使用“同侧过肩视角、同侧固定视角、同侧正面微侧视角、办公桌侧面固定视角、门口侧面固定视角、背后跟拍视角”这类简洁表达。

**硬约束：**

1. 同一 segment 的【时间轴】**禁止**使用人物相对的"左前方、右前方、左后方、右后方"作为最终视角。
2. 同一 segment **禁止**出现"反打至 / 反打镜头 / 翻拍至"等剪辑性反打词。真要反打必须**拆段**，不能在单段 prompt 内做。
3. 镜头句里尽量不使用“左侧 / 右侧”；必须交代关系时，改写成“桌前/桌后”“同侧过肩视角”“同侧固定视角”“门口侧面视角”等可拍表达。
4. 主体转身或换向时，不沿用人物左右；改用新的同侧视角或拆成下一片段。

## 跨轴的合法做法

如果剧情确实需要跨到另一侧，必须**拆成相邻的两个 segment**，并通过下面三种过渡之一衔接：

- **人物自然转身**：上一段尾帧人物完成转身动作，下一段以新朝向开拍。
- **越轴中性镜头**：在两段之间插入一个空镜或正面/俯拍中性视角。
- **固定视角接管**：从人物相对视角切换到门口侧面、办公桌侧面或同侧固定视角作为中转。

## 禁止项

- 禁止写"反打至 X" 在单段 prompt 里。
- 禁止人物相对左右视角：`商北琛左前方`、`乔熙右前方`、`人物左后方`、`主体右后方`。
- 禁止用"同一机位继续"承接一个反向视角描述——这是隐性跨轴。
- 禁止 `scene_analyst.scene_lock.axis` 里写了一条轴线，但 prompt 里多个 segment 用不同轴线却没有过渡说明。

## 正确写法

```text
0-3秒：
商北琛半身中景，正面平稳跟拍。他走向电梯，两侧员工停下交谈，视线集中到他身上。

3-6秒：
镜头切至严飞中近景，同侧固定视角。严飞迈出半步，朝商北琛说出"Welcome, Mr. Pierce."后停住。
```

整段 prompt 保持同侧轴线。**不使用人物左前方/右前方。** 不出现 "反打"。

## 错误写法（你这次踩的坑）

```text
3-6秒：镜头切至双人关系中景，商北琛右前方眼平...
6-8秒：镜头切至商北琛胸部以上中近景，乔熙左前方眼平...   ← 人物左右随朝向翻面
       反打至严飞胸部以上中近景，右前方眼平...             ← 又跨回来
```

模型实际生成时会把空间整个翻面，看起来就是"乱切乱跳"。

## Agent 执行

- `shot_director` 在镜头方案里就要锁好同侧轴线和简洁视角，不能让 compiler 自由发挥人物左右。
- `prompt_compiler` 输出前用 regex 自检：单 segment 内若出现人物相对左右视角，立即报硬失败。
- `quality_inspector` 见到"反打至"出现在单段 prompt 内一律判 fail。
