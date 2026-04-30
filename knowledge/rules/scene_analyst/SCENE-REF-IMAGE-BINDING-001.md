---
rule_id: SCENE-REF-IMAGE-BINDING-001
title: 参考图到角色空间尾帧强绑定
doc_type: rule_card
rule_type: scene_analysis
agent_scope:
  - scene_analyst
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/11_场景分析输入卡与导演意图提取.md
  - knowledge/rules/prompt_compiler/REF-TAILFRAME-PRIORITY-001.md
  - knowledge/rules/prompt_compiler/REFERENCE-ROLE-STRICT-001.md
conflicts_with: []
supersedes: []
applies_to:
  - 参考图绑定
  - 主角身份
  - 对手身份
  - 空间关系图
  - 上一镜尾帧
---

# 参考图到角色/空间/尾帧强绑定

## 规则

`scene_analyst` 对每一张输入的参考图，必须显式绑定到以下四类角色之一，并在输入卡里输出 `reference_bindings[]`：

- `role=hero_id` + 对应 `subject_id`
- `role=rival_id` + 对应 `subject_id`
- `role=position_map` + 对应 `scene_id`
- `role=space_map` + 对应 `scene_id`
- `role=prev_tailframe` + 对应 `shot_id` 或 `segment_id`

每条绑定必须携带：`image_id`、`role`、`target_id`、`first_appearance_segment`、`scope`（`global` / `segment:xx`）。

## 禁止项

- 禁止仅标注"用于参考"而不绑定到具体 `subject_id` / `scene_id`。
- 禁止同一张图被绑定为多种互斥 `role`（例如同时标注 `hero_id` 又标注 `rival_id`）。
- 禁止把 `prev_tailframe` 图绑到非相邻片段——必须指向紧邻的上一段。
- 禁止在 `scene_analyst` 阶段对参考图做画面改写或风格重述——那是 `prompt_compiler` 的职责。

## 正确写法

```yaml
reference_bindings:
  - image_id: ref_01
    role: hero_id
    target_id: SUBJ_YANG
    first_appearance_segment: seg_01
    scope: global
  - image_id: ref_02
    role: rival_id
    target_id: SUBJ_BOSS
    first_appearance_segment: seg_01
    scope: global
  - image_id: ref_03
    role: prev_tailframe
    target_id: shot_05_tail
    first_appearance_segment: seg_02
    scope: segment:seg_02
```

## Agent 执行

- `scene_analyst` 产出 `reference_bindings[]`。
- `prompt_compiler` 在调用 `@image` 时必须按 `target_id` 反查，首次出现时直接附带绑定图。
- `quality_inspector` 检查：每个 `subject_id` 至少有一张绑定图或显式标注 `no_reference_image=true`；每张图至少被某一个片段引用，否则报 `unused_reference_image` 警告。
