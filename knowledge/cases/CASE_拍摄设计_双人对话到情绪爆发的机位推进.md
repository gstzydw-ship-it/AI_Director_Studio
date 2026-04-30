---
rule_id: CASE-拍摄设计_双人对话到情绪爆发的机位推进
title: "视频拆片案例：拍摄设计_双人对话到情绪爆发的机位推进"
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
source_video: "拍摄设计_双人对话到情绪爆发的机位推进.mp4"
extraction_date: "2026-04-24"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---

# 视频拆片案例：拍摄设计_双人对话到情绪爆发的机位推进

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "街头情侣激烈争吵"
    scene_type: "冲突爆发"
    emotional_arc: "铺垫→争吵→爆发→高潮定格"
    duration_estimate: "120s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "女生在左前走，男生在右后追，包含环境信息"
        narrative_function: "建立空间关系和追逐的动态，为争吵做铺垫"
        cut_reason: "前景汽车经过形成自然转场，人物停下准备交锋"
      - index: 2
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "女生转身，两人面对面，占据画面中心"
        narrative_function: "动作停止，正式进入对峙状态"
        cut_reason: "女生开口说话，开始第一轮争吵"
      - index: 3
        duration: "3s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "传递女生抱怨的台词，确立女生在初期的强势地位"
        cut_reason: "男生开口回应"
      - index: 4
        duration: "5s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带女生肩膀，男生面部清晰"
        narrative_function: "展示男生的防御性回应"
        cut_reason: "女生继续强势输出"
      - index: 5
        duration: "8s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "女生长段台词施压，情绪逐渐累积"
        cut_reason: "男生受不了开始走位"
      - index: 6
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人侧面，男生走到画面左侧转身"
        narrative_function: "通过走位打破原有僵局，暗示男生情绪即将爆发"
        cut_reason: "男生开始大声反击"
      - index: 7
        duration: "7s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带女生肩膀，男生面部清晰"
        narrative_function: "男生情绪爆发，开始倾诉委屈"
        cut_reason: "需要展示女生对男生爆发的反应"
      - index: 8
        duration: "2s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "展示女生被男生气势压倒的短暂错愕"
        cut_reason: "男生继续连珠炮式的控诉"
      - index: 9
        duration: "9s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带女生肩膀，男生面部清晰"
        narrative_function: "男生持续输出，将矛盾推向白热化"
        cut_reason: "切回双人全貌展示紧张关系"
      - index: 10
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人侧面相对，中间有一定距离"
        narrative_function: "在长段台词后提供视觉缓冲，重新强调两人的对立"
        cut_reason: "女生开始反击"
      - index: 11
        duration: "4s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "女生抛出核心矛盾点（买礼物）"
        cut_reason: "进入快节奏的问答交锋"
      - index: 12
        duration: "10s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "正反打快速切换"
        narrative_function: "通过高频的正反打切换，表现两人互不相让的激烈争吵"
        cut_reason: "情绪升级，需要更近的景别"
      - index: 13
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生单人画面，无前景遮挡"
        narrative_function: "剥离对方的存在，放大男生个体的委屈情绪"
        cut_reason: "女生继续逼问"
      - index: 14
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女生单人画面"
        narrative_function: "放大女生的愤怒与咄咄逼人"
        cut_reason: "男生情绪到达顶点"
      - index: 15
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生单人画面"
        narrative_function: "男生喊出“因为我喜欢你”，情绪最高点"
        cut_reason: "展示女生听到告白后的反应"
      - index: 16
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "女生面部特写"
        narrative_function: "捕捉女生瞬间的震惊与随后的冷酷"
        cut_reason: "切回双人景别展示关系破裂"
      - index: 17
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人侧面"
        narrative_function: "短暂的停顿，暴风雨前的宁静"
        cut_reason: "女生说出绝情的话"
      - index: 18
        duration: "10s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "单人特写正反打"
        narrative_function: "极近的景别展现两人互相伤害的残忍和心碎"
        cut_reason: "争吵结束，情绪需要释放与定格"
      - index: 19
        duration: "17s"
        scale: "全景"
        angle: "平视"
        movement: "升格"
        composition: "两人相对无言，路人在前景和背景中快速穿梭"
        narrative_function: "用路人的流动反衬两人关系的凝固与死亡，将情绪余韵拉长"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "全景铺垫→过肩正反打(中速)→单人近景/特写(快切)→全景升格(极慢)"
      director_intent: "通过景别从全景到特写的不断收缩来放大人物情绪和压迫感，最后用全景升格和路人穿梭反衬两人关系的破裂与凝固。"
      reusable_pattern: "激烈争吵戏=全景走位定场→过肩正反打铺垫→单人特写推向高潮→全景升格定格情绪"
```

## 原始分析

```yaml
cases:
  - case_title: "街头情侣激烈争吵"
    scene_type: "冲突爆发"
    emotional_arc: "铺垫→争吵→爆发→高潮定格"
    duration_estimate: "120s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "女生在左前走，男生在右后追，包含环境信息"
        narrative_function: "建立空间关系和追逐的动态，为争吵做铺垫"
        cut_reason: "前景汽车经过形成自然转场，人物停下准备交锋"
      - index: 2
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "女生转身，两人面对面，占据画面中心"
        narrative_function: "动作停止，正式进入对峙状态"
        cut_reason: "女生开口说话，开始第一轮争吵"
      - index: 3
        duration: "3s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "传递女生抱怨的台词，确立女生在初期的强势地位"
        cut_reason: "男生开口回应"
      - index: 4
        duration: "5s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带女生肩膀，男生面部清晰"
        narrative_function: "展示男生的防御性回应"
        cut_reason: "女生继续强势输出"
      - index: 5
        duration: "8s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "女生长段台词施压，情绪逐渐累积"
        cut_reason: "男生受不了开始走位"
      - index: 6
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人侧面，男生走到画面左侧转身"
        narrative_function: "通过走位打破原有僵局，暗示男生情绪即将爆发"
        cut_reason: "男生开始大声反击"
      - index: 7
        duration: "7s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带女生肩膀，男生面部清晰"
        narrative_function: "男生情绪爆发，开始倾诉委屈"
        cut_reason: "需要展示女生对男生爆发的反应"
      - index: 8
        duration: "2s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "展示女生被男生气势压倒的短暂错愕"
        cut_reason: "男生继续连珠炮式的控诉"
      - index: 9
        duration: "9s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带女生肩膀，男生面部清晰"
        narrative_function: "男生持续输出，将矛盾推向白热化"
        cut_reason: "切回双人全貌展示紧张关系"
      - index: 10
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人侧面相对，中间有一定距离"
        narrative_function: "在长段台词后提供视觉缓冲，重新强调两人的对立"
        cut_reason: "女生开始反击"
      - index: 11
        duration: "4s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "带男生肩膀，女生面部清晰"
        narrative_function: "女生抛出核心矛盾点（买礼物）"
        cut_reason: "进入快节奏的问答交锋"
      - index: 12
        duration: "10s"
        scale: "中近景"
        angle: "过肩"
        movement: "固定"
        composition: "正反打快速切换"
        narrative_function: "通过高频的正反打切换，表现两人互不相让的激烈争吵"
        cut_reason: "情绪升级，需要更近的景别"
      - index: 13
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生单人画面，无前景遮挡"
        narrative_function: "剥离对方的存在，放大男生个体的委屈情绪"
        cut_reason: "女生继续逼问"
      - index: 14
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女生单人画面"
        narrative_function: "放大女生的愤怒与咄咄逼人"
        cut_reason: "男生情绪到达顶点"
      - index: 15
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生单人画面"
        narrative_function: "男生喊出“因为我喜欢你”，情绪最高点"
        cut_reason: "展示女生听到告白后的反应"
      - index: 16
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "女生面部特写"
        narrative_function: "捕捉女生瞬间的震惊与随后的冷酷"
        cut_reason: "切回双人景别展示关系破裂"
      - index: 17
        duration: "1s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人侧面"
        narrative_function: "短暂的停顿，暴风雨前的宁静"
        cut_reason: "女生说出绝情的话"
      - index: 18
        duration: "10s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "单人特写正反打"
        narrative_function: "极近的景别展现两人互相伤害的残忍和心碎"
        cut_reason: "争吵结束，情绪需要释放与定格"
      - index: 19
        duration: "17s"
        scale: "全景"
        angle: "平视"
        movement: "升格"
        composition: "两人相对无言，路人在前景和背景中快速穿梭"
        narrative_function: "用路人的流动反衬两人关系的凝固与死亡，将情绪余韵拉长"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "全景铺垫→过肩正反打(中速)→单人近景/特写(快切)→全景升格(极慢)"
      director_intent: "通过景别从全景到特写的不断收缩来放大人物情绪和压迫感，最后用全景升格和路人穿梭反衬两人关系的破裂与凝固。"
      reusable_pattern: "激烈争吵戏=全景走位定场→过肩正反打铺垫→单人特写推向高潮→全景升格定格情绪"
```
