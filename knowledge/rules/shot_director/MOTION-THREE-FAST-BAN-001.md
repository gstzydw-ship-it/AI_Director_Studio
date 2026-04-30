---
rule_id: MOTION-THREE-FAST-BAN-001
title: 禁止三快叠加
doc_type: rule_card
rule_type: camera_movement
agent_scope:
  - shot_director
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
applies_to:
  - 快动作
  - 快运镜
  - 复杂环境
---

# 禁止三快叠加

## 规则

如果必须快，只允许以下三者之一快：

- 主体动作快。
- 镜头运动快。
- 环境复杂。

三者不得叠加。

## 高危组合

- 快速奔跑 + 快速推拉镜 + 杂乱人群。
- 快速回头 + 快速环绕 + 闪烁霓虹背景。
- 剧烈打斗 + 快速横移 + 大量前景遮挡。

默认优先使用慢推、稳定平移、固定机位、轻跟随、受控切近。

