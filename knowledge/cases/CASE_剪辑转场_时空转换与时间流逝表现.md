---
rule_id: CASE-剪辑转场_时空转换与时间流逝表现
title: "视频拆片案例：剪辑转场_时空转换与时间流逝表现"
doc_type: case_library
rule_type: shot_sequence_case
agent_scope:
  - shot_director
  - shot_director_layout
  - shot_director_blocking
priority: reference
status: active
runtime_retrieval: true
scene_types:
  - 时间流逝/转场对比
source_video: "剪辑转场_时空转换与时间流逝表现.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：剪辑转场_时空转换与时间流逝表现

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "《好久没做》扣子转场：激情到平淡"
    scene_type: "时间流逝/转场对比"
    emotional_arc: "激情→平静→麻木"
    duration_estimate: "43"
    shots:
      - index: 1
        duration: "10s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，占据画面主体"
        narrative_function: "展示过去的激情状态，为后续的平淡做对比铺垫"
        cut_reason: "扣子崩落，视线跟随掉落的物体"
      - index: 2
        duration: "9s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "扣子居中，地板纹理构成背景"
        narrative_function: "通过扣子上的光影快速变化，视觉化地暗示时间的漫长流逝"
        cut_reason: "一只手入画准备捡起扣子"
      - index: 3
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "手部动作占据画面"
        narrative_function: "通过捡起动作连接两个不同的时空，完成无技巧转场"
        cut_reason: "动作完成，需要展示捡起扣子后的新环境"
      - index: 4
        duration: "12s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男女主分居画面左右，中间有较大空间"
        narrative_function: "建立七年后的新时空，通过空间距离暗示两人关系的疏离与生活的平淡"
        cut_reason: "需要切入细节展示具体的生活状态"
      - index: 5
        duration: "3s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "碗筷居中"
        narrative_function: "展示简单的饭菜，体现节衣缩食的生活细节"
        cut_reason: "顺着吃饭动作切到人物面部反应"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主面部居中偏右"
        narrative_function: "展现女主边吃边看电视的麻木、日常状态"
        cut_reason: "展示同一空间内男主的动作"
      - index: 7
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "手部缝线动作居中"
        narrative_function: "呼应转场元素（扣子），点明男主正在缝补当年掉落的扣子"
        cut_reason: "拉开景别展示男主整体状态"
      - index: 8
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "男主坐在沙发一角"
        narrative_function: "展示男主沉闷的生活状态，与开头的激情形成完整闭环对比"
        cut_reason: "片段结束"
    pattern_summary:
      rhythm: "动→静（特写光影）→全景定场→细节快切"
      director_intent: "通过同一物件（扣子）的掉落与捡起，配合光影变化，巧妙完成时间跨度极大的转场，并利用前后场景的激情与冷淡形成强烈对比。"
      reusable_pattern: "时间跨度转场=动作掉落物件→特写物件+光影变化→手捡起物件切全景新时空"
```

## 原始分析

```yaml
cases:
  - case_title: "《好久没做》扣子转场：激情到平淡"
    scene_type: "时间流逝/转场对比"
    emotional_arc: "激情→平静→麻木"
    duration_estimate: "43"
    shots:
      - index: 1
        duration: "10s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，占据画面主体"
        narrative_function: "展示过去的激情状态，为后续的平淡做对比铺垫"
        cut_reason: "扣子崩落，视线跟随掉落的物体"
      - index: 2
        duration: "9s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "扣子居中，地板纹理构成背景"
        narrative_function: "通过扣子上的光影快速变化，视觉化地暗示时间的漫长流逝"
        cut_reason: "一只手入画准备捡起扣子"
      - index: 3
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "手部动作占据画面"
        narrative_function: "通过捡起动作连接两个不同的时空，完成无技巧转场"
        cut_reason: "动作完成，需要展示捡起扣子后的新环境"
      - index: 4
        duration: "12s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男女主分居画面左右，中间有较大空间"
        narrative_function: "建立七年后的新时空，通过空间距离暗示两人关系的疏离与生活的平淡"
        cut_reason: "需要切入细节展示具体的生活状态"
      - index: 5
        duration: "3s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "碗筷居中"
        narrative_function: "展示简单的饭菜，体现节衣缩食的生活细节"
        cut_reason: "顺着吃饭动作切到人物面部反应"
      - index: 6
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主面部居中偏右"
        narrative_function: "展现女主边吃边看电视的麻木、日常状态"
        cut_reason: "展示同一空间内男主的动作"
      - index: 7
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "手部缝线动作居中"
        narrative_function: "呼应转场元素（扣子），点明男主正在缝补当年掉落的扣子"
        cut_reason: "拉开景别展示男主整体状态"
      - index: 8
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "男主坐在沙发一角"
        narrative_function: "展示男主沉闷的生活状态，与开头的激情形成完整闭环对比"
        cut_reason: "片段结束"
    pattern_summary:
      rhythm: "动→静（特写光影）→全景定场→细节快切"
      director_intent: "通过同一物件（扣子）的掉落与捡起，配合光影变化，巧妙完成时间跨度极大的转场，并利用前后场景的激情与冷淡形成强烈对比。"
      reusable_pattern: "时间跨度转场=动作掉落物件→特写物件+光影变化→手捡起物件切全景新时空"
```
