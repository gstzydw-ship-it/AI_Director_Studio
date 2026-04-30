---
rule_id: REF-TAILFRAME-PRIORITY-001
title: 尾帧图优先于文字复述
doc_type: rule_card
rule_type: reference_control
agent_scope:
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/06_连续性与安全规则.md
  - knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
applies_to:
  - 尾帧图
  - 参考图
  - 空间与首帧总控
---

# 尾帧图优先于文字复述

## 规则

当存在上一段尾帧图时，最终 Seedance prompt 应把尾帧图作为最高优先级首帧与场景锚点，而不是把尾帧分析报告改写成长篇场景描述。

推荐写法：

```text
@图片N（上一段尾帧图）作为本段首帧、场景、构图、光线和空间锚点，直接从图中状态继续。
```

如果尾帧图已经覆盖主要场景，不要再重复调用单独场景参考图；只保留必要人物身份参考图与上一段尾帧图。

## 禁止

- 长篇复述尾帧里的窗、门、沙发、灯光、地面纹理。
- 同时调用尾帧图和重复场景参考图。
- 把尾帧分析报告逐字塞进【空间与首帧总控】。
- 在时间轴里重复执行尾帧中已经完成的站位、入场或转身。

原则：尾帧图负责长相、场景、构图、光线、首帧状态；文字负责尾帧之后的新动作。

