---
rule_id: MOTION-THREE-FAST-BAN-001
title: 禁止三快叠加
doc_type: rule_card
rule_type: camera_movement
owner_agent: shot_director
agent_scope:
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: generation_stability_guard
runtime_retrieval: true
retrieval_key:
- motion-three-fast-ban-001
- signals.action_coverage
- scene_types.action
applies_when:
- 快动作
- 快运镜
- 复杂环境
avoid_when:
- "slow_scene"
- "only_one_fast_factor_present"
failure_mode:
- "fast_action_fast_camera_complex_environment_stack"
output_contract: "Allow only one fast factor among subject, camera, and environment."
example_good: "快速奔跑配固定机位和简洁背景。"
example_bad: "快速奔跑加快速推拉镜加杂乱人群。"
signals:
- action_coverage
scene_types:
- action
applies_to:
- 快动作
- 快运镜
- 复杂环境
source_files:
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
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

