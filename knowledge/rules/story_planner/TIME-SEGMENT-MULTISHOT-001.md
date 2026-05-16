---
rule_id: TIME-SEGMENT-MULTISHOT-001
title: 15秒片段是导演片段不是单分镜
doc_type: rule_card
rule_type: segment_planning
owner_agent: story_planner
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: segment_planning
runtime_retrieval: true
retrieval_key:
- time-segment-multishot-001
- signals.dialogue_coverage
- signals.action_coverage
- events.reaction
- events.cut
- dialogue_types.reaction_beat
- scene_types.action
applies_when:
- 15秒片段
- 主分镜
- 子分镜
avoid_when:
- "用户明确锁定单镜，或片段短到不支持多镜头。"
failure_mode:
- "把 15 秒误当单一长镜头。"
- "主分镜和子分镜共用同一时间标记。"
output_contract: "输出单层时间轴，显式区分主分镜、子分镜和独立时段。"
example_good: "0-3秒主分镜，3-5秒子分镜，5-8秒主分镜。"
example_bad: "外层动作单元下再嵌套子时间轴。"
signals:
- dialogue_coverage
- action_coverage
scene_types:
- action
events:
- reaction
- cut
dialogue_types:
- reaction_beat
applies_to:
- 15秒片段
- 主分镜
- 子分镜
- 多镜头变化
- 同一时间窗
source_files:
- knowledge/00_知识库优先级与冲突裁决规则.md
- knowledge/05_剧本拆分与15秒片段规划规则.md
- knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes: []
---

# 15秒片段是导演片段不是单分镜

## 规则

15 秒是导演编译单位，不是单分镜层，也不是机械平均切割器。

一个 10-15 秒导演片段内可以规划 3-4 个连续镜头组。每个镜头组可以围绕同一动作锚点组织主分镜、子分镜、反应镜头、局部特写或 cutaway。

注意：这是 15 秒导演片段的多分镜能力，必须保留。最终 prompt 使用单层时间轴顺序排列主分镜和子分镜，例如 `0-3秒 主分镜1`、`3-5秒 子分镜1.1`、`5-8秒 主分镜2`。不要写外层动作单元和内层子时间轴。

## 禁止

- 把可在同段完成的镜头变化拆成一堆 5-6 秒小片段。
- 把 15 秒全部写成单调跟随镜头。
- 时间轴平均切成 `0-3 / 3-6 / 6-9 / 9-12`。
- 把多个机位变化塞进同一个未分层的连续镜头段，导致模型不知道哪里是主分镜、哪里是子分镜。
- 主分镜和子分镜共享同一个时间标记。
- 使用外层动作单元 + 内层子时间轴，导致结构过碎。
- 相同景别直接相接，例如特写接特写、半身中景接半身中景。

裁决标准是单层时间轴：导演片段可以多分镜、多机位、多景别；换机位、换景别或插入局部时，必须显式标成子分镜并分配独立时间段，避免相同景别直切。
