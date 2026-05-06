---
rule_id: SCENE-CONSISTENCY-LOCK-001
title: 场景一致性锁写入 state_contract
doc_type: rule_card
rule_type: scene_analysis
agent_scope:
- scene_analyst
- story_planner
- shot_director
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- scene-consistency-lock-001
- signals.continuity_lock
- signals.reference_binding
- events.reference_binding
- risks.axis_confusion
- risks.reference_misuse
applies_when:
- 服装
- 道具
- 光线
avoid_when: []
signals:
- continuity_lock
- reference_binding
events:
- reference_binding
risks:
- axis_confusion
- reference_misuse
applies_to:
- 服装
- 道具
- 光线
- 时段
- 轴线
- 状态快照
source_files:
- knowledge/11_场景分析输入卡与导演意图提取.md
- knowledge/06_连续性与安全规则.md
- knowledge/rules/shared/CONT-STATE-CONTRACT-001.md
conflicts_with: []
supersedes: []
---

# 场景一致性锁写入 state_contract

## 规则

`scene_analyst` 在给出每个场景的输入卡时，必须同时产出一份 `scene_lock`，用于下游 `state_contract.entry_state` 的初始化。`scene_lock` 至少锁定以下 6 组字段：

- `wardrobe`：每个出镜角色的服装状态（颜色 / 关键件 / 是否沾染 / 是否凌乱）。
- `props`：关键道具位置 + 初始状态（门开 / 关、杯满 / 空、刀握 / 放）。
- `lighting`：光线基底（暖黄 / 冷蓝 / 中性 / 逆光 / …）。
- `time_of_day`：时段（晨 / 昼 / 黄昏 / 夜 / 不明）+ 若干关键补光源。
- `axis`：当前场面轴线定义（以哪两个锚点连线为 180° 线）。
- `gaze_network`：角色之间的"看/被看"关系图（subject_id → target_id）。

## 禁止项

- 禁止把 `scene_lock` 留空或只给一两个字段——哪怕是 `null`，也要显式列齐 6 组。
- 禁止在同一场景内输出互相矛盾的锁值（例如 `time_of_day=夜` 与 `lighting=强烈正午日光`）。
- 禁止在没有参考图或剧本描述支撑时，凭空给出服装 / 道具细节——必须标 `inferred=true` 并在 `scene_notes` 说明推理来源。

## 正确写法

```yaml
scene_lock:
  wardrobe:
    SUBJ_YANG: { outfit: 白色衬衣, state: 领口微敞, stain: none }
    SUBJ_BOSS: { outfit: 黑色西装, state: 平整, stain: none }
  props:
    办公桌文件夹: { position: 桌中央, state: 合上 }
    办公室门: { state: 闭合 }
  lighting: 冷蓝办公室顶光
  time_of_day: 夜
  axis: 办公桌两侧（SUBJ_YANG 在桌左，SUBJ_BOSS 在桌右）
  gaze_network:
    - { from: SUBJ_BOSS, to: SUBJ_YANG }
    - { from: SUBJ_YANG, to: 桌上文件夹 }
```

## Agent 执行

- `scene_analyst` 写入 `scene_lock`。
- `story_planner` 把 `scene_lock` 复制为片段 `state_contract.entry_state`，并根据戏剧推进变更为 `exit_state`。
- `shot_director` 不得反向修改 `scene_lock`，只能读取。
- `quality_inspector` 对每个片段检查 `scene_lock` 字段完整性，任何字段缺失 / 矛盾都按 P0 阻断处理。
