---
case_title: 视频拆片案例：拍摄设计_对话场景的景别变化与情绪放大
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 对话递进/情绪升华
- dialogue
events:
- reaction
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- closeup
- over_shoulder
- shot_reverse_shot
risks: []
reusable_pattern: CASE_拍摄设计_对话场景的景别变化与情绪放大
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-拍摄设计_对话场景的景别变化与情绪放大
title: 视频拆片案例：拍摄设计_对话场景的景别变化与情绪放大
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 拍摄设计_对话场景的景别变化与情绪放大.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- continuity_lock
---

# 视频拆片案例：拍摄设计_对话场景的景别变化与情绪放大

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "面试官与女主的对话场景"
    scene_type: "对话递进/情绪升华"
    emotional_arc: "平稳交流→深入探讨→情感放大→升华结束"
    duration_estimate: "55"
    shots:
      - index: 1
        duration: "4s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "面试官居中偏右，女主背影在左侧作为前景"
        narrative_function: "建立对话的初始空间关系，展示面试官的初步态度"
        cut_reason: "女主开始回应"
      - index: 2
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主居中，无明显前景遮挡"
        narrative_function: "展示女主的反应和回答，建立内反拍视角"
        cut_reason: "面试官继续提问"
      - index: 3
        duration: "6s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "面试官居中，距离比镜头1更近"
        narrative_function: "拉近心理距离，暗示聊天内容的深入"
        cut_reason: "女主回答问题"
      - index: 4
        duration: "10s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主居中"
        narrative_function: "展示女主的详细回答和情绪状态"
        cut_reason: "面试官给出重要反馈"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "面试官居中"
        narrative_function: "继续展示面试官的反应，保持对话节奏"
        cut_reason: "女主继续补充"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主居中"
        narrative_function: "展示女主的进一步反应"
        cut_reason: "面试官开始讲述核心内容"
      - index: 7
        duration: "5s"
        scale: "近景"
        angle: "平视"
        movement: "缓推"
        composition: "面试官居中，画面逐渐放大"
        narrative_function: "通过推镜头放大人物情感，强调对话的重点内容"
        cut_reason: "展示女主对重点内容的反应"
      - index: 8
        duration: "6s"
        scale: "近景"
        angle: "平视"
        movement: "缓推"
        composition: "女主居中，画面逐渐放大"
        narrative_function: "刻画女主听到重点内容后的心理活动和情绪变化"
        cut_reason: "面试官给出最终结论"
      - index: 9
        duration: "4s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "面试官面部特写"
        narrative_function: "配合音乐升华情绪，强调最终结论的重量"
        cut_reason: "对话结束，场景转换"
      - index: 10
        duration: "3s"
        scale: "全景"
        angle: "仰拍"
        movement: "固定"
        composition: "建筑外观全景"
        narrative_function: "交代场景转换，为上一段对话的情绪提供缓冲和收尾"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "固定正反打→缓推放大→特写定音→空镜头收尾"
      director_intent: "通过从外反拍到内反拍，再从近景到特写的景别递进，配合推镜头，逐步放大人物情感，使对话更具感染力。"
      reusable_pattern: "深度对话=过肩近景开场→内反拍近景交流→缓推近景强调重点→特写升华情绪→空镜头收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "面试官与女主的对话场景"
    scene_type: "对话递进/情绪升华"
    emotional_arc: "平稳交流→深入探讨→情感放大→升华结束"
    duration_estimate: "55"
    shots:
      - index: 1
        duration: "4s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "面试官居中偏右，女主背影在左侧作为前景"
        narrative_function: "建立对话的初始空间关系，展示面试官的初步态度"
        cut_reason: "女主开始回应"
      - index: 2
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主居中，无明显前景遮挡"
        narrative_function: "展示女主的反应和回答，建立内反拍视角"
        cut_reason: "面试官继续提问"
      - index: 3
        duration: "6s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "面试官居中，距离比镜头1更近"
        narrative_function: "拉近心理距离，暗示聊天内容的深入"
        cut_reason: "女主回答问题"
      - index: 4
        duration: "10s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主居中"
        narrative_function: "展示女主的详细回答和情绪状态"
        cut_reason: "面试官给出重要反馈"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "面试官居中"
        narrative_function: "继续展示面试官的反应，保持对话节奏"
        cut_reason: "女主继续补充"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主居中"
        narrative_function: "展示女主的进一步反应"
        cut_reason: "面试官开始讲述核心内容"
      - index: 7
        duration: "5s"
        scale: "近景"
        angle: "平视"
        movement: "缓推"
        composition: "面试官居中，画面逐渐放大"
        narrative_function: "通过推镜头放大人物情感，强调对话的重点内容"
        cut_reason: "展示女主对重点内容的反应"
      - index: 8
        duration: "6s"
        scale: "近景"
        angle: "平视"
        movement: "缓推"
        composition: "女主居中，画面逐渐放大"
        narrative_function: "刻画女主听到重点内容后的心理活动和情绪变化"
        cut_reason: "面试官给出最终结论"
      - index: 9
        duration: "4s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "面试官面部特写"
        narrative_function: "配合音乐升华情绪，强调最终结论的重量"
        cut_reason: "对话结束，场景转换"
      - index: 10
        duration: "3s"
        scale: "全景"
        angle: "仰拍"
        movement: "固定"
        composition: "建筑外观全景"
        narrative_function: "交代场景转换，为上一段对话的情绪提供缓冲和收尾"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "固定正反打→缓推放大→特写定音→空镜头收尾"
      director_intent: "通过从外反拍到内反拍，再从近景到特写的景别递进，配合推镜头，逐步放大人物情感，使对话更具感染力。"
      reusable_pattern: "深度对话=过肩近景开场→内反拍近景交流→缓推近景强调重点→特写升华情绪→空镜头收尾"
```
