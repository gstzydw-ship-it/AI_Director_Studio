---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事23_女孩推门下车离开
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 日常动作
- 紧张动作
- action
events:
- door_state
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事23_女孩推门下车离开
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事23_女孩推门下车离开
title: 视频拆片案例：镜头叙事_如何用镜头讲故事23_女孩推门下车离开
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事23_女孩推门下车离开.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事23_女孩推门下车离开

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "女生推开车门，下车离开（平静版）"
    scene_type: "日常动作"
    emotional_arc: "平静→平静"
    duration_estimate: "10s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "车身占据大部分画面，人物在车内"
        narrative_function: "建立场景，展示人物准备下车的动作"
        cut_reason: "人物推开车门，动作发生变化"
      - index: 2
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "脚部占据画面中心"
        narrative_function: "强调下车动作的细节，增加真实感"
        cut_reason: "脚部落地，动作完成"
      - index: 3
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "上摇"
        composition: "人物上半身占据画面中心"
        narrative_function: "展示人物下车后的状态和关门动作"
        cut_reason: "关门动作完成，人物准备离开"
      - index: 4
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物和车辆都在画面中，人物向左走"
        narrative_function: "展示人物离开的完整过程，交代空间关系"
        cut_reason: "人物走出画面或动作结束"
    pattern_summary:
      rhythm: "平稳→平稳→平稳→平稳"
      director_intent: "通过常规的景别切换和稳定的镜头语言，展现一个普通的日常下车动作，情绪平静。"
      reusable_pattern: "日常动作=中景交代环境→特写强调细节→中近景展示动作→全景交代结果"

  - case_title: "女生着急地推开车门，下车离开（着急版）"
    scene_type: "紧张动作"
    emotional_arc: "紧张→急促"
    duration_estimate: "10s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物面部和上半身占据画面中心，透过车窗拍摄"
        narrative_function: "突出人物焦急的面部表情，建立紧张情绪"
        cut_reason: "人物推开车门，动作发生变化"
      - index: 2
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "腿部和脚部占据画面中心"
        narrative_function: "展示匆忙的步伐，强化着急的情绪"
        cut_reason: "脚部落地，动作完成"
      - index: 3
        duration: "0.5s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物上半身占据画面中心，头发凌乱"
        narrative_function: "快速展示关门动作，体现急促感"
        cut_reason: "关门动作瞬间完成"
      - index: 4
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "手部和车门把手占据画面中心"
        narrative_function: "增加锁车细节，镜头短促增加紧张感"
        cut_reason: "锁车动作完成"
      - index: 5
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物和车辆都在画面中，人物向左跑"
        narrative_function: "展示人物跑着离开，最终确认着急的情绪"
        cut_reason: "人物跑出画面或动作结束"
    pattern_summary:
      rhythm: "紧凑→快切→快切→快切→跑离"
      director_intent: "通过更近的景别、更短的镜头时长和增加的细节特写，营造出人物焦急、匆忙的情绪状态。"
      reusable_pattern: "紧张动作=近景情绪开场→特写动作细节（快切）→增加动作特写（快切）→全景跑离收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "女生推开车门，下车离开（平静版）"
    scene_type: "日常动作"
    emotional_arc: "平静→平静"
    duration_estimate: "10s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "车身占据大部分画面，人物在车内"
        narrative_function: "建立场景，展示人物准备下车的动作"
        cut_reason: "人物推开车门，动作发生变化"
      - index: 2
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "脚部占据画面中心"
        narrative_function: "强调下车动作的细节，增加真实感"
        cut_reason: "脚部落地，动作完成"
      - index: 3
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "上摇"
        composition: "人物上半身占据画面中心"
        narrative_function: "展示人物下车后的状态和关门动作"
        cut_reason: "关门动作完成，人物准备离开"
      - index: 4
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物和车辆都在画面中，人物向左走"
        narrative_function: "展示人物离开的完整过程，交代空间关系"
        cut_reason: "人物走出画面或动作结束"
    pattern_summary:
      rhythm: "平稳→平稳→平稳→平稳"
      director_intent: "通过常规的景别切换和稳定的镜头语言，展现一个普通的日常下车动作，情绪平静。"
      reusable_pattern: "日常动作=中景交代环境→特写强调细节→中近景展示动作→全景交代结果"

  - case_title: "女生着急地推开车门，下车离开（着急版）"
    scene_type: "紧张动作"
    emotional_arc: "紧张→急促"
    duration_estimate: "10s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物面部和上半身占据画面中心，透过车窗拍摄"
        narrative_function: "突出人物焦急的面部表情，建立紧张情绪"
        cut_reason: "人物推开车门，动作发生变化"
      - index: 2
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "腿部和脚部占据画面中心"
        narrative_function: "展示匆忙的步伐，强化着急的情绪"
        cut_reason: "脚部落地，动作完成"
      - index: 3
        duration: "0.5s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物上半身占据画面中心，头发凌乱"
        narrative_function: "快速展示关门动作，体现急促感"
        cut_reason: "关门动作瞬间完成"
      - index: 4
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "手部和车门把手占据画面中心"
        narrative_function: "增加锁车细节，镜头短促增加紧张感"
        cut_reason: "锁车动作完成"
      - index: 5
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物和车辆都在画面中，人物向左跑"
        narrative_function: "展示人物跑着离开，最终确认着急的情绪"
        cut_reason: "人物跑出画面或动作结束"
    pattern_summary:
      rhythm: "紧凑→快切→快切→快切→跑离"
      director_intent: "通过更近的景别、更短的镜头时长和增加的细节特写，营造出人物焦急、匆忙的情绪状态。"
      reusable_pattern: "紧张动作=近景情绪开场→特写动作细节（快切）→增加动作特写（快切）→全景跑离收尾"
```
