# AI Director Studio — 交接文档 Session 3
> 日期：2026-04-20 00:40 | 项目路径：`AI_Director_Studio_Pack_20260417/AI_Director_Studio`

---

## 一、项目概况

多 Agent 导演工作台：用户输入剧本文本 + 角色参考图，系统自动拆分为 10-15 秒短片段，为每段生成可直接投入即梦/可灵的中文视频 Prompt。

**技术栈**：Python + FastAPI + LangGraph + 多模型 LLM 管线
**启动命令**：`python main.py ui` → 浏览器打开 `http://127.0.0.1:8686`

---

## 二、本次会话完成的所有改动

### 2.1 人物空间逻辑一致性硬约束 ★★★

**文件**：`agents/director_graph.py`（prompt_compiler 系统提示词）

新增**最高优先级规则 Rule 7**——「人物空间逻辑一致性」，包含 5 项自检清单：

| 检查项 | 含义 |
|--------|------|
| a) 朝向 vs 碰撞面 | A面朝/背对决定了B能触碰的部位 |
| b) 距离 vs 动作 | 隔3米不可能凭空触碰 |
| c) 遮挡 vs 可见 | 人在身后就不该正面可见 |
| d) 位置 vs 出入 | 在房间深处不可能瞬间出现在门口 |
| e) 转身 vs 面向切换 | 背对→正面必须有转身动作 |

同时在**绝对禁止清单**新增第 10 条：
> 禁止人物空间逻辑矛盾。这是最严重的错误，一旦出现整段作废。

**适用范围**：任何场景，不限于电梯/走廊/房间。

---

### 2.2 模型配置大改造 ★★★

#### 2.2.1 最终模型阵容

| Agent | 模型 | API 路由 | temperature |
|-------|------|---------|-------------|
| 🎭 节奏改写 | **kimi-k2.5** | Moonshot 官方直连 | 1.0 (强制) |
| 📐 结构规划 | **qwen3.6-plus** | 阿里百炼直连 | 0.3 |
| 🎬 分镜导演 | **qwen3.6-plus** | 阿里百炼直连 | 0.3 |
| ✍️ 画面编译 | **kimi-k2.5** | Moonshot 官方直连 | 1.0 (强制) |
| 🧹 提示词清理 | **gpt-5.4** | Comfly 中转 | 0.2 |
| ✅ 质检主 | **deepseek-v3.2** | Comfly 中转 | 0.1 |
| ✅ 质检副 | **claude-sonnet-4-6** | Comfly 中转 | 0.1 |
| 🔍 场景分析 | **deepseek-v3.2** | Comfly 中转 | 0.1 |
| 📹 视频分析 | **gemini-3.1-pro** | Comfly 专用Key | 0.1 |
| 🔄 全局兜底 | **deepseek-v3.2** | Comfly 中转 | 0.3 |

#### 2.2.2 API Key 清单

| 用途 | Key 前缀 | 服务商 |
|------|---------|--------|
| Comfly 中转（通用） | `sk-wGhoU...` | ai.comfly.chat |
| Moonshot 官方（kimi） | `sk-IJip...` | api.moonshot.cn |
| 阿里百炼（qwen3.6） | `sk-646d...` | dashscope.aliyuncs.com |
| Comfly（视频分析专用） | `sk-WZUx...` | ai.comfly.chat |

#### 2.2.3 关键坑点

- **kimi-k2.5 官方 API 强制 temperature=1**，传其他值直接 HTTP 400
- **kimi-k2.5 经 Comfly 中转站极慢**（简单请求 56s），必须走官方直连（3.6s）
- **真正生效的配置文件是 `config/private/settings.local.yaml`**，不是 `config/settings.yaml`

---

### 2.3 配置系统修复 ★★

**文件**：`agents/director_graph.py` — `_get_llm_settings()`

**改动前**：
- base_url 硬编码为 COMFLY_BASE_URL
- 只有 video_analyst 能覆盖 api_key
- 不读取 per-agent temperature

**改动后**：
- 每个 agent 可独立覆盖 `model`、`api_key`、`base_url`、`temperature`
- 返回值从 `tuple[str, str, str]` 改为 `tuple[str, str, str, float | None]`
- `call_llm` 中 agent temperature 优先于函数参数

---

### 2.4 前端配置锁定 ★★

**文件**：`ui/app.py` — `/api/config` 端点

**改动前**：
- 强制覆盖所有 base_url 为 Comfly
- 删除所有 agent 的 base_url（导致百炼直连被抹掉）

**改动后**：
- 只做脱敏（隐藏 API key），保留所有配置原样
- 返回 `_config_locked: true` 标记

---

### 2.5 任务残留自动清理 ★★

**文件**：`ui/app.py`

**三层防护**：

1. **启动时清理** — `_recover_stale_running_state()` 改为自动重置到 idle（原来标记为 error）
2. **提交时清理** — `/api/run` 入口新增：如果线程已死但状态 running，自动清理再接受提交
3. **恢复时清理** — `/api/resume` 入口同样处理

**效果**：用户再也不需要手动刷新页面 + 重新上传图片。

---

### 2.6 错误诊断增强 ★

**文件**：`agents/director_graph.py` — `call_llm()`

- HTTP 错误日志增加 agent 名和 model 名
- HTTP 429（限流）改为可重试
- 错误信息包含 API 返回的完整 body

---

## 三、核心文件清单

| 文件 | 角色 | 重要度 |
|------|------|--------|
| `config/private/settings.local.yaml` | **真正的配置文件**（优先级最高） | ★★★ |
| `config/settings.yaml` | 备用配置（被 local 覆盖） | ★ |
| `agents/director_graph.py` | 全部 Agent 节点 + 提示词 + LLM 调用 | ★★★ |
| `ui/app.py` | FastAPI 后端 + 前端路由 | ★★ |
| `knowledge/05_剧本拆分与15秒片段规划规则.md` | 视角跳转协议等知识库 | ★★ |

---

## 四、从 Session 1-2 累积的重要改进

| 改进 | 位置 | 说明 |
|------|------|------|
| pov_transition 视角跳转检测 | story_planner state_contract | 自动识别场景内外跳转 |
| pov_obstructed 遮挡检测 | video_analyst + shot_director | 门关闭时强制标注不可见 |
| 人物状态帧自动抽取 (70%) | _extract_tail_frame_from_video | 闭合门下的动作补充 |
| 背景人物点缀规则 | prompt_compiler | 公共场景自动添加路人 |
| 导演气质描写 | prompt_compiler | 语调、微表情强制注入 |

---

## 五、已知问题与待验证

### 5.1 待验证（本次改动后还未完整跑通）

- [ ] kimi-k2.5 temperature=1 下的输出质量是否满足要求
- [ ] qwen3.6-plus 走百炼的完整管线是否稳定
- [ ] prompt_sanitizer (gpt-5.4) 和 quality_inspector_secondary (claude-sonnet-4-6) 这两个 agent 在代码中是否已有对应节点（可能是配置预留但代码尚未实现）
- [ ] 人物空间逻辑一致性自检清单的实际约束效果

### 5.2 潜在风险

- **kimi-k2.5 只能 temperature=1**：输出随机性较高，可能需要在提示词中用更强的约束语言来弥补
- **配置双文件问题**：`settings.yaml` 和 `settings.local.yaml` 并存，容易混淆。建议未来统一为单文件
- **Comfly 中转站稳定性**：部分模型（如 kimi）延迟极高，建议对延迟敏感的 agent 都走官方直连

### 5.3 下一步工作建议

1. 完整跑一次管线，观察新模型阵容的输出质量
2. 如果 kimi-k2.5 温度 1.0 导致输出不稳定，考虑换成 deepseek-v3.2 或 doubao-pro-128k
3. 补充《交互动作朝向矩阵》知识库文档
4. 监控 qwen3.6-plus 百炼 API 的稳定性和速率限制

---

## 六、换电脑快速恢复步骤

```bash
# 1. 拷贝整个项目目录到新电脑
# 2. 安装依赖
pip install -r requirements.txt

# 3. 确认真正的配置文件存在
cat config/private/settings.local.yaml

# 4. 启动服务
python main.py ui

# 5. 浏览器打开
# http://127.0.0.1:8686
```

> **关键提醒**：所有配置改动必须改 `config/private/settings.local.yaml`，改 `config/settings.yaml` 不会生效！

---

*文档生成时间：2026-04-20 00:40*
