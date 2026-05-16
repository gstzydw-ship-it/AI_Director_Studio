---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事14_学校门口送学场景
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 告别离场
- dialogue
- action
events:
- reaction
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事14_学校门口送学场景
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事14_学校门口送学场景
title: 视频拆片案例：镜头叙事_如何用镜头讲故事14_学校门口送学场景
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事14_学校门口送学场景.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事14_学校门口送学场景

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "爸爸送女儿上学目送场景"
    scene_type: "告别离场"
    emotional_arc: "日常平静→关切不舍→欣慰释然"
    duration_estimate: "22"
    shots:
      - index: 1
        duration: "10s"
        scale: "全景"
        angle: "平视"
        movement: "摇摄"
        composition: "车辆从画面左侧驶入并停在右侧，背景有校车作为环境提示"
        narrative_function: "建立环境空间，交代人物到达学校的客观事实"
        cut_reason: "女儿推开车门，以动作为衔接点切入下一个镜头"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "侧面全景，车在画面右侧，女儿向左侧跑去"
        narrative_function: "完整展示女儿下车跑向学校的动作过程"
        cut_reason: "女儿跑向远方，需要转换视角来表现父亲的关注"
      - index: 3
        duration: "1s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "从车内向外拍，爸爸在左侧前景，透过车窗看向右侧窗外"
        narrative_function: "建立人物与环境的空间关系，半主观视角让观众代入父亲的视线"
        cut_reason: "交代完视线方向后，需要看父亲的具体表情反应"
      - index: 4
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "爸爸侧面近景，面部处于画面中心偏右"
        narrative_function: "表现父亲目送女儿时的关切情绪"
        cut_reason: "父亲视线注视前方，需要切到主观镜头展示他看到了什么"
      - index: 5
        duration: "3s"
        scale: "全景"
        angle: "主观POV"
        movement: "固定"
        composition: "操场全景，众多孩子在画面中玩耍，景深较深"
        narrative_function: "展示女儿融入人群的画面，完成父亲视线的闭环"
        cut_reason: "主观画面展示完毕，需要切回人物最终的情感落脚点"
      - index: 6
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "爸爸面部特写，占据画面主体"
        narrative_function: "放大面部细节，强化父亲看到女儿融入集体后欣慰的笑容，完成情绪升华"
        cut_reason: "情绪表达完整，场景结束"
    pattern_summary:
      rhythm: "客观交代→动作衔接→视线交叉→特写定格"
      director_intent: "通过从客观全景到半主观、再到完全主观视角的递进，逐步将观众代入父亲的情感世界，最后用特写放大情绪感染力。"
      reusable_pattern: "目送戏=客观全景交代动作→半主观过肩建立视线→主观POV展示对象→特写反应收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "爸爸送女儿上学目送场景"
    scene_type: "告别离场"
    emotional_arc: "日常平静→关切不舍→欣慰释然"
    duration_estimate: "22"
    shots:
      - index: 1
        duration: "10s"
        scale: "全景"
        angle: "平视"
        movement: "摇摄"
        composition: "车辆从画面左侧驶入并停在右侧，背景有校车作为环境提示"
        narrative_function: "建立环境空间，交代人物到达学校的客观事实"
        cut_reason: "女儿推开车门，以动作为衔接点切入下一个镜头"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "侧面全景，车在画面右侧，女儿向左侧跑去"
        narrative_function: "完整展示女儿下车跑向学校的动作过程"
        cut_reason: "女儿跑向远方，需要转换视角来表现父亲的关注"
      - index: 3
        duration: "1s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "从车内向外拍，爸爸在左侧前景，透过车窗看向右侧窗外"
        narrative_function: "建立人物与环境的空间关系，半主观视角让观众代入父亲的视线"
        cut_reason: "交代完视线方向后，需要看父亲的具体表情反应"
      - index: 4
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "爸爸侧面近景，面部处于画面中心偏右"
        narrative_function: "表现父亲目送女儿时的关切情绪"
        cut_reason: "父亲视线注视前方，需要切到主观镜头展示他看到了什么"
      - index: 5
        duration: "3s"
        scale: "全景"
        angle: "主观POV"
        movement: "固定"
        composition: "操场全景，众多孩子在画面中玩耍，景深较深"
        narrative_function: "展示女儿融入人群的画面，完成父亲视线的闭环"
        cut_reason: "主观画面展示完毕，需要切回人物最终的情感落脚点"
      - index: 6
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "爸爸面部特写，占据画面主体"
        narrative_function: "放大面部细节，强化父亲看到女儿融入集体后欣慰的笑容，完成情绪升华"
        cut_reason: "情绪表达完整，场景结束"
    pattern_summary:
      rhythm: "客观交代→动作衔接→视线交叉→特写定格"
      director_intent: "通过从客观全景到半主观、再到完全主观视角的递进，逐步将观众代入父亲的情感世界，最后用特写放大情绪感染力。"
      reusable_pattern: "目送戏=客观全景交代动作→半主观过肩建立视线→主观POV展示对象→特写反应收尾"
```
