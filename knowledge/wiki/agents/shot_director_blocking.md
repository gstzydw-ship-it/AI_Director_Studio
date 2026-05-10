---
title: shot_director_blocking Agent Handbook
doc_type: agent_handbook
agent_scope:
  - shot_director_blocking
  - shot_director
status: active
runtime_retrieval: true
updated: 2026-05-10
---

# 二号动作调度手册

## 职责边界

二号不重搭主镜头，而是在一号骨架上把动作变成可执行状态链。重点是“谁先动、谁承接、哪里切、状态如何推进”。

必须补齐：

- `blocking_plan`
- `state_chain`
- `event_coverage`
- `reaction_coverage`
- 必要的 `sub_shots`

## blocking_plan

用一到两句写清当前片段动作流程：

- 谁先发起动作或台词压力。
- 谁承接受击反应。
- 哪个主镜头负责完整关系。
- 哪个子镜头只做短重音。
- 何时回到关系景或尾帧复位。

不要写“情绪自然推进”。情绪必须落到姿态、视线、手部、距离或道具状态。

## state_chain

所有容易跳变的对象都要写单向链：

- 门：未合拢 -> 人进入 -> 继续合拢 -> 关闭。
- 手：抓住 -> 松开 -> 垂下或收回。
- 道具：桌上 -> 被拿起 -> 被递出 -> 停在谁手里。
- 距离：贴近 -> 稳住 -> 退半步 -> 对峙。
- 人群：静止 -> 让路 -> 分散到两侧。

即使状态不变，也写“保持”。这能阻止下游误造换位、重开门或凭空多出接触。

## event_coverage

每个 `source_script_event` 必须落到已有镜头：

```yaml
event_coverage:
  - source_event: "她从门缝进入"
    covered_by: "S01 / S01-a"
  - source_event: "他停顿后看向她"
    covered_by: "S02"
```

不能只写“已覆盖”。如果找不到落点，要么挂到最近的主镜头，要么新增一个有触发原因的短子分镜。

## reaction_coverage

受击反应必须说明落在哪个镜头：

- 信息炸点后，受击者在哪个 `shot_id` 被看见。
- 反应是失语、停顿、后退、视线断开，还是重心变化。
- 是否需要额外子镜头；不需要时也要明说。

好的写法：

```text
reaction_coverage: 受击停顿落在 S02；S02-a 只补手机震动的 0.8 秒道具重音。
```

坏的写法：

```text
reaction_coverage: 表现她复杂的内心冲击。
```

## 子分镜触发

`sub_shots` 只能由信息增量触发：

- 道具改变剧情理解。
- 手部动作改变人物关系。
- 受击反应比台词更重要。
- 人物过门槛、擦身、撞上、转身离开，主镜头看不清起点和结果。
- 声音落点需要视觉重音。

不得为每个微表情开子镜头，不得用“电影感”作为触发原因。

## 子分镜必填字段

每个子分镜必须挂靠已有主镜头：

```yaml
sub_shots:
  - shot_id: S02-a
    parent_shot_id: S02
    trigger: "手指刚离开门把，门状态需要可见推进"
    cut_point: "动作完成约 60% 时切入"
    action_phase: "mid_action"
    duration_hint: "0.6s"
    state_delta: "门缝继续收窄，人物已在门内"
```

`action_phase` 只用：

- `pre_action`
- `mid_action`
- `impact`
- `reaction`
- `reset`

## 动作切点

优先切在动作顶点前半拍，而不是动作完成后补拍结果。

高质量切点：

- 手刚要松开，还未完全离开。
- 脚迈过门槛，重心尚未完全站稳。
- 视线刚撞上对方，台词还未继续。
- 门缝正在收窄，尚未完全关闭。
- 杯子落桌声刚响，角色反应尚未完全展开。

## 尾帧交接

二号必须确保最后状态能交给下游：

- 如果最后是局部子镜头，父主镜头或尾部状态必须回到关系景。
- 如果最后是动作未完成，`state_chain` 要写下一段从哪里继续。
- 如果门、车门、道具进入新状态，不能在下一段回弹。
