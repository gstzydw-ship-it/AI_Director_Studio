---
rule_id: LAYOUT-SHOTID-STABILITY-001
title: 主分镜骨架必须先锁定稳定 shot_id
doc_type: rule_card
rule_type: shot_layout_identity
owner_agent: shot_director_layout
agent_scope:
- shot_director_layout
- quality_inspector
priority: P0
status: active
pipeline_stage: layout
runtime_retrieval: true
retrieval_key:
- layout-shotid-stability-001
- signals.action_coverage
- scene_types.action
applies_when:
- shot_id
- main_shots
- 下游交接
avoid_when:
- "当前只是读取或审查既有 shot_id，不生成新的 main_shots"
- "guard 阶段正在最小范围修复真实重复编号"
failure_mode:
- "shot_id 跳号、改名或为局部重音临时占号，导致 blocking 无法挂接。"
output_contract: "每个 main_shot 必须有稳定 shot_id；同一 fragment 内顺序递增。"
example_good: "F05-S01、F05-S02、F05-S03 顺序稳定，下游子分镜可挂 parent_shot_id=F05-S02。"
example_bad: "第一次叫 F05-S01，修改后改成 F05-A，并插入 F05-S01b。"
signals:
- action_coverage
scene_types:
- action
applies_to:
- shot_id
- main_shots
- 下游交接
source_files:
- knowledge/25_镜头摆位主分镜骨架规则.md
- knowledge/21_镜头调用规则与多机位模板.md
conflicts_with: []
supersedes: []
---

# 主分镜骨架必须先锁定稳定 shot_id

## 规则

镜头摆位阶段输出的每个 `main_shot` 都必须先给出稳定的 `shot_id`。

这个 `shot_id` 是给后续动作调度导演和规则守门导演接力用的，所以要求：

- 同一片段内按顺序递增
- 不要随意跳号
- 不要今天叫 `F05-S01`，下一次又改成 `F05-A`
- 不要为了补细节临时重排全部主镜头编号

## 禁止

- 把还没确定的局部重音也占掉主镜头编号
- 用模糊编号让下游无法挂接 `parent_shot_id`
- 为了美观改名，破坏后续 agent 的稳定输入
