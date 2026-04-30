# MCP Director Enhanced 使用指南

## 简介

MCP Director Enhanced 是严格遵循您的核心规则和知识库文档的增强版 MCP 导演服务。

### 核心特性

- **规则优先级系统 (P0-P5)**: 严格遵循知识库的优先级裁决
- **Agent 职责边界**: 每个阶段都有明确的职责范围
- **状态合同机制**: 自动维护连续性和状态转移
- **自动规则验证**: 实时验证输出是否符合规则

## 快速开始

### 1. 创建任务

```
/direct 爱情戏分镜
```

### 2. 输入剧本

```
/script
2-1 日/内/咖啡厅
人物：男主角、女主角
▲男主角坐在窗边，看向窗外。
女主角走过来，坐在对面。
女主角：好久不见。
```

### 3. 查看规则

```
/rules
```

### 4. 执行完整流程

```
/run
```

### 5. 验证规则

```
/validate
```

### 6. 获取结果

```
/result full
```

## 规则优先级系统

根据 `00_知识库优先级与冲突裁决规则.md`：

```
P0: 用户显式要求与安全边界
P1: 连续性与模型可生成性 (06, 07, 18)
P2: 片段边界与主分镜合法性 (03, 05)
P3: 故事节奏与剧本层改写 (09, 15)
P4: 镜头调用、多机位与视觉风格 (20, 21, 22)
P5: 范例、案例与源材料 (19, 23)
```

冲突裁决原则：**高优先级规则覆盖低优先级规则**

## 完整命令列表

### 任务管理

| 命令 | 功能 | 示例 |
|------|------|------|
| `/direct` | 开始新任务 | `/direct 任务名 aspect=16:9` |
| `/script` | 输入剧本 | `/script <剧本内容>` |
| `/style` | 设置风格 | `/style mood=浪漫 visual=电影感` |
| `/ref` | 添加参考 | `/ref 主角形象描述` |
| `/status` | 查看状态 | `/status` |
| `/save` | 保存任务 | `/save 任务1` |
| `/load` | 加载任务 | `/load 任务1` |
| `/reset` | 重置任务 | `/reset` |

### 分阶段执行

| 命令 | 阶段 | Agent | 功能 |
|------|------|-------|------|
| `/analyze` | Phase 1 | scene_analyst | 场景分析 |
| `/rewrite` | Phase 2 | rhythm_rewrite_director | 节奏改写 |
| `/plan` | Phase 3 | story_planner | 故事规划 |
| `/shot` | Phase 4 | shot_director | 分镜设计 |
| `/compile` | Phase 5 | prompt_compiler | Prompt编译 |
| `/qc` | Phase 6 | quality_inspector | 质量检查 |
| `/run` | All | - | 执行完整流程 |

### 结果与验证

| 命令 | 功能 | 示例 |
|------|------|------|
| `/result` | 获取结果摘要 | `/result` |
| `/result full` | 获取完整结果 | `/result full` |
| `/result prompts` | 获取Prompt列表 | `/result prompts` |
| `/result shots` | 获取分镜列表 | `/result shots` |
| `/validate` | 验证规则 | `/validate` |
| `/rules` | 查看规则优先级 | `/rules` |
| `/rules <agent>` | 查看Agent规则 | `/rules shot_director` |

## 工作流程示例

### 示例 1: 完整流程

```
/direct 爱情短片 aspect=16:9

/script
2-1 日/内/咖啡厅
人物：男主角、女主角
▲男主角坐在窗边，看着窗外。
女主角走过来，坐在对面。
女主角：好久不见。
男主角：是啊，三年了。
▲两人相视而笑。

/style mood=浪漫 visual=文艺片 pacing=慢节奏

/ref 场景：复古咖啡厅，木质装修，暖色灯光
/ref 主角：男主角30岁，文艺气质；女主角28岁，知性优雅

/run

/validate

/result full
```

### 示例 2: 分阶段控制

```
/direct 悬疑场景

/script
3-1 夜/外/街道
人物：侦探、嫌疑人
▲侦探从阴影中走出。
嫌疑人转身，手伸进口袋。

/analyze

/result

/rewrite

/plan

/shot

/validate

/compile

/qc

/result full
```

### 示例 3: 验证和修正

```
/direct 动作戏

/script
1-1 日/外/屋顶
人物：特工、反派
▲特工从楼顶跳下，翻滚落地。
反派开车追来。

/run

/validate

/save 动作戏_v1

# 发现问题后修正
/script
1-1 日/外/屋顶
人物：特工、反派
▲特工从楼顶跳下，翻滚落地。
反派开车追来，轮胎摩擦地面。
特工拔枪射击。

/run

/validate

/save 动作戏_v2
```

## Agent 职责边界

根据知识库文档，各 Agent 的职责：

### scene_analyst
- 提取场景、人物、关系、空间
- 提取导演意图
- **不得**: 拆片、改写剧本、下最终镜头指令

### rhythm_rewrite_director
- 动作层和氛围层改写
- 节奏阶段标注
- atmosphere_strategy 生成
- **不得**: 改台词、新增事件、强制指定镜头

### story_planner
- 15秒片段规划
- 主分镜骨架
- 完整发言单元保护
- **不得**: 为镜头美学改写剧本

### shot_director
- 镜头、景别、机位设计
- 反拍、转场规划
- 多机位规划
- **必须**: 继承上游片段骨架
- **不得**: 重拆片、改台词

### prompt_compiler
- 分镜编译为 Seedance prompt
- **不得**: 新增剧情、重新发明镜头逻辑

### quality_inspector
- 检查冲突、遗漏
- 连续性检查
- 模型风险评估
- **可以**: 指出问题
- **不得**: 直接重写上游职责范围外的内容

## 状态合同机制

根据 `06_连续性与安全规则.md`，每个片段必须包含：

```yaml
active_cast: 当前活跃人物名单
offscreen_cast: 退场/不可见人物名单
entry_state: 首帧状态
exit_state: 尾帧状态
object_transitions: 道具状态转移
forbidden_continuity: 禁止项
```

## 分镜格式规范

根据 `01_导演分镜总手册.md`，每个分镜必须包含：

```
[时间段] [主体+主体景别] [焦段] [景深] [机位高度] [拍摄角度] [唯一运镜] [动作/表演描述] [光源描述]
```

### 景别代码
- ELS: 极远景
- LS: 远景
- MLS: 中全景
- MS: 中景
- MCU: 中近景
- CU: 近景/特写
- ECU: 极限特写

### 机位高度
- 仰拍（Low Angle）
- 平视（Eye Level）
- 俯拍（High Angle）
- 顶拍（Bird's-eye）

### 运镜类型
- 推镜、拉镜、横移、横摇
- 垂直摇、升降、变焦
- 稳定器跟拍、手持、固定机位

**硬规则：每个分镜只允许一种主导运镜。**

## 规则验证

使用 `/validate` 命令可以验证：

1. **分镜验证**
   - 必填字段检查
   - 景别代码有效性
   - 时间段合法性

2. **连续性验证**
   - 首帧状态继承
   - 轴线一致性
   - 人物位置连续性

3. **状态合同验证**
   - 活跃/退场人物不重叠
   - 状态转移单向性

## 故障排除

### "没有活动任务"
**解决**: 先使用 `/direct` 创建任务

### "请先输入剧本"
**解决**: 使用 `/script` 输入剧本内容

### 规则验证失败
**解决**: 
- 查看具体错误信息
- 根据知识库规则修正
- 参考 `/rules` 查看相关规则

### 状态合同错误
**解决**:
- 检查人物是否同时在活跃和退场列表
- 检查状态转移格式是否正确

## 技术架构

```
用户输入 → CommandParser → MCPDirectorEnhanced
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
              RuleRegistry Knowledge  RuleValidator
                    ↓
              Agent Phases
                    ↓
              StateContract
                    ↓
              ShotDefinition
                    ↓
              Prompt Output
```

## 文件说明

- `mcp_director_knowledge_core.py`: 知识库核心模块
- `mcp_director_enhanced.py`: 增强版 MCP 服务
- `knowledge/`: 知识库目录

## 版本信息

- 版本: 2.0.0 (Enhanced)
- 基于: 知识库规则体系
- 特性: 规则优先级、Agent边界、状态合同、自动验证

## 使用方式

```python
from mcp_director_enhanced import director_chat

# 在聊天中调用
response = director_chat("/direct 测试任务")
response = director_chat("/script 剧本内容...")
response = director_chat("/run")
response = director_chat("/validate")
response = director_chat("/result full")
```

现在您可以开始使用了！有任何问题请使用 `/help` 查看帮助。
