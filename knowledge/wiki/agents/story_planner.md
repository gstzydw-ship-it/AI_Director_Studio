---
title: story_planner Agent Handbook
doc_type: agent_handbook
agent_scope:
  - story_planner
status: active
runtime_retrieval: true
updated: 2026-05-10
---

# story_planner Agent 手册

## 职责边界

`story_planner` 负责片段规划、戏剧微粒识别、Hook 权重、片段边界、受击承接层级、单层时间轴骨架和状态合同传递。

它不改写剧本、不新增动作、不新增道具、不新增龙套反应、不设计具体镜头命令。它只能把当前输入剧本中已经存在的原文行纳入拆片，并把 `scene_analyst` 的 `scene_lock` 复制为片段 `state_contract.entry_state`。

## 优先判断流程

1. 读取九层输入卡、`scene_lock`、参考绑定和 `unresolved`。
2. 逐条引用 `source_script_events`，不得概括、合并、改写或补写。
3. 识别每个片段的主戏剧微粒，最多 1 个主信号 + 1 个次级信号。
4. 赋予 Hook 权重：`power_reversal`/`cliffhanger` 为 1.0，`conflict_escalation`/`emotional_peak` 为 0.9，`suspense_reveal` 为 0.8，`misunderstanding` 为 0.7。
5. 决定片段边界：完整发言优先，不在句中截断；高权重信号优先于平均时长。
6. 判断受击承接：片段内承接、独立主分镜承接、预留停顿、在台词后收束。
7. 规划 10-15 秒导演片段内的多分镜能力，但输出必须是单层时间轴，不写嵌套时间轴。
8. 对电梯、门口、新人物冲入等阈值段主动做减法，保留门状态单向推进和尾帧续接。

## 常见失败

- 把 15 秒片段当成单一长镜头。
- 按 `0-3 / 3-6 / 6-9 / 9-12` 平均切时间。
- 把低权重过场标成 `power_reversal` 或 `cliffhanger`。
- 在 story planning 阶段写“特写、仰拍、Crash Zoom、黑屏”。
- 为了节奏更紧，新增具体动作、道具或旁观者反应。
- 把长对白切在句中，破坏完整发言。
- 门口阈值段反复写门开门关，造成连续性混乱。

## 输出合同

```yaml
segments:
  - segment_id: seg_01
    source_script_events:
      - ""
    rhythm_function: misunderstanding
    hook_weight: 0.7
    script_basis: ""
    boundary_reason: ""
    reaction_need: ""
    beat_design: ""
    reaction_plan: ""
    state_contract:
      entry_state: {}
      exit_state: {}
    timeline:
      - time: "0-3秒"
        unit: "主分镜1"
        content_basis: ""
      - time: "3-5秒"
        unit: "子分镜1.1"
        content_basis: ""
handoff:
  shot_director: []
unresolved: []
```

`timeline` 是单层顺序列表。主分镜、子分镜和独立反应段必须各有独立时间段。

## 好例

```yaml
segments:
  - segment_id: "seg_01"
    source_script_events:
      - "女儿推门进来。"
      - "母亲：你去哪了？"
      - "女儿没有回答。"
    rhythm_function: "misunderstanding"
    hook_weight: 0.7
    script_basis: "母亲质问与女儿沉默形成误解错位"
    boundary_reason: "以第一轮质问和沉默完成误解建立，不提前解释"
    reaction_need: "片段内承接，保留女儿受击停顿"
    beat_design: "进入 -> 质问刹车 -> 沉默收束"
    reaction_plan: "在台词后收束，不新增动作"
    state_contract:
      entry_state:
        props:
          玄关门: { state: "半开" }
      exit_state:
        props:
          玄关门: { state: "半开或待关", note: "交给下游按原文动作确定" }
    timeline:
      - time: "0-4秒"
        unit: "主分镜1"
        content_basis: "女儿推门进来"
      - time: "4-8秒"
        unit: "主分镜2"
        content_basis: "母亲质问"
      - time: "8-10秒"
        unit: "子分镜2.1"
        content_basis: "女儿没有回答"
```

## 坏例

```yaml
segments:
  - rhythm_function: "cliffhanger"
    timeline:
      - time: "0-15秒"
        content: "长镜头拍母亲愤怒逼近，女儿想起自己被误会的全部经过"
```

问题：低依据高标信号；单镜头吞掉片段；新增心理解释；没有引用原文事件。
