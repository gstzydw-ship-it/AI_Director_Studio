---
case_title: 视频拆片案例：镜头叙事_商场试耳机场景的分镜思路
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 产品体验/日常动作
- action
events:
- reaction
- cut
dialogue_types: []
visual_constraints:
- medium_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_镜头叙事_商场试耳机场景的分镜思路
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头叙事_商场试耳机场景的分镜思路
title: 视频拆片案例：镜头叙事_商场试耳机场景的分镜思路
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_商场试耳机场景的分镜思路.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_商场试耳机场景的分镜思路

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "男生试听耳机（剪辑动机示范）"
    scene_type: "产品体验/日常动作"
    emotional_arc: "平静→好奇→沉浸"
    duration_estimate: "23s"
    shots:
      - index: 1
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，走向柜台，耳机在前景两侧"
        narrative_function: "建立人物与环境的关系，通过人物视线引导观众注意力到耳机上"
        cut_reason: "人物视线看向耳机，产生看清耳机的心理需求"
      - index: 2
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "耳机居中占据画面主体，人物手部从右侧入画"
        narrative_function: "展示产品细节，通过拿起的动作推动叙事"
        cut_reason: "人物拿起耳机的动作完成，需要展示戴耳机的动作"
      - index: 3
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物面部居中，双手在头部两侧"
        narrative_function: "清晰展示戴耳机的动作和人物面部表情"
        cut_reason: "戴耳机的动作完成，双手放下，需要展示下一步操作"
      - index: 4
        duration: "4s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，双手在身前操作台面"
        narrative_function: "交代人物按动开关播放音乐的动作，展示整体状态"
        cut_reason: "音乐响起，人物开始沉浸，需要放大情绪反应"
      - index: 5
        duration: "7s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "人物面部充满画面，闭眼微笑"
        narrative_function: "放大人物沉浸在音乐中的情绪，传达产品带来的美好体验"
        cut_reason: "情绪表达完整，片段结束"
    pattern_summary:
      rhythm: "动作引导→细节展示→动作连贯→情绪放大"
      director_intent: "通过人物的视线和连贯的动作作为剪辑动机，自然流畅地展示产品并传达沉浸感，让观众忘记剪辑的存在。"
      reusable_pattern: "产品体验=中景视线引导→特写动作接触→近景动作完成→特写情绪沉浸"
```

## 原始分析

```yaml
cases:
  - case_title: "男生试听耳机（剪辑动机示范）"
    scene_type: "产品体验/日常动作"
    emotional_arc: "平静→好奇→沉浸"
    duration_estimate: "23s"
    shots:
      - index: 1
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，走向柜台，耳机在前景两侧"
        narrative_function: "建立人物与环境的关系，通过人物视线引导观众注意力到耳机上"
        cut_reason: "人物视线看向耳机，产生看清耳机的心理需求"
      - index: 2
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "耳机居中占据画面主体，人物手部从右侧入画"
        narrative_function: "展示产品细节，通过拿起的动作推动叙事"
        cut_reason: "人物拿起耳机的动作完成，需要展示戴耳机的动作"
      - index: 3
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物面部居中，双手在头部两侧"
        narrative_function: "清晰展示戴耳机的动作和人物面部表情"
        cut_reason: "戴耳机的动作完成，双手放下，需要展示下一步操作"
      - index: 4
        duration: "4s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，双手在身前操作台面"
        narrative_function: "交代人物按动开关播放音乐的动作，展示整体状态"
        cut_reason: "音乐响起，人物开始沉浸，需要放大情绪反应"
      - index: 5
        duration: "7s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "人物面部充满画面，闭眼微笑"
        narrative_function: "放大人物沉浸在音乐中的情绪，传达产品带来的美好体验"
        cut_reason: "情绪表达完整，片段结束"
    pattern_summary:
      rhythm: "动作引导→细节展示→动作连贯→情绪放大"
      director_intent: "通过人物的视线和连贯的动作作为剪辑动机，自然流畅地展示产品并传达沉浸感，让观众忘记剪辑的存在。"
      reusable_pattern: "产品体验=中景视线引导→特写动作接触→近景动作完成→特写情绪沉浸"
```
