# 🚀 Migration from CrewAI to Native Stateful Architecture (HITL Workflow)

## 1. 架构规划与依赖评估 (Planning & Dependencies)
- [ ] 移除对系统侵入性强的 CrewAI 依赖。
- [ ] 仅保留并使用原生 `requests` 库来执行 OpenAI 格式的 HTTP 接口调用（完美兼容代理站，无需编译 32 位轮子）。

## 2. 状态机与节点定义 (Graph State & Nodes)
- [ ] 创建 `agents/state_engine.py`（替换 `crew.py` 中的职责）。
- [ ] 定义并持久化状态（本地 JSON）：包含全局骨架记录以及前台交互记录（当前段落、尾帧图等）。
- [ ] 封装各个阶段为独立的纯函数 API Calling (Raw HTTP)：
  - **阶段一 (全局规划)**: `scene_analyst` -> `story_planner` -> `shot_director`
  - **阶段二 (逐段编译)**: `prompt_compiler` (接收图片 Base64)
- [ ] 构建自建的断点唤醒控制流。

## 3. 后端 API 接口重构 (Backend FastAPI)
- [ ] 在 `ui/app.py` 中引入带有本地 JSON 持久化的读写逻辑，用于跟踪 `task_id`。
- [ ] 修改 `/api/run` 接口：仅执行阶段一（全局宏观分析），并在抵达阶段二开头时挂起。
- [ ] 新增 `/api/resume` 接口：接收前端传来的“尾帧文本/URL上传”，从断点唤醒执行阶段二。
- [ ] 修改 `/api/status` 以适配由 LangGraph 提供的新状态追踪逻辑。

## 4. 前端交互界面升级 (Frontend UI)
- [ ] 在 `ui/templates/index.html` 的执行结果区域新增“等待人类输入框”。
- [ ] 添加逻辑：当检测到后端处于 `suspended` 状态时，弹出尾帧图片或描述输入框。
- [ ] 实现前端发起的异步 `POST /api/resume` 请求以驱动流水线前行。

## 5. 测试与联调 (Verification)
- [ ] 测试全新的全局骨架生成是否连贯。
- [ ] 验收断点续传功能：服务器中断或刷新网页能否找回当前状态。
- [ ] 完成整体联调后确认效果。
