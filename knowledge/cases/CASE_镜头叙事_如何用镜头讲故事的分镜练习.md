---
rule_id: CASE-镜头叙事_如何用镜头讲故事的分镜练习
title: "视频拆片案例：镜头叙事_如何用镜头讲故事的分镜练习"
doc_type: case_library
rule_type: shot_sequence_case
agent_scope:
  - shot_director
  - shot_director_layout
  - shot_director_blocking
priority: reference
status: active
runtime_retrieval: true
scene_types:
  - 追逐紧张
source_video: "镜头叙事_如何用镜头讲故事的分镜练习.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事的分镜练习

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "地铁通道遇狼追逐"
    scene_type: "追逐紧张"
    emotional_arc: "平静→惊恐→逃亡"
    duration_estimate: "24s"
    shots:
      - index: 1
        duration: "5s"
        scale: "中景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物居中偏左，背景为地铁通道"
        narrative_function: "建立空间关系，交代人物刚下地铁的初始状态"
        cut_reason: "人物进入通道，场景转换"
      - index: 2
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，背景为通道海报"
        narrative_function: "通过人物表情变化，传递听到异响后的警觉和恐惧"
        cut_reason: "需要展示引起恐惧的源头"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "主观POV"
        movement: "跟拍"
        composition: "从拐角处探出，人物在通道远端"
        narrative_function: "建立狼的主观视角，制造悬念和压迫感"
        cut_reason: "切回人物反应，强化紧张感"
      - index: 4
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "缓退"
        composition: "人物居中，背景为通道海报"
        narrative_function: "展示人物惊慌后退的反应，强化恐惧情绪"
        cut_reason: "需要展示狼的逼近"
      - index: 5
        duration: "6s"
        scale: "全景"
        angle: "主观POV"
        movement: "跟拍"
        composition: "通道纵深，人物在远端奔跑"
        narrative_function: "通过狼的视角快速逼近，制造强烈的追逐压迫感"
        cut_reason: "切换视角，展示人物的逃跑状态"
      - index: 6
        duration: "5s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从通道深处向镜头奔跑"
        narrative_function: "正面展示人物的逃亡，强化紧张和绝望感"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "平缓→定格反应→主观逼近→快切逃亡"
      director_intent: "通过主观视角和人物反应的交替，在不出现实体狼的情况下，利用声音和镜头语言制造强烈的追逐压迫感。"
      reusable_pattern: "无实物追逐=人物反应近景→主观POV逼近→人物逃亡全景"
```

## 原始分析

```yaml
cases:
  - case_title: "地铁通道遇狼追逐"
    scene_type: "追逐紧张"
    emotional_arc: "平静→惊恐→逃亡"
    duration_estimate: "24s"
    shots:
      - index: 1
        duration: "5s"
        scale: "中景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物居中偏左，背景为地铁通道"
        narrative_function: "建立空间关系，交代人物刚下地铁的初始状态"
        cut_reason: "人物进入通道，场景转换"
      - index: 2
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，背景为通道海报"
        narrative_function: "通过人物表情变化，传递听到异响后的警觉和恐惧"
        cut_reason: "需要展示引起恐惧的源头"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "主观POV"
        movement: "跟拍"
        composition: "从拐角处探出，人物在通道远端"
        narrative_function: "建立狼的主观视角，制造悬念和压迫感"
        cut_reason: "切回人物反应，强化紧张感"
      - index: 4
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "缓退"
        composition: "人物居中，背景为通道海报"
        narrative_function: "展示人物惊慌后退的反应，强化恐惧情绪"
        cut_reason: "需要展示狼的逼近"
      - index: 5
        duration: "6s"
        scale: "全景"
        angle: "主观POV"
        movement: "跟拍"
        composition: "通道纵深，人物在远端奔跑"
        narrative_function: "通过狼的视角快速逼近，制造强烈的追逐压迫感"
        cut_reason: "切换视角，展示人物的逃跑状态"
      - index: 6
        duration: "5s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从通道深处向镜头奔跑"
        narrative_function: "正面展示人物的逃亡，强化紧张和绝望感"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "平缓→定格反应→主观逼近→快切逃亡"
      director_intent: "通过主观视角和人物反应的交替，在不出现实体狼的情况下，利用声音和镜头语言制造强烈的追逐压迫感。"
      reusable_pattern: "无实物追逐=人物反应近景→主观POV逼近→人物逃亡全景"
```
