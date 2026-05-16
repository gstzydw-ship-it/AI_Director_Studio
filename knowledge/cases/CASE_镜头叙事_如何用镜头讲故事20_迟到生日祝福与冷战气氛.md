---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事20_迟到生日祝福与冷战气氛
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 冷战对峙
- dialogue
- action
events:
- collision
- door_state
- reaction
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
- shot_reverse_shot
- offscreen_space
risks:
- blood_avoidance
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事20_迟到生日祝福与冷战气氛
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事20_迟到生日祝福与冷战气氛
title: 视频拆片案例：镜头叙事_如何用镜头讲故事20_迟到生日祝福与冷战气氛
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事20_迟到生日祝福与冷战气氛.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事20_迟到生日祝福与冷战气氛

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "迟到的生日祝福"
    scene_type: "冷战对峙"
    emotional_arc: "愧疚→试探→冷漠"
    duration_estimate: "25"
    shots:
      - index: 1
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面左侧，看向右侧画外"
        narrative_function: "展示女主进门，建立初始情境"
        cut_reason: "女主视线看向客厅，切主观镜头展示她看到的内容"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "主观POV"
        movement: "固定"
        composition: "男友坐在左侧沙发上，环境昏暗"
        narrative_function: "代入女主视角，让观众直接感受到男友的冷漠和压抑氛围"
        cut_reason: "展示完男友状态，切回女主反应"
      - index: 3
        duration: "5s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面中央，关门并整理物品"
        narrative_function: "展示女主的动作和愧疚情绪，为接下来的互动做铺垫"
        cut_reason: "女主开始走向客厅，通过动作衔接切全景"
      - index: 4
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男主在右侧前景（实），女主在左侧后景（虚），男主占据画面2/3"
        narrative_function: "通过构图比例和景深关系，暗示两人心理距离和男主失落的心情"
        cut_reason: "女主走近，需要更近的景别展示两人互动"
      - index: 5
        duration: "3s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "女主过肩，男主在画面右侧"
        narrative_function: "拉近距离，展示男主对女主靠近的冷漠反应"
        cut_reason: "女主准备说话，切正面展示情绪"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主正面居中，手捧蜡烛"
        narrative_function: "传递对白“生日快乐”，清晰展示女主的讨好和歉意"
        cut_reason: "说完台词，需要看男主反应"
      - index: 7
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男主侧面，低头看报纸"
        narrative_function: "展示男主的拒绝和冷战态度的延续，形成情绪受击"
        cut_reason: "场景情绪表达完整，片段结束"
    pattern_summary:
      rhythm: "主观代入→全景关系→过肩拉近→正反打特写"
      director_intent: "通过主观镜头建立代入感，利用全景的景深和构图比例暗示心理距离，最后用内反拍的近景正反打强化冷战的隔阂感。"
      reusable_pattern: "冷战戏=主观视角代入→全景景深构图暗示关系→过肩拉近→近景正反打展现隔阂"
```

## 原始分析

```yaml
cases:
  - case_title: "迟到的生日祝福"
    scene_type: "冷战对峙"
    emotional_arc: "愧疚→试探→冷漠"
    duration_estimate: "25"
    shots:
      - index: 1
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面左侧，看向右侧画外"
        narrative_function: "展示女主进门，建立初始情境"
        cut_reason: "女主视线看向客厅，切主观镜头展示她看到的内容"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "主观POV"
        movement: "固定"
        composition: "男友坐在左侧沙发上，环境昏暗"
        narrative_function: "代入女主视角，让观众直接感受到男友的冷漠和压抑氛围"
        cut_reason: "展示完男友状态，切回女主反应"
      - index: 3
        duration: "5s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面中央，关门并整理物品"
        narrative_function: "展示女主的动作和愧疚情绪，为接下来的互动做铺垫"
        cut_reason: "女主开始走向客厅，通过动作衔接切全景"
      - index: 4
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男主在右侧前景（实），女主在左侧后景（虚），男主占据画面2/3"
        narrative_function: "通过构图比例和景深关系，暗示两人心理距离和男主失落的心情"
        cut_reason: "女主走近，需要更近的景别展示两人互动"
      - index: 5
        duration: "3s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "女主过肩，男主在画面右侧"
        narrative_function: "拉近距离，展示男主对女主靠近的冷漠反应"
        cut_reason: "女主准备说话，切正面展示情绪"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主正面居中，手捧蜡烛"
        narrative_function: "传递对白“生日快乐”，清晰展示女主的讨好和歉意"
        cut_reason: "说完台词，需要看男主反应"
      - index: 7
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男主侧面，低头看报纸"
        narrative_function: "展示男主的拒绝和冷战态度的延续，形成情绪受击"
        cut_reason: "场景情绪表达完整，片段结束"
    pattern_summary:
      rhythm: "主观代入→全景关系→过肩拉近→正反打特写"
      director_intent: "通过主观镜头建立代入感，利用全景的景深和构图比例暗示心理距离，最后用内反拍的近景正反打强化冷战的隔阂感。"
      reusable_pattern: "冷战戏=主观视角代入→全景景深构图暗示关系→过肩拉近→近景正反打展现隔阂"
```
