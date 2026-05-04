# 分镜流程图生成器 (Storyboard Designer)

## 功能概述

**分镜流程图生成器** (`storyboard_designer_node`) 是一个全新的 LangGraph 节点，插入在 `shot_director` → `wait_for_segment_request` 之间。

### 核心目标
- 每个片段独立生成分镜流程图
- 不再一次性输出全部分段的镜头设计，而是**逐段处理**
- 利用 **gpt-image-2 / DALL-E 3 / GPT-Image-1** 等图像生成 API，在**单张图片**上渲染专业分镜草图
- 支持上传**人物/场景参考图**以保持视觉一致性

## 工作流

```
shot_director 完成第 N 段镜头设计
          ↓
storyboard_designer 提取该段 shots
          ↓
构建分镜流程图专用 prompt（含参考图信息）
          ↓
调用 LLM 生成图像生成专用 prompt（英文）
          ↓
调用图像生成 API（可附带参考图 base64）
          ↓
保存分镜图 → 写入 state
          ↓
wait_for_segment_request（继续原有流程）
```

## 输入 State

| 字段 | 来源 | 说明 |
|------|------|------|
| `agent_outputs["shot_director"]` | shot_director | 该段完整的 YAML 镜头设计 |
| `agent_outputs["story_planner"]` | story_planner | 该段策划上下文（可选） |
| `reference_image_manifest` | UI/CLI 上传 | 参考图元数据列表 |
| `reference_image_b64s` | UI/CLI 上传 | 参考图 base64 编码列表 |
| `active_segment_index` | graph state | 当前处理片段索引 |
| `aspect_ratio` | graph state | 画面比例（默认 16:9） |
| `segment_names` | graph state | 各片段名称列表 |

## 输出 State

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_outputs["storyboard_prompt_seg{N:02d}"]` | str | 图像生成专用 prompt 文本 |
| `agent_outputs["storyboard_image_seg{N:02d}"]` | str | 生成的分镜图文件路径 |
| `storyboard_images_by_segment` | dict | `{segment_index: image_path}` 映射 |

## Prompt 工程策略

### 第一阶段：Prompt 生成器（文本 LLM）

系统 Prompt 角色设定为 "storyboard flowchart prompt engineer"，约束条件：

1. **纯英文输出** — 图像模型对英文 prompt 理解最佳
2. **单张 storyboard sheet** — 所有镜头按序排列在同一画布上
3. **保留全部镜头信息** — shot number、duration、framing、camera angle、movement、subject action、emotional beat
4. **空间布局指令** — panel grid、camera movement arrows、cut markers
5. **视觉一致性注入** — 将参考图描述注入 prompt，指示模型匹配人物造型、服装、场景美学
6. **输出结构契约** — Header + Panel-by-panel descriptions + Style instructions

### 第二阶段：图像生成器

- 使用 `call_llm(..., images_base64=reference_b64s)` 调用图像生成模型
- 支持数据 URI、URL、raw base64 等多种返回格式自动解析
- 失败时回退到保存文本占位，不中断 pipeline

## 参考图上传 API

```python
from agents.director_graph_package.storyboard_designer_impl import (
    generate_storyboard_for_segment,
)

state = {
    "active_segment_index": 1,
    "agent_outputs": {
        "shot_director": "...yaml...",
        "story_planner": "...yaml...",
    },
    "reference_image_manifest": [
        {"filename": "hero.jpg", "description": "男主角参考：黑色西装，短发"},
        {"filename": "office.jpg", "description": "办公室场景参考：现代极简"},
    ],
    "reference_image_b64s": ["data:image/jpeg;base64,/9j/4AAQ...", "..."],
    "aspect_ratio": "9:16",
}

result = generate_storyboard_for_segment(state, segment_index=1)
# result → {"prompt": "...", "image_path": "output/sessions/xxx/storyboards/storyboard_seg01.png"}
```

## Graph 集成

在 `graph_api.py` 中：

```python
# 构建 Graph
graph.add_node("storyboard_designer", storyboard_designer_node)
# 插入在 shot_director 之后
graph.add_edge("shot_director", "storyboard_designer")
graph.add_edge("storyboard_designer", "wait_for_segment_request")
```

## 文件清单

| 文件 | 说明 |
|------|------|
| `agents/director_graph_package/storyboard_designer_impl.py` | 核心实现 |
| `agents/director_graph_package/types.py` | 添加 `storyboard_images_by_segment` |
| `agents/director_graph_package/graph_api.py` | 插入 graph 节点和边 |
| `agents/director_graph_package/nodes.py` | 导出节点函数 |
| `agents/director_graph_package/__init__.py` | 懒加载导出 |
| `config/settings.yaml` | 添加 agent 配置 |
| `agents/director_graph.py` | Shim 层兼容 |
| `tests/test_storyboard_designer.py` | 16 项单元/集成测试 |
| `docs/storyboard_designer_feature.md` | 本文档 |

## 使用场景

1. **导演确认镜头设计** — 每段 shot_director 完成后立即看到可视化分镜，便于人工审核
2. **AI 视频生成前置校验** — 分镜图作为视频生成前的视觉锚点，降低 prompt 理解偏差
3. **参考图驱动一致性** — 上传角色定妆照、场景概念图，确保全片视觉风格统一
4. **逐段迭代优化** — 不满意某段分镜？直接修改该段镜头设计重新生成，不影响其他段

## 扩展建议

- **UI 集成**：在 `ui/app.py` 或 `ui/native_studio.py` 中增加分镜图预览面板
- **批量下载**：提供 `storyboard_images_by_segment` 的打包导出
- **版本对比**：保存历史分镜图，支持 A/B 对比
- **视频预演**：将分镜图序列合成为低帧率 animatic，辅助节奏判断
