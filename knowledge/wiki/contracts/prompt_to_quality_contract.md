---
title: Prompt To Quality Contract
doc_type: contract
agent_scope:
  - prompt_compiler
  - quality_inspector
status: active
runtime_retrieval: true
updated: 2026-05-10
---

# Prompt to Quality Contract

## 目的

本合同定义 `prompt_compiler` 交给 `quality_inspector` 的质检输入。质检层要判断当前片段是否可生成、是否忠实、是否连续、是否满足输出结构；发现硬伤时必须给出可执行返修方向。

## 输入

`prompt_compiler` 至少应提交：

- 当前片段最终 prompt。
- `segment_id`、`shot_id`、单层时间轴。
- `source_script_events`、`exact_dialogue_units`、`assigned_dialogue`。
- `active_cast`、`offscreen_cast`、`state_contract`。
- `scene_lock`：服装、道具、光线、时段、轴线、视线网络。
- `reference_bindings` 与实际 prompt 中使用的 `@image` 列表。
- `first_frame_lock`、`tailframe_lock`、像素锚点描述。
- `negative_constraints`：字幕/屏幕文字、无戏份人物、错误状态、参考图误用等。
- `compiler_self_check`：当前片段范围、轴线、对白、参考图、状态继承的自检结果。

## 输出

`quality_inspector` 应输出：

- `status`: `pass` / `fail` / `needs_repair`。
- `failed_rule_id[]`：命中的规则 ID 或知识文件名。
- `evidence[]`：引用 prompt 或输入中的具体问题片段。
- `severity`：P0/P1/P2 或 hard/style。
- `required_repair[]`：可执行返修动作。
- `pacing_checks`：首镜 Hook、首 3 秒空转、单镜上限、反应窗口、节奏拖沓。
- `safety_checks`：物理安全、隐私/亲密误读、碰撞浪漫化、复杂动作可生成性。
- `continuity_checks`：active/offscreen、门/道具单向变化、轴线、尾帧首帧一致。
- `schema_checks`：必填字段、时间轴、参考图职责、负约束。

## 必须继承的状态

质检不得只看最终文字，还必须回看：

- 上游 `source_script_events` 是否被 prompt 忠实继承。
- `exact_dialogue_units` 拼回后是否与最终可见对白一致。
- `state_contract.entry_state` 和 `exit_state` 是否在首尾帧落实。
- `object_state_transitions` 是否保持单向。
- `active_cast` 是否完全覆盖当前可见人物。
- `offscreen_cast` 是否没有被尾帧、参考图或背景描述复活。
- `scene_lock.axis` 是否与 prompt 的机位侧一致。
- `reference_bindings` 是否按职责使用，没有互相污染。

## 禁止事项

- 禁止把 hard 规则违反标为 pass。
- 禁止用“整体更紧凑”“更有电影感”替代具体返修指令。
- 禁止把风格偏好当作硬失败。
- 禁止为了审美重写整个 prompt 或镜头方案。
- 禁止忽略缺失 `active_cast / offscreen_cast / state_contract` 的片段。
- 禁止在返修建议中新增剧本外动作、人物、道具、台词或空间。
- 禁止质检失败后仍把片段标记为完成。

## 最小返修原则

质检失败时只要求最小可执行修复：

- `hard fail`：必须阻断，返回 `failed_rule_id`、证据和必要修复。
- 节奏问题：指出具体时间段，给出缩首镜、补 Micro-Pause、增加受击窗口、删除无效位移等动作。
- 连续性问题：只修状态、轴线、首尾帧或人物过滤，不重写镜头创意。
- 参考图问题：只修绑定或删错图，不重写场景。
- 对白问题：按 `exact_dialogue_units` 恢复原文和顺序。
- prompt 结构问题：补可执行自然句、分镜基底或负约束，不改剧情。

## 原始来源

- `QC-HARD-FAIL-001`
- `QC-PACING-SAFETY-CHECKLIST-001`
- `QC-DIRECTOR-TASTE-SCORE-002`
- `GUARD-MINIMAL-REPAIR-001`
- `CONT-STATE-CONTRACT-001`
- `CONT-CAST-ACTIVE-001`
- `PROMPT-EXECUTABLE-STRUCTURE-001`
- `PROMPT-CURRENT-SEGMENT-ONLY-001`
- `PROMPT-AXIS-LOCK-PER-SEGMENT-001`
- `REFERENCE-ROLE-STRICT-001`
- `knowledge/00_知识库优先级与冲突裁决规则.md`
- `knowledge/17_结果质检与回溯修正规则.md`
- `knowledge/15_故事节奏控制规则.md`
