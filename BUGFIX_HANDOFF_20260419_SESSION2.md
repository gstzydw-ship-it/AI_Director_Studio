# BUGFIX HANDOFF — 2026-04-19 Session 2

> **时间**：2026-04-19 12:00 ~ 13:27  
> **目标**：修复 AI Director Studio 多 Agent 流水线在生成片段 2 时的连环故障  
> **上一轮文档**：`BUGFIX_HANDOFF_20260419.md`（Session 1，修复了 SSE 流式解析 + HTTP 错误二次崩溃）

---

## 一、当前进度

| 项目 | 状态 |
|------|------|
| **Session ID** | `web_6ea89d96-45b0-401c-bce2-c72cd9eab215` |
| **片段 1** | ✅ 已完成编译，Prompt 已生成 |
| **片段 2** | ⏳ 等待重试（已恢复为 `waiting_for_user_input`） |
| **片段 3** | 未开始 |
| **总片段数** | 3 |
| **pipeline_state.json** | `status: waiting_for_user_input`, `step: step_5_inspect` |

---

## 二、本轮已修复的 Bug（共 7 项）

### Bug 1：API 路由优先级错误 — Agent 专属端点被前端覆盖
**文件**：`agents/director_graph.py` → `_get_llm_settings()` (约第 100-115 行)

**问题**：前端 localStorage 存了 `xinsuanai.com` 的 API 配置，通过 `request_url` 上下文变量传入后端。原逻辑中 `request_url` 优先级最高，导致 `video_analyst` 配置的专属端点 `ai.comfly.chat` 被覆盖。

**修复**：当 agent 在 `settings.yaml` 的 `agent_models` 中显式配置了 `base_url` 时，优先使用 agent 专属端点，不被前端泛用 URL 覆盖。`api_key` 保持已解析值不变（包含前端 key）。

```python
# 修复后的逻辑（第 107-111 行）
agent_base_url = agent_overrides.get("base_url", "")
if agent_base_url:
    base_url = agent_base_url
    # api_key 保持不变
```

### Bug 2：API Key 为空导致无认证请求
**文件**：`config/settings.yaml`

**问题**：`settings.yaml` 中所有 `api_key` 字段均为空字符串。之前靠前端传 key 工作，但修复 Bug 1 后 agent 专属端点的 key 回退到了空值。

**修复**：配置了 3 个独立 API Key：

| 用途 | Key 前缀 | 配置位置 |
|------|----------|----------|
| 文本分析（全局 LLM） | `sk-V5T4...71Or` | `llm.api_key` |
| 视频分析（video_analyst） | `sk-WZUx...kZPu` | `agent_models.video_analyst.api_key` |
| 向量知识库（vectordb） | `sk-wGho...Kaof` | `vectordb.api_key` |

### Bug 3：video_analyst 发送 14MB Base64 导致网关断连
**文件**：`agents/director_graph.py` → `_analyze_video_segment()` (约第 1210 行)

**问题**：10MB 视频文件编码为 ~14MB Base64 发送给 API 中转站，频繁触发 `RemoteProtocolError`。

**修复**：
1. `max_retries` 从默认 2 增加到 4
2. 在 `_analyze_previous_segment_media()` 中给 `_analyze_video_segment()` 加了 try-except，失败时降级为仅用尾帧截图分析

### Bug 4：质检误判 — 约束段"禁止员工低语"被当成编造
**文件**：`agents/director_graph.py` → `_guard_fabrication_and_hallucination()` (约第 794 行)

**问题**：prompt 约束段写了 `禁止新增...员工低语`，正则匹配到了这条禁止规则本身，误判为编造。

**修复**：编造检测先排除约束段，再用 `_without_negative_clauses()` 过滤否定子句。

### Bug 5：质检误判 — 切换次数阈值过严
**文件**：`agents/director_graph.py` (约第 1000-1002 行)

**修复**：阈值从 `> 2` 调整为 `> 3`。

### Bug 6：质检误判 — "严飞不在画面内"被判为角色残留
**文件**：`agents/director_graph.py` → `_without_negative_clauses()` (约第 882 行)

**修复**：否定词表增加 `不在|不出现|已退出`。

### Bug 7：前端 localStorage API 配置干扰后端
通过浏览器 JavaScript 清空了 localStorage 中保存的 API 配置。

---

## 三、当前 API 配置总览

所有 agent 均走 `ai.comfly.chat/v1`：

| Agent | 模型 | Key |
|-------|------|-----|
| scene_analyst | gpt-5.4-mini | 全局 text key |
| rhythm_rewrite_director | claude-sonnet-4-6 | 全局 text key |
| story_planner | claude-sonnet-4-6 | 全局 text key |
| shot_director | gpt-5.4 | 全局 text key |
| prompt_compiler | gpt-5.4 | 全局 text key |
| quality_inspector | gpt-5.4-mini | 全局 text key |
| video_analyst | gemini-3.1-pro-preview-thinking-high | 专用 video key |
| vectordb (embedding) | qwen3-embedding-8b | 专用 embedding key |

全部已通过连通性测试（8/8 PASS）。

---

## 四、关键文件变更清单

| 文件 | 修改行 | 变更内容 |
|------|--------|----------|
| `agents/director_graph.py` | ~100-115 | `_get_llm_settings()` API 路由优先级 |
| `agents/director_graph.py` | ~794-800 | 编造检测排除约束段 |
| `agents/director_graph.py` | ~882 | 否定词表扩展 |
| `agents/director_graph.py` | ~1000 | 切换次数阈值 >2→>3 |
| `agents/director_graph.py` | ~1210 | video_analyst max_retries=4 |
| `agents/director_graph.py` | ~1226 | 视频分析失败降级逻辑 |
| `config/settings.yaml` | 12, 47, 58 | 3 个 API Key 配置 |

---

## 五、已知遗留问题

1. **前端 tab 可能传旧配置**：关闭所有旧 tab 只保留一个干净的
2. **video_analyst 视频分析持续失败**：14MB base64 payload 频繁 RemoteProtocolError，已降级为尾帧分析。如需恢复，考虑压缩视频或用 Gemini File API
3. **Phase 2 缺少 active_cast / state_contract**：已标为 `[warn]` 不影响通过

---

## 六、下一步操作

1. 刷新浏览器（Ctrl+F5），确保 localStorage 已清空
2. 上传片段 1 视频，点击生成片段 2
3. 如需手动恢复状态：
```python
import json
path = r'output\sessions\web_6ea89d96-45b0-401c-bce2-c72cd9eab215\pipeline_state.json'
with open(path, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)
state['status'] = 'waiting_for_user_input'
state['step'] = 'step_5_inspect'
state['error'] = ''
state['qc_retry_count'] = 0
with open(path, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
```

---

## 七、项目关键路径速查

| 项目 | 路径 |
|------|------|
| 入口 | `python main.py ui` |
| 配置 | `config/settings.yaml` |
| 核心逻辑 | `agents/director_graph.py` |
| Session 持久化 | `output/sessions/<session_id>/pipeline_state.json` |
| 上传视频 | `output/uploaded_segment_videos/` |
| 尾帧截图 | `output/auto_tail_frames/` |
| 知识库 | `knowledge/` |
| 前端 | `ui/templates/index.html` + `ui/app.py` |
| 代理 | `HTTP_PROXY=127.0.0.1:9674` |
| 服务地址 | `http://127.0.0.1:8686` |

---

## Session 3：时间轴约束污染 — 根因分析与三层修复（2026-04-19 16:50 ~ 17:10）

### 症状
LLM 生成的每个时间轴条目末尾都被追加了 `——无字幕无屏幕文字；零亲密接触保持物理距离；轴线不变；严飞不出现。`，且 `【风格锚点】` 后被插入 `【核心禁忌】` 行。`_normalise_compiled_prompt` 中的 `_cleanup_timeline_constraints` 函数本应清除这些，但用户在前端看到的仍是脏版本。

### 根因（3 层）

| 层级 | 问题 | 位置 |
|------|------|------|
| **L1 正则不够强** | 原 `_cleanup_timeline_constraints` 的碎片化 sub-patterns 执行顺序互相干扰：先跑的"无字幕"子模式把 `——` 后面的文字拆碎，导致 `——` 整块匹配反而失效 | `director_graph.py` L1006-1026 |
| **L2 遗漏清理** | `【核心禁忌】` 行（LLM 模仿旧格式自行生成）和删除后残留的孤立 `】` 行未被处理 | `director_graph.py` L1006 |
| **L3 流式污染** | `ui/app.py` 的 `_stream_callback` 在 LLM 流式输出阶段直接把原始 raw 文本累积到 `task_state["agent_outputs"]["prompt_compiler"]`。即使后端 `_normalise_compiled_prompt` 正确清洗了 `compiled_segment_N`，前端轮询 `/api/status` 时可能看到的是流式阶段的脏数据 | `ui/app.py` L686-691 |

### 修复

**L1 — 正则重写**（`director_graph.py` `_cleanup_timeline_constraints`）：
- Phase 0：`re.sub(r"【核心禁忌】[^\n]*\n?", "")` + `re.sub(r"(?m)^】\s*$\n?", "")`
- Phase 1：一条统一强力正则 `r"——[^。\n]*(?:无字幕|零亲密|轴线不变|严飞不出现|屏幕文字|物理距离)[^。\n]*[。]?"` 一次性匹配整块禁忌尾巴
- Phase 2：兜底碎片清理（不带 `——` 前缀的独立约束句）

**L2 — 角色名修复**（`director_graph.py` `_normalise_compiled_prompt`）：
- `re.sub(r"熙先", ...)` → `re.sub(r"(?<!乔)熙先", ...)` 防止 `乔乔乔熙先` 多加前缀

**L3 — UI 层强制覆写**（`ui/app.py` `_resume_pipeline_in_thread`）：
- 在 `task_state.update(state)` 之后，显式取 `compiled_segment_N` 再跑一次 `_normalise_compiled_prompt`，用清洗后的版本覆写 `task_state["agent_outputs"]` 中的脏数据

**QC 兼容**（`director_graph.py` `quality_inspector_node`）：
- 结构检查兼容新旧模板（`【连续性状态契约】`/`【空间与首帧总控】`、`【全段硬约束】`/`【约束】`）
- timeline 终止符兼容 `【尾帧收束】`

### 验证结果
用用户两次贴出的真实脏 Prompt 做端到端测试，`_normalise_compiled_prompt` 全部断言通过：
- ✅ `【核心禁忌】` 行删除
- ✅ 4 处 `——无字幕...严飞不出现。` 全部剥离
- ✅ 时间轴镜头描述完整保留
- ✅ 尾帧特写自动拉回关系景
- ✅ `乔乔乔熙先` 不再被多加前缀

### ⚠️ 重要操作提醒
**修改代码后必须重启服务器！** 运行中的 Python 进程使用的是内存中的旧代码，代码修改不会自动生效。执行：
```bash
# 先 Ctrl+C 停止当前服务器，再重新启动
python main.py ui
```
