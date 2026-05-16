---
case_title: 视频拆片案例：镜头叙事_如何用镜头讲故事13_校车送别场景
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
- shot_reverse_shot
risks: []
reusable_pattern: CASE_镜头叙事_如何用镜头讲故事13_校车送别场景
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-镜头叙事_如何用镜头讲故事13_校车送别场景
title: 视频拆片案例：镜头叙事_如何用镜头讲故事13_校车送别场景
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头叙事_如何用镜头讲故事13_校车送别场景.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头叙事_如何用镜头讲故事13_校车送别场景

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "爸爸送女儿上校车"
    scene_type: "告别离场"
    emotional_arc: "平静→不舍→释然离去"
    duration_estimate: "40s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物位于画面中央偏左，校车从右侧驶入，占据画面右半部分"
        narrative_function: "建立整体空间关系，交代人物所处环境及即将发生的事件（校车到来），为后续动作提供舞台"
        cut_reason: "校车停稳，车门即将打开，需要更近的景别来展示细节动作"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "爸爸的肩膀占据画面左下角，视线引导至右侧打开的车门"
        narrative_function: "通过爸爸的视角代入，聚焦车门打开的动作，建立人物与校车的联系"
        cut_reason: "车门完全打开，需要切换视角以展示车内与车外的互动"
      - index: 3
        duration: "16s"
        scale: "全景"
        angle: "俯拍"
        movement: "摇摄"
        composition: "以车门为画框形成框中框构图，父女在画框中央，镜头随女儿上车动作向下摇"
        narrative_function: "从车内视角客观记录女儿上车的过程及父女对话，俯拍角度暗示女儿即将进入的新环境，摇摄保持动作连贯"
        cut_reason: "女儿上车动作完成并回头，需要切换景别捕捉其面部表情"
      - index: 4
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "女儿位于画面中央偏左，背景为车厢内部"
        narrative_function: "展示女儿回头的不舍表情，传递离别时的依恋情绪，引导观众关注其心理状态"
        cut_reason: "女儿看向爸爸，需要反打镜头展示爸爸的反应和回应"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "爸爸位于画面中央，背景适度虚化"
        narrative_function: "清晰展示爸爸的面部表情和对白，传递父亲的鼓励与隐藏的不舍，加深情感厚度"
        cut_reason: "爸爸说完话，需要切回女儿的反应及后续动作"
      - index: 6
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女儿在车门处，车门关闭后透过玻璃形成隔绝感"
        narrative_function: "通过车门关闭的动作和玻璃的阻隔，视觉化地呈现物理空间的物理分离，强化离别感"
        cut_reason: "离别动作完成，需要看爸爸最终的情绪落点"
      - index: 7
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "爸爸面部特写，眼神注视前方"
        narrative_function: "捕捉父亲目送女儿时的复杂情绪，作为情感高潮的余韵"
        cut_reason: "情绪表达充分，需要拉开景别交代最终的离场动作"
      - index: 8
        duration: "8s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "回到开场的侧面全景，校车驶离画面，爸爸转身"
        narrative_function: "首尾呼应，交代校车离开和父亲转身的完整动作，为整个场景画上句号"
        cut_reason: "场景叙事结束"
    pattern_summary:
      rhythm: "客观全景→主观代入→互动长镜→正反打快切→全景收尾"
      director_intent: "通过景别的由远及近再到远，配合视角的内外切换，细腻地展现了父女离别时的不舍情绪，同时利用动作的连贯性（如车门打开）保持了叙事的流畅。"
      reusable_pattern: "告别戏=全景建立环境→过肩/主观视角切入→近景正反打传递情绪→全景目送离场收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "爸爸送女儿上校车"
    scene_type: "告别离场"
    emotional_arc: "平静→不舍→释然离去"
    duration_estimate: "40s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物位于画面中央偏左，校车从右侧驶入，占据画面右半部分"
        narrative_function: "建立整体空间关系，交代人物所处环境及即将发生的事件（校车到来），为后续动作提供舞台"
        cut_reason: "校车停稳，车门即将打开，需要更近的景别来展示细节动作"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "爸爸的肩膀占据画面左下角，视线引导至右侧打开的车门"
        narrative_function: "通过爸爸的视角代入，聚焦车门打开的动作，建立人物与校车的联系"
        cut_reason: "车门完全打开，需要切换视角以展示车内与车外的互动"
      - index: 3
        duration: "16s"
        scale: "全景"
        angle: "俯拍"
        movement: "摇摄"
        composition: "以车门为画框形成框中框构图，父女在画框中央，镜头随女儿上车动作向下摇"
        narrative_function: "从车内视角客观记录女儿上车的过程及父女对话，俯拍角度暗示女儿即将进入的新环境，摇摄保持动作连贯"
        cut_reason: "女儿上车动作完成并回头，需要切换景别捕捉其面部表情"
      - index: 4
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "女儿位于画面中央偏左，背景为车厢内部"
        narrative_function: "展示女儿回头的不舍表情，传递离别时的依恋情绪，引导观众关注其心理状态"
        cut_reason: "女儿看向爸爸，需要反打镜头展示爸爸的反应和回应"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "爸爸位于画面中央，背景适度虚化"
        narrative_function: "清晰展示爸爸的面部表情和对白，传递父亲的鼓励与隐藏的不舍，加深情感厚度"
        cut_reason: "爸爸说完话，需要切回女儿的反应及后续动作"
      - index: 6
        duration: "4s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女儿在车门处，车门关闭后透过玻璃形成隔绝感"
        narrative_function: "通过车门关闭的动作和玻璃的阻隔，视觉化地呈现物理空间的物理分离，强化离别感"
        cut_reason: "离别动作完成，需要看爸爸最终的情绪落点"
      - index: 7
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "爸爸面部特写，眼神注视前方"
        narrative_function: "捕捉父亲目送女儿时的复杂情绪，作为情感高潮的余韵"
        cut_reason: "情绪表达充分，需要拉开景别交代最终的离场动作"
      - index: 8
        duration: "8s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "回到开场的侧面全景，校车驶离画面，爸爸转身"
        narrative_function: "首尾呼应，交代校车离开和父亲转身的完整动作，为整个场景画上句号"
        cut_reason: "场景叙事结束"
    pattern_summary:
      rhythm: "客观全景→主观代入→互动长镜→正反打快切→全景收尾"
      director_intent: "通过景别的由远及近再到远，配合视角的内外切换，细腻地展现了父女离别时的不舍情绪，同时利用动作的连贯性（如车门打开）保持了叙事的流畅。"
      reusable_pattern: "告别戏=全景建立环境→过肩/主观视角切入→近景正反打传递情绪→全景目送离场收尾"
```
