# 系统流程速记

AI Director Studio 的核心不是“一次性生成视频 prompt”，而是有状态、可打断、可逐段续接的导演流水线。

## 总流程

```text
用户输入剧本/想法/参考图
  -> scene_analyst: 场景分析与参考图职责绑定
  -> director_showrunner: 导演意图与剧本增强
  -> rhythm_rewrite_director: 节奏改写与戏剧微粒强化
  -> story_planner: 10-15 秒片段拆分
  -> shot_director: 当前片段镜头设计
  -> storyboard_designer: 当前片段分镜图 prompt / 分镜图
  -> prompt_compiler: 视频模型可执行 prompt
  -> quality_inspector: 质检、返修、阻断
  -> wait_for_segment_request: 等待用户生成视频并上传尾帧
  -> 下一片段续接
```

## 两阶段运行心智模型

### 阶段一：全篇骨架规划

- 场景分析
- 故事/节奏规划
- 片段边界
- 主要镜头骨架
- 关键连续性状态

目标：先确定全片结构，避免后续逐段 prompt 各自发散。

### 阶段二：逐段增量生成

- 每次只处理一个 segment。
- 当前段完成后，等待用户提供上一段视频的尾帧截图或尾帧文字描述。
- 下一段必须继承尾帧、角色状态、道具状态、轴线、参考图职责。

目标：让 AI 视频模型逐段生成时保持角色、空间、动作和情绪连续。

## Agent 职责

### scene_analyst

输出场景输入卡：

- 地点、时段、光线、服装、道具
- 人物关系与当前可见角色
- 空间轴线、视线网络
- 参考图绑定：人物图、场景图、尾帧图、风格图

### director_showrunner

输出导演意图：

- 用户想要的类型、情绪、叙事重点
- 可以增强表达，但不能改写剧本事实
- 处理逻辑漏洞和明显不适合生成的表达

### story_planner

输出片段规划：

- `fragment_id` / `segment_id`
- `source_script_events`
- `exact_dialogue_units`
- `rhythm_function`
- `boundary_reason`
- `reaction_need`
- `time_budget`
- `state_contract`

### shot_director

输出镜头设计：

- `main_shots[]`
- `sub_shots[]`
- `assigned_dialogue`
- `visible_action`
- `cut_points`
- `shot_level_state_delta`
- `first_frame`
- `tailframe_intent`

### storyboard_designer

输出英文 storyboard image prompt：

- 单张 storyboard sheet
- panel-by-panel
- shot number、duration、framing、camera angle、movement、subject action、emotional beat
- 参考图视觉一致性说明

### prompt_compiler

输出视频模型可执行 prompt：

- 当前片段最终 prompt
- 空间与首帧总控
- 时间轴
- 参考图绑定说明
- 连续性约束
- negative constraints
- compiler self check

### quality_inspector

输出质检结果：

- pass / needs_repair / fail
- failed rule / evidence / severity
- required repairs
- pacing / safety / continuity / schema checks

