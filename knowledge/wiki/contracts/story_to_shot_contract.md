---
title: Story To Shot Contract
doc_type: contract
agent_scope:
  - story_planner
  - shot_director
  - shot_director_layout
  - shot_director_blocking
  - shot_director_guard
  - quality_inspector
status: active
runtime_retrieval: true
updated: 2026-05-10
---

# Story to Shot Contract

## 目的

本合同定义 `story_planner` 交给 `shot_director` 的最小可执行输入。目标不是提前设计镜头，而是把当前片段的剧本事实、节奏功能、时间边界和连续性状态交清楚，让镜头层只在合法事实内做导演执行。

## 输入

`story_planner` 至少应提供：

- `fragment_id` / `segment_id`：片段稳定编号。
- `source_script_events`：逐条来自当前输入剧本的可见事实、动作、台词、道具或空间变化。
- `exact_dialogue_units`：本片段允许使用的对白原文与说话者。
- `rhythm_function`：本片段承担的戏剧功能，例如冲突升级、悬念揭示、情绪极点、权力反转。
- `hook_weight`：高价值节拍权重，用于决定是否需要停顿、受击反应或片段阻断。
- `boundary_reason`：为什么本片段在此开始和结束。
- `reaction_need`：受击或听者反应的承接层级，只写结构判断，不写具体镜头。
- `time_budget`：10-15 秒内的时间容量、必须保留的动作和可压缩的无效位移。
- `scene_lock`：来自场景分析的服装、道具、光线、时段、轴线、视线网络。
- `state_contract`：本片段入口/出口状态。

## 输出

`shot_director` 应基于输入输出：

- `main_shots[]`：稳定 `shot_id`、镜头承担的叙事功能、主体、景别、机位、角度、运镜。
- `sub_shots[]` 或等价字段：挂接到 `parent_shot_id` 的局部重音、反应镜头、cutaway。
- `assigned_dialogue`：只来自 `exact_dialogue_units` 的对白落点。
- `visible_action`：只来自 `source_script_events` 的可见动作。
- `cut_points`：有信息变化的切点，而不是机械平均切割。
- `shot_level_state_delta`：镜头内人物、道具、门、身体接触的状态推进。
- `tailframe_intent`：尾帧应留下的可续接关系、构图或状态。

## 必须继承的状态

- `active_cast`：当前片段真正有动作、台词、受击或关系功能的人。
- `offscreen_cast`：上一段可能出现但当前不得继续出镜的人。
- `state_contract.entry_state`：首帧人物位置、空间轴线、门/车/道具初始状态。
- `state_contract.exit_state`：尾帧必须留给下游的状态。
- `state_contract.object_state_transitions`：门、车、道具、身体接触的单向变化。
- `state_contract.forbidden_continuity`：禁止复活的人、禁止回弹的门状态、禁止偷跑的反应。
- `scene_lock.axis` 与 `scene_lock.gaze_network`：镜头层不得反向改写。
- `reference_bindings` 中与人物身份、场景、尾帧相关的绑定关系。

## 禁止事项

- 禁止把 `story_planner` 的节奏判断扩写成剧本外动作、道具、人物或空间。
- 禁止用英文台词、昵称或 OS 的联想替换人物行中的角色名。
- 禁止把 15 秒片段当成单一长镜头，也禁止机械拆成多个 5-6 秒小片段。
- 禁止把完整发言单元截断到两个片段，除非剧本明确打断或戏剧动作重置。
- 禁止在 `story_planner` 阶段写特写、仰拍、Crash Zoom、黑屏等具体镜头执行。
- 禁止让低权重过场冒充 `power_reversal` 或 `cliffhanger`。
- 禁止保留无叙事增量的走路、站桩、问候或背景群演反应。

## 最小返修原则

若交接不合格，优先补齐缺失字段，而不是重写片段：

- 缺 `state_contract`：补入口、出口、对象状态变化和禁止项。
- 缺 `source_script_events` 证据：回到剧本逐条引用，不改写原意。
- 时间过满：先删除无叙事增量位移，再考虑增加新片段。
- 受击承接不清：只补 `reaction_need` 的承接层级，不提前设计镜头。
- 阈值空间混乱：只保留核心动作、门状态单向推进、进入触发点和尾帧状态。

## 原始来源

- `knowledge/agent_retrieval_contracts.yaml`
- `TIME-SEGMENT-MULTISHOT-001`
- `TIME-THRESHOLD-003`
- `RHYTHM-SIGNAL-TAXONOMY-001`
- `CONT-STATE-CONTRACT-001`
- `SCENE-CONSISTENCY-LOCK-001`
- `SHOT-SOURCE-EVENT-FIDELITY-001`
- `knowledge/05_剧本拆分与15秒片段规划规则.md`
- `knowledge/24_戏剧微粒识别与节奏触发规则.md`
- `knowledge/25_镜头摆位主分镜骨架规则.md`
