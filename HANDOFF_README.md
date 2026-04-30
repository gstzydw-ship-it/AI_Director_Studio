# AI Director Studio — 新电脑迁移交接文档

> **打包时间**: 2026-04-16 07:50 (北京时间)  
> **打包方式**: 完整源码 + 知识库 + 配置 + 输出结果 + 会话记录  
> **上次会话**: 知识库10大冲突修复（会话ID: 4928825e-bd90-402e-bfd5-9fb56c9d067c）

---

## 一、项目当前状态

### 核心进展
1. **知识库冲突修复已完成** — 10条冲突全部消解，并通过端到端测试验证
2. **流水线可用** — 多Agent LangGraph导演流水线可正常运行（需配置API Key）
3. **Web UI可用** — `python main.py` 或 `python main.py ui` 启动浏览器界面

### 最近解决的问题
- 05 规则07：从"必须换段"改为 A/B/C 三级条件化决策树
- 19 新增范例F（双人焦点转移）+ 范例A措辞调整
- 14/18 新增动作精度 S/A/B 三档 + 情绪锚点精度对齐
- 17 质检规则碎片段/受击者检查同步
- 22 多机位反应镜头措辞条件化

### 待处理事项
- 质检规则中"子分镜递进连接"的检查标准可能过严（所有片段都fail on这一条）
- Web UI 打包验证（dist目录未包含在压缩包中，需在新电脑重新执行 `build.bat`）
- 端到端测试的全面回归

---

## 二、解压后的恢复步骤

### 1. 解压到目标位置
```
7z x AI_Director_Studio_Pack_20260416.zip -o"D:\AI_Director_Studio_Full_Backup"
```

### 2. 安装Python依赖
```bash
cd D:\AI_Director_Studio_Full_Backup
pip install -r requirements.txt
```

### 3. 检查配置
**config/settings.yaml** 中的API Key需要确认是否仍然有效：
- `llm.api_key` — 主LLM接口（comfly）
- `agent_models.prompt_compiler.api_key` — Comfly接口（Claude Opus）
- `vectordb.api_key` — 文档嵌入模型接口

### 4. 重建向量库
```bash
python main.py build-db
```

### 5. 验证运行
```bash
# 方式1：启动 Web UI
python main.py

# 方式2：命令行测试
python test_conflict_fix.py
```

### 6. (可选) 重新打包 Web UI
```bash
build.bat
```

---

## 三、会话记录说明

`_session_artifacts/` 目录包含本次冲突修复会话的完整记录：
- `implementation_plan.md` — 修复方案设计
- `task.md` — 任务清单
- `walkthrough.md` — 修复walkthrough + 测试结果

---

## 四、关键文件索引

| 文件/目录 | 说明 |
|----------|------|
| `PROJECT_MEMORY.md` | **项目记忆文档**，包含完整冲突清单与修复记录 |
| `knowledge/` | 17个知识库规则文件（已完成冲突修复） |
| `agents/director_graph.py` | LangGraph核心流水线 |
| `agents/knowledge_base.py` | 知识库检索逻辑 |
| `config/settings.yaml` | API Key与模型配置 |
| `ui/app.py` | Web UI 后端入口 |
| `ui/templates/` | Web UI 页面模板 |
| `main.py` | CLI入口 |
| `output/conflict_test_result.txt` | 最新的冲突修复测试结果 |

---

## 五、代理设置提醒

`main.py` 中硬编码了本地代理：
```python
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
```
新电脑如果代理端口不同，需要修改这三行（main.py 第29-31行）。
