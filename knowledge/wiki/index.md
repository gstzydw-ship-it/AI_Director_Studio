---
title: LLM Wiki Index
doc_type: wiki_index
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

# LLM Wiki 内容层索引

本 Wiki 是给各导演 Agent 执行用的知识入口，不替代 `knowledge/rules` 中的原始规则卡，也不复制完整规则卡。这里把规则编译成跨 Agent 可交接、可质检、可返修的操作手册。

## 使用顺序

1. 先读取 `knowledge/agent_retrieval_contracts.yaml`，确定当前 Agent 的检索范围、优先级和冲突裁决方式。
2. 再读取本 Wiki 的对应合同，确认本阶段必须接收什么、产出什么、继承哪些状态。
3. 最后按合同列出的原始规则 ID 回查 `knowledge/rules` 或 `knowledge/*.md`，只补充当前任务需要的细节。

## 合同入口

| 合同 | 负责阶段 | 主要作用 |
|---|---|---|
| [Story to Shot Contract](contracts/story_to_shot_contract.md) | `story_planner` -> `shot_director` | 把剧本片段、节奏微粒、状态合同交给镜头设计层。 |
| [Shot to Prompt Contract](contracts/shot_to_prompt_contract.md) | `shot_director` -> `prompt_compiler` | 把稳定镜头骨架、轴线、动作和对白落点翻译为可执行 prompt 输入。 |
| [Prompt to Quality Contract](contracts/prompt_to_quality_contract.md) | `prompt_compiler` -> `quality_inspector` | 把最终 prompt、约束、参考图绑定和自检结果交给质检层。 |
| [Continuity Contract](contracts/continuity_contract.md) | 全流程共享 | 约束人物、尾帧、门/道具、像素锚点、轴线与参考图继承。 |

## 全局裁决原则

- P0/P1 规则优先于案例和风格偏好。
- 用户显式约束、连续性、模型可生成性和安全边界优先于“更有戏”的改写。
- Case 只能作为范式参考，不能覆盖规则卡中的硬约束。
- 下游只能翻译或细化上游批准的信息，不能反向发明剧情、人物、道具或空间关系。
- 返修必须最小化：只修会导致下游报错、质检 fail 或连续性断裂的硬伤。

## 常用原始来源

- `knowledge/agent_retrieval_contracts.yaml`
- `knowledge/00_知识库优先级与冲突裁决规则.md`
- `knowledge/05_剧本拆分与15秒片段规划规则.md`
- `knowledge/06_连续性与安全规则.md`
- `knowledge/07_Seedance输出词典与模型适配.md`
- `knowledge/17_结果质检与回溯修正规则.md`
- `knowledge/20_镜头库与机位库.md`
- `knowledge/21_镜头调用规则与多机位模板.md`
- `knowledge/24_戏剧微粒识别与节奏触发规则.md`
- `knowledge/25_镜头摆位主分镜骨架规则.md`
