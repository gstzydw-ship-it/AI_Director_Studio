# 2026-05-10 WebUI / 模型配置交接 Prompt

你接手的是 `AI_Director_Studio` 当前分支 `拆分` 的 WebUI 与模型配置改造。请先阅读本交接，再继续开发。

## 当前目标

继续把本地 WebUI 做成更直观的导演工作台，重点围绕模型配置、Agent 可用性、知识库构建和错误可诊断性。不要回滚用户本地配置或私有知识库文件。

## 今天已完成

1. 修复模型列表拉取失败时直接暴露 `JSONDecodeError` 的问题。
   - `/api/model_list` 会尝试兼容 `/models` 与 `/v1/models`。
   - 非 JSON 响应会显示可读错误预览。
   - 覆盖测试在 `tests/test_model_list_api.py`。

2. 重设计 WebUI 主界面。
   - 新增 `DESIGN.md` 记录设计系统。
   - 改造 `ui/templates/index.html` 与 `ui/static/style.css`。
   - 工作台、模型配置、知识库页已调整为更紧凑的深色控制台风格。

3. 修复知识库页面空白问题。
   - 根因是重构时 HTML section/div 闭合错位。
   - 已用浏览器确认知识库页可见。

4. 修复“构建向量知识库没走当前向量网站”的问题。
   - 前端构建按钮会把当前页面中的 `embedding_base_url`、`embedding_api_key`、`embedding_model` 发给后端。
   - 后端 `/api/build_vectordb` 会在构建前把本次向量配置写入实际生效配置源。
   - 根因：`config/private/settings.local.yaml` 优先级高于公开配置，旧 private 向量地址覆盖了页面显示的公开配置。

5. 新增 Agent 连通性测试。
   - 模型配置页的 Agent 模型分配下方新增“Agent 连通性测试”面板。
   - `/api/test_agent_connections` 会按当前页面配置逐个测试 Agent。
   - 文本/视觉 Agent 走文本中转站；生图 Agent 走生图中转站。
   - 每个测试只发一个小型 `/chat/completions` 请求，会消耗少量额度。

## 重要文件

- `ui/app.py`
  - `/api/model_list`
  - `/api/build_vectordb`
  - `/api/test_agent_connections`
- `ui/templates/index.html`
  - 模型配置表单
  - `buildVectorDB()`
  - `testAgentConnections()`
- `ui/static/style.css`
  - 2026 WebUI 覆盖样式
  - Agent 连通性测试面板样式
- `tests/test_model_list_api.py`
  - 模型列表兼容测试
  - Agent 连通性路由测试
- `DESIGN.md`
  - WebUI 设计规则与视觉方向

## 验证记录

已运行：

```powershell
py -3 -m pytest tests/test_model_list_api.py tests/test_session_state_isolation.py -q
```

结果：`10 passed`。

本地 WebUI 已重启，默认地址：

```text
http://127.0.0.1:8686
```

## 接手注意

- 当前工作树可能包含用户本地文件变更，例如 `.codex_ui_pid`、`config/settings.yaml`、`config/private/settings.local.yaml`、`.obsidian/`、`GitNexus/`、私有知识库文档等。不要默认提交或回滚这些文件。
- 项目要求提交前运行 GitNexus 变更检测：

```powershell
npx.cmd gitnexus detect-changes --repo AI_Director_Studio
```

- 修改函数/类/方法前按 `AGENTS.md` 要求先跑 GitNexus impact。
- 如果继续调试模型连通性，优先看页面当前配置与 private 配置是否不一致。

## 建议下一步

1. 给 Agent 连通性测试增加“只测试失败项 / 只测试选中 Agent”。
2. 把向量嵌入连接也加入同一个测试面板，单独调用 `/embeddings`。
3. 给配置页显示“当前实际生效配置源”，避免 private 配置覆盖公开配置时用户困惑。
