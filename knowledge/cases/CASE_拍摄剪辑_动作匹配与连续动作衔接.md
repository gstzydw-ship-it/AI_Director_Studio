---
case_title: 视频拆片案例：拍摄剪辑_动作匹配与连续动作衔接
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 动作连贯展示
- 日常动作连贯
- 运动位置连贯
- action
events:
- cut
dialogue_types:
- argument_escalation
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_拍摄剪辑_动作匹配与连续动作衔接
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-拍摄剪辑_动作匹配与连续动作衔接
title: 视频拆片案例：拍摄剪辑_动作匹配与连续动作衔接
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 拍摄剪辑_动作匹配与连续动作衔接.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：拍摄剪辑_动作匹配与连续动作衔接

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "汽车行驶（方向匹配）"
    scene_type: "动作连贯展示"
    emotional_arc: "平稳"
    duration_estimate: "12"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车在画面中央，向右行驶"
        narrative_function: "建立汽车运动方向，为下一镜做铺垫"
        cut_reason: "展示同一运动过程的延续"
      - index: 2
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车在画面中央，继续向右行驶"
        narrative_function: "保持运动方向一致，确保视觉流畅"
        cut_reason: "展示错误示范的对比"
      - index: 3
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车向左行驶（错误示范）"
        narrative_function: "通过反差说明方向不匹配导致的视觉冲突"
        cut_reason: "回到正确示范"
      - index: 4
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车向右行驶，扬起沙尘"
        narrative_function: "强化正确匹配带来的流畅感"
        cut_reason: "案例结束"
    pattern_summary:
      rhythm: "匀速切换"
      director_intent: "通过正反例对比，直观展示运动方向一致性对画面流畅度的影响"
      reusable_pattern: "运动主体转场=上一镜运动方向→下一镜保持同向"

  - case_title: "喝水（动作匹配）"
    scene_type: "日常动作连贯"
    emotional_arc: "平稳"
    duration_estimate: "3"
    shots:
      - index: 1
        duration: "1.5s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物坐在沙发上，拿起水杯准备喝水"
        narrative_function: "交代人物所处环境及动作起始"
        cut_reason: "动作进行到关键节点（水杯靠近嘴边），切近景强化细节"
      - index: 2
        duration: "1.5s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物喝水动作继续"
        narrative_function: "承接上一镜动作，保持动作连续性，拉近观众距离"
        cut_reason: "动作完成，案例结束"
    pattern_summary:
      rhythm: "动作中切"
      director_intent: "利用动作的连贯性掩盖镜头的切换，使剪辑不留痕迹"
      reusable_pattern: "连贯动作=起势全景→动作进行中切中近景完成动作"

  - case_title: "跑步（位置匹配）"
    scene_type: "运动位置连贯"
    emotional_arc: "平稳"
    duration_estimate: "8"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从画面中央跑向右侧出画"
        narrative_function: "建立人物运动轨迹和最终屏幕位置"
        cut_reason: "人物即将出画，需要切换场景"
      - index: 2
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从画面右侧入画继续跑"
        narrative_function: "保持人物在屏幕上的位置一致，避免视觉跳跃"
        cut_reason: "展示错误示范"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从画面左侧入画（错误示范）"
        narrative_function: "说明位置不匹配会造成人物退回的错觉"
        cut_reason: "案例结束"
    pattern_summary:
      rhythm: "出画入画切换"
      director_intent: "通过保持人物在屏幕上的相对位置，维持观众的视觉惯性"
      reusable_pattern: "同场景运动=上一镜右侧出/偏右→下一镜右侧入/偏右"
```

## 原始分析

```yaml
cases:
  - case_title: "汽车行驶（方向匹配）"
    scene_type: "动作连贯展示"
    emotional_arc: "平稳"
    duration_estimate: "12"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车在画面中央，向右行驶"
        narrative_function: "建立汽车运动方向，为下一镜做铺垫"
        cut_reason: "展示同一运动过程的延续"
      - index: 2
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车在画面中央，继续向右行驶"
        narrative_function: "保持运动方向一致，确保视觉流畅"
        cut_reason: "展示错误示范的对比"
      - index: 3
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车向左行驶（错误示范）"
        narrative_function: "通过反差说明方向不匹配导致的视觉冲突"
        cut_reason: "回到正确示范"
      - index: 4
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "汽车向右行驶，扬起沙尘"
        narrative_function: "强化正确匹配带来的流畅感"
        cut_reason: "案例结束"
    pattern_summary:
      rhythm: "匀速切换"
      director_intent: "通过正反例对比，直观展示运动方向一致性对画面流畅度的影响"
      reusable_pattern: "运动主体转场=上一镜运动方向→下一镜保持同向"

  - case_title: "喝水（动作匹配）"
    scene_type: "日常动作连贯"
    emotional_arc: "平稳"
    duration_estimate: "3"
    shots:
      - index: 1
        duration: "1.5s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物坐在沙发上，拿起水杯准备喝水"
        narrative_function: "交代人物所处环境及动作起始"
        cut_reason: "动作进行到关键节点（水杯靠近嘴边），切近景强化细节"
      - index: 2
        duration: "1.5s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物喝水动作继续"
        narrative_function: "承接上一镜动作，保持动作连续性，拉近观众距离"
        cut_reason: "动作完成，案例结束"
    pattern_summary:
      rhythm: "动作中切"
      director_intent: "利用动作的连贯性掩盖镜头的切换，使剪辑不留痕迹"
      reusable_pattern: "连贯动作=起势全景→动作进行中切中近景完成动作"

  - case_title: "跑步（位置匹配）"
    scene_type: "运动位置连贯"
    emotional_arc: "平稳"
    duration_estimate: "8"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从画面中央跑向右侧出画"
        narrative_function: "建立人物运动轨迹和最终屏幕位置"
        cut_reason: "人物即将出画，需要切换场景"
      - index: 2
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从画面右侧入画继续跑"
        narrative_function: "保持人物在屏幕上的位置一致，避免视觉跳跃"
        cut_reason: "展示错误示范"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物从画面左侧入画（错误示范）"
        narrative_function: "说明位置不匹配会造成人物退回的错觉"
        cut_reason: "案例结束"
    pattern_summary:
      rhythm: "出画入画切换"
      director_intent: "通过保持人物在屏幕上的相对位置，维持观众的视觉惯性"
      reusable_pattern: "同场景运动=上一镜右侧出/偏右→下一镜右侧入/偏右"
```
