# 智能导演多Agent团队 — 工作总结

## 一、完成的工作

### Phase 1：知识文件优化 ✅

| 操作 | 原文件 | 目标 | 状态 |
|------|--------|------|------|
| 合并 | 02 + 13 | `02_焦段景深与景别画幅策略.md` | ✅ |
| 合并 | 07 + 10 + 12 | `07_Seedance输出词典与模型适配.md` | ✅ |
| 合并 | 08 + 09 | `08_错误纠偏与判例库.md` | ✅ |
| 合并 | 15 + 16 | `15_故事节奏控制规则.md` | ✅ |
| 保留 | 01, 03, 04, 05, 06, 11, 14, 17, 18 | 直接复制 | ✅ |

**验证结果**：19 → 13 文件，140.2KB → 141.4KB（多出的 1.2KB 为合并说明头，**零内容丢失**）

---

### Phase 2-3：项目骨架 ✅

项目目录：`D:\daoyan\`

```
D:\daoyan\
├── main.py                    # 主入口（ui/build-db/run三种模式）
├── requirements.txt           # Python依赖
├── pyproject.toml             # 项目元数据
│
├── config/
│   └── settings.yaml          # LLM/向量库/UI配置
│
├── knowledge/                 # 优化后的13个知识文件
│   ├── 01_导演分镜总手册.md
│   ├── 02_焦段景深与景别画幅策略.md  ← 合并
│   ├── 03_镜头切换与推进规则.md
│   ├── 04_对白与表演镜头规则.md
│   ├── 05_剧本拆分与15秒片段规划规则.md
│   ├── 06_连续性与安全规则.md
│   ├── 07_Seedance输出词典与模型适配.md  ← 合并
│   ├── 08_错误纠偏与判例库.md  ← 合并
│   ├── 11_场景分析输入卡与导演意图提取.md
│   ├── 14_动作描述精细化控制规则.md
│   ├── 15_故事节奏控制规则.md  ← 合并
│   ├── 17_结果质检与回溯修正规则.md
│   └── 18_情绪锚点与逐段交互与仰拍限制补丁.md
│
├── agents/                    # CrewAI 多Agent核心
│   ├── __init__.py
│   ├── crew.py                # 5个Agent + 5个Task定义
│   ├── knowledge_base.py      # ChromaDB向量库构建与RAG检索
│   └── tools.py               # CrewAI RAG检索工具
│
├── ui/                        # 本地Web UI
│   ├── app.py                 # FastAPI后端
│   ├── templates/index.html   # 前端页面
│   └── static/style.css       # 暗色主题样式
│
├── vectordb/                  # ChromaDB持久化目录
└── output/                    # 输出结果目录
```

---

## 二、核心架构

### Agent 团队

| Agent | 职责 | 知识包 |
|-------|------|--------|
| 📋 场景分析师 | 提取戏剧任务/主体/炸点/发言单元 | 11, 01, 04 |
| 🎬 结构规划师 | 15秒拆片/节奏规划/分镜骨架 | 05, 15, 03, 01 |
| 🎥 镜头导演 | 焦段/景别/运镜/对白/动作/情绪 | 01,02,03,04,06,14,18 |
| ✍️ Seedance编译师 | 编译最终Prompt | 07, 01, 06 |
| 🔍 质检导演 | pass/warn/fail质检 | 08, 17 |

### 知识注入：双通道

1. **RAG 向量检索**（首选）：ChromaDB + 中文Embedding，按Agent过滤检索
2. **System Prompt 全量注入**（兜底）：把Agent专属知识文件完整写入backstory

---

## 三、后续步骤

你需要完成以下步骤来让系统跑起来：

### 1. 安装依赖
```bash
cd D:\daoyan
pip install -r requirements.txt
```

### 2. 配置 API
编辑 `config/settings.yaml`，填入你的第三方中转站信息：
```yaml
llm:
  api_key: "YOUR_API_KEY_HERE"
  base_url: "https://ai.comfly.chat/v1"
  model: "claude-opus-4-6"
```

### 3. 构建向量知识库
```bash
python main.py build-db
```

### 4. 启动 Web UI
```bash
python main.py
```
然后浏览器访问 `http://127.0.0.1:8686`

### 5. 或命令行执行
```bash
python main.py run --script your_script.txt --aspect-ratio 16:9
```
