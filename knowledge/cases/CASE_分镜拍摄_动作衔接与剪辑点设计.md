---
case_title: 视频拆片案例：分镜拍摄_动作衔接与剪辑点设计
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 日常动作衔接
- action
events:
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_分镜拍摄_动作衔接与剪辑点设计
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-分镜拍摄_动作衔接与剪辑点设计
title: 视频拆片案例：分镜拍摄_动作衔接与剪辑点设计
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 分镜拍摄_动作衔接与剪辑点设计.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
---

# 视频拆片案例：分镜拍摄_动作衔接与剪辑点设计

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "男子拿篮子戴帽子离场（动作衔接示范）"
    scene_type: "日常动作衔接"
    emotional_arc: "平静→平静→平静"
    duration_estimate: "6"
    shots:
      - index: 1
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "长椅在画面左下方，人物从右侧入画走向长椅"
        narrative_function: "建立院子空间关系，交代人物动作的起点和意图"
        cut_reason: "人物手刚接触到篮子，利用动作接触点切入细节"
      - index: 2
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "篮子和帽子占据画面左侧前景，人物躯干在右侧"
        narrative_function: "清晰展示拿取物品的具体动作细节，强调动作本身"
        cut_reason: "帽子被拿起并向上移动出画，利用出画动作作为剪辑点"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中背影，走向画面深处，两侧有植物框架"
        narrative_function: "交代动作的完成和人物的去向，形成视觉纵深并结束场景"
        cut_reason: "人物走远，场景动作序列完成"
    pattern_summary:
      rhythm: "全景起→近景细→全景收"
      director_intent: "通过景别变化打破单调，利用动作的接触点和出画点进行无缝剪辑，使多角度拍摄的画面在视觉上保持流畅连贯。"
      reusable_pattern: "连贯动作=全景交代起势→近景展示动作细节（接触点切入）→全景展示动作结果及离场（出画点切出）"
```

## 原始分析

```yaml
cases:
  - case_title: "男子拿篮子戴帽子离场（动作衔接示范）"
    scene_type: "日常动作衔接"
    emotional_arc: "平静→平静→平静"
    duration_estimate: "6"
    shots:
      - index: 1
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "长椅在画面左下方，人物从右侧入画走向长椅"
        narrative_function: "建立院子空间关系，交代人物动作的起点和意图"
        cut_reason: "人物手刚接触到篮子，利用动作接触点切入细节"
      - index: 2
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "篮子和帽子占据画面左侧前景，人物躯干在右侧"
        narrative_function: "清晰展示拿取物品的具体动作细节，强调动作本身"
        cut_reason: "帽子被拿起并向上移动出画，利用出画动作作为剪辑点"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中背影，走向画面深处，两侧有植物框架"
        narrative_function: "交代动作的完成和人物的去向，形成视觉纵深并结束场景"
        cut_reason: "人物走远，场景动作序列完成"
    pattern_summary:
      rhythm: "全景起→近景细→全景收"
      director_intent: "通过景别变化打破单调，利用动作的接触点和出画点进行无缝剪辑，使多角度拍摄的画面在视觉上保持流畅连贯。"
      reusable_pattern: "连贯动作=全景交代起势→近景展示动作细节（接触点切入）→全景展示动作结果及离场（出画点切出）"
```
