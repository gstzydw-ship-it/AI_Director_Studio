---
rule_id: QC-RHYTHM-EMOTION-LEGIBILITY-003
title: 质检必须检查节奏密度、情绪可读性和动作覆盖价值
doc_type: rule_card
rule_type: quality
owner_agent: quality_inspector
agent_scope:
- quality_inspector
- director_showrunner
- rhythm_rewrite_director
- story_planner
- shot_director
- prompt_compiler
priority: P0
status: active
pipeline_stage: quality_inspection
runtime_retrieval: true
retrieval_key:
- qc-rhythm-emotion-legibility-003
- signals.pace
- signals.action_density
- signals.emotion
- risks.too_many_cuts
- risks.flat_emotion
- risks.dialogue_drop
- risks.undercovered_event
applies_when:
- 质检
- 节奏密度
- 情绪表达
- 动作覆盖
avoid_when:
- "当前只检查非叙事素材或静态参考图。"
failure_mode:
- "质检只看格式和连续性，不检查镜头是否服务情绪、故事和动作密度。"
output_contract: "质检必须按节奏矩阵、戏剧任务、动作覆盖和情绪可读性给通过/返修判断。"
example_good: "指出 6 秒 6 镜超过紧凑档，且安抚台词无听者反应，要求合并无信息短切。"
example_bad: "格式完整，所以通过。"
signals:
- pace
- action_density
- emotion
scene_types:
- any
events:
- cut
- action_peak
- reaction
risks:
- too_many_cuts
- flat_emotion
- dialogue_drop
- undercovered_event
applies_to:
- 质检
- 节奏
- 情绪
- 动作覆盖
source_files:
- knowledge/rules/rhythm_rewrite_director/RHYTHM-SHOT-DENSITY-MATRIX-003.md
- knowledge/rules/director_showrunner/SHOWRUNNER-SCENE-TASK-ENHANCEMENT-003.md
- knowledge/rules/shot_director_guard/GUARD-EMOTION-STORY-RHYTHM-PRIORITY-007.md
external_sources:
- https://www.backstage.com/magazine/article/film-rhythm-editing-guide-77147/
- https://hollywoodwritersgroup.com/quicksheets-scene-building-screenwriting/
- https://www.backstage.com/magazine/article/what-are-beats-in-acting-76101/
conflicts_with: []
supersedes: []
---

# 质检必须检查节奏密度、情绪可读性和动作覆盖价值

## 质检维度

`quality_inspector` 不能只看字段完整和连续性，还必须检查：

1. `戏剧任务`：片段是否清楚服务一个任务，片尾是否有变化。
2. `节奏密度`：每 5 秒镜头数是否落在节奏档位范围内。
3. `动作覆盖`：必拍动作是否看清；可省略动作是否被错误升成镜头。
4. `情绪可读`：人物目标、阻碍、策略变化和反应是否可见。
5. `台词落点`：台词是否完整，听者或说话者是否有可读落点。
6. `首尾继承`：首帧是否建立关系，尾帧是否可接下一段。

## 硬失败

以下情况必须 fail：

- 节奏档位写“紧凑”，但镜头密度超过矩阵上限且没有主观失控理由。
- 情绪转折没有反应时间或被无信息短切打断。
- 必拍动作缺失或关键道具凭空出现。
- 可省略动作占据独立镜头，导致台词、关系或尾帧被挤掉。
- 每个动作都拍，但片段任务反而不清楚。

## 返修建议格式

```yaml
节奏密度问题:
  当前: 每5秒4镜
  应为: 紧凑生活动作每5秒2-3镜
  修复: 合并无信息动作，保留关键动作短插入
情绪可读性问题:
  当前: 安抚台词后立刻切书包
  修复: 留0.4-0.8秒孩子反应或脚停止抗拒
动作覆盖问题:
  当前: 拍停闹钟未可见
  修复: 首帧关系锚定后给0.5-1.0秒闹钟动作插入
```
