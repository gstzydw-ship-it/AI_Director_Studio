---
rule_id: PROMPT-MAIN-SUBSHOT-TIMELINE-001
title: 主分镜与子分镜是内部结构，最终输出只写单层时间轴
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: timeline_flattening
runtime_retrieval: true
retrieval_key:
- prompt-main-subshot-timeline-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.door_state
- events.reaction
- risks.door_state_jump
- risks.blood_avoidance
- scene_types.elevator
- scene_types.dialogue
- scene_types.action
applies_when:
- Seedance Prompt
- 时间轴
- 主分镜
avoid_when:
- "上游没有 main_shots/sub_shots 结构。"
failure_mode:
- "把主分镜、子分镜、动作单元等内部标签输出成嵌套时间轴。"
output_contract: "最终 Seedance prompt 只写单层时间轴；主/子分镜翻译为普通时间段自然句。"
example_good: "0-3秒：商北琛正面半身中景，平视后退跟拍。"
example_bad: "0-3秒 主分镜1；1.5-2.1秒 子分镜1.1。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- elevator
- dialogue
- action
events:
- collision
- door_state
- reaction
risks:
- door_state_jump
- blood_avoidance
applies_to:
- Seedance Prompt
- 时间轴
- 主分镜
- 子分镜
- 机位库
- 景别库
- 景别切换
source_files:
- knowledge/00_知识库优先级与冲突裁决规则.md
- knowledge/05_剧本拆分与15秒片段规划规则.md
- knowledge/21_镜头调用规则与多机位模板.md
- knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes:
- PROMPT-SINGLE-CAMERA-CONTINUOUS-001
- PROMPT-SUBSHOT-WINDOW-NESTING-001
---

# 主分镜与子分镜是内部结构，最终输出只写单层时间轴

## 规则

最终 Seedance prompt 使用单层时间轴顺序排列主分镜和子分镜。

主分镜、子分镜是内部导演命名，不是最终 Seedance prompt 的显性标签。

最终输出不要出现“主分镜1”“子分镜1.1”“动作单元1”等教学标签。只用普通时间轴自然写出每个镜头段。

正确结构是：

```text
0-3秒：
主体半身中景，平视轻微后退跟拍，动作从 A 推进到 B。

3-5秒：
局部、关系、侧面、低机位或道具镜头，用来补足上一段动作锚点。

5-8秒：
进入下一拍主要镜头，承接上一段留下的动作或空间状态。
```

## 子分镜的定义

内部意义上，子分镜不是必须特写。它是服务上一动作起始镜头或当前动作锚点的短插入段，可以是：

- 局部特写。
- 低机位脚步景。
- 侧前方半身景。
- 背面跟随景。
- 双人关系景。
- 道具或手部镜头。
- 受击者、旁观者或儿童反应景。

子分镜必须有明确功能：补动作、补空间、补关系、补反应、补道具状态、补情绪落点。

## 景别接续

相邻主分镜/子分镜不能用相同景别直接硬接。

禁止：

- 特写接特写。
- 半身中景接半身中景，只换一点角度。
- 中近景接中近景，只换主体但没有反应功能。

允许：

- 半身中景主分镜接脚部或书包局部子分镜。
- 半身中景主分镜接低机位脚步中近景。
- 正面半身主分镜接侧前方双人关系景。
- 中景主分镜接手部或道具局部子分镜。
- 台词主体中近景接受击者反应半身景。

## 动作顶点前切

子分镜切入点优先放在动作顶点前，而不是动作完成后。

例如：

- 手指按下按钮之前切到按钮子分镜。
- 照片完全落地之前切到地面或书包关系景。
- 小豆丁的小脚完全伸稳之前切到脚步/鞋子子分镜。
- 人物完全转身之前切到背面或侧面承接镜头。

## 禁止

```text
0-3秒 动作单元1：
0-1.5秒 主分镜1……
1.5-2.1秒 子分镜1.1……
2.1-3秒 主分镜1延续……
```

错误原因：这会让结构太复杂，也容易诱导 agent 把动作切碎。

```text
0-3秒 主分镜1：
……
3-5秒 子分镜1.1：
……
```

错误原因：最终 Seedance prompt 不应出现“主分镜/子分镜”标签；这些只是内部镜头结构概念。

## 推荐写法

```text
0-3秒：
商北琛正面半身中景，平视轻微后退跟拍，他沿大堂中轴走向电梯，步伐沉稳，视线始终向前。

3-5秒：
电梯按钮局部特写，侧前方固定机位，商北琛的手指按下按钮，按钮灯亮起。

5-8秒：
电梯内正面半身中景，固定机位，商北琛站入电梯中央，电梯门从两侧缓缓合拢。
```

## Agent执行

- story_planner：可以在内部规划主分镜/子分镜顺序，不使用嵌套时间轴。
- shot_director：让内部子分镜承担机位、景别、关系或动作锚点功能，不默认写成特写。
- prompt_compiler：输出最终 Seedance prompt 时，只写普通时间段，不写“主分镜/子分镜”标签。
- quality_inspector：发现嵌套时间轴、重复时间窗、无功能插入段、相同景别直切、最终 prompt 出现“主分镜/子分镜”标签时判为不合格。
