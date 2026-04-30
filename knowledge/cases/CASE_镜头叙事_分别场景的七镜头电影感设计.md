---
rule_id: CASE-镜头叙事_分别场景的七镜头电影感设计
title: "视频拆片案例：镜头叙事_分别场景的七镜头电影感设计"
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
  - 告别离场
source_video: "镜头叙事_分别场景的七镜头电影感设计.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：镜头叙事_分别场景的七镜头电影感设计

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "《好好先生》分别时的亲吻"
    scene_type: "告别离场"
    emotional_arc: "平静→亲密互动→喜悦与留恋"
    duration_estimate: "29s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "男生背影在左侧前景，女生在右侧中景走来"
        narrative_function: "建立两人空间关系，交代女生主动靠近的动作"
        cut_reason: "女生走到男生面前，需要切换视角展示男生反应"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "女生背影在右侧前景，男生在左侧中景"
        narrative_function: "反打镜头，展示男生面对女生靠近时的状态"
        cut_reason: "两人即将发生亲密接触，需要更近的景别强调动作"
      - index: 3
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "女生侧脸亲吻男生，占据画面中心"
        narrative_function: "放大亲吻动作，强调情感的瞬间升温"
        cut_reason: "动作完成，需要展示被亲吻者的情绪反应"
      - index: 4
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "男生面部特写，女生头盔遮挡部分画面"
        narrative_function: "捕捉男生被亲吻后的意外与享受的细腻表情"
        cut_reason: "亲吻结束，两人分开，需要恢复关系景别"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "摇摄"
        composition: "两人对视，随后镜头跟随女生向右摇"
        narrative_function: "交代道别对白，并通过摇镜自然过渡到女生离开的动作"
        cut_reason: "女生走出画面中心，需要切回男生视角看其反应"
      - index: 6
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生面部居中，表情回味"
        narrative_function: "展示男生对刚才互动的内心喜悦和意犹未尽"
        cut_reason: "男生视线跟随女生，需要切到他所看的方向"
      - index: 7
        duration: "6s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "男生在左侧前景，女生骑车在右侧背景驶出画框"
        narrative_function: "交代女生离开的物理动作，男生转头目送，强化不舍情绪"
        cut_reason: "女生驶出画框，切入主观视角增强代入感"
      - index: 8
        duration: "3s"
        scale: "全景"
        angle: "主观POV"
        movement: "固定"
        composition: "女生骑车在画面中央远去，环境黑暗"
        narrative_function: "完全代入男生视角，表现目送心上人远去的留恋感"
        cut_reason: "主观情绪表达充分，需要拉开距离做场景收尾"
      - index: 9
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男生在左侧中景，女生在右侧远景，两人同框"
        narrative_function: "客观视角交代两人最终的空间距离，定格男生独自喜悦的状态，为场景画上句号"
        cut_reason: "场景情绪释放完毕，自然结束"
    pattern_summary:
      rhythm: "关系建立→特写互动→主观目送→全景收尾"
      director_intent: "通过丰富的视点切换（旁观到主观），细腻地展现了两人告别时的情感互动和男生的心理变化，营造出丰富的层次感。"
      reusable_pattern: "告别戏=过肩近景建立关系→正反打特写互动→主观镜头目送→全景留白收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "《好好先生》分别时的亲吻"
    scene_type: "告别离场"
    emotional_arc: "平静→亲密互动→喜悦与留恋"
    duration_estimate: "29s"
    shots:
      - index: 1
        duration: "2s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "男生背影在左侧前景，女生在右侧中景走来"
        narrative_function: "建立两人空间关系，交代女生主动靠近的动作"
        cut_reason: "女生走到男生面前，需要切换视角展示男生反应"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "女生背影在右侧前景，男生在左侧中景"
        narrative_function: "反打镜头，展示男生面对女生靠近时的状态"
        cut_reason: "两人即将发生亲密接触，需要更近的景别强调动作"
      - index: 3
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "女生侧脸亲吻男生，占据画面中心"
        narrative_function: "放大亲吻动作，强调情感的瞬间升温"
        cut_reason: "动作完成，需要展示被亲吻者的情绪反应"
      - index: 4
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "男生面部特写，女生头盔遮挡部分画面"
        narrative_function: "捕捉男生被亲吻后的意外与享受的细腻表情"
        cut_reason: "亲吻结束，两人分开，需要恢复关系景别"
      - index: 5
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "摇摄"
        composition: "两人对视，随后镜头跟随女生向右摇"
        narrative_function: "交代道别对白，并通过摇镜自然过渡到女生离开的动作"
        cut_reason: "女生走出画面中心，需要切回男生视角看其反应"
      - index: 6
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生面部居中，表情回味"
        narrative_function: "展示男生对刚才互动的内心喜悦和意犹未尽"
        cut_reason: "男生视线跟随女生，需要切到他所看的方向"
      - index: 7
        duration: "6s"
        scale: "中景"
        angle: "过肩"
        movement: "固定"
        composition: "男生在左侧前景，女生骑车在右侧背景驶出画框"
        narrative_function: "交代女生离开的物理动作，男生转头目送，强化不舍情绪"
        cut_reason: "女生驶出画框，切入主观视角增强代入感"
      - index: 8
        duration: "3s"
        scale: "全景"
        angle: "主观POV"
        movement: "固定"
        composition: "女生骑车在画面中央远去，环境黑暗"
        narrative_function: "完全代入男生视角，表现目送心上人远去的留恋感"
        cut_reason: "主观情绪表达充分，需要拉开距离做场景收尾"
      - index: 9
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男生在左侧中景，女生在右侧远景，两人同框"
        narrative_function: "客观视角交代两人最终的空间距离，定格男生独自喜悦的状态，为场景画上句号"
        cut_reason: "场景情绪释放完毕，自然结束"
    pattern_summary:
      rhythm: "关系建立→特写互动→主观目送→全景收尾"
      director_intent: "通过丰富的视点切换（旁观到主观），细腻地展现了两人告别时的情感互动和男生的心理变化，营造出丰富的层次感。"
      reusable_pattern: "告别戏=过肩近景建立关系→正反打特写互动→主观镜头目送→全景留白收尾"
```
