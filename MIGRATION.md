# 智能导演多Agent团队 — 迁移指南

## 项目说明
本项目是一个基于 LangGraph 的多Agent导演团队系统，负责自动化分镜生成。

## 在新电脑上恢复步骤

### 1. 解压到任意目录
```bash
# 例如解压到 D:\daoyan
```

### 2. 安装 Python 依赖
```bash
cd D:\daoyan
pip install -r requirements.txt
```

### 3. 重建向量知识库
向量库依赖在线 Embedding API，需要重新构建：
```bash
python main.py build-db
```

### 4. 确认配置
检查 `config/settings.yaml`，确保 API Key 和 Base URL 正确：
```yaml
llm:
  api_key: "你的API Key"
  base_url: "https://ai.comfly.chat/v1"
  model: "claude-opus-4-6"
```

### 5. 启动
```bash
python main.py
```
浏览器访问 http://127.0.0.1:8686

## 项目结构
```
daoyan/
├── main.py                 # 主入口（默认启动 Web UI；也支持 build-db/run）
├── requirements.txt        # Python 依赖
├── config/settings.yaml    # 配置文件（含API Key）
├── knowledge/              # 13个导演知识文件
├── agents/                 # LangGraph 核心代码
│   ├── director_graph.py   # LangGraph 状态机 + interrupt/resume
│   ├── state_engine.py     # 兼容旧 UI 导入的包装层
│   ├── crew.py             # 旧 CrewAI 实验路径（保留兼容）
│   ├── knowledge_base.py   # JSON + numpy 向量库
│   └── tools.py            # 旧 CrewAI RAG 工具
├── ui/                     # Web UI
│   ├── app.py              # FastAPI 后端(异步模式)
│   ├── templates/          # 前端页面
│   └── static/             # CSS 样式
└── _docs/                  # 任务文档（来自本次会话）
    ├── implementation_plan.md
    ├── task.md
    └── walkthrough.md
```

## 已知问题与解决状态
- [已迁移] CrewAI 主流水线 → LangGraph 状态机
- [已修复] ChromaDB $contains 不支持 → 改为 JSON + numpy 纯向量检索
- [已修复] RAG 工具中文名注册失败 → 改为英文名
- [已修复] 前端 fetch 超时 → 改为异步轮询
- [已修复] 质检导演卡死 → 移除工具+缩减context
- [待验证] LangGraph 全流程在线 LLM 端到端跑通
