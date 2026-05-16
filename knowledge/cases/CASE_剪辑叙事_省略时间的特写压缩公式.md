---
case_title: 视频拆片案例：剪辑叙事_省略时间的特写压缩公式
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 日常压缩
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
reusable_pattern: CASE_剪辑叙事_省略时间的特写压缩公式
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-剪辑叙事_省略时间的特写压缩公式
title: 视频拆片案例：剪辑叙事_省略时间的特写压缩公式
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 剪辑叙事_省略时间的特写压缩公式.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：剪辑叙事_省略时间的特写压缩公式

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "早晨起床穿衣过程压缩"
    scene_type: "日常压缩"
    emotional_arc: "平静→忙碌→整洁"
    duration_estimate: "20"
    shots:
      - index: 1
        duration: "8s"
        scale: "近景"
        angle: "俯拍"
        movement: "摇摄"
        composition: "画面从左侧闹钟摇至右侧人物面部，人物居中"
        narrative_function: "交代时间背景，展示人物苏醒并猛然起身的动作，建立初始状态"
        cut_reason: "人物掀开被子起身，动作完成，需要转入下一个环节"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "衣柜居中对称构图，占据整个画面"
        narrative_function: "建立新的空间（衣帽间），灯光亮起暗示动作的开始"
        cut_reason: "灯光亮起，空间交代完毕，切入细节动作"
      - index: 3
        duration: "1s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "手部和开关占据画面中心"
        narrative_function: "展示开灯的细节动作，增加真实感和节奏感"
        cut_reason: "按键动作完成"
      - index: 4
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "一排领带占据画面，色彩丰富"
        narrative_function: "展示挑选衣物的过程，用局部代表整体"
        cut_reason: "展示时间足够，切入下一个挑选动作"
      - index: 5
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "另一排领带特写，手部入画挑选"
        narrative_function: "继续展示挑选过程，强化忙碌感"
        cut_reason: "挑选动作完成，需要展示最终结果"
      - index: 6
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影在前景，镜子中的正面在后景，形成空间纵深"
        narrative_function: "展示穿衣打扮的最终结果，人物整理仪容准备出门，完成叙事闭环"
        cut_reason: "整个起床穿衣事件结束"
    pattern_summary:
      rhythm: "缓摇→定格→快切→稳定"
      director_intent: "通过省略繁琐的中间过程，利用关键特写镜头压缩时间，既交代了完整的行为逻辑，又避免了流水账式的记录，保持了紧凑的叙事节奏。"
      reusable_pattern: "繁琐过程=中景记录事件开始→多个特写镜头呈现过程→中景呈现事件结果"
```

## 原始分析

```yaml
cases:
  - case_title: "早晨起床穿衣过程压缩"
    scene_type: "日常压缩"
    emotional_arc: "平静→忙碌→整洁"
    duration_estimate: "20"
    shots:
      - index: 1
        duration: "8s"
        scale: "近景"
        angle: "俯拍"
        movement: "摇摄"
        composition: "画面从左侧闹钟摇至右侧人物面部，人物居中"
        narrative_function: "交代时间背景，展示人物苏醒并猛然起身的动作，建立初始状态"
        cut_reason: "人物掀开被子起身，动作完成，需要转入下一个环节"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "衣柜居中对称构图，占据整个画面"
        narrative_function: "建立新的空间（衣帽间），灯光亮起暗示动作的开始"
        cut_reason: "灯光亮起，空间交代完毕，切入细节动作"
      - index: 3
        duration: "1s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "手部和开关占据画面中心"
        narrative_function: "展示开灯的细节动作，增加真实感和节奏感"
        cut_reason: "按键动作完成"
      - index: 4
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "一排领带占据画面，色彩丰富"
        narrative_function: "展示挑选衣物的过程，用局部代表整体"
        cut_reason: "展示时间足够，切入下一个挑选动作"
      - index: 5
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "另一排领带特写，手部入画挑选"
        narrative_function: "继续展示挑选过程，强化忙碌感"
        cut_reason: "挑选动作完成，需要展示最终结果"
      - index: 6
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影在前景，镜子中的正面在后景，形成空间纵深"
        narrative_function: "展示穿衣打扮的最终结果，人物整理仪容准备出门，完成叙事闭环"
        cut_reason: "整个起床穿衣事件结束"
    pattern_summary:
      rhythm: "缓摇→定格→快切→稳定"
      director_intent: "通过省略繁琐的中间过程，利用关键特写镜头压缩时间，既交代了完整的行为逻辑，又避免了流水账式的记录，保持了紧凑的叙事节奏。"
      reusable_pattern: "繁琐过程=中景记录事件开始→多个特写镜头呈现过程→中景呈现事件结果"
```
