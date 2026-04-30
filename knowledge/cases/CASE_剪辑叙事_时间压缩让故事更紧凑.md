---
rule_id: CASE-剪辑叙事_时间压缩让故事更紧凑
title: "视频拆片案例：剪辑叙事_时间压缩让故事更紧凑"
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
  - 日常压缩, 追逐紧张
source_video: "剪辑叙事_时间压缩让故事更紧凑.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：剪辑叙事_时间压缩让故事更紧凑

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "小偷销赃"
    scene_type: "日常压缩"
    emotional_arc: "平稳→得意"
    duration_estimate: "15s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "摇摄"
        composition: "街道全景，摩托车从左至右驶入画面"
        narrative_function: "建立空间环境，交代人物到达目的地"
        cut_reason: "人物到达店门口，需要展示具体动作"
      - index: 2
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "两人在画面中央，背景是店铺橱窗"
        narrative_function: "展示人物下车动作，交代人物状态"
        cut_reason: "动作完成，需要展示进入店铺"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "店内视角，两人从门外进入"
        narrative_function: "时间压缩，省略从车到门的行走过程，直接展示进入店内"
        cut_reason: "人物进入店内，需要展示店主反应"
      - index: 4
        duration: "2s"
        scale: "近景"
        angle: "仰拍"
        movement: "固定"
        composition: "店主在画面中央，眼神看向镜头方向"
        narrative_function: "展示店主反应，建立人物关系"
        cut_reason: "需要展示小偷的动作"
      - index: 5
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "电脑放在柜台上，占据画面中心"
        narrative_function: "时间压缩，省略从门口到柜台的行走过程，直接展示核心动作（放电脑）"
        cut_reason: "动作完成，需要展示人物对话"
      - index: 6
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "小偷在画面中央，表情得意"
        narrative_function: "展示人物情绪，推进剧情"
        cut_reason: "需要展示全景关系"
      - index: 7
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "店主和小偷在画面两侧，中间是柜台"
        narrative_function: "展示双方交流，完成销赃过程"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "全景→近景→特写→中景"
      director_intent: "通过省略不必要的行走过程，利用观众的心理补偿机制，加快叙事节奏，使片段干脆利落。"
      reusable_pattern: "时间压缩=动作起点→省略过程→动作终点/核心动作特写"

  - case_title: "女主追小偷"
    scene_type: "追逐紧张"
    emotional_arc: "焦急→果断"
    duration_estimate: "10s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面中央，背景是模糊的人群"
        narrative_function: "展示女主焦急的情绪，交代她发现手机被偷"
        cut_reason: "需要展示女主的应对动作"
      - index: 2
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "摇摄"
        composition: "出租车从左至右驶入画面"
        narrative_function: "展示女主发现交通工具，为下一步行动做铺垫"
        cut_reason: "需要展示女主上车后的状态"
      - index: 3
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在车内，司机在背景"
        narrative_function: "时间压缩，省略上车过程，直接展示女主在车内交代情况，加快节奏"
        cut_reason: "需要展示女主的追踪手段"
      - index: 4
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "手机屏幕占据画面中心"
        narrative_function: "展示追踪信息，推进剧情"
        cut_reason: "需要展示女主的指令"
      - index: 5
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面中央，手指向前方"
        narrative_function: "展示女主果断的指令，增强紧张感"
        cut_reason: "需要展示车辆启动"
      - index: 6
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "出租车在道路上行驶"
        narrative_function: "展示追逐开始，提升紧张氛围"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "近景→摇摄→近景→特写→全景"
      director_intent: "通过省略上车过程，直接切入车内对话，加快叙事节奏，增强追逐的紧张感。"
      reusable_pattern: "追逐戏=发现目标→省略上车过程→车内交代/追踪特写→车辆启动全景"
```

## 原始分析

```yaml
cases:
  - case_title: "小偷销赃"
    scene_type: "日常压缩"
    emotional_arc: "平稳→得意"
    duration_estimate: "15s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "摇摄"
        composition: "街道全景，摩托车从左至右驶入画面"
        narrative_function: "建立空间环境，交代人物到达目的地"
        cut_reason: "人物到达店门口，需要展示具体动作"
      - index: 2
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "两人在画面中央，背景是店铺橱窗"
        narrative_function: "展示人物下车动作，交代人物状态"
        cut_reason: "动作完成，需要展示进入店铺"
      - index: 3
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "店内视角，两人从门外进入"
        narrative_function: "时间压缩，省略从车到门的行走过程，直接展示进入店内"
        cut_reason: "人物进入店内，需要展示店主反应"
      - index: 4
        duration: "2s"
        scale: "近景"
        angle: "仰拍"
        movement: "固定"
        composition: "店主在画面中央，眼神看向镜头方向"
        narrative_function: "展示店主反应，建立人物关系"
        cut_reason: "需要展示小偷的动作"
      - index: 5
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "电脑放在柜台上，占据画面中心"
        narrative_function: "时间压缩，省略从门口到柜台的行走过程，直接展示核心动作（放电脑）"
        cut_reason: "动作完成，需要展示人物对话"
      - index: 6
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "小偷在画面中央，表情得意"
        narrative_function: "展示人物情绪，推进剧情"
        cut_reason: "需要展示全景关系"
      - index: 7
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "店主和小偷在画面两侧，中间是柜台"
        narrative_function: "展示双方交流，完成销赃过程"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "全景→近景→特写→中景"
      director_intent: "通过省略不必要的行走过程，利用观众的心理补偿机制，加快叙事节奏，使片段干脆利落。"
      reusable_pattern: "时间压缩=动作起点→省略过程→动作终点/核心动作特写"

  - case_title: "女主追小偷"
    scene_type: "追逐紧张"
    emotional_arc: "焦急→果断"
    duration_estimate: "10s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面中央，背景是模糊的人群"
        narrative_function: "展示女主焦急的情绪，交代她发现手机被偷"
        cut_reason: "需要展示女主的应对动作"
      - index: 2
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "摇摄"
        composition: "出租车从左至右驶入画面"
        narrative_function: "展示女主发现交通工具，为下一步行动做铺垫"
        cut_reason: "需要展示女主上车后的状态"
      - index: 3
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在车内，司机在背景"
        narrative_function: "时间压缩，省略上车过程，直接展示女主在车内交代情况，加快节奏"
        cut_reason: "需要展示女主的追踪手段"
      - index: 4
        duration: "2s"
        scale: "特写"
        angle: "俯拍"
        movement: "固定"
        composition: "手机屏幕占据画面中心"
        narrative_function: "展示追踪信息，推进剧情"
        cut_reason: "需要展示女主的指令"
      - index: 5
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主在画面中央，手指向前方"
        narrative_function: "展示女主果断的指令，增强紧张感"
        cut_reason: "需要展示车辆启动"
      - index: 6
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "出租车在道路上行驶"
        narrative_function: "展示追逐开始，提升紧张氛围"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "近景→摇摄→近景→特写→全景"
      director_intent: "通过省略上车过程，直接切入车内对话，加快叙事节奏，增强追逐的紧张感。"
      reusable_pattern: "追逐戏=发现目标→省略上车过程→车内交代/追踪特写→车辆启动全景"
```
