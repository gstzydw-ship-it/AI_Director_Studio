---
rule_id: GUARD-SPATIAL-RESET-BUDGET-004
title: 必须修复空间重置和特写偷时间
doc_type: rule_card
rule_type: continuity_guard
owner_agent: shot_director_guard
agent_scope:
- shot_director_guard
- quality_inspector
priority: P0
status: active
pipeline_stage: guard
runtime_retrieval: true
retrieval_key:
- guard-spatial-reset-budget-004
- signals.vertical_framing
- signals.dialogue_coverage
- signals.action_coverage
- events.reaction
- risks.axis_confusion
- risks.vertical_closeup_overuse
- dialogue_types.long_dialogue_compression
- scene_types.dialogue
- scene_types.action
applies_when:
- 空间连续
- 9:16竖屏
- 群体调度
avoid_when:
- "没有空间跳变、角色消失、轴线重置或特写吞时间问题"
- "修改需要重新编排整段动作而不是最小补可见性说明"
failure_mode:
- "同场角色无解释消失或空间关系重置；9:16 大头特写吞掉反应和动作时间。"
output_contract: "优先补可见性说明和位置继承；无信息大头特写降级为中近景或关系景。"
example_good: "补充被切出角色在画面右缘虚化；把 4 秒脸部特写缩为 0.5 秒子分镜。"
example_bad: "单人特写持续到群体散开后，其他角色无出画说明。"
signals:
- vertical_framing
- dialogue_coverage
- action_coverage
scene_types:
- dialogue
- action
events:
- reaction
risks:
- axis_confusion
- vertical_closeup_overuse
dialogue_types:
- long_dialogue_compression
aspect_ratios:
- '9:16'
applies_to:
- 空间连续
- 9:16竖屏
- 群体调度
- 切镜守门
source_files:
- knowledge/27_规则守门与最小修复规则.md
- knowledge/28_全场景分镜与转场案例库.md
conflicts_with: []
supersedes: []
---

# 必须修复空间重置和特写偷时间

## 空间重置硬伤

三号规则守门导演看到以下情况必须修复：

- 右前方让路位的人物在下一镜无解释跳到主角身后
- 侧前方人物突然变成并排行走或跟随
- 刚刚同场的人物在下一镜被抹掉，且没有出画、遮挡或画外方位说明
- 关系镜头切单人镜头后，轴线、左右关系、前后关系被重置

修复时优先补充可见性说明和位置继承，不要重写整套镜头。

## 大头和时间预算硬伤

9:16 竖屏下，整张脸贴满画面的“大头”如果吞掉群体反应、台词落点、动作完成或空间交代时间，必须改成：

- 肩部以上特写
- 胸口以上中近景
- 半身中景
- 双层关系中景

如果 6 到 9 秒本应完成命令台词和关系压制，特写不能拖到 9 秒以后；如果 9 秒开始群体散开，9 秒必须进入群体关系镜头，而不是继续停在主角脸上。

## 最小修复方式

- 把无信息增量的脸部特写并回父级主镜头
- 把“眼神局部”缩成 0.3 到 0.6 秒的短子分镜
- 明确被切出角色在画面边缘、前景肩影、画外左侧或画外右侧
- 把群体动作恢复到它原本的时间段
