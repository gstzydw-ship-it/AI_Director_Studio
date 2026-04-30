---
rule_id: PROMPT-CUT-BUDGET-001
title: 单片段切镜预算（含隐性切镜识别）
doc_type: rule_card
rule_type: prompt_compilation
agent_scope:
  - story_planner
  - shot_director
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/07_Seedance输出词典与模型适配.md
  - knowledge/19_Gold_Standard_Prompt范例.md
  - knowledge/rules/prompt_compiler/PROMPT-CINEMATIC-DOWNTRANSLATION-002.md
  - knowledge/rules/prompt_compiler/PROMPT-MAIN-SUBSHOT-TIMELINE-001.md
conflicts_with: []
supersedes: []
applies_to:
  - 切镜预算
  - 隐性切镜
  - 同一机位继续
  - segment 拆分
  - Seedance 单镜头限制
---

# 单片段切镜预算（含隐性切镜识别）

## 背景

Seedance 2.0 物理上是单镜头连续生成模型——它每次只能渲染一段连续画面，无法真正完成"硬切"。当 prompt 在一段里要求 4-5 次切镜时，模型只能用"快速摇镜 / 加速剪辑感"去糊近似，结果就是观感上的乱切乱跳。

`PROMPT-CINEMATIC-DOWNTRANSLATION-002` 写的"6-12 秒最多 2-4 个镜头变化"对当前 Seedance 仍然偏宽，本卡进一步收紧，并显式定义"隐性切镜"。

## 切镜预算（按 segment 时长划档）

| segment 时长 | 显式切镜上限 | 隐性切镜上限 | 总切镜上限 |
|---|---|---|---|
| ≤ 3 秒  | 0 | 0 | 0（必须全段单一连续镜头） |
| 3-8 秒  | 1 | 0 | 1 |
| 8-13 秒 | 2 | 0 | 2 |
| 13-15 秒 | 3 | 0 | 3 |

超出预算时 **强制拆段**，由 `story_planner` 重新规划 segment 边界——不允许 compiler 自己塞进单段。

## 切镜的两种类型

**显式切镜**（容易被 regex 抓到）：
- "镜头切至 / 切到 / 切回"
- "反打至 / 反打镜头"
- "切入 / 切出"
- "镜头跳转"

**隐性切镜**（最容易漏判，必须特别识别）：
- "**同一机位继续**" 后跟一个**不同的景别 / 不同的主体框 / 不同的聚焦人物**——这本质就是切，模型识别不到"机位没变"，只看到画面突变。
- "镜头保持 / 机位不变" 后接构图重大变化。
- 一句话内同时描述两个不同人物的中近景以上景别（"商北琛胸部以上中近景，前景严飞..."如果严飞也是中近景级聚焦）。

## 识别"同一机位继续"是真延续还是隐性切镜

**真延续（允许）**：
- "同一机位继续" → 同一主体 + 同一景别 + 仅动作 / 表情变化
- 例："同一机位继续，商北琛保持站位，眉头微皱，视线下移 15°。"

**隐性切镜（禁止）**：
- "同一机位继续" → 不同主体 / 不同景别 / 不同框中心
- 例："同一机位继续，严飞胸部以上中近景落在画面中心，商北琛在左侧前景轻虚。"
  （主体从商北琛换成严飞 + 景别变成中近景 + 画面中心换人 = 隐性切镜）

## 强制拆段触发

`prompt_compiler` 编译完成后必须自检：
1. 数显式切镜数量 → 超 segment 时长档位上限即报硬失败。
2. 扫描每个"同一机位继续"，检查后续 50 字内是否引入**新主体名 + 新景别**——是则计为 1 次隐性切镜并报硬失败。
3. 失败后 compiler **不能自行硬塞进单段**，必须把问题抛回 `story_planner`，由 planner 重新拆段。

## 禁止项

- 禁止 `scene_analyst` 或 `story_planner` 把超过预算的事件全塞进一个 segment。
- 禁止 `prompt_compiler` 通过缩短 segment 时长来绕开预算（例如 13 秒压成 11 秒以适配 2 个切镜上限——必须真的拆成两段）。
- 禁止用"同一机位继续 / 镜头保持"做隐性切镜伪装。

## 正确写法（按预算拆段）

原方案（错）：13 秒一段塞 5 个镜头。
新方案（对）：拆成 8 秒 + 5 秒两段，分别承担 2 个 + 1 个镜头。

```text
[Segment A] 0-8 秒
0-4秒：摄影机位于商北琛右前方眼平，稳定器同速后退。商北琛沿中轴前进，员工列收拢视线。
4-8秒：同一机位继续（右前方眼平），前排主管退开让通道。商北琛走到通道中段。

[Segment B] 0-5 秒
0-3秒：摄影机切至商北琛右前方双人关系中景。严飞迈出半步，说出"Welcome, Mr. Pierce."
3-5秒：同一机位继续，商北琛沉默经过严飞，视线只短暂掠过右侧。
```

## Agent 执行

- `story_planner`：拆 segment 时按"每段事件密度 ≤ 切镜预算"做约束；超出立刻拆。
- `shot_director`：`main_shots` 数量必须 ≤ 当前 segment 切镜预算 + 1。
- `prompt_compiler`：编译后 regex 自检 + 隐性切镜识别，超预算抛 `PromptCutBudgetExceeded` 强制重拆。
- `quality_inspector`：见到隐性切镜模式直接判 fail。
