---
rule_id: QC-PACING-SAFETY-CHECKLIST-001
title: 节奏与物理安全质检清单
doc_type: rule_card
rule_type: quality_control
agent_scope:
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/17_结果质检与回溯修正规则.md
  - knowledge/15_故事节奏控制规则.md
  - knowledge/24_戏剧微粒识别与节奏触发规则.md
conflicts_with: []
supersedes: []
applies_to:
  - 质检
  - 节奏拖沓
  - Hook
  - 对白忠实
  - 复杂动作
  - prompt合规
---

# 节奏与物理安全质检清单

## 必查项

`quality_inspector` 必须对最终片段执行以下检查：

- 对白完整性：所有 `assigned_dialogue` 或最终 prompt 中可见对白按时间顺序拼回后，必须与 `exact_dialogue_units` 一致。
- 首镜 Hook：承担 Hook 的片段，首镜超过 4 秒仍未释放高价值信息、关系压力、动作启动或明显情绪信号时，必须打回。
- 首 3 秒空转：若片段前 3 秒只有无意义走路、站桩、空镜或解释性铺垫，且没有必要空间建立任务，必须打回。
- 节奏拖沓：连续 3 个非空镜头都超过 6 秒时，必须要求重切或补反应/插入镜头。
- 高潮密度：高潮段 10 秒内超过 3 句短台词，且没有 Micro-Pause 或反应镜头承接时，必须打回。
- 反应窗口：高价值信息命中后，没有至少 1.5 秒受击、停顿或回味窗口时，必须打回。
- 单镜上限：单镜超过 8 秒时，必须是 `emotional_peak` 且画面动作、背景和运镜足够简单，否则打回。
- 复杂动作：同一镜头内出现两人以上高密度物理交互、长台词和大幅动作叠加时，必须打回。
- 约束污染：时间轴段落反复粘贴禁忌串，或禁忌与画面描述互相冲突时，必须要求 `prompt_compiler` 清洗。
- 钩子结尾：`cliffhanger` 命中后若继续释怀拉远、离场解释或情绪缓冲，必须打回。

## 返修方向

质检失败时，不要只写“节奏不好”。必须指出具体违反的规则，并给出可执行返修方向，例如：
- 缩首镜
- 补 Micro-Pause
- 增加受击窗口
- 去掉无意义位移
- 降低对白密度
- 把尾帧改回可续接的关系景
