---
rule_id: RHYTHM-SIGNAL-TAXONOMY-001
title: 戏剧微粒识别与 Hook 权重判定
doc_type: rule_card
rule_type: rhythm_signal_identification
agent_scope:
- story_planner
- quality_inspector
- shot_director
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- rhythm-signal-taxonomy-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.reaction
- risks.script_invention_risk
- risks.blood_avoidance
- dialogue_types.long_dialogue_compression
- dialogue_types.reaction_beat
- scene_types.dialogue
- scene_types.action
- scene_types.suspense
applies_when:
- 权力反转
- 冲突升级
- 悬念揭晓
avoid_when: []
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- suspense
events:
- collision
- reaction
risks:
- script_invention_risk
- blood_avoidance
dialogue_types:
- long_dialogue_compression
- reaction_beat
applies_to:
- 权力反转
- 冲突升级
- 悬念揭晓
- 误解错位
- 情绪极点
- Cliffhanger
source_files:
- knowledge/24_戏剧微粒识别与节奏触发规则.md
- knowledge/15_故事节奏控制规则.md
- knowledge/05_剧本拆分与15秒片段规划规则.md
conflicts_with: []
supersedes: []
---

# 戏剧微粒识别与 Hook 权重判定

## 规则

`story_planner` 必须先识别每个片段的主戏剧微粒，再决定片段边界、`boundary_reason` 和 `reaction_need`。  
戏剧微粒只服务节奏与拆片，不提前设计具体镜头。

主信号与推荐 Hook 权重：
- `power_reversal` -> `1.0`
- `cliffhanger` -> `1.0`
- `conflict_escalation` -> `0.9`
- `emotional_peak` -> `0.9`
- `suspense_reveal` -> `0.8`
- `misunderstanding` -> `0.7`

每个片段最多保留：
- 1 个主信号
- 1 个次级信号

若结构支持，优先显式输出：
- `rhythm_function`
- `hook_weight`
- `script_basis`
- `boundary_reason`
- `reaction_need`

若结构暂不支持新增字段，也必须在片段说明里清楚体现这些判断。

## 执行要求

- `story_planner` 只负责识别戏剧微粒、Hook 权重、片段边界、受击承接层级和节拍轻重，不负责改写剧本。
- 如果检索到含“改写、增补动作、氛围具象化”的节奏规则，这些权限只属于 `rhythm_rewrite_director`；`story_planner` 只能把已经写进当前剧本的原文行纳入拆片。
- `source_script_events` 必须逐条引用当前输入剧本中的原文，不得概括、改写、合并或补写。
- `beat_design` 和 `reaction_plan` 只能写结构判断，例如“片段内承接”“独立主分镜承接”“预留停顿”“在台词后收束”；不得新增具体动作、道具、龙套反应或人物调度。
- `power_reversal`：反转命中后必须预留受击或黄金停顿空间。
- `conflict_escalation`：片段应更短、更硬，去掉无意义位移。
- `suspense_reveal`：优先安排“发现前停顿 -> 揭示 -> 反应”。
- `misunderstanding`：优先保留听者反应，不要先替角色解释清楚。
- `emotional_peak`：允许更长回味，但动作和空间必须简化。
- `cliffhanger`：`boundary_reason` 必须明确说明为什么在这里阻断。

## 禁止

- 不得把低权重过场强行标成 `power_reversal` 或 `cliffhanger`。
- 不得在 `story_planner` 阶段写“特写、仰拍、Crash Zoom、黑屏”等镜头执行方案。
- 不得改写、润色、压缩或重排原剧本对白。
- 不得因为命中了高权重信号，就补写剧本外人物、事件或道具。
- 不得把“节奏需要更紧/更有气口”落成新的具体动作；如果当前剧本没有对应动作，只能在 `reaction_plan` 中标注承接层级，等待下游镜头执行或上游改写层提供原文动作。
