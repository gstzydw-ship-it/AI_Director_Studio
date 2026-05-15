---
rule_id: TIME-ACTION-DENSITY-COVERAGE-004
title: 拆片必须按动作密度决定拍摄覆盖而不是逐动作列清单
doc_type: rule_card
rule_type: segmentation
owner_agent: story_planner
agent_scope:
- story_planner
- rhythm_rewrite_director
- shot_director
- quality_inspector
priority: P0
status: active
pipeline_stage: story_planning
runtime_retrieval: true
retrieval_key:
- time-action-density-coverage-004
- signals.time_budget
- signals.action_density
- events.action_peak
- events.reaction
- risks.too_many_events_in_fragment
- risks.undercovered_event
applies_when:
- 拆片
- 动作密集
- 事件覆盖
- 省略动作
avoid_when:
- "用户明确要求逐动作记录，且不是给视频生成模型使用。"
failure_mode:
- "拆片把所有小动作都当成必须拍，导致后续镜头导演只能碎切或超预算。"
output_contract: "story_planner 必须把动作分成必拍、可压缩、可省略，并给动作密度和镜头密度建议。"
example_good: "必拍：拍停闹钟、穿袜完成、拎起书包；可省：身体转向、重复整理。"
example_bad: "逐条保留伸手、摸口袋、转身、低头、抓杯、放杯、碰杂志等全部动作。"
signals:
- time_budget
- action_density
scene_types:
- action
- domestic_scene
- dialogue
events:
- action_peak
- reaction
risks:
- too_many_events_in_fragment
- undercovered_event
applies_to:
- 拆片
- 动作覆盖
- 事件密度
source_files:
- knowledge/rules/rhythm_rewrite_director/RHYTHM-SHOT-DENSITY-MATRIX-003.md
- knowledge/rules/prompt_compiler/PROMPT-CUT-BUDGET-001.md
- knowledge/05_剧本拆分与15秒片段规划规则.md
external_sources:
- https://cursa.app/en/page/pacing-and-structure-making-cuts-feel-invisible-and-intentional
- https://screencraft.org/blog/anatomy-of-a-scene-how-to-make-action-sequences-matter/
conflicts_with: []
supersedes: []
---

# 拆片必须按动作密度决定拍摄覆盖而不是逐动作列清单

## 三类动作

`story_planner` 必须把增强后的动作分成三类：

1. `必拍动作`：改变剧情、人物目标、道具状态、关系或信息的动作。
2. `可压缩动作`：观众需要知道结果，但不需要看完整过程的动作。
3. `可省略动作`：删掉后不影响理解，只是生活化填充或重复表演。

## 必拍动作判断

满足任一条件即为必拍：

- 触发后续事件，例如闹钟被拍停、照片滑落、门打开。
- 完成片段目标，例如鞋袜穿好、书包被拎起、文件被递出。
- 改变人物关系，例如抗拒变配合、沉默变让步、压制变反击。
- 改变信息状态，例如看见照片、听到名字、发现手机。
- 是台词落点的身体反应，例如被一句话击中后的停顿或避开视线。

## 可压缩动作

以下动作通常只保留起点和结果：

- 走到某处、转身靠近、从桌上拿起普通物件。
- 重复整理、穿戴过程中的机械步骤。
- 没有阻碍的移动。
- 已经被上一镜解释清楚的手部延续。

## 可省略动作

以下动作通常不应进入镜头任务：

- 无信息的摸头发、整理衣角、看窗、低头。
- 同一情绪的重复身体反应。
- 不改变道具状态的手指移动。
- 不改变关系的随意喝水、抿嘴、眨眼。

## 拆片输出要求

每个片段必须输出：

```yaml
动作密度: 低/中/高
必拍动作:
  - 动作
  - 为什么必须拍
可压缩动作:
  - 动作
  - 压缩方式
可省略动作:
  - 动作
  - 省略原因
推荐节奏档位: 中速/紧凑/慢节奏
每5秒镜头数建议: 1.5-2 或 2-3
```

如果必拍动作超过当前片段时长能承载的镜头密度，必须拆成多个片段，而不是把镜头交给下游硬塞。
