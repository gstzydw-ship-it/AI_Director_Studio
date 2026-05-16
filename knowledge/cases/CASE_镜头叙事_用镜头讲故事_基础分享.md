---
case_title: 视频拆片案例：镜头叙事_用镜头讲故事_基础分享
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 悬念建立与警示
- dialogue
- action
- suspense
events:
- collision
- reaction
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
risks:
- blood_avoidance
reusable_pattern: CASE_镜头叙事_用镜头讲故事_基础分享
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头叙事_用镜头讲故事_基础分享
title: 视频拆片案例：镜头叙事_用镜头讲故事_基础分享
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_用镜头讲故事_基础分享.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
---

# 视频拆片案例：镜头叙事_用镜头讲故事_基础分享

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "酒驾公益广告：按车钥匙亮起手术室"
    scene_type: "悬念建立与警示"
    emotional_arc: "日常平静→悬念突变→震惊受击→释然放弃"
    duration_estimate: "28s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "两人在画面中央，背景是酒吧门头"
        narrative_function: "交代故事发生的地点和人物关系，暗示可能喝了酒"
        cut_reason: "动作完成，女生转身，需要跟进女生的单人动作"
      - index: 2
        duration: "8s"
        scale: "中景"
        angle: "平视"
        movement: "缓拉"
        composition: "女生在画面中央，随着镜头拉远，背景的BAR标志显现"
        narrative_function: "通过拉镜头强调环境信息，强化女生刚从酒吧出来的情境铺垫"
        cut_reason: "女生找到钥匙并准备按动，需要展示按动钥匙后的结果"
      - index: 3
        duration: "6s"
        scale: "全景"
        angle: "过肩"
        movement: "固定"
        composition: "女生在前景（背影），远处是亮起的手术室，形成强烈的视觉对比"
        narrative_function: "制造视觉奇观，将酒驾与严重后果（手术室）进行空间上的直接拼接，产生心理冲击"
        cut_reason: "需要展示手术室内部的细节，强化压迫感"
      - index: 4
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "医生在画面中央，直视镜头"
        narrative_function: "打破第四面墙，给观众和女主带来直接的死亡警告和压迫感"
        cut_reason: "需要看女主受到冲击后的反应"
      - index: 5
        duration: "1s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女主面部占据画面主体，背景虚化"
        narrative_function: "展示人物内心的挣扎、犹豫与觉醒"
        cut_reason: "女主做出决定，需要展示她的下一步行动"
      - index: 6
        duration: "3s"
        scale: "全景"
        angle: "过肩"
        movement: "固定"
        composition: "同镜头3，但灯光熄灭，回归黑暗"
        narrative_function: "象征女生放弃了酒驾的念头，切断了通往悲剧的可能"
        cut_reason: "危机解除，需要交代人物的最终去向"
      - index: 7
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "女生背影逐渐远去，画面中央留白出字幕"
        narrative_function: "交代最终选择，点明广告主题（酒后不开车）"
        cut_reason: "案例结束"
    pattern_summary:
      rhythm: "日常铺垫→拉镜头强调环境→突变（奇观）→快切反应→回归现实"
      director_intent: "通过将日常动作（按车钥匙）与极端后果（手术室）进行超现实的空间拼接，制造强烈的视觉和心理冲击，从而达到警示目的。"
      reusable_pattern: "警示类广告=日常行为铺垫→超现实后果闪现→人物受击短特写→放弃错误行为"
```

## 原始分析

```yaml
cases:
  - case_title: "酒驾公益广告：按车钥匙亮起手术室"
    scene_type: "悬念建立与警示"
    emotional_arc: "日常平静→悬念突变→震惊受击→释然放弃"
    duration_estimate: "28s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "两人在画面中央，背景是酒吧门头"
        narrative_function: "交代故事发生的地点和人物关系，暗示可能喝了酒"
        cut_reason: "动作完成，女生转身，需要跟进女生的单人动作"
      - index: 2
        duration: "8s"
        scale: "中景"
        angle: "平视"
        movement: "缓拉"
        composition: "女生在画面中央，随着镜头拉远，背景的BAR标志显现"
        narrative_function: "通过拉镜头强调环境信息，强化女生刚从酒吧出来的情境铺垫"
        cut_reason: "女生找到钥匙并准备按动，需要展示按动钥匙后的结果"
      - index: 3
        duration: "6s"
        scale: "全景"
        angle: "过肩"
        movement: "固定"
        composition: "女生在前景（背影），远处是亮起的手术室，形成强烈的视觉对比"
        narrative_function: "制造视觉奇观，将酒驾与严重后果（手术室）进行空间上的直接拼接，产生心理冲击"
        cut_reason: "需要展示手术室内部的细节，强化压迫感"
      - index: 4
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "医生在画面中央，直视镜头"
        narrative_function: "打破第四面墙，给观众和女主带来直接的死亡警告和压迫感"
        cut_reason: "需要看女主受到冲击后的反应"
      - index: 5
        duration: "1s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女主面部占据画面主体，背景虚化"
        narrative_function: "展示人物内心的挣扎、犹豫与觉醒"
        cut_reason: "女主做出决定，需要展示她的下一步行动"
      - index: 6
        duration: "3s"
        scale: "全景"
        angle: "过肩"
        movement: "固定"
        composition: "同镜头3，但灯光熄灭，回归黑暗"
        narrative_function: "象征女生放弃了酒驾的念头，切断了通往悲剧的可能"
        cut_reason: "危机解除，需要交代人物的最终去向"
      - index: 7
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "女生背影逐渐远去，画面中央留白出字幕"
        narrative_function: "交代最终选择，点明广告主题（酒后不开车）"
        cut_reason: "案例结束"
    pattern_summary:
      rhythm: "日常铺垫→拉镜头强调环境→突变（奇观）→快切反应→回归现实"
      director_intent: "通过将日常动作（按车钥匙）与极端后果（手术室）进行超现实的空间拼接，制造强烈的视觉和心理冲击，从而达到警示目的。"
      reusable_pattern: "警示类广告=日常行为铺垫→超现实后果闪现→人物受击短特写→放弃错误行为"
```
