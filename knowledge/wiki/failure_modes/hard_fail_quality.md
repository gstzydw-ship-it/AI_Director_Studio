---
title: Hard Fail Quality Failure Mode
doc_type: failure_mode
agent_scope:
  - quality_inspector
  - prompt_compiler
  - shot_director_guard
status: active
runtime_retrieval: true
updated: 2026-05-10
---

# 失败模式：hard fail 质检误判

## 定义

`quality_inspector` 命中 hard/P0 规则后仍输出 `pass` 或 `warn`，或者只写“整体可用、略有问题”，没有阻断生成、没有归因、没有证据和最小返修建议。

这是质量门失效，比普通软问题更严重。

## 典型表现

- 含台词 Prompt 未禁止字幕、水印和屏幕文字，质检只写“注意字幕风险”。
- 门已经关闭后又无触发地重新打开，质检只写“连续性略弱”。
- `state_contract` 缺失，质检仍判 `pass`。
- 当前片段无戏份角色从上一段尾帧残留里复活，质检未归因。
- 意外碰撞被写成拥抱、贴身或亲密对视，质检只建议“弱化暧昧”。
- 对白与 `exact_dialogue_units` 不一致，质检没有拼回校验。
- 尾帧落在手部/眼神/道具局部特写，下一段无法继承，质检未阻断。

## hard fail 清单

以下问题必须 `fail`：

- 状态合同缺失或未继承：`active_cast / offscreen_cast / state_contract` 缺失、被改写或被下游忽略。
- 角色残留：当前无戏份角色继续出现、站位、旁白或抢画面。
- 物理状态回弹：门、车门、电梯门、道具从关闭/合拢/放下后无触发地回到打开/拿起/重置。
- 字幕污染：含台词、口型或画外声但未禁止字幕、屏幕文字、英文字幕、水印、文字浮层。
- 碰撞误读：冲入、撞上、扑到等意外动作被写成怀里、拥抱、贴身或亲密凝视。
- 抽象不可执行：时间轴不能映射成画面内动作、运镜、表情、台词声音。
- 对白不忠实：删字、换词、重排、跨片拼接或切分破坏自然发声。
- 首尾帧断裂：首帧不继承上一段尾帧/空间锁，或尾帧失去可续接关系景。
- 节奏阻断：Hook 首镜超过 4 秒仍无高价值信息，首 3 秒空转，反转后无受击窗口。

## hard fail 与 soft issue 的边界

| 类型 | 判定 | 示例 |
| --- | --- | --- |
| hard fail | 必须返修，阻断生成 | 有台词但未禁字幕；门状态回弹；状态合同缺失 |
| soft issue | 可优化，不阻断 | 镜头略安全；反应窗口略短但仍可见；风格词少量残留 |
| 导演品味问题 | 通常 `warn`，除非影响信息理解 | 镜头有更强角度，但当前版本仍能讲清楚 |

不要因为“整体氛围不错”降低 hard fail 等级；也不要因为个人审美把软问题升成 fail。

## 正确质检输出

`fail` 必须包含：

- `target_agent`：scene_analyst / story_planner / shot_director / prompt_compiler。
- `failed_rule_id`：能对应到规则卡或文档项。
- `evidence`：引用具体片段、时间段、字段或句子。
- `required_repair`：最小可执行返修动作。

示例：

```yaml
status: fail
target_agent: prompt_compiler
failed_rule_id: QC-HARD-FAIL-001
evidence: "【时间轴】含乔熙台词，但【约束】只写“无多余文字”，没有禁止字幕、屏幕文字、英文字幕、水印和文字浮层。"
required_repair: "仅补充硬约束：禁止字幕、屏幕文字、英文字幕、水印、文字浮层；台词只作为声音或口型存在。"
```

## 按 Agent 归因

- `scene_analyst`：首帧锁、空间锚点、参考图职责不足。
- `story_planner`：片段边界、对白底本、状态合同、角色进出场缺失。
- `shot_director`：分镜、景别、机位、动作覆盖、尾帧关系景设计失败。
- `prompt_compiler`：最终 Prompt 结构、约束、状态翻译、抽象降维、参考调用失败。

若上游字段存在且正确，但最终 Prompt 没有执行，归因给 `prompt_compiler`。若最终 Prompt 忠实继承了上游错误，归因给最早产生错误的 Agent。

## 最小返修原则

质检建议要小、准、可执行：

- 缺字幕禁令：只要求补一句硬约束。
- 门状态回弹：只要求删除“重新打开”，改为“门尚未合拢，人物从将合未合的门缝进入”。
- 角色残留：只要求把该角色移到 `offscreen_cast` 并删除正向站位。
- 尾帧断裂：只要求最后 0.5-1 秒切回双人/多人关系景。
- 抽象情绪：只要求替换为一个可见身体反应。
- 对白不忠实：要求按 `exact_dialogue_units` 原文恢复，不重写剧情。

## 质检自检

交付前确认：

- 我是否把所有 P0/hard 规则命中项判成 `fail`？
- 每条 fail 是否有证据，而不是笼统评价？
- `target_agent` 是否指向最早错误来源？
- `required_repair` 是否是最小修改，而不是整段重做？
- soft issue 是否没有误伤为 hard fail？
