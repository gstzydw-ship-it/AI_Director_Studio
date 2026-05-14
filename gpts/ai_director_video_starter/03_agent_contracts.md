# Agent 交接合同浓缩版

## Story to Shot Contract

目的：`story_planner` 交给 `shot_director` 的不是镜头，而是当前片段的合法事实、时间边界、节奏功能和连续性状态。

### story_planner 必须交付

- `fragment_id` / `segment_id`
- `source_script_events`: 当前剧本里的可见事实、动作、台词、道具或空间变化
- `exact_dialogue_units`: 允许使用的对白原文与说话者
- `rhythm_function`: 冲突升级、悬念揭示、情绪极点、权力反转等
- `hook_weight`
- `boundary_reason`
- `reaction_need`
- `time_budget`
- `scene_lock`
- `state_contract`

### shot_director 必须输出

- `main_shots[]`: 稳定 shot_id、主体、景别、机位、角度、运镜、叙事功能
- `sub_shots[]`: 挂接到 parent_shot_id 的局部重音、反应镜头、cutaway
- `assigned_dialogue`: 只能来自 exact_dialogue_units
- `visible_action`: 只能来自 source_script_events
- `cut_points`: 有信息变化的切点
- `shot_level_state_delta`
- `tailframe_intent`

### 禁止

- 禁止把节奏判断扩写成剧本外动作、道具、人物或空间。
- 禁止在 story_planner 阶段写特写、仰拍、Crash Zoom、黑屏等具体镜头执行。
- 禁止把完整发言单元无理由截断到两个片段。
- 禁止保留无叙事增量的走路、站桩、问候或背景反应。

## Shot to Prompt Contract

目的：`prompt_compiler` 只能把已批准镜头方案翻译成可执行自然语言，不新增剧情，不改镜头决策，不重排状态。

### prompt_compiler 输入

- `segment_id` 与稳定 `shot_id`
- `main_shots[]` / `sub_shots[]`
- `timeline`
- `assigned_dialogue`
- `visible_action`
- `camera_axis`
- `first_frame` / `tailframe`
- `state_contract` / `scene_lock`
- `reference_bindings`

### prompt_compiler 输出

- 当前片段最终 prompt
- `空间与首帧总控`
- `时间轴`
- `参考图绑定说明`
- `连续性约束`
- `negative_constraints`
- `compiler_self_check`

### 禁止

- 禁止把 prompt 写成关键词串或概念标签。
- 禁止输出当前片段之外的历史片段完整 prompt。
- 禁止因参考图中有人，就把无戏份人物写入时间轴。
- 禁止人物图背景覆盖当前场景，或场景图改写人物身份。

## Continuity Contract

所有阶段都必须继承：

- `scene_lock`
- `active_cast`
- `offscreen_cast`
- `state_contract.entry_state`
- `state_contract.exit_state`
- `state_contract.object_state_transitions`
- `state_contract.forbidden_continuity`
- `reference_bindings`
- `first_frame_lock` / `tailframe_lock`

硬禁令：

- 禁止缺失 active_cast / offscreen_cast / state_contract。
- 禁止把尾帧中可见但当前无戏份的人继续写进 prompt。
- 禁止门、车、道具无因回弹。
- 禁止单片段内跨轴。
- 禁止参考图职责污染。

