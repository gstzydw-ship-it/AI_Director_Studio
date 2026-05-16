---
title: Continuity Contract
doc_type: contract
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

# Continuity Contract

## 目的

本合同是全流程共享的连续性状态协议。它规定哪些状态必须显式继承，哪些状态只能作为参考，哪些状态禁止被下游自动复活。所有 Agent 都应把连续性当作硬约束，而不是风格建议。

## 输入

任一阶段处理片段时，应能读取：

- `scene_lock`：服装、道具、光线、时段、轴线、视线网络。
- `active_cast`：当前片段允许可见并发生动作、台词或关系功能的人。
- `offscreen_cast`：当前片段必须退出、不可见或无戏份的人。
- `state_contract.entry_state`：首帧人物位置、空间轴线、门/车/道具状态。
- `state_contract.exit_state`：尾帧要留给下一段的状态。
- `state_contract.object_state_transitions`：门、车、道具、身体接触的单向变化。
- `state_contract.forbidden_continuity`：禁止复活的人、禁止回弹的状态、禁止偷跑的反应。
- `reference_bindings`：人物图、场景图、位置图、尾帧图的职责绑定。
- `first_frame_lock` / `tailframe_lock`：像素级锚点和段间承接描述。

## 输出

每个 Agent 应按职责输出连续性相关字段：

- `scene_analyst`：输出完整 `scene_lock` 与 `reference_bindings`。
- `story_planner`：把 `scene_lock` 初始化为片段 `state_contract.entry_state`，并写出 `exit_state`、状态变化和禁止项。
- `shot_director`：在 `main_shots` 与 `sub_shots` 中继承人物、道具、门状态和轴线，不反向改写。
- `prompt_compiler`：把连续性状态翻译为首帧、时间轴、尾帧、参考图和负约束。
- `quality_inspector`：检查所有连续性字段是否存在、互相一致、可生成，并对 P0 断裂阻断。

## 必须继承的状态

- 人物身份：角色名、`subject_id`、参考图绑定、服装关键件。
- 人物可见性：只继承 `active_cast`，不从尾帧图自动继承全部可见人物。
- 空间轴线：以 `scene_lock.axis` 为准，单片段内摄影机在同一轴线侧。
- 首尾帧像素锚：上一段尾帧描述应与下一段首帧描述字面对齐。
- 道具状态：位置、归属、开合、拿放、是否破损/沾染。
- 门/阈值状态：必须按物理方向单调推进。
- 光线和时段：不得在同一场景内无理由跳变。
- 参考图职责：人物图管身份，场景图管空间，尾帧图管首帧连续。

## 禁止事项

- 禁止缺失 `active_cast / offscreen_cast / state_contract`。
- 禁止把尾帧中可见但当前无戏份的人继续写进 prompt。
- 禁止门已关闭后又无触发原因地打开，或门缝收窄后又被冲开。
- 禁止单片段内跨轴，或把“反打至”写成连续生成动作。
- 禁止只写“位于中轴/前方/后方”而缺少像素锚点。
- 禁止参考图职责污染，例如人物图背景覆盖当前场景、场景图改写人物身份。
- 禁止用尾帧文字分析替代尾帧图的首帧锚定职责。
- 禁止下游为了镜头效果改写上游状态合同。

## 最小返修原则

- 字段缺失：补齐字段，不重写创意。
- 人物复活：删除无戏份人物及其参考图调用，必要时加负绑定。
- 门状态回弹：保留剧本核心动作，只修为单向状态链；若剧本明确重开，补触发原因。
- 轴线冲突：统一到既定轴线侧；必须换侧时拆段并补自然转身、中性镜头或固定机位中转。
- 像素跳位：补主体像素位置、背景锚点、构图比例，使首尾帧描述对齐。
- 参考图污染：改绑定或删错图，不重写剧情。
- 光线/时段矛盾：按 `scene_lock` 或上游明确来源修正，不凭空创造新环境。

## 原始来源

- `CONT-STATE-CONTRACT-001`
- `SCENE-CONSISTENCY-LOCK-001`
- `SCENE-REF-IMAGE-BINDING-001`
- `PROMPT-FIRST-FRAME-PIXEL-LOCK-001`
- `PROMPT-AXIS-LOCK-PER-SEGMENT-001`
- `REF-TAILFRAME-PRIORITY-001`
- `REFERENCE-ROLE-STRICT-001`
- `CONT-CAST-ACTIVE-001`
- `CONT-DOOR-MONOTONIC-001`
- `QC-HARD-FAIL-001`
- `knowledge/06_连续性与安全规则.md`
- `knowledge/11_场景分析输入卡与导演意图提取.md`
