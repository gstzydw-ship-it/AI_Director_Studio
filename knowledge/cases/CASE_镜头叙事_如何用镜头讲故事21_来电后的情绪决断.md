---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事21_来电后的情绪决断
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 情绪转折/决绝离场
- action
events:
- reaction
- cut
dialogue_types:
- argument_escalation
visual_constraints:
- wide_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事21_来电后的情绪决断
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事21_来电后的情绪决断
title: 视频拆片案例：镜头叙事_如何用镜头讲故事21_来电后的情绪决断
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事21_来电后的情绪决断.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事21_来电后的情绪决断

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "裸辞女孩扔手机决绝离场"
    scene_type: "情绪转折/决绝离场"
    emotional_arc: "平静→犹豫→决绝→释然"
    duration_estimate: "24"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中背影，走向喷泉，环境开阔"
        narrative_function: "建立空间环境，交代人物行走的初始平静状态"
        cut_reason: "人物停下脚步，需要切换视角观察其正面反应"
      - index: 2
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物位于画面左侧，背景为喷泉，视线下垂看手机"
        narrative_function: "展示人物停步看手机的动作，引出外部刺激"
        cut_reason: "需要向观众展示手机上的具体内容以传递关键信息"
      - index: 3
        duration: "2s"
        scale: "特写"
        angle: "主观POV/俯拍"
        movement: "固定"
        composition: "手机屏幕充满画面，清晰显示来电人信息"
        narrative_function: "主观视角传递核心信息（老板来电），建立冲突点"
        cut_reason: "信息传递完毕，需要切回人物面部展示其心理活动和反应"
      - index: 4
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物居左，右侧留出喷泉空间，动作幅度大"
        narrative_function: "展示人物短暂犹豫后做出扔手机的决绝动作"
        cut_reason: "动作已经发生，需要切到特写展示动作的直接结果"
      - index: 5
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "水面居中，水花溅起"
        narrative_function: "视觉和听觉上强调手机落水的结果，增强戏剧性和决绝感"
        cut_reason: "结果展示完毕，需要切回人物展示其扔完手机后的情绪状态"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "摇摄/跟拍"
        composition: "人物面部特写，眼神坚定，向右走出画框"
        narrative_function: "放大人物面部表情，展现其做出决定后的坚定与释然"
        cut_reason: "人物走出画框，需要用全景交代其最终的离去"
      - index: 7
        duration: "7s"
        scale: "全景"
        angle: "仰拍"
        movement: "缓升"
        composition: "喷泉居中，人物背影在右侧逐渐变小"
        narrative_function: "交代人物离场，环境的宏大与人物的背影形成对比，提供情绪留白"
        cut_reason: "场景叙事结束"
    pattern_summary:
      rhythm: "平缓交代→聚焦信息→动作爆发→情绪特写→远景留白"
      director_intent: "通过景别的收放（全-近-特-近-特-近-全）精准控制信息流和情绪张力，主观视角的切入增强代入感，最终的远景升降镜头强化了人物内心的释然与坚定。"
      reusable_pattern: "情绪转折戏=全景入场→近景反应→主观特写信息→动作爆发→特写结果→近景情绪→全景离场"
```

## 原始分析

```yaml
cases:
  - case_title: "裸辞女孩扔手机决绝离场"
    scene_type: "情绪转折/决绝离场"
    emotional_arc: "平静→犹豫→决绝→释然"
    duration_estimate: "24"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中背影，走向喷泉，环境开阔"
        narrative_function: "建立空间环境，交代人物行走的初始平静状态"
        cut_reason: "人物停下脚步，需要切换视角观察其正面反应"
      - index: 2
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物位于画面左侧，背景为喷泉，视线下垂看手机"
        narrative_function: "展示人物停步看手机的动作，引出外部刺激"
        cut_reason: "需要向观众展示手机上的具体内容以传递关键信息"
      - index: 3
        duration: "2s"
        scale: "特写"
        angle: "主观POV/俯拍"
        movement: "固定"
        composition: "手机屏幕充满画面，清晰显示来电人信息"
        narrative_function: "主观视角传递核心信息（老板来电），建立冲突点"
        cut_reason: "信息传递完毕，需要切回人物面部展示其心理活动和反应"
      - index: 4
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物居左，右侧留出喷泉空间，动作幅度大"
        narrative_function: "展示人物短暂犹豫后做出扔手机的决绝动作"
        cut_reason: "动作已经发生，需要切到特写展示动作的直接结果"
      - index: 5
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "水面居中，水花溅起"
        narrative_function: "视觉和听觉上强调手机落水的结果，增强戏剧性和决绝感"
        cut_reason: "结果展示完毕，需要切回人物展示其扔完手机后的情绪状态"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "摇摄/跟拍"
        composition: "人物面部特写，眼神坚定，向右走出画框"
        narrative_function: "放大人物面部表情，展现其做出决定后的坚定与释然"
        cut_reason: "人物走出画框，需要用全景交代其最终的离去"
      - index: 7
        duration: "7s"
        scale: "全景"
        angle: "仰拍"
        movement: "缓升"
        composition: "喷泉居中，人物背影在右侧逐渐变小"
        narrative_function: "交代人物离场，环境的宏大与人物的背影形成对比，提供情绪留白"
        cut_reason: "场景叙事结束"
    pattern_summary:
      rhythm: "平缓交代→聚焦信息→动作爆发→情绪特写→远景留白"
      director_intent: "通过景别的收放（全-近-特-近-特-近-全）精准控制信息流和情绪张力，主观视角的切入增强代入感，最终的远景升降镜头强化了人物内心的释然与坚定。"
      reusable_pattern: "情绪转折戏=全景入场→近景反应→主观特写信息→动作爆发→特写结果→近景情绪→全景离场"
```
