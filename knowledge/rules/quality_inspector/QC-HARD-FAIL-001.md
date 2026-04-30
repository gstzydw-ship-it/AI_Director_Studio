---
rule_id: QC-HARD-FAIL-001
title: Hard规则违反必须阻断
doc_type: rule_card
rule_type: quality_control
agent_scope:
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/00_知识库优先级与冲突裁决规则.md
  - knowledge/17_结果质检与回溯修正规则.md
conflicts_with: []
supersedes: []
applies_to:
  - 质检
  - fail阻断
  - hard规则
---

# Hard规则违反必须阻断

## 规则

`priority: hard` 的规则不是建议，而是阻断条件。

Quality Inspector 发现以下问题时必须输出 fail：

- 当前戏份角色过滤失败。
- 门状态合拢后重新打开或冲开。
- 缺失 `active_cast / offscreen_cast / state_contract`。
- 含对白但未禁止字幕/屏幕文字。
- 意外碰撞被写成怀里、拥抱、贴身或亲密对视。
- 片段被压成 5-6 秒，或时间轴机械均分且缺少镜头变化。

返修后仍失败时，不应继续标记片段完成，应让用户看到质检失败原因。

