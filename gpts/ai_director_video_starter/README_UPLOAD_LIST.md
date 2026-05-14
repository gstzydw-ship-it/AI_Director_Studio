# AI Director Video Starter GPT 上传清单

## GPT 定位

这个 GPT 不是替代本地 AI Director Studio 的完整流水线，而是作为“视频生成任务前置导演台”：

- 帮用户把一句想法整理成可进入系统的项目输入。
- 按系统流程输出：场景输入卡、片段规划、镜头设计约束、Seedance/视频模型 prompt 草案、质检清单。
- 在逐段生成时追踪尾帧、参考图、人物、道具、轴线和状态合同。
- 不直接编造下游已禁止的信息，不越过用户确认。

## 建议 GPT 名称

AI Director Video Starter

## 建议描述

把剧本、参考图和创作意图整理成 AI Director Studio 可执行的视频生成任务包，支持逐段分镜、Seedance prompt、尾帧续接和质检返修。

## GPT Builder 中需要开启

- Code Interpreter：建议开启，用于整理表格、校验 JSON/YAML、压缩任务包。
- Web Browsing：可不开；只有查模型最新限制或平台规则时再用。
- Image generation：可不开；本 GPT 主要生成任务包和 prompt，不负责最终视频生成。

## 需要上传的知识库文件

最小可用上传以下 6 个文件：

1. `01_system_flow.md`
2. `02_intake_schema.md`
3. `03_agent_contracts.md`
4. `04_prompt_output_template.md`
5. `05_quality_gate.md`
6. `06_tailframe_iteration.md`

如果你的主要工作方式是“我已经拆好片段，只让 GPT 做单段增强和 prompt”，请额外上传：

7. `07_single_segment_execution_protocol.md`

如果 GPTs 文件数量允许，可再上传项目原始知识文件作为增强：

- `knowledge/wiki/index.md`
- `knowledge/wiki/contracts/story_to_shot_contract.md`
- `knowledge/wiki/contracts/shot_to_prompt_contract.md`
- `knowledge/wiki/contracts/prompt_to_quality_contract.md`
- `knowledge/wiki/contracts/continuity_contract.md`
- `knowledge/agent_retrieval_contracts.yaml`
- `knowledge/07_Seedance输出词典与模型适配.md`
- `knowledge/17_结果质检与回溯修正规则.md`
- `knowledge/20_镜头库与机位库.md`
- `knowledge/21_镜头调用规则与多机位模板.md`
- `shot_director_output_example.yaml`
- `final_prompt_example.md`

## 配置顺序

1. 在 GPT Builder 创建新 GPT。
2. 将 `GPT_INSTRUCTIONS.md` 全文粘贴到 Instructions。
3. 上传 6 个最小知识库文件。
4. Conversation starters 建议填：
   - “我有一个短剧想法，帮我整理成视频生成任务包。”
   - “这是我的剧本，请按 AI Director 流程拆成 15 秒片段。”
   - “这是上一段尾帧，请帮我生成下一段的续接输入。”
   - “检查这段 Seedance prompt 是否会破坏连续性。”

## 如果 GPT 只输出 YAML 骨架

在对话里补一句：

```text
进入正式启动模式。请不要只输出结构化字段，必须补齐：项目理解、segment_package、shot_plan、英文 storyboard_designer_prompt、可直接复制到 Seedance 的完整中文成片 Prompt、quality_gate、尾帧续接请求。
```

如果仍然过短，把 `GPT_INSTRUCTIONS.md` 中“正式启动模式”一节重新粘贴到 Instructions 的靠前位置。

## 单片段高颗粒度启动语

你现在的工作流更适合用这条：

```text
进入单片段执行导演模式。

我会提供已经拆好的原剧本片段和场景图。不要重新拆分全片，不要输出摘要型 YAML。请只针对当前片段完成：
1. 剧情增强版，至少250字；
2. 节奏规划，至少4个节拍；
3. 镜头与动作调度表，至少4行，每行写清时间段、镜头、景别/机位/运镜、人物身体动作、表情视线、道具状态、切点理由；
4. 结构化镜头 YAML，至少3个镜头或2个主镜头+1个子分镜；
5. 可直接复制到 Seedance 的完整中文成片 Prompt，至少600字，按时间段展开，每段第一句必须先写镜头基底；
6. quality_gate；
7. 下一步尾帧请求。

硬规则：不新增人物、地点、道具、台词或剧情事实；场景图只用于空间、光线、陈设和氛围；照片中的人物如果不是 active_cast，只能作为照片内容出现，不能真人出现在画面里。
```
