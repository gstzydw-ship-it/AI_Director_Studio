---
rule_id: CASE-剪辑叙事_省略中间过程的镜头设计
title: "视频拆片案例：剪辑叙事_省略中间过程的镜头设计"
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
  - 寻人/空间转换
source_video: "剪辑叙事_省略中间过程的镜头设计.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：剪辑叙事_省略中间过程的镜头设计

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "三人酒店寻人"
    scene_type: "寻人/空间转换"
    emotional_arc: "急切寻找→目标锁定→行动落地"
    duration_estimate: "28s"
    shots:
      - index: 1
        duration: "8s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "三人并排迎面走来，占据画面主体"
        narrative_function: "建立人物急切的状态和初始街道空间，交代寻找的起点"
        cut_reason: "人物走出画框，利用出画进行空间转场"
      - index: 2
        duration: "10s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "酒店大门居中，从室外透视室内前台"
        narrative_function: "交代到达酒店并询问前台，完成关键信息的获取"
        cut_reason: "人物再次走出画框，准备转场至楼上"
      - index: 3
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "狭长走廊透视，人物从画面深处入画"
        narrative_function: "通过入画衔接上一个出画，省略上楼过程，建立楼道空间"
        cut_reason: "人物正在四处张望寻找，需要切到目标物"
      - index: 4
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "门牌号613居中充满画面"
        narrative_function: "在角色发现前提前揭示目标，让观众领先角色一步，增强期待感"
        cut_reason: "目标已明确，需要切回人物的最终行动"
      - index: 5
        duration: "4s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影走向画面深处的房门"
        narrative_function: "角色到达目标并敲门，完成整个寻找的动作闭环"
        cut_reason: "动作完成，该段落叙事结束"
    pattern_summary:
      rhythm: "平稳交代→出画入画快切→特写定格→动作落幅"
      director_intent: "利用出画入画转场大幅压缩物理空间时间，加快节奏；通过提前展示门牌号特写制造观众的心理优势与期待。"
      reusable_pattern: "空间压缩寻人=全景出画入画省略路程→目标特写提前揭示→中景动作落幅"
```

## 原始分析

```yaml
cases:
  - case_title: "三人酒店寻人"
    scene_type: "寻人/空间转换"
    emotional_arc: "急切寻找→目标锁定→行动落地"
    duration_estimate: "28s"
    shots:
      - index: 1
        duration: "8s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "三人并排迎面走来，占据画面主体"
        narrative_function: "建立人物急切的状态和初始街道空间，交代寻找的起点"
        cut_reason: "人物走出画框，利用出画进行空间转场"
      - index: 2
        duration: "10s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "酒店大门居中，从室外透视室内前台"
        narrative_function: "交代到达酒店并询问前台，完成关键信息的获取"
        cut_reason: "人物再次走出画框，准备转场至楼上"
      - index: 3
        duration: "4s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "狭长走廊透视，人物从画面深处入画"
        narrative_function: "通过入画衔接上一个出画，省略上楼过程，建立楼道空间"
        cut_reason: "人物正在四处张望寻找，需要切到目标物"
      - index: 4
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "门牌号613居中充满画面"
        narrative_function: "在角色发现前提前揭示目标，让观众领先角色一步，增强期待感"
        cut_reason: "目标已明确，需要切回人物的最终行动"
      - index: 5
        duration: "4s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影走向画面深处的房门"
        narrative_function: "角色到达目标并敲门，完成整个寻找的动作闭环"
        cut_reason: "动作完成，该段落叙事结束"
    pattern_summary:
      rhythm: "平稳交代→出画入画快切→特写定格→动作落幅"
      director_intent: "利用出画入画转场大幅压缩物理空间时间，加快节奏；通过提前展示门牌号特写制造观众的心理优势与期待。"
      reusable_pattern: "空间压缩寻人=全景出画入画省略路程→目标特写提前揭示→中景动作落幅"
```
