---
title: Elevator Exit Playbook
doc_type: playbook
agent_scope:
  - scene_analyst
  - story_planner
  - shot_director
  - shot_director_layout
  - shot_director_blocking
  - shot_director_guard
  - prompt_compiler
  - quality_inspector
  - storyboard_designer
status: active
runtime_retrieval: true
updated: 2026-05-10
---

# Playbook：电梯出入与门缝动作

## 适用场景

人物从电梯内外进出、门正在合拢、有人赶入或停在门口对峙。高风险点是门状态回弹、人物空间跳变、竖屏只拍脸导致门缝和身体动作不可见。

## 核心判断

电梯门是状态锚点，不是背景。先决定门状态，再决定镜头。

合法状态链：

```text
门打开/将合未合 -> 人物进入或退出 -> 门继续合拢 -> 门关闭
```

除非剧本明确写按开门键、挡门或门被重开，否则不得写“人进入后门又打开”。

## 摆位模板

推荐主镜头链：

1. `establish_relation`：电梯门、门内人物、门外人物、门缝宽度同框。
2. `pressure_source` 或 `action_start`：冲入者/阻拦者的动作起势。
3. `action_insert_slot`：预留手按门、脚过门槛、门缝收窄等短插入。
4. `impact_reaction`：被撞见、被阻拦或被命中的人反应。
5. `tailframe_reset`：回到电梯内外关系，门状态明确。

9:16 构图优先半身或中景，让门框成为纵向边界。不要用脸部特写替代门缝和身体位置。

## 动作锚点

优先使用：

- 脚跨过门槛，重心尚未完全站稳。
- 手按住电梯门边或松开门框。
- 门缝继续收窄。
- 电梯内人物退半步让出空间。
- 门外人物停在门口而没有进入。

切点通常放在动作完成 50%-70%：

```text
脚已经越过门槛但身体还未完全进入 -> 切到门内关系景
```

## blocking 必填

`state_chain` 至少覆盖：

- 门状态。
- 进入/退出人物的位置。
- 手部是否接触门。
- 同场人物是否被门框遮挡、留在画面边缘或画外。

`event_coverage` 必须把“进入”“阻拦”“门继续合拢”“停顿反应”等事件挂到镜头编号。

## 常见错误

- 门缝收窄后又被人物冲开，但没有阻门动作。
- 人已进电梯，下一镜仍在门外正面站立。
- 竖屏连续大头特写，门和身体位置完全不可见。
- 把意外撞入拍成慢动作拥抱或亲密凝视。
- 尾帧停在手部特写，下一段无法知道谁在门内外。

## 最小修复

- 给门补 `state_chain`，明确单向推进。
- 把无信息脸部特写降为电梯门框内半身关系景。
- 在 `companion_visibility` 写明被裁掉的人在门内左侧、门外右侧或画外哪一侧。
- 若必须重开门，补“按开门键/手挡住门”的触发动作。
- 尾镜头最后 0.5-1 秒回到门内外关系，写清门是将合、合拢中还是关闭。
