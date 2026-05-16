---
rule_id: BLOCKING-STATE-DELTA-005
title: 动作调度必须写状态推进和切点
doc_type: rule_card
rule_type: state_delta_cutpoint
owner_agent: shot_director_blocking
agent_scope:
- shot_director_blocking
- quality_inspector
priority: P0
status: active
pipeline_stage: blocking
runtime_retrieval: true
retrieval_key:
- blocking-state-delta-005
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- signals.reference_binding
- events.collision
- events.cut
- events.reference_binding
- risks.reference_misuse
- scene_types.dialogue
- scene_types.action
applies_when:
- state_delta
- cut_point
- sub_shots
avoid_when:
- "当前只生成 layout 骨架，不补动作状态"
- "guard 阶段只检查并最小补齐缺失字段"
failure_mode:
- "主镜头没有 state_delta，子分镜没有 cut_point，下游误造状态变化。"
output_contract: "每个 main_shot 补 state_delta；每个 sub_shot 补 cut_point；状态不变也写保持。"
example_good: "state_delta=两人距离保持不变；cut_point=台词落点后半拍。"
example_bad: "state_delta=情绪更强；cut_point=合适的时候切。"
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
- reference_binding
scene_types:
- dialogue
- action
events:
- collision
- cut
- reference_binding
risks:
- reference_misuse
applies_to:
- state_delta
- cut_point
- sub_shots
- dialogue_coverage
source_files:
- knowledge/26_动作调度与受击覆盖规则.md
- knowledge/03_镜头切换与推进规则.md
- knowledge/06_连续性与安全规则.md
- knowledge/20_镜头库与机位库.md
conflicts_with: []
supersedes: []
---

# 动作调度必须写状态推进和切点

## 规则

二号动作调度导演必须把一号的覆盖蓝图变成可执行状态链。每个主镜头至少补出 `state_delta`；每个子分镜必须补出 `cut_point`。

## state_delta

说明当前镜头推进或保持了什么状态：

- 手从抓扶到松开
- 门从将合未合到完全关闭
- 视线从回避到撞上
- 人群从静止到四散
- 位置关系保持不变

即使没有变化，也写“保持”。这样下游不会误造变化。

## cut_point

子分镜切点必须绑定具体时刻：

- 台词落点后半拍
- 抬头撞上视线时
- 手指刚离开布料前
- 动作完成 50%-70% 时
- 群体散开的第一步

不要用抽象词代替切点。
