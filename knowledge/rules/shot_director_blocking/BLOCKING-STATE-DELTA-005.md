---
rule_id: BLOCKING-STATE-DELTA-005
title: 动作调度必须写状态推进和切点
doc_type: rule_card
rule_type: state_delta_cutpoint
agent_scope:
  - shot_director_blocking
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/26_动作调度与受击覆盖规则.md
  - knowledge/03_镜头切换与推进规则.md
  - knowledge/06_连续性与安全规则.md
  - knowledge/20_镜头库与机位库.md
conflicts_with: []
supersedes: []
applies_to:
  - state_delta
  - cut_point
  - sub_shots
  - dialogue_coverage
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
