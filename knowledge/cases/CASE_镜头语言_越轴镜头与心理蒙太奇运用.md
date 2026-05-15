---
case_title: 视频拆片案例：镜头语言_越轴镜头与心理蒙太奇运用
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 幻觉/心理活动展现
- dialogue
- action
- psychology_fantasy
events:
- collision
- reaction
- cut
dialogue_types:
- reaction_beat
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
- reaction_shot
risks:
- axis_confusion
- blood_avoidance
reusable_pattern: CASE_镜头语言_越轴镜头与心理蒙太奇运用
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头语言_越轴镜头与心理蒙太奇运用
title: 视频拆片案例：镜头语言_越轴镜头与心理蒙太奇运用
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头语言_越轴镜头与心理蒙太奇运用.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头语言_越轴镜头与心理蒙太奇运用

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "《玫瑰的故事》画展前等候（心理蒙太奇示范）"
    scene_type: "幻觉/心理活动展现"
    emotional_arc: "平静等待→惊讶恍惚→回到现实"
    duration_estimate: "43s"
    shots:
      - index: 1
        duration: "4s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居左，背景虚化，留出右侧视线空间"
        narrative_function: "建立人物等待的状态和环境空间"
        cut_reason: "人物听到声音转头，视线引导切换"
      - index: 2
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，回头微笑"
        narrative_function: "展示女主视线所及的内容（幻觉中的前男友）"
        cut_reason: "需要展示女主看到此景的反应"
      - index: 3
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物面部特写，占据画面中心"
        narrative_function: "放大人物惊讶和受击的心理状态"
        cut_reason: "前男友做出进一步动作"
      - index: 4
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，挥手"
        narrative_function: "幻觉人物的互动动作"
        cut_reason: "切回女主视角看其走近"
      - index: 5
        duration: "2s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "带前景虚化肩膀，女主居右"
        narrative_function: "建立两人之间的空间关系和视线联系"
        cut_reason: "展示前男友走过来的完整动作"
      - index: 6
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "大景深，人物从背景走向前景"
        narrative_function: "交代空间距离和人物移动过程"
        cut_reason: "切回女主情绪反应"
      - index: 7
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，眼神跟随"
        narrative_function: "持续展现女主沉浸在幻觉中的状态"
        cut_reason: "前男友走到跟前，需要重新建立关系景"
      - index: 8
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "双人全身，环境交代"
        narrative_function: "建立两人汇合后的新空间关系"
        cut_reason: "开始对话，切近景"
      - index: 9
        duration: "3s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "带女主肩膀，男主居左"
        narrative_function: "传递对话信息"
        cut_reason: "切听者反应"
      - index: 10
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主单人，视线未对齐"
        narrative_function: "通过单人构图和越轴暗示这是不真实的幻觉"
        cut_reason: "对话继续"
      - index: 11
        duration: "9s"
        scale: "近景"
        angle: "平视"
        movement: "摇摄"
        composition: "从女主单人摇至男主入画"
        narrative_function: "通过声音变化和镜头摇动，打破幻觉，将人物拉回现实"
        cut_reason: "现实人物走到跟前，建立新的对话场景"
      - index: 12
        duration: "5s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "双人对话构图"
        narrative_function: "现实中的互动，结束心理蒙太奇段落"
        cut_reason: "场景结束，人物离开"
    pattern_summary:
      rhythm: "平稳铺垫→视线快切入幻→越轴跳跃→摇摄回现"
      director_intent: "利用相似元素的视觉误导进入幻觉，通过刻意越轴和孤立构图制造不真实感，最后用声音和运镜无缝切回现实。"
      reusable_pattern: "心理蒙太奇=现实触媒→视线匹配入幻→越轴/单人构图造虚幻感→声音打断+摇摄回现实"
```

## 原始分析

```yaml
cases:
  - case_title: "《玫瑰的故事》画展前等候（心理蒙太奇示范）"
    scene_type: "幻觉/心理活动展现"
    emotional_arc: "平静等待→惊讶恍惚→回到现实"
    duration_estimate: "43s"
    shots:
      - index: 1
        duration: "4s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居左，背景虚化，留出右侧视线空间"
        narrative_function: "建立人物等待的状态和环境空间"
        cut_reason: "人物听到声音转头，视线引导切换"
      - index: 2
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，回头微笑"
        narrative_function: "展示女主视线所及的内容（幻觉中的前男友）"
        cut_reason: "需要展示女主看到此景的反应"
      - index: 3
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物面部特写，占据画面中心"
        narrative_function: "放大人物惊讶和受击的心理状态"
        cut_reason: "前男友做出进一步动作"
      - index: 4
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，挥手"
        narrative_function: "幻觉人物的互动动作"
        cut_reason: "切回女主视角看其走近"
      - index: 5
        duration: "2s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "带前景虚化肩膀，女主居右"
        narrative_function: "建立两人之间的空间关系和视线联系"
        cut_reason: "展示前男友走过来的完整动作"
      - index: 6
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "大景深，人物从背景走向前景"
        narrative_function: "交代空间距离和人物移动过程"
        cut_reason: "切回女主情绪反应"
      - index: 7
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，眼神跟随"
        narrative_function: "持续展现女主沉浸在幻觉中的状态"
        cut_reason: "前男友走到跟前，需要重新建立关系景"
      - index: 8
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "双人全身，环境交代"
        narrative_function: "建立两人汇合后的新空间关系"
        cut_reason: "开始对话，切近景"
      - index: 9
        duration: "3s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "带女主肩膀，男主居左"
        narrative_function: "传递对话信息"
        cut_reason: "切听者反应"
      - index: 10
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主单人，视线未对齐"
        narrative_function: "通过单人构图和越轴暗示这是不真实的幻觉"
        cut_reason: "对话继续"
      - index: 11
        duration: "9s"
        scale: "近景"
        angle: "平视"
        movement: "摇摄"
        composition: "从女主单人摇至男主入画"
        narrative_function: "通过声音变化和镜头摇动，打破幻觉，将人物拉回现实"
        cut_reason: "现实人物走到跟前，建立新的对话场景"
      - index: 12
        duration: "5s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "双人对话构图"
        narrative_function: "现实中的互动，结束心理蒙太奇段落"
        cut_reason: "场景结束，人物离开"
    pattern_summary:
      rhythm: "平稳铺垫→视线快切入幻→越轴跳跃→摇摄回现"
      director_intent: "利用相似元素的视觉误导进入幻觉，通过刻意越轴和孤立构图制造不真实感，最后用声音和运镜无缝切回现实。"
      reusable_pattern: "心理蒙太奇=现实触媒→视线匹配入幻→越轴/单人构图造虚幻感→声音打断+摇摄回现实"
```
