---
rule_id: PROMPT-FIRST-FRAME-PIXEL-LOCK-001
title: 首帧锁必须含像素锚点（不只人物相对位置）
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- scene_analyst
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: first_frame_lock_translation
runtime_retrieval: true
retrieval_key:
- prompt-first-frame-pixel-lock-001
- signals.vertical_framing
- signals.tailframe_lock
- events.door_state
- events.tailframe
- risks.door_state_jump
- risks.vertical_closeup_overuse
- risks.reference_misuse
- scene_types.elevator
applies_when:
- 首帧锁定
- 像素锚点
- 空间与首帧总控
avoid_when:
- "没有首帧、尾帧或空间继承需求。"
failure_mode:
- "首帧只写相对位置，缺少像素锚点，导致段间跳位。"
output_contract: "首帧至少覆盖主体像素位置、背景锚点或构图比例中的两类。"
example_good: "商北琛半身正面位于画面中央，背景远端正中可见电梯门。"
example_bad: "商北琛位于中轴入口方向面朝电梯。"
signals:
- vertical_framing
- tailframe_lock
scene_types:
- elevator
events:
- door_state
- tailframe
risks:
- door_state_jump
- vertical_closeup_overuse
- reference_misuse
aspect_ratios:
- '9:16'
- '16:9'
applies_to:
- 首帧锁定
- 像素锚点
- 空间与首帧总控
- 段间承接
- 尾帧像素一致
source_files:
- knowledge/11_场景分析输入卡与导演意图提取.md
- knowledge/rules/scene_analyst/SCENE-CONSISTENCY-LOCK-001.md
- knowledge/rules/scene_analyst/SCENE-REF-MISSING-FALLBACK-001.md
- knowledge/rules/prompt_compiler/REF-TAILFRAME-PRIORITY-001.md
conflicts_with: []
supersedes: []
---

# 首帧锁必须含像素锚点（不只人物相对位置）

## 背景

`scene_lock.first_frame_lock` 现在常写成"商北琛位于中轴入口方向面朝电梯"——这是**人物相对场景**的描述。视频模型每次生成时，只要"中轴""入口方向""面朝电梯"这几个语义要素满足，**首帧像素位置可以差很多**：人物可能在画面中央、画面左 1/3、画面右 1/4 的任何位置。

这个不确定性是段间空间跳变的根源：上一段尾帧人物在画面中央，下一段首帧人物突然到了画面左侧——视觉上就是"瞬移"。

## 规则

`scene_lock.first_frame_lock` 与 prompt 的【空间与首帧总控】**必须同时包含像素级锚点描述**，至少满足以下三类锚点中的两类：

### 类型 A：主体像素位置
- "商北琛位于画面**中央**" / "在画面**右 1/3**" / "在画面**左侧 1/4**" / "在画面**纵向 1/2** 处"
- "商北琛**占画面高度** 1/2" / "**占画面宽度** 1/3"
- "商北琛**胸口**对齐画面**纵向 1/2** 处" / "**头顶**距画面顶部 1/8"

### 类型 B：背景锚点像素位置
- "电梯门框位于画面**远端中央**" / "在画面**右上角**"
- "桌沿在画面**底部 1/4**"
- "员工列分布于画面**左 1/4 与右 3/4**"

### 类型 C：构图比例
- 画幅中央十字线人物胸口落点
- 9:16 竖屏，人物占画面**纵向 50%-60%**，头顶留**画面顶部 1/8** 安全区
- 16:9 横屏，三分法**右垂线** 上对齐人物视线

## 禁止项

- 禁止只写"X 位于中轴入口方向"这种**纯人物相对场景**的描述。
- 禁止只写"X 在画面前方 / 后方"这种**深度方向无像素锚**的描述。
- 禁止首帧锚点和后续段尾帧锚点用**不同的像素描述体系**（例如本段用"画面中央"，下段用"右前方稍偏左"——下游模型接不上）。

## 段间一致性

**前一段的尾帧像素描述 = 下一段的首帧像素描述**，必须**逐字对齐**。例如：

```text
[Segment A] 尾帧锁：
商北琛站定于画面中央偏右 1/8 处，胸口对齐画面纵向 1/2 处，
背后远端中央电梯金属门关闭，左右两侧员工列虚化。

[Segment B] 首帧锁：
商北琛站定于画面中央偏右 1/8 处，胸口对齐画面纵向 1/2 处，
背后远端中央电梯金属门关闭，左右两侧员工列虚化。
```

字面一致，模型才能在段间无缝接续。

## 正确写法

```text
【空间与首帧总控】
现代集团大堂，9:16 竖屏。
首帧像素锁：商北琛半身正面位于画面中央，胸口对齐画面纵向 1/2 处，
占画面高度约 50%。背景远端正中可见电梯金属门作为锚点，左右两侧
员工列各 4 人虚化分布于画面 1/4 与 3/4 纵线处。冷蓝顶光基底。
```

## 错误写法（你这次踩的坑）

```text
【空间与首帧总控】
集团大堂明亮自然光，电梯方向位于大堂中轴前方，两侧员工分列通道两边。
首帧中商北琛位于中轴入口方向面朝电梯，前排主管仍占据中间通道，
严飞在右侧前缘。
```

只有"中轴""入口方向""右侧前缘"这种相对位置——**完全没说像素位置**。模型每次首帧都不一样，段间必跳。

## Agent 执行

- `scene_analyst` 写 `scene_lock.first_frame_lock` 时**必须**写出至少 2 类像素锚点（A/B/C 三类）。
- `shot_director` 在 `main_shots[0].first_frame` 字段同样要包含像素锚点字段（subject_pixel_position / background_pixel_anchor / composition_ratio）。
- `prompt_compiler` 编译时把这些字段翻译成自然中文像素描述，写入【空间与首帧总控】。
- `prompt_compiler` 自检：【空间与首帧总控】中若缺失像素锚关键词（"画面中央"/"画面 X/Y"/"占画面"/"纵向 X 处"/"横向 X 处"等）即报硬失败。
- `quality_inspector` 检查段间像素描述是否字面一致；不一致按 P0 阻断。
