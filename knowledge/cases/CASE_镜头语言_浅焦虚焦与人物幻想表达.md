---
case_title: 视频拆片案例：镜头语言_浅焦虚焦与人物幻想表达
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 危险逼近/悬念建立
- 细节展示/性格刻画
- 心理活动/意外打断
- 幻想/情绪蒙太奇
- 氛围营造/心理外化
- dialogue
- action
- suspense
- psychology_fantasy
events:
- reaction
- cut
dialogue_types: []
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
- handheld
- focus_pull
- shallow_focus
risks: []
reusable_pattern: CASE_镜头语言_浅焦虚焦与人物幻想表达
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-镜头语言_浅焦虚焦与人物幻想表达
title: 视频拆片案例：镜头语言_浅焦虚焦与人物幻想表达
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 镜头语言_浅焦虚焦与人物幻想表达.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：镜头语言_浅焦虚焦与人物幻想表达

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "《这个杀手不太冷》反派持枪威胁"
    scene_type: "危险逼近/悬念建立"
    emotional_arc: "压迫→极度危险"
    duration_estimate: "8s"
    shots:
      - index: 1
        duration: "8s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "反派面部居中，手枪在前景"
        narrative_function: "焦点从反派狰狞的表情转移到前景的枪口，强调主角正面临的致命威胁，将注意力集中在武器上"
        cut_reason: "完成焦点转移和情绪压迫的展示"
    pattern_summary:
      rhythm: "定格→焦点转移→定格"
      director_intent: "通过焦点从人物表情到武器的转移，具象化危险的逼近，增加画面的压迫感。"
      reusable_pattern: "威胁戏=反派面部特写→焦点转移至前景武器"

  - case_title: "《校园风云》女生递蛋糕"
    scene_type: "细节展示/性格刻画"
    emotional_arc: "平静→意图揭示"
    duration_estimate: "12s"
    shots:
      - index: 1
        duration: "3s"
        scale: "中景"
        angle: "仰拍"
        movement: "固定"
        composition: "男老师居中，面带伤痕"
        narrative_function: "展示接收者的状态和场景环境"
        cut_reason: "切到动作发出者"
      - index: 2
        duration: "9s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女生面部清晰，递出蛋糕到前景"
        narrative_function: "焦点从女生得意的笑脸转移到前景蛋糕上的竞选口号，通过细节强化其势在必得的性格"
        cut_reason: "信息传递完毕"
    pattern_summary:
      rhythm: "人物反应→动作展示→焦点转移至细节"
      director_intent: "利用焦点转移引导观众阅读关键道具上的文字信息，同时补充人物性格。"
      reusable_pattern: "道具展示戏=人物表情近景→递出道具至前景→焦点转移至道具细节"

  - case_title: "《毕业生》男生走神"
    scene_type: "心理活动/意外打断"
    emotional_arc: "紧张坦白→意外惊吓→走神迷茫"
    duration_estimate: "16s"
    shots:
      - index: 1
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "男生面部特写，满头大汗"
        narrative_function: "展示男生坦白前的紧张心理"
        cut_reason: "切到对话对象的反应"
      - index: 2
        duration: "14s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "女生在前景，门后妈妈在背景"
        narrative_function: "焦点从前景女生转移到背景突然出现的妈妈，揭示意外情况；人物离开后保持虚焦，外化男生犹豫、走神的心理状态"
        cut_reason: "心理状态展示完整"
    pattern_summary:
      rhythm: "清晰对话→焦点后移揭示意外→保持虚焦留白"
      director_intent: "通过焦点转移揭示空间中的新人物，随后利用持续的虚焦画面直接视觉化角色的心理空白和迷茫。"
      reusable_pattern: "意外走神戏=前景清晰→焦点转移至后景意外元素→元素消失后保持虚焦"

  - case_title: "《妈咪》母亲的幻想"
    scene_type: "幻想/情绪蒙太奇"
    emotional_arc: "现实→美好憧憬"
    duration_estimate: "19s"
    shots:
      - index: 1
        duration: "19s"
        scale: "近景/特写"
        angle: "平视"
        movement: "手持/缓推"
        composition: "人物面部或动作细节，大光圈浅景深"
        narrative_function: "画面在短暂的清晰与模糊间不断交替，营造一种亦真亦幻的感觉，表现母亲脑海中虚构的幸福场景"
        cut_reason: "蒙太奇片段的自然过渡"
    pattern_summary:
      rhythm: "清晰与模糊快速交替"
      director_intent: "利用大光圈和选择性对焦的失控感，打破现实的视觉逻辑，营造梦幻、不真实的心理空间。"
      reusable_pattern: "幻想戏=浅景深特写+焦点在清晰与模糊间无规律交替"

  - case_title: "《大象》走廊环境对比"
    scene_type: "氛围营造/心理外化"
    emotional_arc: "客观展示→主观孤立"
    duration_estimate: "25s"
    shots:
      - index: 1
        duration: "10s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物背影居中，走廊环境清晰"
        narrative_function: "环境对焦清晰，寓意该学生被环境接纳，属于正常的校园生活"
        cut_reason: "对比展示下一个学生"
      - index: 2
        duration: "15s"
        scale: "中景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物背影居中，周围环境极度模糊"
        narrative_function: "控制焦点范围让环境模糊，营造孤独、迷茫的氛围，寓意该学生自卑自闭，与世界格格不入"
        cut_reason: "对比概念阐述完毕"
    pattern_summary:
      rhythm: "客观跟拍→主观跟拍对比"
      director_intent: "通过景深的控制（清晰vs模糊）来外化不同人物的心理状态和他们与周围环境的关系。"
      reusable_pattern: "孤立氛围戏=人物背影跟拍+极浅景深模糊周围环境"
```

## 原始分析

```yaml
cases:
  - case_title: "《这个杀手不太冷》反派持枪威胁"
    scene_type: "危险逼近/悬念建立"
    emotional_arc: "压迫→极度危险"
    duration_estimate: "8s"
    shots:
      - index: 1
        duration: "8s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "反派面部居中，手枪在前景"
        narrative_function: "焦点从反派狰狞的表情转移到前景的枪口，强调主角正面临的致命威胁，将注意力集中在武器上"
        cut_reason: "完成焦点转移和情绪压迫的展示"
    pattern_summary:
      rhythm: "定格→焦点转移→定格"
      director_intent: "通过焦点从人物表情到武器的转移，具象化危险的逼近，增加画面的压迫感。"
      reusable_pattern: "威胁戏=反派面部特写→焦点转移至前景武器"

  - case_title: "《校园风云》女生递蛋糕"
    scene_type: "细节展示/性格刻画"
    emotional_arc: "平静→意图揭示"
    duration_estimate: "12s"
    shots:
      - index: 1
        duration: "3s"
        scale: "中景"
        angle: "仰拍"
        movement: "固定"
        composition: "男老师居中，面带伤痕"
        narrative_function: "展示接收者的状态和场景环境"
        cut_reason: "切到动作发出者"
      - index: 2
        duration: "9s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女生面部清晰，递出蛋糕到前景"
        narrative_function: "焦点从女生得意的笑脸转移到前景蛋糕上的竞选口号，通过细节强化其势在必得的性格"
        cut_reason: "信息传递完毕"
    pattern_summary:
      rhythm: "人物反应→动作展示→焦点转移至细节"
      director_intent: "利用焦点转移引导观众阅读关键道具上的文字信息，同时补充人物性格。"
      reusable_pattern: "道具展示戏=人物表情近景→递出道具至前景→焦点转移至道具细节"

  - case_title: "《毕业生》男生走神"
    scene_type: "心理活动/意外打断"
    emotional_arc: "紧张坦白→意外惊吓→走神迷茫"
    duration_estimate: "16s"
    shots:
      - index: 1
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "男生面部特写，满头大汗"
        narrative_function: "展示男生坦白前的紧张心理"
        cut_reason: "切到对话对象的反应"
      - index: 2
        duration: "14s"
        scale: "近景"
        angle: "过肩"
        movement: "固定"
        composition: "女生在前景，门后妈妈在背景"
        narrative_function: "焦点从前景女生转移到背景突然出现的妈妈，揭示意外情况；人物离开后保持虚焦，外化男生犹豫、走神的心理状态"
        cut_reason: "心理状态展示完整"
    pattern_summary:
      rhythm: "清晰对话→焦点后移揭示意外→保持虚焦留白"
      director_intent: "通过焦点转移揭示空间中的新人物，随后利用持续的虚焦画面直接视觉化角色的心理空白和迷茫。"
      reusable_pattern: "意外走神戏=前景清晰→焦点转移至后景意外元素→元素消失后保持虚焦"

  - case_title: "《妈咪》母亲的幻想"
    scene_type: "幻想/情绪蒙太奇"
    emotional_arc: "现实→美好憧憬"
    duration_estimate: "19s"
    shots:
      - index: 1
        duration: "19s"
        scale: "近景/特写"
        angle: "平视"
        movement: "手持/缓推"
        composition: "人物面部或动作细节，大光圈浅景深"
        narrative_function: "画面在短暂的清晰与模糊间不断交替，营造一种亦真亦幻的感觉，表现母亲脑海中虚构的幸福场景"
        cut_reason: "蒙太奇片段的自然过渡"
    pattern_summary:
      rhythm: "清晰与模糊快速交替"
      director_intent: "利用大光圈和选择性对焦的失控感，打破现实的视觉逻辑，营造梦幻、不真实的心理空间。"
      reusable_pattern: "幻想戏=浅景深特写+焦点在清晰与模糊间无规律交替"

  - case_title: "《大象》走廊环境对比"
    scene_type: "氛围营造/心理外化"
    emotional_arc: "客观展示→主观孤立"
    duration_estimate: "25s"
    shots:
      - index: 1
        duration: "10s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物背影居中，走廊环境清晰"
        narrative_function: "环境对焦清晰，寓意该学生被环境接纳，属于正常的校园生活"
        cut_reason: "对比展示下一个学生"
      - index: 2
        duration: "15s"
        scale: "中景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物背影居中，周围环境极度模糊"
        narrative_function: "控制焦点范围让环境模糊，营造孤独、迷茫的氛围，寓意该学生自卑自闭，与世界格格不入"
        cut_reason: "对比概念阐述完毕"
    pattern_summary:
      rhythm: "客观跟拍→主观跟拍对比"
      director_intent: "通过景深的控制（清晰vs模糊）来外化不同人物的心理状态和他们与周围环境的关系。"
      reusable_pattern: "孤立氛围戏=人物背影跟拍+极浅景深模糊周围环境"
```
