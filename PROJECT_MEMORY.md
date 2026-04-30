# AI Director Studio - 项目记忆与进度文档

> **最后更新时间**: 2026-04-17 17:00 (北京时间)  
> **目的**: 确保换电脑后可以无缝衔接当前工作进度，新对话中直接把本文件喂给 AI 即可恢复全部上下文

---

## 一、项目概况

**项目名称**: AI Director Studio (AI短剧导演系统)  
**项目路径**: `AI_Director_Studio` (可移动到任意磁盘)  
**核心功能**: 基于 LLM 多 Agent 的 AI 短剧导演流水线，将剧本自动转换为 Seedance/Kling 视频生成 Prompt  
**Python 版本**: 3.11.9 (64位，路径 `D:\Python311-64`)

### 系统架构（LangGraph 状态机流水线）

```
剧本输入
  ↓
rhythm_rewrite_director (节奏总控与改写导演)  ← 增补动作细节与氛围，输出 atmosphere_strategy
  ↓
scene_analyst (场景分析师)  ← 提取时间/地点/人物/核心动作
  ↓
story_planner (故事规划师)  ← 15秒分片规划，输出 YAML 骨架
  ↓
shot_director (镜头导演)  ← 景别/焦段/运镜/子分镜设计
  ↓ (进入 Phase 2，逐段编译)
prompt_compiler (提示词编译导演)  ← 编译为最终视频生成 Prompt
  ↓
quality_inspector (质检员)  ← 规则合规检查，pass/warn/fail
  ↓
[等待用户上传尾帧] → video_analyst → 编译下一段...
```

### 技术栈
- Python 3.11+ (主语言)
- LangGraph + SQLite 检查点 (Agent 编排 + 断点续传)
- OpenAI-compatible API (通过 comfly.chat 中转)
- FastAPI + Web UI (ui/app.py)
- 混合知识库检索 (BM25 + 向量库 ChromaDB)
- 22 个 markdown 知识库规则文件

---

## 二、API 配置 (2026-04-17 实测通过)

### API 网关
- **统一网关地址**: `https://ai.comfly.chat/v1`
- **协议**: OpenAI 兼容格式

### 三组 API Key（按模型厂商分渠道）

| 渠道 | Key | 适用模型 |
|:---|:---|:---|
| **Claude 渠道** | `sk-REDACTED` | claude-opus-4-6, claude-sonnet-4-6 |
| **GPT 渠道** | `sk-REDACTED` | gpt-5.4-pro, gpt-5.4, gpt-5.4-mini, deepseek-r1 |
| **Gemini 渠道** | `sk-REDACTED` | gemini-3.1-pro-preview-thinking-high |
| **向量库 Embedding** | `sk-REDACTED` | qwen3-embedding-8b |

### 各 Agent 节点最终模型配置

| Agent 节点 | 模型 | 渠道 | Temperature | 选型理由 |
|:---|:---|:---|:---|:---|
| **全局兜底(llm)** | `claude-opus-4-6` | Claude | 0.3 | 最高智力上限兜底 |
| **rhythm_rewrite_director** | `claude-opus-4-6` | Claude | 0.4 | 最强文学性+台词保护能力 |
| **scene_analyst** | `gpt-5.4-mini` | GPT | 0.1 | 简单抽取，超低延迟 |
| **story_planner** | `claude-sonnet-4-6` | Claude | 0.3 | 结构化 YAML 输出+逻辑骨架 |
| **shot_director** | `gpt-5.4` | GPT | 0.3 | 空间调度+景别设计 |
| **prompt_compiler** | `gpt-5.4-pro` | GPT | 0.5 | 视觉 Prompt 扩展+光影语感 |
| **quality_inspector** | `deepseek-r1` | GPT | 0.1 | 深度推理纠错 |
| **video_analyst** | `gemini-3.1-pro-preview-thinking-high` | Gemini | 0.1 | 原生视频/帧解析 |

---

## 三、已知的渠道兼容性问题（踩坑记录）

> ⚠️ 这些都是在 2026-04-17 实机测试中发现的硬约束，换渠道前务必重新测试

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| `claude-opus-4-7` 返回 503 | Claude Key 所在分组 (cc) 不支持 4.7 | 降级为 `claude-opus-4-6` |
| `claude-sonnet-4-6-thinking` 在 shot_director 持续 524 | 知识库注入 260 chunks，prompt 极大，thinking 模型内部推理时间超出网关超时限制 | shot_director 切换到 GPT 渠道的 `gpt-5.4` |
| `claude-sonnet-4-6-thinking` 在 story_planner 偶发 524 | 同上但略好，约 50% 成功率 | 已改为非 thinking 的 `claude-sonnet-4-6`，100% 稳定 |
| `claude-sonnet-4-6` 在 shot_director 仍 524 | Claude 渠道网关对长响应不友好 | shot_director 必须用 GPT 渠道 |
| story_planner 偶尔首次 HTTP 错误 | 渠道不稳定 | 代码已有指数退避重试（2s→4s→8s→16s），通常第2次即成功 |

### 如果将来渠道升级了，可以尝试恢复的理想配置

```yaml
# 理想配置（需要渠道支持 4.7 和 thinking 且不超时）
story_planner:  claude-sonnet-4-6-thinking   # 自带校验，拆片逻辑更强
shot_director:  claude-sonnet-4-6-thinking   # 空间推演更精准
rhythm_rewrite_director: claude-opus-4-7     # 文学性更上一层
```

---

## 四、知识库文件清单 (knowledge/ 目录，共 22 个)

| 文件 | 核心职责 | 对应 Agent |
|:---|:---|:---|
| 01_导演分镜总手册.md | 景别定义总纲 | 全局 |
| 02_焦段景深与景别画幅策略.md | 焦段、景深、画幅技术 | shot_director |
| 03_镜头切换与推进规则.md | 主分镜/子分镜层级、切镜触发条件 | shot_director |
| 04_对白与表演镜头规则.md | 台词嵌入、完整发言单元、炸点/受击 | shot_director, prompt_compiler |
| 05_剧本拆分与15秒片段规划规则.md | 15秒片段拆分、片段边界、A/B/C三级受击决策树 | story_planner |
| 06_连续性与安全规则.md | 空间继承、场面总控、道具连续性 | 全局 |
| 07_Seedance输出词典与模型适配.md | Seedance模型的输出格式适配 | prompt_compiler |
| 08_错误纠偏与判例库.md | 常见错误案例与修正方案 | quality_inspector |
| **09_节奏总控与剧本改写规则.md** | **改写边界、台词保护禁令、atmosphere_strategy 输出** | **rhythm_rewrite_director** |
| 11_场景分析输入卡与导演意图提取.md | 输入卡模板、导演判断流程 | scene_analyst |
| 14_动作描述精细化控制规则.md | 动作写执行句而非结果句，S/A/B三档精度 | prompt_compiler |
| 15_故事节奏控制规则.md | 节拍(建立/预压/炸点/受击等)+运镜联动 | shot_director |
| 17_结果质检与回溯修正规则.md | QC检查项(拆片/镜头/动作/空间等) | quality_inspector |
| 18_情绪锚点与逐段交互与仰拍限制补丁.md | 情绪锚点+逐段交互工作流+仰拍限制 | shot_director |
| 19_Gold_Standard_Prompt范例.md | 最终输出格式的权威范例(范例A-F) | prompt_compiler |
| 20_镜头库与机位库.md | 镜头类型表(SH-xxx)和机位表(CAM-xxx) | shot_director |
| 21_镜头调用规则与多机位模板.md | 条件化镜头调用规则(R-001~R-010)+多机位模板 | shot_director |
| 22_多机位分镜与镜头多样性规则.md | 多机位分镜与跳切减法 | shot_director |
| 23_视频教学提取_全场景分镜与转场库.md | 基于视频原片提取的实战微短剧干货法则汇总 | 全局 |

---

## 五、当前工作进度

### ✅ 已完成的重大里程碑

1. **知识库体系建设** ✅ — 22个规则文件全部就位
2. **Agent 流水线搭建** ✅ — LangGraph 状态机，支持逐段交互(上传尾帧继续)
3. **Web UI 打包** ✅ — main.py 默认启动 Web UI，支持角色/场景图片上传与视频续接
4. **知识库 10 大冲突审计与修复** ✅ — 三级决策树 + 范例F + 精度分级 + 质检同步
5. **节奏总控导演节点新增** ✅ — rhythm_rewrite_director，09号知识库文件
6. **视频原生解析管线** ✅ — video_analyst 使用 Gemini 3.1 Pro
7. **模型配置全面升级 (2026-04-17)** ✅ — 从旧的 deepseek/mini 全面升级为旗舰模型
8. **全链路测试通过 (2026-04-17)** ✅ — 使用"4-1 高端餐吧"剧本，Phase1+Phase2 全部 pass

### 最新测试结果 (2026-04-17)

**测试剧本**: 4-1 高端餐吧（乔熙、商北琛、陈进）  
**结果**: ✅ Phase 1 (规划) + Phase 2 (片段1编译) 全部通过  
**质检评级**: pass  
**输出文件**: `output/full_pipeline_result.txt` (667行 / 43KB)  
**拆片结果**: 5个片段 (F01-F05)

| 片段 | 时长 | 内容 |
|:---|:---|:---|
| F01 | ~12秒 | 商北琛整理袖口发令 → 乔熙受击拒绝 |
| F02 | ~13秒 | 商北琛用公司规则压迫 → 乔熙二次受击 → 向陈进道歉 |
| F03 | ~10秒 | 大手扣腰 → 乔熙被扛上肩（动作顶点前切） |
| F04 | ~12秒 | 商北琛扛着乔熙走向门口 → 乔熙喊话 |
| F05 | ~10秒 | 陈进当场石化 → 酒液滑落 → 收束 |

---

## 六、已完成的冲突修复 (2026-04-16)

### 10大知识库冲突归因

所有冲突归根结底是**两套并行逻辑的拉扯**:

| 逻辑体系 | 核心价值 | 代表文件 |
|:---|:---|:---|
| **导演语义逻辑** | 主分镜/子分镜层级、完整发言、炸点/受击递进、节拍控制 | 03, 04, 11, 15 |
| **视频模型约束逻辑** | 单片段单主体、实际生成稳定性、避错拆段 | 05(规则07), 19(范例A) |

### 修复方案

1. **05 规则07 改写** ✅ → 从"独立受击必须换片段"改为 A/B/C 三级条件化决策树
2. **19 新增范例F + 范例A措辞调整** ✅ → 消解"主导=唯一"的误读
3. **14/18 精度分级标准** ✅ → 动作精度 S/A/B 三档，情绪锚点不堆砌
4. **17 质检规则同步** ✅ → 碎片段不自动 fail，受击者只查"是否遗漏"
5. **22 多机位措辞微调** ✅ → 引用05规则07三级决策树

---

## 七、关键文件索引

| 文件 | 用途 |
|:---|:---|
| `config/settings.yaml` | **核心配置！** 所有模型、API Key、知识库配置 |
| `agents/director_graph.py` | LangGraph 流水线主文件 (1557行) |
| `agents/knowledge_base.py` | 知识库检索逻辑 (BM25+向量混合) |
| `knowledge/` | 22个知识库规则文件 |
| `ui/app.py` | Web UI 后端入口 |
| `main.py` | CLI入口 (默认 ui，也支持 build-db / run) |
| `test_full_pipeline.py` | 全链路测试脚本（推荐用于验证） |
| `output/` | 测试输出结果 |

---

## 八、换电脑操作步骤

### 环境搭建
```bash
# 1. 安装 Python 3.11+ (64位)
# 2. 安装依赖
pip install -r requirements.txt

# 3. 构建向量知识库 (首次必须)
python main.py build-db

# 4. 设置代理（如果需要，在 main.py 第29-31行修改端口）
# 默认: HTTP_PROXY=http://127.0.0.1:9674
```

### 快速验证
```bash
# 跑全链路测试（不需要参考图）
python test_full_pipeline.py

# 输出在 output/full_pipeline_result.txt
```

### 启动 Web UI
```bash
python main.py
# 浏览器打开 http://127.0.0.1:8686
```

### ⚠️ 注意事项
1. `config/settings.yaml` 中的 API Key 已配好，如果过期需要更换
2. 代理端口 `9674` 需要与本机的科学上网工具一致（在 main.py 中修改）
3. 首次运行必须 `python main.py build-db` 构建向量库
4. 如果 Claude 渠道升级支持了 `claude-opus-4-7`，可以在 settings.yaml 中替换
5. 如果渠道网关超时限制解除，可以尝试把 story_planner/shot_director 换回 `thinking` 版本

---

## 九、下一步计划

### 优先级 1: 多片段端到端验证
- 目前只测试了 Phase 2 的片段1编译
- 需要测试完整的 5 个片段编译流程（需要模拟尾帧上传）
- 验证片段间的连续性锚点是否真正生效

### 优先级 2: 视频生成实测
- 将编译好的 Prompt 实际投入 Seedance/Kling 生成视频
- 检查生成的画面是否匹配分镜设计
- 根据实际生成效果调优 prompt_compiler 的输出格式

### 优先级 3: Web UI 打包与部署
- 验证 Web UI 在新版模型配置下的表现
- 重新打包 exe（使用 main.py Web UI 入口）

---

## 十、历史对话参考

| 对话ID | 时间 | 主题 | 关键成果 |
|:---|:---|:---|:---|
| 539fc36b | 04-15 | 知识库审计与重构 | 合并15+16、重构05 v5.2、新增22、更新17/19 v2.0 |
| 0f6b343a | 04-15 | 10大冲突验证 | Claude Code 冲突清单全部行号级验证通过 |
| 6a13c8e6 | 04-16 | 流水线修复 | sub-shot progression regex 修复、gpt-5.4-mini 切换 |
| 54f41712 | 04-16 | UI自动化修复 | JzOrderExport Save-As 对话框逻辑修复 |
| 33640f31 | 04-17 | 自动化性能优化 | JzOrderExport 短路机制、剪贴板输入 |
| **326f3fc3** | **04-17** | **模型全面升级** | **旗舰模型配置、3组API Key分渠道、全链路测试pass** |

