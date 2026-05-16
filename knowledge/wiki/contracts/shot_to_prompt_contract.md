---
title: Shot To Prompt Contract
doc_type: contract
agent_scope:
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

# Shot to Prompt Contract

## 目的

本合同定义 `shot_director` 交给 `prompt_compiler` 的镜头执行边界。Prompt 层只能把已批准的镜头方案翻译成可执行自然语言，不新增剧情、不改镜头决策、不重排状态。

## 输入

`shot_director` 至少应提供：

- `fragment_id` / `segment_id` 与稳定 `shot_id`。
- `main_shots[]`：主体、镜头功能、景别、机位高度、拍摄角度、运镜、承载的信息。
- `sub_shots[]`：`parent_shot_id`、局部重音、反应、cutaway、时间段。
- `timeline`：单层时间轴，主分镜和子分镜各有独立时间窗。
- `assigned_dialogue`：对白原文、说话者、落点时间。
- `visible_action`：可见动作与道具变化。
- `camera_axis`：本片段轴线定义、摄影机所在侧、合法过渡方式。
- `first_frame` / `tailframe`：首尾帧构图、人物位置、状态锚点。
- `state_contract` 与 `scene_lock`。
- `reference_bindings`：人物、场景、尾帧图的职责绑定。

## 输出

`prompt_compiler` 应输出：

- 当前片段的最终 prompt，不夹带历史片段完整 prompt 或时间轴。
- `空间与首帧总控`：场景、画幅、首帧像素锁、尾帧继承、参考图职责。
- `时间轴`：每个时间段先立分镜基底，再写动作、对白落点和状态变化。
- `参考图绑定说明`：每张图只承担一种职责，必要时附 `@图片N`。
- `连续性约束`：active/offscreen、道具、门状态、轴线、尾帧衔接。
- `negative_constraints` 或等价约束：不允许出字幕、屏幕文字、无戏份人物、反向门状态等。
- `compiler_self_check`：覆盖当前片段范围、轴线、参考图、对白、状态合同的自检结果。

## 必须继承的状态

- `active_cast` 只决定当前可见人物，尾帧中可见但当前无戏份的人不得自动继承。
- `offscreen_cast` 必须转为负绑定或不出现约束。
- `state_contract.entry_state` 必须进入首帧描述。
- `state_contract.exit_state` 必须进入尾帧或最后时间段描述。
- `object_state_transitions` 必须按单向物理变化翻译，不得回弹。
- `scene_lock.axis` 必须转为 prompt 中的轴线侧约束。
- `first_frame` 像素锚点必须保留主体像素位置、背景锚点或构图比例中的至少两类。
- `reference_bindings` 必须按 `role` 使用，不能让人物图、场景图、尾帧图互相污染。

## 禁止事项

- 禁止把当前 prompt 写成关键词串或概念标签，必须是可直接执行的自然导演句。
- 禁止输出当前片段之外的历史片段标题、完整 prompt 或旧时间轴。
- 禁止时间段先写动作再补镜头基底；每段第一句至少明确主体、景别、机位高度、角度、运镜中的三项。
- 禁止单个 segment 内同时出现左前方和右前方，禁止写“反打至”作为连续段内动作。
- 禁止因参考图中有人，就把无戏份人物写入时间轴。
- 禁止长篇复述尾帧分析报告；有尾帧图时，尾帧图优先承担首帧、场景、构图、光线和空间锚点。
- 禁止用人物参考图背景覆盖当前场景，或用场景参考图改写人物身份。
- 禁止让 prompt 新增床边、车内、保镖、记者、闪光灯等上游未批准前提。

## 最小返修原则

返修时只处理会导致模型误解或质检 fail 的硬伤：

- 缺分镜基底：补主体、景别、机位高度、角度或运镜，不改变动作。
- 轴线冲突：保留上游主镜头意图，只统一为同一侧；需要跨轴时拆相邻 segment 并补合法过渡。
- 参考图污染：删掉错误绑定和无戏份人物，不重写整段 prompt。
- 首帧跳位：补像素锚点，使上一段尾帧描述与本段首帧描述字面对齐。
- 历史片段污染：删除旧片段内容，只保留用于连续性的尾帧、角色、道具和轴线信息。
- 对白问题：恢复 `assigned_dialogue` 原文与顺序，不润色、不增补。

## 原始来源

- `PROMPT-EXECUTABLE-STRUCTURE-001`
- `PROMPT-CURRENT-SEGMENT-ONLY-001`
- `PROMPT-TIMELINE-SHOT-BASE-001`
- `PROMPT-FIRST-FRAME-PIXEL-LOCK-001`
- `PROMPT-AXIS-LOCK-PER-SEGMENT-001`
- `REF-TAILFRAME-PRIORITY-001`
- `REFERENCE-ROLE-STRICT-001`
- `CONT-CAST-ACTIVE-001`
- `SHOT-DIRECTOR-STEPWISE-PIPELINE-001`
- `SHOT-ACTION-COVERAGE-001`
- `SHOT-DIALOGUE-COVERAGE-001`
- `LAYOUT-SHOTID-STABILITY-001`
- `knowledge/07_Seedance输出词典与模型适配.md`
- `knowledge/20_镜头库与机位库.md`
- `knowledge/21_镜头调用规则与多机位模板.md`
