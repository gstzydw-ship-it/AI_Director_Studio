---
rule_id: CASE-镜头叙事_情绪升级时的景别递进与压迫感
title: "视频拆片案例：镜头叙事_情绪升级时的景别递进与压迫感"
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
  - 冲突爆发
source_video: "镜头叙事_情绪升级时的景别递进与压迫感.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：镜头叙事_情绪升级时的景别递进与压迫感

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "餐桌黑老大连扇小弟四个嘴巴子"
    scene_type: "冲突爆发"
    emotional_arc: "紧张→激烈→爆发"
    duration_estimate: "10"
    shots:
      - index: 1
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "黑老大在画面右侧，小弟在左侧，展现扇巴掌的动作全貌"
        narrative_function: "建立动作发生的空间关系，展示施暴者的动作幅度"
        cut_reason: "动作完成，需要展示受击者的反应"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "从黑老大过肩拍小弟，小弟在画面中央受击"
        narrative_function: "展示受击者的痛苦反应，强调打击的力度"
        cut_reason: "受击反应结束，切回施暴者准备下一次攻击"
      - index: 3
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "黑老大在画面中央，景别比镜头1更近"
        narrative_function: "通过景别推近，放大施暴者的愤怒情绪和压迫感"
        cut_reason: "动作完成，需要展示受击者的反应"
      - index: 4
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "从黑老大过肩拍小弟，小弟在画面中央受击"
        narrative_function: "再次展示受击反应，维持施暴与受击的节奏"
        cut_reason: "受击反应结束，切回施暴者"
      - index: 5
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "黑老大面部特写"
        narrative_function: "景别进一步缩小，极度放大施暴者的情绪张力"
        cut_reason: "动作完成，需要展示受击者的反应"
      - index: 6
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "从黑老大过肩拍小弟，小弟在画面中央受击"
        narrative_function: "展示第三次受击，受击者景别保持不变，凸显其被动地位"
        cut_reason: "受击反应结束，切回施暴者"
      - index: 7
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "黑老大在画面中央，景别拉回近景"
        narrative_function: "为最后一次爆发蓄力，通过景别后退制造节奏变化"
        cut_reason: "动作完成，准备最后的情绪爆发"
      - index: 8
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "黑老大面部特写"
        narrative_function: "不切受击反应，直接切特写，通过快切和景别跳跃将情绪推向最高潮"
        cut_reason: "场景情绪达到顶点，段落结束"
    pattern_summary:
      rhythm: "正反打交替→施暴者景别渐进→快切特写爆发"
      director_intent: "通过施暴者景别的不断推近和受击者景别的固定，强化施暴者的压迫感和主角地位，最后通过打破正反打规律和快切特写将情绪推向高潮。"
      reusable_pattern: "单向施暴戏=正反打交替+施暴者景别递进+受击者景别固定→打破规律快切特写爆发"
```

## 原始分析

```yaml
cases:
  - case_title: "餐桌黑老大连扇小弟四个嘴巴子"
    scene_type: "冲突爆发"
    emotional_arc: "紧张→激烈→爆发"
    duration_estimate: "10"
    shots:
      - index: 1
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "黑老大在画面右侧，小弟在左侧，展现扇巴掌的动作全貌"
        narrative_function: "建立动作发生的空间关系，展示施暴者的动作幅度"
        cut_reason: "动作完成，需要展示受击者的反应"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "从黑老大过肩拍小弟，小弟在画面中央受击"
        narrative_function: "展示受击者的痛苦反应，强调打击的力度"
        cut_reason: "受击反应结束，切回施暴者准备下一次攻击"
      - index: 3
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "黑老大在画面中央，景别比镜头1更近"
        narrative_function: "通过景别推近，放大施暴者的愤怒情绪和压迫感"
        cut_reason: "动作完成，需要展示受击者的反应"
      - index: 4
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "从黑老大过肩拍小弟，小弟在画面中央受击"
        narrative_function: "再次展示受击反应，维持施暴与受击的节奏"
        cut_reason: "受击反应结束，切回施暴者"
      - index: 5
        duration: "1s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "黑老大面部特写"
        narrative_function: "景别进一步缩小，极度放大施暴者的情绪张力"
        cut_reason: "动作完成，需要展示受击者的反应"
      - index: 6
        duration: "1s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "从黑老大过肩拍小弟，小弟在画面中央受击"
        narrative_function: "展示第三次受击，受击者景别保持不变，凸显其被动地位"
        cut_reason: "受击反应结束，切回施暴者"
      - index: 7
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "黑老大在画面中央，景别拉回近景"
        narrative_function: "为最后一次爆发蓄力，通过景别后退制造节奏变化"
        cut_reason: "动作完成，准备最后的情绪爆发"
      - index: 8
        duration: "3s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "黑老大面部特写"
        narrative_function: "不切受击反应，直接切特写，通过快切和景别跳跃将情绪推向最高潮"
        cut_reason: "场景情绪达到顶点，段落结束"
    pattern_summary:
      rhythm: "正反打交替→施暴者景别渐进→快切特写爆发"
      director_intent: "通过施暴者景别的不断推近和受击者景别的固定，强化施暴者的压迫感和主角地位，最后通过打破正反打规律和快切特写将情绪推向高潮。"
      reusable_pattern: "单向施暴戏=正反打交替+施暴者景别递进+受击者景别固定→打破规律快切特写爆发"
```
