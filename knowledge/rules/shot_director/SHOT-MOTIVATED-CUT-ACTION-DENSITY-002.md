---
rule_id: SHOT-MOTIVATED-CUT-ACTION-DENSITY-002
title: 镜头导演按动作密度和信息增量决定切不切
doc_type: rule_card
rule_type: shot_language
owner_agent: shot_director
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: shot_director
runtime_retrieval: true
retrieval_key:
- shot-motivated-cut-action-density-002
- signals.action_coverage
- signals.pace
- events.cut
- events.action_peak
- risks.too_many_cuts
- risks.spatial_jump
applies_when:
- 镜头设计
- 动作密度
- 切镜理由
- 信息增量
avoid_when:
- "实验性碎片蒙太奇由用户明确指定，且允许破坏连续性。"
failure_mode:
- "每个动作都开一个镜头，导致空间和情绪不可读；或所有动作都塞进一个镜头导致关键动作看不清。"
output_contract: "每个切镜必须有信息增量、动作阶段变化、台词落点或情绪转折；否则并回父镜头。"
example_good: "拍闹钟是状态改变，给短插入；转身去沙发只是过渡，并入关系镜。"
example_bad: "伸手、看一眼、放下杯、整理袖口都各开一个镜头。"
signals:
- action_coverage
- pace
scene_types:
- action
- dialogue
- emotional_turning_point
events:
- cut
- action_peak
risks:
- too_many_cuts
- spatial_jump
applies_to:
- 镜头导演
- 切镜动机
- 动作覆盖
source_files:
- knowledge/rules/rhythm_rewrite_director/RHYTHM-SHOT-DENSITY-MATRIX-003.md
- knowledge/rules/story_planner/TIME-ACTION-DENSITY-COVERAGE-004.md
- knowledge/rules/shot_director_blocking/BLOCKING-FAST-CUT-LEGIBILITY-008.md
external_sources:
- https://www.premiumbeat.com/blog/cutting-on-the-blink-editing-tips-from-walter-murch/
- https://cursa.app/en/page/pacing-and-structure-making-cuts-feel-invisible-and-intentional
- https://www.backstage.com/magazine/article/film-rhythm-editing-guide-77147/
conflicts_with: []
supersedes: []
---

# 镜头导演按动作密度和信息增量决定切不切

## 切镜动机

`shot_director` 设计镜头时，必须给每个切镜一个明确动机。允许切镜的动机：

- `信息增量`：观众看到新信息、新道具、新表情反应或新关系。
- `状态改变`：道具、人物姿态、位置关系或目标发生变化。
- `动作阶段`：动作从准备、执行、完成、反应进入新阶段。
- `台词落点`：一句话需要落在说话者、听者或被影响的道具上。
- `情绪转折`：人物策略、态度、目标或关系发生变化。
- `空间复位`：局部镜后需要回到关系景，让下一段可继承。

不允许的切镜动机：

- 更有电影感。
- 换个角度好看。
- 每个动作都要看见。
- 模型可能不懂所以多写几个镜头。

## 动作密度决策

根据动作密度选择镜头策略：

- `高动作密度 + 高内部运动`：优先关系跟随镜、侧面关系景、稳定运动镜；少切但让镜内动作快。
- `高动作密度 + 关键状态变化`：只给状态改变点短插入，例如拍停、抓住、滑落、落桌。
- `低动作密度 + 高情绪密度`：延长镜头，保留呼吸、停顿、视线和反应，不要用碎切制造假节奏。
- `台词密集`：先保证台词落点和口型/听者反应，再考虑插入动作。

## 镜头数量自检

输出镜头表前必须自检：

1. 删除任意一个镜头，剧情是否仍完整？如果是，删掉或并回。
2. 这个镜头是否改变观众理解？如果否，删掉或并回。
3. 这个镜头是否让同场人物或道具关系更清楚？如果否，删掉或并回。
4. 这个镜头是否打断台词或情绪？如果是，延长父镜头或移到台词后。

## 片段时长自适应

镜头数量按 `RHYTHM-SHOT-DENSITY-MATRIX-003` 的每 5 秒密度计算，不按固定 6 秒模板。任何时长都先算：

```text
建议镜头数 = 片段秒数 / 5 * 当前节奏档位每5秒镜头数
```

然后按必拍动作数量做微调。必拍动作超过建议镜头数时，优先合并同空间同目标动作；仍超出则要求拆片。
