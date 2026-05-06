---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事18_所听所见与主观感知
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 日常压缩/对话场景
- dialogue
- action
events:
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
- offscreen_space
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事18_所听所见与主观感知
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事18_所听所见与主观感知
title: 视频拆片案例：镜头叙事_如何用镜头讲故事18_所听所见与主观感知
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事18_所听所见与主观感知.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事18_所听所见与主观感知

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "壁球馆与更衣室对话（声画分离案例）"
    scene_type: "日常压缩/对话场景"
    emotional_arc: "激烈运动→疲惫放松→平稳交流"
    duration_estimate: "35"
    shots:
      - index: 1
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "两人在壁球馆内，一前一后，空间开阔"
        narrative_function: "建立人物关系与运动场景，通过画外音交代对话内容"
        cut_reason: "动作段落结束，丰富视觉角度"
      - index: 2
        duration: "4s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "从场馆上方俯视两人，人物占画面比例较小"
        narrative_function: "展现运动的激烈程度与空间全貌，维持视觉新鲜感"
        cut_reason: "需要聚焦单人动作状态"
      - index: 3
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物居中，占据画面主体"
        narrative_function: "突出人物运动时的专注与体力消耗"
        cut_reason: "运动动作结束，展示结果"
      - index: 4
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物倒在画面中央地板上，留白较多"
        narrative_function: "标志运动结束，体力耗尽，为场景转换做视觉缓冲"
        cut_reason: "声画分离结束，转入声画同步的真实对话空间"
      - index: 5
        duration: "6s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物侧脸，背景为红色储物柜，景深较浅"
        narrative_function: "声画合一，将观众拉回真实的对话时空，聚焦人物情绪"
        cut_reason: "另一角色加入画面，需要展示两人互动"
      - index: 6
        duration: "11s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人同框，一坐一站，红色柜子作为背景"
        narrative_function: "完整展示两人在更衣室的交流状态与肢体语言"
        cut_reason: "案例片段展示结束"
    pattern_summary:
      rhythm: "快切运动→定格倒地→平稳对话"
      director_intent: "通过声画分离将冗长的对话与激烈的运动画面结合，加快叙事节奏，避免纯对话戏的沉闷拖沓。"
      reusable_pattern: "长对话戏=激烈运动画面+对话画外音→运动结束定格→转场声画同步收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "壁球馆与更衣室对话（声画分离案例）"
    scene_type: "日常压缩/对话场景"
    emotional_arc: "激烈运动→疲惫放松→平稳交流"
    duration_estimate: "35"
    shots:
      - index: 1
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "两人在壁球馆内，一前一后，空间开阔"
        narrative_function: "建立人物关系与运动场景，通过画外音交代对话内容"
        cut_reason: "动作段落结束，丰富视觉角度"
      - index: 2
        duration: "4s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "从场馆上方俯视两人，人物占画面比例较小"
        narrative_function: "展现运动的激烈程度与空间全貌，维持视觉新鲜感"
        cut_reason: "需要聚焦单人动作状态"
      - index: 3
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物居中，占据画面主体"
        narrative_function: "突出人物运动时的专注与体力消耗"
        cut_reason: "运动动作结束，展示结果"
      - index: 4
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物倒在画面中央地板上，留白较多"
        narrative_function: "标志运动结束，体力耗尽，为场景转换做视觉缓冲"
        cut_reason: "声画分离结束，转入声画同步的真实对话空间"
      - index: 5
        duration: "6s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物侧脸，背景为红色储物柜，景深较浅"
        narrative_function: "声画合一，将观众拉回真实的对话时空，聚焦人物情绪"
        cut_reason: "另一角色加入画面，需要展示两人互动"
      - index: 6
        duration: "11s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人同框，一坐一站，红色柜子作为背景"
        narrative_function: "完整展示两人在更衣室的交流状态与肢体语言"
        cut_reason: "案例片段展示结束"
    pattern_summary:
      rhythm: "快切运动→定格倒地→平稳对话"
      director_intent: "通过声画分离将冗长的对话与激烈的运动画面结合，加快叙事节奏，避免纯对话戏的沉闷拖沓。"
      reusable_pattern: "长对话戏=激烈运动画面+对话画外音→运动结束定格→转场声画同步收尾"
```
