---
type: dashboard
status: active
runtime_retrieval: false
---

# AI Director 知识库首页

这是当前项目的 Obsidian Vault。这里负责整理规则；真正给 Agent 使用时，仍由项目里的知识库构建流程生成向量库。

## 工作入口

- [[_indexes/Agent规则索引|Agent 规则索引]]
- [[_indexes/冲突与废弃规则检查|冲突与废弃规则检查]]
- [[_indexes/运行时检索范围|运行时检索范围]]
- [[_indexes/按规则类型索引|按规则类型索引]]
- [[rule_registry.yaml|规则注册表]]
- [[_templates/规则卡模板|规则卡模板]]

## 推荐规则结构

每条新增规则尽量使用 YAML frontmatter：

```yaml
---
rule_id: CONT-DOOR-MONOTONIC-001
title: 电梯门状态单调
agent_scope:
  - prompt_compiler
  - quality_inspector
rule_type: continuity
priority: hard
status: active
conflicts_with: []
supersedes: []
applies_to:
  - 电梯
  - 门
  - 尾帧连续性
---
```

## Active Hard Rules

```dataview
TABLE rule_id, title, agent_scope, rule_type
WHERE status = "active" AND priority = "hard"
SORT rule_type ASC, rule_id ASC
```

## 按 Agent 快速入口

- [[_indexes/Agent规则索引#Prompt Compiler|Prompt Compiler]]
- [[_indexes/Agent规则索引#Shot Director|Shot Director]]
- [[_indexes/Agent规则索引#Story Planner|Story Planner]]
- [[_indexes/Agent规则索引#Scene Analyst|Scene Analyst]]
- [[_indexes/Agent规则索引#Quality Inspector|Quality Inspector]]

## 需要补元数据的文档

```dataview
TABLE file.mtime AS "last modified"
WHERE !rule_id AND file.name != "_Dashboard_知识库首页" AND !contains(file.folder, "_indexes") AND !contains(file.folder, "_templates")
SORT file.mtime DESC
```
