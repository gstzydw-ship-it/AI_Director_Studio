---
rule_id: GUARD-FIRST-FRAME-PROP-CUT-BUDGET-006
title: 守门必须拦截首帧缺锚和过碎快切
doc_type: rule_card
rule_type: continuity_guard
owner_agent: shot_director_guard
agent_scope:
- shot_director_guard
- quality_inspector
- prompt_compiler
priority: P0
status: active
pipeline_stage: guard
runtime_retrieval: true
retrieval_key:
- guard-first-frame-prop-cut-budget-006
- signals.continuity_lock
- signals.action_coverage
- events.cut
- events.object_handoff
- risks.spatial_jump
- risks.missing_required_prop
- risks.too_many_cuts
applies_when:
- 首帧缺锚
- 关键道具缺失
- 快切过碎
avoid_when:
- "首帧、道具、人物关系和切镜预算均已清楚满足。"
failure_mode:
- "最终 YAML 允许人物突然出现、关键道具凭空出现，或 6 秒片段被切成不可读碎镜。"
output_contract: "guard 必须最小修复：补首帧锚点、补关键道具可见性、降级无信息短切。"
example_good: "把首镜改为双人关系景含闹钟和书包；保留一次闹钟特写，删除无信息喝咖啡切镜。"
example_bad: "保留 6 秒 6 镜头，且首镜只有单人、关键道具突然出现。"
signals:
- continuity_lock
- action_coverage
scene_types:
- interior
- action
- dialogue
events:
- cut
- object_handoff
risks:
- spatial_jump
- missing_required_prop
- too_many_cuts
applies_to:
- 规则守门
- 首帧关系锚点
- 切镜预算
source_files:
- knowledge/rules/shot_director_layout/LAYOUT-FIRST-FRAME-SPATIAL-ANCHOR-006.md
- knowledge/rules/shot_director_blocking/BLOCKING-FAST-CUT-LEGIBILITY-008.md
- knowledge/rules/prompt_compiler/PROMPT-CUT-BUDGET-001.md
conflicts_with: []
supersedes: []
---

# 守门必须拦截首帧缺锚和过碎快切

## 硬失败项

`shot_director_guard` 看到以下情况必须修复或阻断：

- 首镜没有建立当前片段必须同场的人物关系。
- 剧本关键道具没有起始位置，却在动作中突然被使用。
- 单人镜或局部镜导致另一位同场人物无解释消失。
- 6 秒片段超过 4 个镜头，且多个镜头低于 1 秒并更换主体。
- 台词所在镜头被无信息短切打断，导致说话者不可见或画外声无承接。

## 最小修复方式

- 把首镜改成关系景或半身关系景，包含同场人物、关键道具和固定物体。
- 把关键动作特写挂靠到关系景之后，并限制在 0.5-1.0 秒。
- 删除或并回无信息短切，例如无剧情状态变化的喝咖啡、看一眼、衣角移动。
- 将尾帧恢复成可继承关系：人物状态、关键道具状态和同场空间都可读。

## 禁止

- 禁止保留“看起来节奏紧凑但空间不可读”的镜头表。
- 禁止把 `prompt_compiler` 当成修复首帧和切镜预算的最后一关；守门阶段必须先修。
