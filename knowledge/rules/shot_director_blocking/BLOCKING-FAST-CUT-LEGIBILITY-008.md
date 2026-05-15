---
rule_id: BLOCKING-FAST-CUT-LEGIBILITY-008
title: 快切必须服从可读性和镜头时长预算
doc_type: rule_card
rule_type: blocking_rhythm
owner_agent: shot_director_blocking
agent_scope:
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: blocking
runtime_retrieval: true
retrieval_key:
- blocking-fast-cut-legibility-008
- signals.action_coverage
- signals.dialogue_coverage
- events.cut
- events.action_peak
- risks.too_many_cuts
- risks.dialogue_drop
- risks.spatial_jump
applies_when:
- 快切
- 6秒片段
- 动作密集
- 台词覆盖
avoid_when:
- "单一连续长镜已能清楚覆盖动作、台词和状态变化。"
failure_mode:
- "6 秒内塞入过多短切，关键动作、人物关系和台词落点被切碎。"
output_contract: "快切默认 1-3 秒/镜，低于 1 秒只给明确信息增量；6 秒叙事段优先 3-4 个可读镜头。"
example_good: "6 秒：0.8 秒闹钟特写、1.0 秒关系锚定、3.0 秒穿袜安抚长镜、1.2 秒书包关系收束。"
example_bad: "6 秒：6 个以上镜头，每个都换主体和景别，台词被压掉。"
signals:
- action_coverage
- dialogue_coverage
scene_types:
- action
- dialogue
- domestic_scene
events:
- cut
- action_peak
risks:
- too_many_cuts
- dialogue_drop
- spatial_jump
dialogue_types:
- visible_speaking
- rapid_exchange
applies_to:
- 快切节奏
- 子分镜时长
- 台词覆盖
source_files:
- knowledge/rules/prompt_compiler/PROMPT-CUT-BUDGET-001.md
- knowledge/rules/shot_director_blocking/BLOCKING-SUBSHOT-TRIGGER-007.md
- knowledge/rules/shot_director/SHOT-VERTICAL-RHYTHM-001.md
conflicts_with: []
supersedes: []
---

# 快切必须服从可读性和镜头时长预算

## 规则

快切不是“镜头越碎越紧凑”。`shot_director_blocking` 必须先保证动作、台词、同场关系和道具状态可读，再决定是否切入。

执行基准：

- 常规快切：单镜约 1-3 秒。
- 极短切：低于 1 秒只允许用于明确的信息增量，例如闹钟被拍停、手机入袋完成、照片边缘露出。
- 6 秒叙事片段：优先 3-4 个可读镜头；若超过 4 个镜头，必须有两个以上镜头共享同一关系景或连续机位，避免空间重置。
- 台词所在镜头不得被无信息局部特写切断；一句台词至少要有稳定可见的说话者口型或明确画外声承接。

## 子分镜触发

允许短子分镜的条件：

- 关键动作必须看清，如拍停闹钟、抓住提带、照片滑落。
- 该动作改变后续状态。
- 父镜头已经建立人物和空间关系。
- 子分镜后必须回到可继承关系或明确尾帧。

## 禁止

- 禁止为了“紧凑”把同一动作拆成多个无信息局部镜。
- 禁止连续两个低于 1 秒的镜头都更换主体、景别和空间中心。
- 禁止把喝咖啡、看一眼、手指移动等低信息动作升成独立硬切，除非它改变剧情状态。
- 禁止让台词在切镜中丢失或只剩无口型画外声。
