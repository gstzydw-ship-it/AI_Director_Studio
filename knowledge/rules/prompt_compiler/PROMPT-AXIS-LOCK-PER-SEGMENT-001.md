---
rule_id: PROMPT-AXIS-LOCK-PER-SEGMENT-001
title: 单片段内摄影机必须始终在轴线同侧
doc_type: rule_card
rule_type: prompt_compilation
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
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
avoid_when: []
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
- 左前方
- 右前方
- 单片段机位
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

Seedance 2.0 是单镜头连续生成模型。一个 segment 内出现"左前方"和"右前方"两种机位，模型只能用一次连续摇镜来糊近似，结果就是空间瞬间翻面、人物左右颠倒、背景错乱。这就是教科书级的 180° 轴线违规在 AI 视频生成里的具体后果。

## 规则

每个 prompt segment 必须在开头明确轴线方向（以哪两个锚点的连线为 180° 线），并选定摄影机所在的 **轴线一侧**（左 / 中 / 右），整段 prompt 内不得跨到另一侧。

**硬约束：**

1. 同一 segment 的【时间轴】**禁止**同时出现"左前方"与"右前方"——只能选一个并贯穿全段。
2. 同一 segment **禁止**出现"反打至 / 反打镜头 / 翻拍至"等剪辑性反打词。真要反打必须**拆段**，不能在单段 prompt 内做。
3. "侧面 / 侧前方 / 侧后方"必须明确指出是 **左侧** 还是 **右侧**，不许只写"侧面"。
4. 主体（人物）的视线轴线 + 摄影机位置必须保持几何自洽——不能写"商北琛面朝电梯（前方）+ 摄影机右前方拍摄"同时又写"摄影机左前方拍摄"。

## 跨轴的合法做法

如果剧情确实需要跨到另一侧，必须**拆成相邻的两个 segment**，并通过下面三种过渡之一衔接：

- **人物自然转身**：上一段尾帧人物完成转身动作，下一段以新朝向开拍。
- **越轴中性镜头**：在两段之间插入一个空镜或正面/俯拍中性视角。
- **场景固定机位接管**：从人物相对机位切换到 scene_fixed 机位作为中转。

## 禁止项

- 禁止写"反打至 X" 在单段 prompt 里。
- 禁止单段同时出现 `左前方` + `右前方` 两个方向词。
- 禁止用"同一机位继续"承接一个反向机位描述——这是隐性跨轴。
- 禁止 `scene_analyst.scene_lock.axis` 里写了一条轴线，但 prompt 里多个 segment 用不同轴线却没有过渡说明。

## 正确写法

```text
0-3秒：
摄影机位于商北琛右前方眼平高度，距其约 2 米，沿大堂中轴方向以稳定器同速后退。
商北琛沿中轴匀速前进，视线平视前方。两侧员工同时停止交谈，目光向中轴收拢。

3-6秒：
同一机位继续（右前方眼平），固定不动。前排主管从中间向左右退开让出通道。
严飞从右侧前缘迈出半步，朝商北琛说出"Welcome, Mr. Pierce."后停住。
```

整段 prompt 摄影机始终在轴线右侧。**不出现 "左前方"。** 不出现 "反打"。

## 错误写法（你这次踩的坑）

```text
3-6秒：镜头切至双人关系中景，右前方眼平...
6-8秒：镜头切至商北琛胸部以上中近景，左前方眼平...   ← 跨轴
       反打至严飞胸部以上中近景，右前方眼平...        ← 又跨回来
```

模型实际生成时会把空间整个翻面，看起来就是"乱切乱跳"。

## Agent 执行

- `shot_director` 在 `main_shots[*].camera_position` 字段里就要锁好"左/中/右轴线侧"，不能让 compiler 自由发挥。
- `prompt_compiler` 输出前用 regex 自检：单 segment 内若同时出现 `左前方` + `右前方`，立即报硬失败。
- `quality_inspector` 见到"反打至"出现在单段 prompt 内一律判 fail。
