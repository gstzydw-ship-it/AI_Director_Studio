---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事4_旅行场景故事感
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 旅行记录/情绪抒发
- action
events:
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事4_旅行场景故事感
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事4_旅行场景故事感
title: 视频拆片案例：镜头叙事_如何用镜头讲故事4_旅行场景故事感
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事4_旅行场景故事感.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事4_旅行场景故事感

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "轮渡看海旅行短片"
    scene_type: "旅行记录/情绪抒发"
    emotional_arc: "期待→平静→开阔"
    duration_estimate: "11"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "仰拍"
        movement: "固定"
        composition: "人物从画面中央走向镜头，随后向右侧走出画框"
        narrative_function: "交代人物出场与轮渡环境，通过人物走动建立旅行的动态感"
        cut_reason: "人物完全走出画框，利用出画动作自然衔接下一个场景"
      - index: 2
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物从左侧入画，走到栏杆边，背影/侧脸占据画面左半部分，视线向右"
        narrative_function: "承接上一个镜头的动作，展现人物看海的状态，通过视线引导观众的好奇心"
        cut_reason: "人物视线固定看向远方，利用视线转场切入主观视角"
      - index: 3
        duration: "2s"
        scale: "远景"
        angle: "平视"
        movement: "固定"
        composition: "远处的雪山、城市和海面，天空占画面上半部分"
        narrative_function: "作为人物的主观POV，展示其看到的壮阔风景，传达开阔的心境"
        cut_reason: "风景信息传递完毕，切换另一个角度丰富视觉"
      - index: 4
        duration: "3s"
        scale: "远景"
        angle: "平视"
        movement: "固定"
        composition: "波光粼粼的海面，太阳位于画面右上角，船只栏杆作为前景"
        narrative_function: "进一步强化阳光明媚的环境氛围，烘托积极向上的情绪，作为视频的结尾留白"
        cut_reason: "情绪抒发完整，视频结束"
    pattern_summary:
      rhythm: "动→静→空"
      director_intent: "通过人物的走动和视线引导，自然地将观众带入旅行场景。利用出画入画和视线转场规避杂乱环境，低成本营造故事感。"
      reusable_pattern: "旅行打卡=人物全景出画→人物近景入画看远方→主观视角空镜头"
```

## 原始分析

```yaml
cases:
  - case_title: "轮渡看海旅行短片"
    scene_type: "旅行记录/情绪抒发"
    emotional_arc: "期待→平静→开阔"
    duration_estimate: "11"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "仰拍"
        movement: "固定"
        composition: "人物从画面中央走向镜头，随后向右侧走出画框"
        narrative_function: "交代人物出场与轮渡环境，通过人物走动建立旅行的动态感"
        cut_reason: "人物完全走出画框，利用出画动作自然衔接下一个场景"
      - index: 2
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物从左侧入画，走到栏杆边，背影/侧脸占据画面左半部分，视线向右"
        narrative_function: "承接上一个镜头的动作，展现人物看海的状态，通过视线引导观众的好奇心"
        cut_reason: "人物视线固定看向远方，利用视线转场切入主观视角"
      - index: 3
        duration: "2s"
        scale: "远景"
        angle: "平视"
        movement: "固定"
        composition: "远处的雪山、城市和海面，天空占画面上半部分"
        narrative_function: "作为人物的主观POV，展示其看到的壮阔风景，传达开阔的心境"
        cut_reason: "风景信息传递完毕，切换另一个角度丰富视觉"
      - index: 4
        duration: "3s"
        scale: "远景"
        angle: "平视"
        movement: "固定"
        composition: "波光粼粼的海面，太阳位于画面右上角，船只栏杆作为前景"
        narrative_function: "进一步强化阳光明媚的环境氛围，烘托积极向上的情绪，作为视频的结尾留白"
        cut_reason: "情绪抒发完整，视频结束"
    pattern_summary:
      rhythm: "动→静→空"
      director_intent: "通过人物的走动和视线引导，自然地将观众带入旅行场景。利用出画入画和视线转场规避杂乱环境，低成本营造故事感。"
      reusable_pattern: "旅行打卡=人物全景出画→人物近景入画看远方→主观视角空镜头"
```
