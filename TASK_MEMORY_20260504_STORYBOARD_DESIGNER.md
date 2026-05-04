# 任务记录：分镜流程图设计环节

**日期**: 2026-05-04  
**任务**: 设计分镜流程图环节 — 分镜导演不再输出全部分段镜头设计，改为每段分别设计，每生成一段加入一个分镜流程图设计。  
**提交 Commit**: 504a8aa（含所有分镜流程图相关改动）

---

## 1. 需求背景

用户希望：
- 分镜导演不需要输出全部分段的镜头设计，改为**每段分别设计**
- 每生成一段镜头设计后，加入一个**分镜流程图设计**环节
- 分镜导演可以输出**专属于 gpt-image-2 的分镜流程图设计 prompt**
- 通过 API 上传人物场景参考图和每段的镜头设计，生成专业的分镜流程草图 prompt
- 调用图像生成 API，在一张图片上生成分镜流程图

## 2. 核心实现

### 2.1 后端 LangGraph 节点

**新建文件**: `agents/director_graph_package/storyboard_designer_impl.py`

该节点核心功能：
1. **逐段处理**：读取 `shot_director` 输出中当前片段的各镜头设计
2. **镜头解析**：用正则提取每个镜头的机号、景别、动作、对白、运镜等字段
3. **Prompt 构建**：将解析出的镜头信息翻译成**专用于 gpt-image-2 的英文视觉 prompt**，包含：
   - panel grid 指令（横向多格排列）
   - camera arrows / cut markers / perspective labels
   - reference image annotations（REFERENCE IMAGE #1 / #2 / #3）
   - aspect ratio / frame borders / black ink style
4. **参考图注入**：自动将用户上传的人物/场景参考图附加到 prompt 中
5. **图像生成**：调用图像生成 API（`gpt-image-2`），获取图片后保存到 `output/storyboards/`
6. **状态存储**：将结果写入 `storyboard_prompt_seg{index}`、`storyboard_image_seg{index}`、`storyboard_images_by_segment`

**节点插入位置**：`shot_director` → `storyboard_designer` → `wait_for_segment_request`

### 2.2 状态类型扩展

**修改文件**: `agents/director_graph_package/types.py`

新增字段：
```python
storyboard_images_by_segment: dict = field(default_factory=dict)  # 各片段的分镜图数据
storyboard_prompt_seg01: str = ""
storyboard_image_seg01: str = ""  # 以此类推
```

### 2.3 Graph API 更新

**修改文件**: `agents/director_graph_package/graph_api.py`

在 `_build_storyboard_graph()` 函数中：
```python
graph.add_node("shot_director", _shot_director_node)
graph.add_node("storyboard_designer", _storyboard_designer_node)
graph.add_edge("shot_director", "storyboard_designer")
graph.add_conditional_edges(
    "storyboard_designer",
    _route_segment_or_wait,
    {"compile": "prompt_compiler", "wait": "wait_for_segment_request"},
)
```

### 2.4 配置系统

**修改文件**: `config/settings.yaml`

新增 `storyboard_designer` agent 配置：
```yaml
storyboard_designer:
  model: "gpt-image-2"
  temperature: 1.0
```

### 2.5 节点导出与懒加载

**修改文件**: `agents/director_graph_package/nodes.py`、`agents/director_graph_package/__init__.py`、`agents/director_graph.py`

新增 `storyboard_designer_node` 导出和懒加载机制。

## 3. Web UI 集成

### 3.1 流水线步骤展示

**修改文件**: `ui/templates/index.html`

在"三段镜头导演"和"Seedance编译"之间新增第 5 步：
```html
<div class="step" id="step-storyboard">
    <div class="step-icon">🎨</div>
    <div class="step-info">
        <div class="step-name">分镜流程图</div>
        <div class="step-desc">可视化设计</div>
    </div>
    <div class="step-status">等待</div>
</div>
```

STEP_ORDER 从 6 步扩展为 7 步：
```javascript
const STEP_ORDER = ['rhythm', 'analyze', 'plan', 'direct', 'storyboard', 'compile', 'inspect'];
```

### 3.2 结果标签页

新增"🎨 分镜流程图"标签页：
```html
<button class="result-tab" data-agent="storyboard_designer">🎨 分镜流程图</button>
```

点击后调用 `renderStoryboardImages()` 函数，按片段展示分镜图卡片。

### 3.3 分镜图卡片展示

- 每个片段一张卡片，显示标题"片段 X 分镜流程图"
- 图片通过 `/api/storyboard_image?path=xxx` 安全加载
- 支持"显示/隐藏生成 Prompt"切换，可查看传递给 gpt-image-2 的完整 prompt

### 3.4 API 端点

**修改文件**: `ui/app.py`

新增端点：
```python
@app.get("/api/storyboard_image")
async def api_storyboard_image(path: str = ""):
    """返回分镜流程图图片文件"""
    # 安全检查：只允许访问 output/storyboards 目录
```

### 3.5 CSS 样式

**修改文件**: `ui/static/style.css`

新增 `.storyboard-card`、`.storyboard-image-wrap`、`.storyboard-prompt-toggle` 等样式，暗色主题 + 玻璃态效果。

## 4. 测试覆盖

**新建文件**: `tests/test_storyboard_designer.py`

16 项测试全部通过：

| 测试类别 | 测试数量 | 说明 |
|---------|---------|------|
| 镜头解析 | 4 | 提取镜头数量、字段、片段元信息、格式化 |
| 片段块解析 | 2 | 正确/缺失场景 |
| 参考图注释 | 2 | 无清单/有清单 |
| Prompt 构建 | 1 | prompt 结构验证 |
| 图片保存 | 2 | 文本回退/Data URI 保存 |
| 节点行为 | 2 | 无导演输出时跳过/无解析镜头时跳过 |
| Graph 集成 | 2 | 节点存在性/节点位置验证 |
| 逐段生成 | 1 | 返回字典含正确字段 |

运行结果：
```bash
$ py -m pytest tests/test_storyboard_designer.py -v
16 passed in 2.75s
```

## 5. 文档

**新建文件**: `docs/storyboard_designer_feature.md`

完整说明：
- 架构位置（pipeline 中的位置）
- 执行流程图
- 状态字段说明
- 错误处理策略
- 未来优化方向（多 panel、动画预览、图层编辑等）

## 6. 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `agents/director_graph_package/storyboard_designer_impl.py` | 新建 | 分镜流程图节点核心实现 |
| `agents/director_graph_package/types.py` | 修改 | 新增分镜相关状态字段 |
| `agents/director_graph_package/graph_api.py` | 修改 | 插入 storyboard 节点 |
| `agents/director_graph_package/nodes.py` | 修改 | 导出 storyboard_designer_node |
| `agents/director_graph_package/__init__.py` | 修改 | 懒加载新节点 |
| `agents/director_graph.py` | 修改 | Shim 模块更新 |
| `config/settings.yaml` | 修改 | 新增 agent 配置 |
| `ui/templates/index.html` | 修改 | 流水线步骤 + 标签页 + 图片渲染 |
| `ui/app.py` | 修改 | 新增图片 API 端点 |
| `ui/static/style.css` | 修改 | 分镜图卡片样式 |
| `tests/test_storyboard_designer.py` | 新建 | 16 项测试 |
| `docs/storyboard_designer_feature.md` | 新建 | 功能文档 |
| `AGENTS.md` / `CLAUDE.md` | 修改 | 索引更新 |

**总计**: +1,168 行，-13 行

## 7. 使用方式

1. 启动 Web UI：`py ui/app.py`
2. 在浏览器打开 http://127.0.0.1:8686
3. 输入剧本，上传人物/场景参考图
4. 点击"启动导演流水线"
5. 流程运行到"三段镜头导演"后，自动进入"🎨 分镜流程图"步骤
6. 切换结果区"🎨 分镜流程图"标签页，查看各片段的分镜流程图
7. 可点击"显示生成 Prompt"查看传给 gpt-image-2 的完整英文 prompt

## 8. 未来优化方向

- **多 panel 独立生成**：当前为单图多格，未来可支持每镜头独立 panel
- **动画预览**：添加简单的镜头切换动画预览
- **交互式编辑**：支持拖拽调整镜头顺序、修改机位标注
- **与 Seedance 联动**：将分镜图作为 Seedance 视频生成的首帧参考
