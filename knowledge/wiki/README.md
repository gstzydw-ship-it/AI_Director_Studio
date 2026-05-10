---
title: LLM Wiki Maintenance Guide
doc_type: wiki_guide
agent_scope:
  - director_showrunner
  - rhythm_rewrite_director
  - scene_analyst
  - story_planner
  - shot_director
  - shot_director_layout
  - shot_director_blocking
  - shot_director_guard
  - prompt_compiler
  - quality_inspector
  - storyboard_designer
status: active
runtime_retrieval: false
updated: 2026-05-10
---

# LLM Wiki 说明

## 定位

`knowledge/wiki` 是内容层 Wiki，用于把分散在规则卡、知识文档和检索合同里的要求，整理成 Agent 能直接执行的交接合同。它面向运行时编排和多 Agent 协作，不是规则卡的镜像仓库。

## 写作规范

- 使用中文 Markdown。
- 不复制整张规则卡，只提炼可执行约束。
- 每个合同必须包含：输入、输出、必须继承的状态、禁止事项、最小返修原则、引用的原始规则/知识来源 ID 或文件名。
- 合同中出现的字段名应尽量保持与上游/下游结构一致，例如 `active_cast`、`state_contract`、`main_shots`、`reference_bindings`。
- 若合同与原始规则卡冲突，以 `knowledge/rules` 的 active P0/P1 规则和 `knowledge/agent_retrieval_contracts.yaml` 的优先级策略为准。

## Agent 读取建议

| Agent | 优先读取 |
|---|---|
| `story_planner` | `contracts/story_to_shot_contract.md`、`contracts/continuity_contract.md` |
| `shot_director` | `contracts/story_to_shot_contract.md`、`contracts/shot_to_prompt_contract.md`、`contracts/continuity_contract.md` |
| `prompt_compiler` | `contracts/shot_to_prompt_contract.md`、`contracts/prompt_to_quality_contract.md`、`contracts/continuity_contract.md` |
| `quality_inspector` | 全部合同，尤其是 `prompt_to_quality_contract.md` 与 `continuity_contract.md` |

## 维护边界

- Wiki 只解释合同和执行流程，不直接修改规则优先级。
- 新规则卡上线后，应在对应合同的“原始来源”中补充 ID，并把影响落成输入/输出/继承/禁止项。
- 如果某条要求属于风格建议，应明确标为建议，不应写成阻断条件。
- 如果某条要求会导致质检 fail，应写明失败证据和可执行返修方向。
