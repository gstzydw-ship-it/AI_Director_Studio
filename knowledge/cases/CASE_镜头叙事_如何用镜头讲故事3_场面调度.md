---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事3_场面调度
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 冲突爆发
- dialogue
- action
events:
- reaction
- cut
dialogue_types:
- argument_escalation
- reaction_beat
visual_constraints:
- medium_shot
- closeup
- over_shoulder
- shot_reverse_shot
- focus_pull
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事3_场面调度
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事3_场面调度
title: 视频拆片案例：镜头叙事_如何用镜头讲故事3_场面调度
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事3_场面调度.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事3_场面调度

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "情侣吵架场面调度（3.0版本）"
    scene_type: "冲突爆发"
    emotional_arc: "激动指责→情绪爆发→背离逃避→反向压迫→冷酷回击"
    duration_estimate: "21s"
    shots:
      - index: 1
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "缓拉"
        composition: "女生居中，随着镜头后移，画面右下角露出男生肩膀作为前景"
        narrative_function: "建立两人面对面争吵的空间关系，女生主动逼近施加压力"
        cut_reason: "女生动作停顿，需要展示男生的视角和女生的进一步动作"
      - index: 2
        duration: "3s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "男生过肩，女生在画面左侧，朝男生走去"
        narrative_function: "反打镜头，强化女生的步步紧逼和男生的被动防守"
        cut_reason: "女生情绪升级，需要更具冲击力的视角"
      - index: 3
        duration: "2s"
        scale: "近景"
        angle: "主观POV"
        movement: "固定"
        composition: "女生居中，手指镜头"
        narrative_function: "代入男生主观视角，直观传递女生极具攻击性的情绪爆发点"
        cut_reason: "女生情绪宣泄完毕，动作发生转变"
      - index: 4
        duration: "8s"
        scale: "中景转近景"
        angle: "平视"
        movement: "跟拍"
        composition: "女生转身背对镜头，镜头后退保持距离；随后男生入画逼近，占据画面主体"
        narrative_function: "女生转身暗示心理防线的退缩与疏远；焦点转移至男生，男生反向逼近打破空间，实现权力反转和情绪压迫"
        cut_reason: "男生台词结束，需要展示女生对这番压迫的最终反应"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "男生过肩，女生面部特写在画面左侧"
        narrative_function: "承接男生的压迫，展现女生冷酷、决绝的情绪反击，作为场景的情绪落点"
        cut_reason: "场景情绪达到顶点，片段结束"
    pattern_summary:
      rhythm: "逼近施压→主观爆发→拉开距离→反向压迫→定格反击"
      director_intent: "通过演员的走位调度和镜头的跟随，将心理博弈外化为空间距离的拉扯，利用焦点的转换实现攻守势态的无缝切换。"
      reusable_pattern: "激烈争吵戏=单人逼近施压→主观视角爆发→转身拉开距离→对方反向逼近压迫→过肩近景情绪落点"
```

## 原始分析

```yaml
cases:
  - case_title: "情侣吵架场面调度（3.0版本）"
    scene_type: "冲突爆发"
    emotional_arc: "激动指责→情绪爆发→背离逃避→反向压迫→冷酷回击"
    duration_estimate: "21s"
    shots:
      - index: 1
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "缓拉"
        composition: "女生居中，随着镜头后移，画面右下角露出男生肩膀作为前景"
        narrative_function: "建立两人面对面争吵的空间关系，女生主动逼近施加压力"
        cut_reason: "女生动作停顿，需要展示男生的视角和女生的进一步动作"
      - index: 2
        duration: "3s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "男生过肩，女生在画面左侧，朝男生走去"
        narrative_function: "反打镜头，强化女生的步步紧逼和男生的被动防守"
        cut_reason: "女生情绪升级，需要更具冲击力的视角"
      - index: 3
        duration: "2s"
        scale: "近景"
        angle: "主观POV"
        movement: "固定"
        composition: "女生居中，手指镜头"
        narrative_function: "代入男生主观视角，直观传递女生极具攻击性的情绪爆发点"
        cut_reason: "女生情绪宣泄完毕，动作发生转变"
      - index: 4
        duration: "8s"
        scale: "中景转近景"
        angle: "平视"
        movement: "跟拍"
        composition: "女生转身背对镜头，镜头后退保持距离；随后男生入画逼近，占据画面主体"
        narrative_function: "女生转身暗示心理防线的退缩与疏远；焦点转移至男生，男生反向逼近打破空间，实现权力反转和情绪压迫"
        cut_reason: "男生台词结束，需要展示女生对这番压迫的最终反应"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "男生过肩，女生面部特写在画面左侧"
        narrative_function: "承接男生的压迫，展现女生冷酷、决绝的情绪反击，作为场景的情绪落点"
        cut_reason: "场景情绪达到顶点，片段结束"
    pattern_summary:
      rhythm: "逼近施压→主观爆发→拉开距离→反向压迫→定格反击"
      director_intent: "通过演员的走位调度和镜头的跟随，将心理博弈外化为空间距离的拉扯，利用焦点的转换实现攻守势态的无缝切换。"
      reusable_pattern: "激烈争吵戏=单人逼近施压→主观视角爆发→转身拉开距离→对方反向逼近压迫→过肩近景情绪落点"
```
