---
rule_id: RHYTHM-SHOT-DENSITY-MATRIX-003
title: 每五秒镜头密度与镜头时长矩阵
doc_type: rule_card
rule_type: rhythm
owner_agent: rhythm_rewrite_director
agent_scope:
- rhythm_rewrite_director
- story_planner
- shot_director
- shot_director_layout
- shot_director_blocking
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: rhythm_handoff
runtime_retrieval: true
retrieval_key:
- rhythm-shot-density-matrix-003
- signals.pace
- signals.time_budget
- signals.action_density
- events.cut
- events.action_peak
- risks.too_many_cuts
- risks.dialogue_drop
applies_when:
- 节奏判断
- 每5秒镜头数
- 镜头时长
- 动作密度
avoid_when:
- "用户明确指定单镜到底或固定镜头实验风格。"
failure_mode:
- "只写节奏紧凑，但没有给镜头密度、镜头时长和动作密度的施工边界。"
output_contract: "节奏总控必须给每5秒镜头密度档位、目标ASL、单镜时长范围和例外条件。"
example_good: "紧凑生活动作：每5秒2-3镜，单镜1.0-2.5秒，关键插入0.5-1.0秒，关系镜不少于1.5秒。"
example_bad: "节奏要快，镜头多切一点。"
signals:
- pace
- time_budget
- action_density
scene_types:
- action
- dialogue
- emotional_turning_point
- domestic_scene
events:
- cut
- action_peak
risks:
- too_many_cuts
- dialogue_drop
dialogue_types:
- rapid_exchange
- visible_speaking
applies_to:
- 节奏总控
- 拆片
- 镜头密度
- 平均镜头时长
source_files:
- knowledge/rules/prompt_compiler/PROMPT-CUT-BUDGET-001.md
- knowledge/rules/shot_director_blocking/BLOCKING-FAST-CUT-LEGIBILITY-008.md
- knowledge/reports/RHYTHM_CUTTING_TEMPO_RESEARCH_2026-05-13.md
external_sources:
- https://www.toolsforfilm.com/glossary/fast-cutting
- https://edurev.in/t/478056/class-7-editing-short-film-basic-cuts-transitions
- https://benly.ai/learn/ad-creative/ad-pacing-cuts-per-second
- https://www.backstage.com/magazine/article/film-rhythm-editing-guide-77147/
- https://cursa.app/en/page/pacing-and-structure-making-cuts-feel-invisible-and-intentional
conflicts_with: []
supersedes: []
---

# 每五秒镜头密度与镜头时长矩阵

## 核心原则

节奏不是“切得多”。节奏由以下因素共同决定：

- 镜头时长。
- 单镜内部运动量。
- 每秒新增信息量。
- 台词和声音节拍。
- 情绪是否需要观众消化。

`rhythm_rewrite_director` 必须把“快/慢/紧凑/压迫/留白”翻译成可执行的镜头密度边界。

## 每 5 秒镜头密度矩阵

| 节奏档位 | 适用戏剧任务 | 每 5 秒建议镜头数 | 目标 ASL | 单镜常规范围 | 允许极短插入 |
|---|---|---:|---:|---:|---:|
| 慢节奏/情绪消化 | 反应、犹豫、压抑、亲密、等待 | 0.5-1 镜 | 5-8 秒 | 4-10 秒 | 通常不用 |
| 中慢/关系观察 | 对话、试探、照顾、关系变化 | 1-1.5 镜 | 3.5-5 秒 | 2.5-6 秒 | 0-1 个，0.7-1.2 秒 |
| 中速/叙事推进 | 信息交代、普通行动、轻冲突 | 1.5-2 镜 | 2.5-3.5 秒 | 1.8-4 秒 | 0-1 个，0.6-1.0 秒 |
| 紧凑/生活动作压力 | 赶时间、收拾、打断、短促互动 | 2-3 镜 | 1.6-2.5 秒 | 1.0-3 秒 | 1 个，0.5-1.0 秒 |
| 高压/动作峰值 | 追逐、抢夺、撞击、爆点 | 3-4 镜 | 1.0-1.7 秒 | 0.8-2 秒 | 1-2 个，0.4-0.8 秒 |
| 混乱/主观失控 | 恐慌、幻觉、强主观碎片 | 4+ 镜 | <1.2 秒 | 0.4-1.5 秒 | 必须用户或剧本明确需要 |

默认不得超过“高压/动作峰值”。只有剧本任务明确是主观失控、梦境、恐慌或蒙太奇，才允许进入“混乱”档。

## 动作密度和镜头时长绑定

每个镜头的时长要和内部动作密度绑定：

- `高内部运动`：人物或摄影机一直在动，可以少切；1 个 2 秒跟随镜头往往比 3 个碎切更紧凑。
- `低内部运动`：人物静止但情绪在变化，要延长到 4-8 秒，让观众读表情、停顿和视线。
- `高信息密度`：新人物、新道具、新地点、新台词、新动作不能同时堆在同一秒里；如果必须出现，优先拆段，不是强行碎切。
- `台词承载`：一句完整台词所在镜头通常不少于 1.5 秒；情绪台词或关系转折通常 2.5 秒以上。

## 例外条件

允许短于矩阵下限的镜头，必须满足至少一项：

- 动作瞬间会改变状态，例如拍停闹钟、手机入袋、照片滑落、门锁响。
- 它是父关系镜下的插入镜，前后关系已经清楚。
- 它承接声音落点，且下一个镜头能继承空间关系。

禁止短切的情况：

- 同场人物还没建立位置关系。
- 关键道具还没有起始位置。
- 台词还没有说完或口型不可见。
- 上一镜和下一镜同时更换主体、景别、空间中心。

## 输出要求

节奏总控交给下游时必须写：

```yaml
节奏档位: 紧凑/生活动作压力
每5秒镜头数: 2-3
目标ASL: 1.6-2.5秒
单镜时长范围: 1.0-3.0秒
允许短插入: 1个，0.5-1.0秒，必须是状态改变动作
必须留白: 安抚或反应台词后至少0.4秒
应省略动作: 无信息走位、重复整理、低价值手部动作
```
