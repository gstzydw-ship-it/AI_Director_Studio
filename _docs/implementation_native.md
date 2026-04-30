# 架构升级：从 CrewAI 迈向原生有状态断点长交互工作流

本次升级旨在抛弃 CrewAI 单向“发射即遗忘”的线性执行流，采用 **自建的原生状态机 (Native Stateful Machine)** 实现完全兼容原有导演知识库理念的“有状态断点续传”交互模式。核心能力是让系统能够**在每个片段的生成之间暂停，等待使用者输入真实的尾帧状况后再次前行。**

这种自研原生架构（抛弃重量级的 LangGraph / CrewAI）的好处是：**无需安装任何需要 C++/Rust 编译的复杂依赖（完美兼容 32 位 Python），速度更快，且可以直接对 OpenAI API 发送包含 Base64 图片数据的原生 HTTP 请求！**

## User Review Required
> [!IMPORTANT]
> 需要用户首肯：在刚才的尝试中，我发现由于你的 Python 环境是 32 位版本，所有业内流行的重量级框架（如 LangGraph, CrewAI 的底层依赖）在你的机器上都会因为没有 32 位预编译库而无法安装/升级。
> **因此，我果断调整了战术，决定亲自动手为你手写一个“超轻量级、无依赖、速度极快”的原生状态机！** 效果与 LangGraph 完全一致，甚至更贴合你的看图生文需求！

## Proposed Changes

### 1. `agents/state_engine.py` [NEW]
我们将把原有的 `crew.py` 重构为基于 `原生 Python 字典 + JSON 持久化` 的状态机流程图。
- **状态 (State) 定义：**
  包含所有的过程资产，如：`script`, `scene_analysis`, `story_plan`, `shot_skeleton`, `segment_list` (列表形式存储各片段骨架), `current_segment_index` (int), 以及 `user_tail_frame_input`。
- **执行节点 (Nodes)：** 直接使用 `requests` 库调用代理站点的 `/v1/chat/completions`。
  - **`analyze_scene_node`**：读取剧本，调用大模型生成场景分析。
  - **`plan_story_node`**：根据场景分析生成拆片方案。
  - **`direct_shots_node`**：根据拆片方案为**所有片段**生成主副分镜骨架。
  - **`compile_segment_node`**：关键更新。仅对当前 `current_segment_index` 所指的单一片段生成 Prompt。支持接收前端传入的 `Base64` 尾帧图谱，拼接成多模态 Prompt 发送！
- **边与中断 (Edges & Interrupts)：**
  在 `compile_segment_node` 执行完毕后，保存状态为 `suspended` 到本地文件。程序在此刻挂起，不再继续消耗资源，等待外部触发。

### 2. `ui/app.py` [MODIFY]
- 接管原先单纯通过 `crew.kickoff()` 执行后台线程的方式，更换为通过 `MemorySaver` 来维护所有任务的 `thread_id`。
  - **`/api/run`**：创建新的 `thread_id`，启动跑全集的图节点，跑到第一个段落生成处后挂起。
  - **`/api/resume` [NEW]**：接收携带 `thread_id` 和“尾帧描述/图谱”的新请求，唤醒图节点继续走入下一次的 `compile_segment_node`。
  - **`/api/status`**：获取指定 `thread_id` 对应的运行时状态，区分系统究竟是在 `running`，还是在 `wait_for_user_input`，还是 `finished`。

### 3. `ui/templates/index.html` [MODIFY]
- 修改前端的轮询展示逻辑。
- 当探知状态为 `wait_for_user_input` 时，在界面上动态渲染出上传组件或文本框（例如「上传第 1 段尾帧截图或补充设定」），并展现“继续下一段”的交互按钮。
- 让原本一次性全部展示的 Tab 变为增量展示模式。每次循环新增一个 Fragment Tab。

## Verification Plan

### 手动验收
1. 启动 WebUI，输入测试剧本。点击开始。
2. 观察后台能够在完成场景分析、结构规划、骨干分镜和片段01 Prompt 生成后**自动挂起停住**。
3. 检查前端是否弹出“等待第二段生成：请补充首帧/尾帧”的交互卡片。
4. 提交测试尾帧补充说明给后端。
5. 观察系统**秒级唤醒**，并成功吐出片段02的 Prompt，且这部分 Prompt 正确承接了用户刚才喂养的数据！
