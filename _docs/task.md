# 智能导演多 Agent 团队 — 任务清单

## Phase 1：知识文件优化
- [x] 创建项目目录结构 `D:\daoyan\`
- [x] 合并 02 + 13 → `02_焦段景深与景别画幅策略.md`
- [x] 合并 07 + 10 + 12 → `07_Seedance输出词典与模型适配.md`
- [x] 合并 08 + 09 → `08_错误纠偏与判例库.md`
- [x] 合并 15 + 16 → `15_故事节奏控制规则.md`
- [x] 复制不变文件（01, 03, 04, 05, 06, 11, 14, 17, 18）
- [x] 验证优化后文件完整性（19→13文件，140.2KB→141.4KB，零内容丢失）

## Phase 2：CrewAI + RAG 搭建
- [x] 初始化 Python 项目（pyproject.toml / requirements.txt）
- [x] 配置文件（config/settings.yaml）
- [x] 搭建 ChromaDB 向量库模块（agents/knowledge_base.py）
- [x] 创建 RAG 检索工具（agents/tools.py）
- [x] 定义 5 个 Agent + 5 个 Task（agents/crew.py）
- [x] 主入口文件（main.py）
- [x] 安装依赖（`pip install -r requirements.txt`）
- [ ] 配置 Comfly 中转站 API Key ← **需要用户操作**
- [x] 构建向量知识库（186个片段，13文件全部入库）
- [ ] 端到端测试（需API Key后测试）

## Phase 3：本地 UI
- [x] FastAPI 后端（ui/app.py）
- [x] 前端 HTML（ui/templates/index.html）
- [x] CSS 样式（ui/static/style.css）
- [x] 启动 UI 测试 — 已在 http://127.0.0.1:8686 运行
- [ ] 前后端联调验证（需API Key后测试）

## Phase 4：测试与打磨
- [ ] 用简单剧本测试全流程
- [ ] 测试多场景类型（对白/动作/情绪）
- [ ] 调整 Agent Prompt 与知识分配
- [ ] 文档整理
