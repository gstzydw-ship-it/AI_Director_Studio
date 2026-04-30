---
title: 视频拆片案例库说明
doc_type: index
runtime_retrieval: false
---

# 视频拆片案例库 (Cases Library)

本目录存放从教学视频中自动提取的**逐镜头导演决策案例**。

## 与规则库的区别

| 维度 | 规则库 (rules/) | 案例库 (cases/) |
|------|----------------|----------------|
| 内容 | "什么时候该怎么做" | "导演实际拍了哪几个镜头" |
| 格式 | 单条规则 + 适用/例外 | 逐镜头序列 + 模式总结 |
| 作用 | 验证合法性 | 提供创作灵感 |

## 文件命名规范

```
CASE_{视频文件名}.md
```

## 生成方式

```bash
python tools/video_case_extractor.py
```

## 检索机制

案例文件通过 frontmatter 中的 `agent_scope` 字段自动路由到对应的 Agent。
`build_vectordb` 时会自动索引本目录下的所有 `.md` 文件。
