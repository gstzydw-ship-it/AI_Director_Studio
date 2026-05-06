---
case_title: 视频拆片案例：镜头叙事_进门场景的空间调度与故事感
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 悬念建立/探索未知
- action
- suspense
events:
- door_state
- reaction
- cut
- enter_unknown_space
dialogue_types: []
visual_constraints:
- wide_shot
- closeup
- over_shoulder
risks: []
reusable_pattern: CASE_镜头叙事_进门场景的空间调度与故事感
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头叙事_进门场景的空间调度与故事感
title: 视频拆片案例：镜头叙事_进门场景的空间调度与故事感
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_进门场景的空间调度与故事感.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_进门场景的空间调度与故事感

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "美女开车来到郊外别墅推门而入"
    scene_type: "悬念建立/探索未知"
    emotional_arc: "平静→好奇/紧张"
    duration_estimate: "55s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "车内向外拍，人物背影在左侧，车窗外是别墅环境"
        narrative_function: "建立人物与目的地的空间关系，通过主观视点代入观众"
        cut_reason: "车辆驶近目的地，需要客观视角展示外部环境"
      - index: 2
        duration: "4s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "红车在画面中央，向右下行驶，周围是草地"
        narrative_function: "客观展示车辆驶向别墅的动态，交代周边荒僻环境"
        cut_reason: "车辆即将到达，需要展示目的地全貌"
      - index: 3
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "别墅占据画面主体，红车在左下角停下"
        narrative_function: "交代目的地别墅的全貌，确认车辆停稳"
        cut_reason: "车辆停稳，人物准备下车"
      - index: 4
        duration: "3s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "同镜头2的俯视角度，人物推开车门"
        narrative_function: "动作衔接，展示人物下车的初始动作"
        cut_reason: "需要看清人物下车后的面部表情和状态"
      - index: 5
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "摇摄"
        composition: "人物面部特写，镜头随人物起身向上摇"
        narrative_function: "展示人物对别墅的观察和略带紧张的情绪反应"
        cut_reason: "人物视线看向前方，需要展示她看到了什么"
      - index: 6
        duration: "6s"
        scale: "全景"
        angle: "仰拍"
        movement: "固定"
        composition: "别墅二楼阳台及建筑细节"
        narrative_function: "主观POV，展示人物视线所及，建立建筑物的压迫感和悬念"
        cut_reason: "视线观察结束，回到客观动作"
      - index: 7
        duration: "2s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "同镜头4的俯视角度，人物关上车门"
        narrative_function: "动作连贯性展示，交代人物彻底离开车辆"
        cut_reason: "动作完成，需要更细节的视角来衔接走向别墅的动作"
      - index: 8
        duration: "4s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "通过汽车后视镜看到人物背影向别墅走去"
        narrative_function: "通过后视镜的框架构图增加窥视感，强化悬念氛围"
        cut_reason: "人物走出后视镜范围，需要展示她接近别墅的全过程"
      - index: 9
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "缓推"
        composition: "别墅全貌为背景，人物在画面中央走向大门"
        narrative_function: "展示人物接近目标，缓推镜头增加心理压迫感"
        cut_reason: "人物到达门口，需要展示具体的试探动作"
      - index: 10
        duration: "7s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物在门外，手扶门框向内张望"
        narrative_function: "展示人物在门口的试探、呼喊及犹豫的心理状态"
        cut_reason: "需要从另一个角度展示开门动作的完整性"
      - index: 11
        duration: "11s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "侧面拍摄，人物拉开纱门走入"
        narrative_function: "完整展示开门进入的动作，保持动作的流畅性"
        cut_reason: "人物进入室内，需要切换到室内视角迎接人物"
      - index: 12
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "室内向外拍，人物在门口形成逆光剪影"
        narrative_function: "人物正式进入未知空间，完成室外到室内的场景转换"
        cut_reason: "场景动作结束"
    pattern_summary:
      rhythm: "客观全景交代→主观视点代入→动作细节切分→缓推压迫"
      director_intent: "通过多视点切换和动作连贯性，将简单的'下车进门'动作拆解，利用主观POV和后视镜等特殊视角增加悬念感和故事感。"
      reusable_pattern: "探索未知=客观全景交代环境→主观POV+面部特写建立情绪→动作细节切分保持流畅→室内逆光全景收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "美女开车来到郊外别墅推门而入"
    scene_type: "悬念建立/探索未知"
    emotional_arc: "平静→好奇/紧张"
    duration_estimate: "55s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "车内向外拍，人物背影在左侧，车窗外是别墅环境"
        narrative_function: "建立人物与目的地的空间关系，通过主观视点代入观众"
        cut_reason: "车辆驶近目的地，需要客观视角展示外部环境"
      - index: 2
        duration: "4s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "红车在画面中央，向右下行驶，周围是草地"
        narrative_function: "客观展示车辆驶向别墅的动态，交代周边荒僻环境"
        cut_reason: "车辆即将到达，需要展示目的地全貌"
      - index: 3
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "别墅占据画面主体，红车在左下角停下"
        narrative_function: "交代目的地别墅的全貌，确认车辆停稳"
        cut_reason: "车辆停稳，人物准备下车"
      - index: 4
        duration: "3s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "同镜头2的俯视角度，人物推开车门"
        narrative_function: "动作衔接，展示人物下车的初始动作"
        cut_reason: "需要看清人物下车后的面部表情和状态"
      - index: 5
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "摇摄"
        composition: "人物面部特写，镜头随人物起身向上摇"
        narrative_function: "展示人物对别墅的观察和略带紧张的情绪反应"
        cut_reason: "人物视线看向前方，需要展示她看到了什么"
      - index: 6
        duration: "6s"
        scale: "全景"
        angle: "仰拍"
        movement: "固定"
        composition: "别墅二楼阳台及建筑细节"
        narrative_function: "主观POV，展示人物视线所及，建立建筑物的压迫感和悬念"
        cut_reason: "视线观察结束，回到客观动作"
      - index: 7
        duration: "2s"
        scale: "全景"
        angle: "俯拍"
        movement: "固定"
        composition: "同镜头4的俯视角度，人物关上车门"
        narrative_function: "动作连贯性展示，交代人物彻底离开车辆"
        cut_reason: "动作完成，需要更细节的视角来衔接走向别墅的动作"
      - index: 8
        duration: "4s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "通过汽车后视镜看到人物背影向别墅走去"
        narrative_function: "通过后视镜的框架构图增加窥视感，强化悬念氛围"
        cut_reason: "人物走出后视镜范围，需要展示她接近别墅的全过程"
      - index: 9
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "缓推"
        composition: "别墅全貌为背景，人物在画面中央走向大门"
        narrative_function: "展示人物接近目标，缓推镜头增加心理压迫感"
        cut_reason: "人物到达门口，需要展示具体的试探动作"
      - index: 10
        duration: "7s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "人物在门外，手扶门框向内张望"
        narrative_function: "展示人物在门口的试探、呼喊及犹豫的心理状态"
        cut_reason: "需要从另一个角度展示开门动作的完整性"
      - index: 11
        duration: "11s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "侧面拍摄，人物拉开纱门走入"
        narrative_function: "完整展示开门进入的动作，保持动作的流畅性"
        cut_reason: "人物进入室内，需要切换到室内视角迎接人物"
      - index: 12
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "室内向外拍，人物在门口形成逆光剪影"
        narrative_function: "人物正式进入未知空间，完成室外到室内的场景转换"
        cut_reason: "场景动作结束"
    pattern_summary:
      rhythm: "客观全景交代→主观视点代入→动作细节切分→缓推压迫"
      director_intent: "通过多视点切换和动作连贯性，将简单的'下车进门'动作拆解，利用主观POV和后视镜等特殊视角增加悬念感和故事感。"
      reusable_pattern: "探索未知=客观全景交代环境→主观POV+面部特写建立情绪→动作细节切分保持流畅→室内逆光全景收尾"
```
