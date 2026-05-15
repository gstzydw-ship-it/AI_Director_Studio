---
case_title: 视频拆片案例：拍摄设计_动作片段的景别角度与拍法拆解
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 悬念建立
- elevator
- action
- suspense
events:
- door_state
- cut
dialogue_types:
- argument_escalation
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
- handheld
- high_angle
- low_angle
risks:
- door_state_jump
- power_angle_mismatch
reusable_pattern: CASE_拍摄设计_动作片段的景别角度与拍法拆解
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-拍摄设计_动作片段的景别角度与拍法拆解
title: 视频拆片案例：拍摄设计_动作片段的景别角度与拍法拆解
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 拍摄设计_动作片段的景别角度与拍法拆解.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：拍摄设计_动作片段的景别角度与拍法拆解

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "雨夜小偷入室下药"
    scene_type: "悬念建立"
    emotional_arc: "神秘→紧张→惊悚"
    duration_estimate: "60s"
    shots:
      - index: 1
        duration: "1s"
        scale: "特写"
        angle: "低机位"
        movement: "固定"
        composition: "脚部占据画面中心，背景模糊"
        narrative_function: "隐藏人物身份，建立神秘感"
        cut_reason: "脚步动作完成，需要交代人物动向"
      - index: 2
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "手持"
        composition: "人物背影居中，向亮处走去"
        narrative_function: "交代人物潜入环境，手持增加紧张感"
        cut_reason: "人物到达观察位置"
      - index: 3
        duration: "3s"
        scale: "全景"
        angle: "主观POV"
        movement: "手持"
        composition: "门缝形成前景遮挡，受害者在画面深处"
        narrative_function: "建立窥视视角，明确猎物与猎手的空间关系"
        cut_reason: "转场交代受害者清晰状态"
      - index: 4
        duration: "5s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，环境安静"
        narrative_function: "展现受害者毫无防备的状态，与小偷的潜伏形成对比"
        cut_reason: "人物动作发生变化（喝水）"
      - index: 5
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物侧面，水杯在画面右侧"
        narrative_function: "引出关键道具水杯"
        cut_reason: "需要强调水杯"
      - index: 6
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "水杯居中占据画面主体"
        narrative_function: "强化水杯的视觉印象，为后续下药做铺垫"
        cut_reason: "门铃声响起，打断当前状态"
      - index: 7
        duration: "5s"
        scale: "全景"
        angle: "主观POV"
        movement: "手持"
        composition: "门缝窥视，人物起身"
        narrative_function: "回到小偷视角，观察受害者离开，寻找作案时机"
        cut_reason: "受害者离开画面"
      - index: 8
        duration: "6s"
        scale: "全景"
        angle: "主观POV"
        movement: "手持"
        composition: "门缝窥视，受害者走向深处"
        narrative_function: "确认受害者完全离开，空间安全"
        cut_reason: "小偷开始行动"
      - index: 9
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "手持"
        composition: "小偷从窗帘后钻出，进入客厅"
        narrative_function: "危机正式侵入受害者安全空间"
        cut_reason: "需要展示小偷面部特征"
      - index: 10
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "缓推"
        composition: "京剧面具充满画面"
        narrative_function: "放大诡异面具，制造惊悚情绪"
        cut_reason: "进行下药动作"
      - index: 11
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "手部和水杯特写"
        narrative_function: "清晰交代下药的致命动作"
        cut_reason: "动作完成"
      - index: 12
        duration: "2s"
        scale: "特写"
        angle: "仰拍"
        movement: "固定"
        composition: "面具俯视镜头"
        narrative_function: "展现施害者的压迫感和阴险"
        cut_reason: "小偷撤离"
      - index: 13
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "小偷从右侧离开，受害者从左侧进入"
        narrative_function: "交代空间内人物的交替，危机已埋下"
        cut_reason: "受害者回到座位"
      - index: 14
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "受害者居中看书"
        narrative_function: "恢复平静状态，利用信息差制造观众的紧张感"
        cut_reason: "受害者准备喝水"
      - index: 15
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "受害者喝水动作"
        narrative_function: "触发致命危机"
        cut_reason: "喝水动作结束"
      - index: 16
        duration: "8s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "受害者居中，随后倒下离开画面"
        narrative_function: "展示中毒结果，完成叙事闭环"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "局部悬念→窥视交替→快切危机动作→平静对比→突发结果"
      director_intent: "通过主观窥视视角和手持晃动建立紧张感，利用特写强调关键道具和动作，最后在受害者不知情的平静中爆发危机，利用信息差最大化悬念。"
      reusable_pattern: "悬念戏=局部特写开场→窥视视角建立空间→特写交代危机动作→受害者不知情的中景对比→危机爆发"
```

## 原始分析

```yaml
cases:
  - case_title: "雨夜小偷入室下药"
    scene_type: "悬念建立"
    emotional_arc: "神秘→紧张→惊悚"
    duration_estimate: "60s"
    shots:
      - index: 1
        duration: "1s"
        scale: "特写"
        angle: "低机位"
        movement: "固定"
        composition: "脚部占据画面中心，背景模糊"
        narrative_function: "隐藏人物身份，建立神秘感"
        cut_reason: "脚步动作完成，需要交代人物动向"
      - index: 2
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "手持"
        composition: "人物背影居中，向亮处走去"
        narrative_function: "交代人物潜入环境，手持增加紧张感"
        cut_reason: "人物到达观察位置"
      - index: 3
        duration: "3s"
        scale: "全景"
        angle: "主观POV"
        movement: "手持"
        composition: "门缝形成前景遮挡，受害者在画面深处"
        narrative_function: "建立窥视视角，明确猎物与猎手的空间关系"
        cut_reason: "转场交代受害者清晰状态"
      - index: 4
        duration: "5s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，环境安静"
        narrative_function: "展现受害者毫无防备的状态，与小偷的潜伏形成对比"
        cut_reason: "人物动作发生变化（喝水）"
      - index: 5
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "人物侧面，水杯在画面右侧"
        narrative_function: "引出关键道具水杯"
        cut_reason: "需要强调水杯"
      - index: 6
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "水杯居中占据画面主体"
        narrative_function: "强化水杯的视觉印象，为后续下药做铺垫"
        cut_reason: "门铃声响起，打断当前状态"
      - index: 7
        duration: "5s"
        scale: "全景"
        angle: "主观POV"
        movement: "手持"
        composition: "门缝窥视，人物起身"
        narrative_function: "回到小偷视角，观察受害者离开，寻找作案时机"
        cut_reason: "受害者离开画面"
      - index: 8
        duration: "6s"
        scale: "全景"
        angle: "主观POV"
        movement: "手持"
        composition: "门缝窥视，受害者走向深处"
        narrative_function: "确认受害者完全离开，空间安全"
        cut_reason: "小偷开始行动"
      - index: 9
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "手持"
        composition: "小偷从窗帘后钻出，进入客厅"
        narrative_function: "危机正式侵入受害者安全空间"
        cut_reason: "需要展示小偷面部特征"
      - index: 10
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "缓推"
        composition: "京剧面具充满画面"
        narrative_function: "放大诡异面具，制造惊悚情绪"
        cut_reason: "进行下药动作"
      - index: 11
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "手部和水杯特写"
        narrative_function: "清晰交代下药的致命动作"
        cut_reason: "动作完成"
      - index: 12
        duration: "2s"
        scale: "特写"
        angle: "仰拍"
        movement: "固定"
        composition: "面具俯视镜头"
        narrative_function: "展现施害者的压迫感和阴险"
        cut_reason: "小偷撤离"
      - index: 13
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "小偷从右侧离开，受害者从左侧进入"
        narrative_function: "交代空间内人物的交替，危机已埋下"
        cut_reason: "受害者回到座位"
      - index: 14
        duration: "6s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "受害者居中看书"
        narrative_function: "恢复平静状态，利用信息差制造观众的紧张感"
        cut_reason: "受害者准备喝水"
      - index: 15
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "受害者喝水动作"
        narrative_function: "触发致命危机"
        cut_reason: "喝水动作结束"
      - index: 16
        duration: "8s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "受害者居中，随后倒下离开画面"
        narrative_function: "展示中毒结果，完成叙事闭环"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "局部悬念→窥视交替→快切危机动作→平静对比→突发结果"
      director_intent: "通过主观窥视视角和手持晃动建立紧张感，利用特写强调关键道具和动作，最后在受害者不知情的平静中爆发危机，利用信息差最大化悬念。"
      reusable_pattern: "悬念戏=局部特写开场→窥视视角建立空间→特写交代危机动作→受害者不知情的中景对比→危机爆发"
```
