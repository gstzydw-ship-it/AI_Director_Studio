---
rule_id: GUARD-EMOTION-STORY-RHYTHM-PRIORITY-007
title: 守门按情绪故事节奏优先级裁剪镜头
doc_type: rule_card
rule_type: continuity_guard
owner_agent: shot_director_guard
agent_scope:
- shot_director_guard
- shot_director_blocking
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: guard
runtime_retrieval: true
retrieval_key:
- guard-emotion-story-rhythm-priority-007
- signals.dialogue_coverage
- signals.action_coverage
- signals.emotion
- events.reaction
- events.cut
- risks.too_many_cuts
- risks.flat_emotion
- risks.dialogue_drop
applies_when:
- 最终守门
- 情绪表达
- 切镜裁剪
- 台词覆盖
avoid_when:
- "当前镜头表没有切镜、情绪或台词问题。"
failure_mode:
- "守门只检查空间连续，却保留破坏情绪、故事和节奏的机械切镜。"
output_contract: "优先保护情绪、故事和节奏；只有在前三者成立后再保留空间和轴线层面的切镜。"
example_good: "为了保留安抚台词和孩子反应，删除无信息咖啡特写。"
example_bad: "空间都对，但台词被切掉、情绪没有停顿、关键反应不可见。"
signals:
- dialogue_coverage
- action_coverage
- emotion
scene_types:
- dialogue
- action
- emotional_turning_point
events:
- reaction
- cut
risks:
- too_many_cuts
- flat_emotion
- dialogue_drop
dialogue_types:
- visible_speaking
- reaction_pause
applies_to:
- 规则守门
- 情绪表达
- 切镜裁剪
source_files:
- knowledge/rules/shot_director_guard/GUARD-FIRST-FRAME-PROP-CUT-BUDGET-006.md
- knowledge/rules/shot_director/SHOT-MOTIVATED-CUT-ACTION-DENSITY-002.md
- knowledge/rules/shot_director_blocking/BLOCKING-FAST-CUT-LEGIBILITY-008.md
external_sources:
- https://www.premiumbeat.com/blog/cutting-on-the-blink-editing-tips-from-walter-murch/
- https://www.backstage.com/magazine/article/film-rhythm-editing-guide-77147/
conflicts_with: []
supersedes: []
---

# 守门按情绪故事节奏优先级裁剪镜头

## 优先级

`shot_director_guard` 检查切镜时，必须按以下顺序判断：

1. `情绪`：切镜是否保留或强化此刻的情绪冲击。
2. `故事`：切镜是否推进剧情、信息或人物目标。
3. `节奏`：切镜是否符合当前节奏档位，而不是机械变快。
4. `视线`：切镜后观众目光是否能自然找到重点。
5. `画面方向`：左右、前后、轴线是否不乱。
6. `三维空间`：人物和道具位置是否继承。

空间连续很重要，但不能以“空间没错”为理由保留破坏情绪、台词和故事的碎切。

## 必须删除或并回的镜头

以下镜头必须删除、并回父镜头，或降级为镜内动作：

- 没有新信息的手部、衣角、杯子、眼神短切。
- 打断台词完整性或听者反应的短切。
- 让情绪刚出现就被切走的镜头。
- 只重复上一镜已经看清的动作。
- 导致尾帧不可继承的局部特写。

## 必须保留或补足的镜头

以下镜头不能因为“节奏快”被删：

- 情绪转折后的反应停顿。
- 关系变化后的同框复位。
- 关键道具状态改变后的完成态。
- 台词落点后的听者反应。

## 输出要求

守门修复报告必须说明：

```yaml
裁剪依据:
  情绪: 保留/删除原因
  故事: 保留/删除原因
  节奏: 当前档位与每5秒镜头数
  台词: 是否完整覆盖
  空间: 是否可继承
```
