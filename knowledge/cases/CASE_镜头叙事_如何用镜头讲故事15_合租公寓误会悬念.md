---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事15_合租公寓误会悬念
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 尴尬撞见/日常冲突
- dialogue
- action
- suspense
events:
- collision
- door_state
- reaction
- cut
dialogue_types:
- argument_escalation
visual_constraints:
- medium_shot
- closeup
- over_shoulder
- shot_reverse_shot
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事15_合租公寓误会悬念
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事15_合租公寓误会悬念
title: 视频拆片案例：镜头叙事_如何用镜头讲故事15_合租公寓误会悬念
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事15_合租公寓误会悬念.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事15_合租公寓误会悬念

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "合租公寓撞见闺蜜洗澡"
    scene_type: "尴尬撞见/日常冲突"
    emotional_arc: "平静→吃惊→无语→生气→焦急"
    duration_estimate: "20"
    shots:
      - index: 1
        duration: "5s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影居中，走向正前方的门"
        narrative_function: "建立空间环境，交代人物的行动轨迹"
        cut_reason: "人物推开门，需要展示门内的景象或人物的反应"
      - index: 2
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "人物面部居中，占据大部分画面"
        narrative_function: "通过面部表情直接传递吃惊的情绪，制造悬念"
        cut_reason: "观众需要知道她看到了什么，切向主观视点"
      - index: 3
        duration: "3s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "女主背影作为前景遮挡在左下角，门内两人在画面中央"
        narrative_function: "揭示悬念，建立三人之间的空间和视线关系"
        cut_reason: "门内人物打招呼，需要切回女主的反应"
      - index: 4
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "人物面部居中"
        narrative_function: "展示人物的无语和尴尬，并完成关门的动作"
        cut_reason: "门关上，动作结束，需要展示门外的后续行动"
      - index: 5
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物站在门前居中，全身可见"
        narrative_function: "重新建立门外的空间，展示人物生气的情绪状态"
        cut_reason: "人物情绪升级并开始抱怨，需要更近的景别来强调台词"
      - index: 6
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "面部特写，人物说完后向左走出画框"
        narrative_function: "放大情绪，强调抱怨的台词，出画动作为转场做准备"
        cut_reason: "人物走出画面，利用空镜头进行场景和时间的转换"
      - index: 7
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物侧面坐在沙发上，看手表的动作居中"
        narrative_function: "通过入画动作和看表交代时间流逝和焦急等待，实现时间压缩"
        cut_reason: "场景叙事完成"
    pattern_summary:
      rhythm: "动作引导→正反打快切→情绪放大→出画留白"
      director_intent: "利用正反打和过肩镜头清晰交代空间关系，通过景别收缩（中景到特写）强化人物的心理反应，最后用出画入画巧妙压缩时间。"
      reusable_pattern: "尴尬撞见=动作入场→特写反应→过肩视点揭示→特写反应并退出→情绪放大→出画转场"
```

## 原始分析

```yaml
cases:
  - case_title: "合租公寓撞见闺蜜洗澡"
    scene_type: "尴尬撞见/日常冲突"
    emotional_arc: "平静→吃惊→无语→生气→焦急"
    duration_estimate: "20"
    shots:
      - index: 1
        duration: "5s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影居中，走向正前方的门"
        narrative_function: "建立空间环境，交代人物的行动轨迹"
        cut_reason: "人物推开门，需要展示门内的景象或人物的反应"
      - index: 2
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "人物面部居中，占据大部分画面"
        narrative_function: "通过面部表情直接传递吃惊的情绪，制造悬念"
        cut_reason: "观众需要知道她看到了什么，切向主观视点"
      - index: 3
        duration: "3s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "女主背影作为前景遮挡在左下角，门内两人在画面中央"
        narrative_function: "揭示悬念，建立三人之间的空间和视线关系"
        cut_reason: "门内人物打招呼，需要切回女主的反应"
      - index: 4
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "人物面部居中"
        narrative_function: "展示人物的无语和尴尬，并完成关门的动作"
        cut_reason: "门关上，动作结束，需要展示门外的后续行动"
      - index: 5
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物站在门前居中，全身可见"
        narrative_function: "重新建立门外的空间，展示人物生气的情绪状态"
        cut_reason: "人物情绪升级并开始抱怨，需要更近的景别来强调台词"
      - index: 6
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "面部特写，人物说完后向左走出画框"
        narrative_function: "放大情绪，强调抱怨的台词，出画动作为转场做准备"
        cut_reason: "人物走出画面，利用空镜头进行场景和时间的转换"
      - index: 7
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物侧面坐在沙发上，看手表的动作居中"
        narrative_function: "通过入画动作和看表交代时间流逝和焦急等待，实现时间压缩"
        cut_reason: "场景叙事完成"
    pattern_summary:
      rhythm: "动作引导→正反打快切→情绪放大→出画留白"
      director_intent: "利用正反打和过肩镜头清晰交代空间关系，通过景别收缩（中景到特写）强化人物的心理反应，最后用出画入画巧妙压缩时间。"
      reusable_pattern: "尴尬撞见=动作入场→特写反应→过肩视点揭示→特写反应并退出→情绪放大→出画转场"
```
