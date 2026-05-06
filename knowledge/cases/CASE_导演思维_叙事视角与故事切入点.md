---
case_title: 视频拆片案例：导演思维_叙事视角与故事切入点
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 冲突爆发/争吵离场
- dialogue
- action
events:
- reaction
- cut
dialogue_types:
- teasing
- argument_escalation
- reaction_beat
visual_constraints:
- wide_shot
- closeup
- over_shoulder
- shot_reverse_shot
- reaction_shot
risks: []
reusable_pattern: CASE_导演思维_叙事视角与故事切入点
aspect_ratio: unspecified
runtime_retrieval: true
source_files: []
rule_id: CASE-导演思维_叙事视角与故事切入点
title: 视频拆片案例：导演思维_叙事视角与故事切入点
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 导演思维_叙事视角与故事切入点.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
---

# 视频拆片案例：导演思维_叙事视角与故事切入点

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "《那些年》男女主树下争吵戏"
    scene_type: "冲突爆发/争吵离场"
    emotional_arc: "日常调侃→情绪升级→爆发离场→失落留白"
    duration_estimate: "55s"
    shots:
      - index: 1
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男生蹲在右侧修车，女生站在左侧看书，环境开阔"
        narrative_function: "建立空间关系，交代两人所处环境及初始状态"
        cut_reason: "男生开始大段台词，需要看清其表情"
      - index: 2
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生面部占据画面主体，低头看书"
        narrative_function: "展示男生的动作和对白，确立其漫不经心的态度"
        cut_reason: "女生接话，需要展示听者反应"
      - index: 3
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，背景虚化"
        narrative_function: "展示女生的对白及略带说教的态度"
        cut_reason: "男生反驳"
      - index: 4
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生侧脸，抬头看女生后又低头"
        narrative_function: "通过眼神变化展现男生的不屑与敷衍"
        cut_reason: "女生继续说教"
      - index: 5
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，表情认真"
        narrative_function: "传递对白，推动情绪逐渐累积"
        cut_reason: "男生回应"
      - index: 6
        duration: "7s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生低头专心修车"
        narrative_function: "展示男生回避沟通、满不在乎的心理状态"
        cut_reason: "女生情绪开始激动"
      - index: 7
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，眉头微皱"
        narrative_function: "表达女生的不满情绪"
        cut_reason: "男生反击"
      - index: 8
        duration: "5s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生侧脸，边修车边说话"
        narrative_function: "展现男生的倔强和言语上的攻击性"
        cut_reason: "女生情绪爆发"
      - index: 9
        duration: "5s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，表情严肃且带有怒意"
        narrative_function: "展示女生情绪的彻底爆发和对男生的失望"
        cut_reason: "男生最后的回应"
      - index: 10
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生低头，表情微变"
        narrative_function: "展示男生被戳中痛处但仍强装镇定的状态"
        cut_reason: "女生下最后通牒并离开"
      - index: 11
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生说完台词后转身走出画面"
        narrative_function: "完成情绪宣泄，通过出画动作切断对话"
        cut_reason: "需要交代女生离开后的整体空间状态"
      - index: 12
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "女生向左走远，男生仍在右侧蹲着"
        narrative_function: "视觉化呈现两人关系的破裂和心理距离的拉开"
        cut_reason: "需要展示男生在女生离开后的真实内心反应"
      - index: 13
        duration: "7s"
        scale: "近景"
        angle: "侧后方"
        movement: "固定"
        composition: "男生背影转侧脸，视线望向画左"
        narrative_function: "作为主观视角的落幅，展现男生内心的触动、懊悔与失落"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "平稳交代→正反打快切升温→全景拉开→特写定格留白"
      director_intent: "通过给男生分配更多机位（侧面+正面）和最后的反应特写，牢牢锚定男生的主观叙事视角，让观众代入男生的内心世界去感受女生的影响。"
      reusable_pattern: "主观视角争吵戏=全景开场→正反打对话（主视角角色多机位/多反应）→全景交代分离→主视角角色反应特写收尾"
```

## 原始分析

```yaml
cases:
  - case_title: "《那些年》男女主树下争吵戏"
    scene_type: "冲突爆发/争吵离场"
    emotional_arc: "日常调侃→情绪升级→爆发离场→失落留白"
    duration_estimate: "55s"
    shots:
      - index: 1
        duration: "6s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "男生蹲在右侧修车，女生站在左侧看书，环境开阔"
        narrative_function: "建立空间关系，交代两人所处环境及初始状态"
        cut_reason: "男生开始大段台词，需要看清其表情"
      - index: 2
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生面部占据画面主体，低头看书"
        narrative_function: "展示男生的动作和对白，确立其漫不经心的态度"
        cut_reason: "女生接话，需要展示听者反应"
      - index: 3
        duration: "2s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，背景虚化"
        narrative_function: "展示女生的对白及略带说教的态度"
        cut_reason: "男生反驳"
      - index: 4
        duration: "4s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生侧脸，抬头看女生后又低头"
        narrative_function: "通过眼神变化展现男生的不屑与敷衍"
        cut_reason: "女生继续说教"
      - index: 5
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，表情认真"
        narrative_function: "传递对白，推动情绪逐渐累积"
        cut_reason: "男生回应"
      - index: 6
        duration: "7s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生低头专心修车"
        narrative_function: "展示男生回避沟通、满不在乎的心理状态"
        cut_reason: "女生情绪开始激动"
      - index: 7
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，眉头微皱"
        narrative_function: "表达女生的不满情绪"
        cut_reason: "男生反击"
      - index: 8
        duration: "5s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生侧脸，边修车边说话"
        narrative_function: "展现男生的倔强和言语上的攻击性"
        cut_reason: "女生情绪爆发"
      - index: 9
        duration: "5s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生居中，表情严肃且带有怒意"
        narrative_function: "展示女生情绪的彻底爆发和对男生的失望"
        cut_reason: "男生最后的回应"
      - index: 10
        duration: "3s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男生低头，表情微变"
        narrative_function: "展示男生被戳中痛处但仍强装镇定的状态"
        cut_reason: "女生下最后通牒并离开"
      - index: 11
        duration: "3s"
        scale: "中近景"
        angle: "平视"
        movement: "固定"
        composition: "女生说完台词后转身走出画面"
        narrative_function: "完成情绪宣泄，通过出画动作切断对话"
        cut_reason: "需要交代女生离开后的整体空间状态"
      - index: 12
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "女生向左走远，男生仍在右侧蹲着"
        narrative_function: "视觉化呈现两人关系的破裂和心理距离的拉开"
        cut_reason: "需要展示男生在女生离开后的真实内心反应"
      - index: 13
        duration: "7s"
        scale: "近景"
        angle: "侧后方"
        movement: "固定"
        composition: "男生背影转侧脸，视线望向画左"
        narrative_function: "作为主观视角的落幅，展现男生内心的触动、懊悔与失落"
        cut_reason: "场景结束"
    pattern_summary:
      rhythm: "平稳交代→正反打快切升温→全景拉开→特写定格留白"
      director_intent: "通过给男生分配更多机位（侧面+正面）和最后的反应特写，牢牢锚定男生的主观叙事视角，让观众代入男生的内心世界去感受女生的影响。"
      reusable_pattern: "主观视角争吵戏=全景开场→正反打对话（主视角角色多机位/多反应）→全景交代分离→主视角角色反应特写收尾"
```
