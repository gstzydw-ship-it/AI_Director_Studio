---
rule_id: SHOT-VERTICAL-RHYTHM-001
title: 竖屏景别节奏守则
doc_type: rule_card
rule_type: vertical_framing
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- shot-vertical-rhythm-001
- signals.vertical_framing
- signals.action_coverage
- events.collision
- risks.vertical_closeup_overuse
- risks.blood_avoidance
- scene_types.action
applies_when:
- 9:16竖屏
- 景别节奏
- 特写限频
avoid_when: []
signals:
- vertical_framing
- action_coverage
scene_types:
- action
events:
- collision
risks:
- vertical_closeup_overuse
- blood_avoidance
aspect_ratios:
- '9:16'
applies_to:
- 9:16竖屏
- 景别节奏
- 特写限频
source_files:
- D:/AI 导演系统工程文档规范.md
- knowledge/20_镜头库与机位库.md
- knowledge/02_焦段景深与景别画幅策略.md
conflicts_with: []
supersedes: []
---

# 竖屏景别节奏守则

## 规则

9:16 竖屏的片段必须优先让半身、中景和双人关系镜头承担叙事。若片段时长接近 15 秒，至少应包含两类景别：

- 半身或中景作为主力。
- 更近景别用于强化。
- 更完整景别用于缓冲和空间交代。

面部特写每段最多一次，只用于炸点、受击、情绪顶点或关键信息插入。

如果主镜头已经能讲清人物动作与关系，不要再为手指、掌心、鞋尖、袖口、嘴唇、眼角等微细节单独开镜头。

## 禁止

- 长期用中近景替代所有景别。
- 连续多个时间段都使用同主体、同角度、同景别。
- 把面部特写当默认景别。
- 把每个细节动作都拆成一个局部镜头。

受击优先级：半身 + 姿态变化 > 局部特写 > 面部特写。
