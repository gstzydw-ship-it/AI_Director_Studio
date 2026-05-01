# Director Graph 拆分收口大纲

本文件用于约束 `agents.director_graph` / `agents.director_graph_package` 拆分任务，防止并行智能体继续扩大范围。

当前阶段不是继续大规模重构，而是 **冻结边界、完成验收、只修拆分阻塞问题**。

## 1. 总目标

把原来的 monolith `agents/director_graph.py` / `legacy_impl.py` 收敛为：

- `agents/director_graph.py`：只做 backward-compatible shim。
- `agents/director_graph_package/nodes.py`：只做 graph node delegation。
- `agents/director_graph_package/*_impl.py`：承载各节点和节点专属 helper。
- `agents/director_graph_package/runners.py` / `state_store.py` / `graph_api.py`：承载运行入口、状态存储和 graph 构建。
- `legacy_impl.py`：保留兼容导出，不作为新代码依赖入口。

## 2. 当前拆分状态

`nodes.py` 当前 delegation 目标如下：

| Node | 目标模块 | 状态 |
| --- | --- | --- |
| `rhythm_rewrite_director_node` | `rhythm_rewrite_impl.py` | 已拆出 |
| `director_showrunner_node` | `planning_context_impl.py` | 已拆出，待最终验收 |
| `scene_analyst_node` | `planning_context_impl.py` | 已拆出，待最终验收 |
| `story_planner_node` | `story_planner_impl.py` | 已拆出，待最终验收 |
| `shot_director_node` | `shot_director_impl.py` | 已拆出，但旧测试债较多，本轮不扩修 |
| `wait_for_segment_request_node` | `segment_flow_impl.py` | 已拆出 |
| `segment_complete_node` | `segment_flow_impl.py` | 已拆出 |
| `prompt_compiler_node` | `prompt_compiler_impl.py` | 已拆出 |
| `quality_inspector_node` | `quality_inspector_impl.py` | 已拆出 |
| `qc_router_node` | `quality_inspector_impl.py` | 已拆出 |

## 3. 本轮明确不做

- 不删除 `legacy_impl.py` 里的旧节点函数。
- 不修 `shot_director_impl.py` 的历史架构债，除非它阻塞 import 或 compile。
- 不重写 prompt/compiler/quality/runner 的业务规则。
- 不新增新的拆分方向。
- 不做格式化全仓、编码修复、命名大改。
- 不把 helper 为了“更干净”到处搬家，除非有明确反向依赖或循环 import。

## 4. 拆分判定标准

某一条线只有同时满足以下条件，才算完成：

1. 对应 node 在 `nodes.py` 只委托到目标 `_impl.py`。
2. 目标 `_impl.py` 中包含 node 实现和直接 helper。
3. 目标 `_impl.py` 不反向 import `agents.director_graph`。
4. 目标 `_impl.py` 不为了调用节点逻辑而依赖 `legacy_impl`。
5. `legacy_impl.py` 中旧函数保留或 shim 保留，兼容旧 import。
6. `compileall` 通过。
7. 该线最小相关 pytest 通过。
8. 剩余失败能明确归为其他线或历史测试债。

## 5. 并行任务线

### A. Coordinator / 集成负责人

负责人：主智能体。

允许修改：

- `docs/director_graph_split_plan.md`
- 必要时 `agents/director_graph.py`
- 必要时跨线测试清单

禁止修改：

- 不直接改业务节点实现，除非修集成冲突。

职责：

- 分配并行任务。
- 审核 dirty 文件来源。
- 跑组合验证。
- 维护最终验收表。
- 发现跑偏时立即冻结新任务。

验收命令：

```powershell
python -m compileall agents\director_graph.py agents\director_graph_package
python -m pytest tests\test_call_llm_network.py tests\test_session_state_isolation.py tests\test_phase2_resume_direct.py tests\test_video_bridge_handoff.py tests\test_clear_segment.py tests\test_prompt_compiler_boundaries.py tests\test_quality_inspector_merge.py -q
```

### B. Planning Context 线

适合交给 Cline。

允许修改：

- `agents/director_graph_package/planning_context_impl.py`
- `tests/test_director_showrunner_orchestration.py`
- `tests/test_scene_vision_analyst.py`

只读查看：

- `agents/director_graph_package/nodes.py`
- `agents/director_graph_package/legacy_impl.py`

禁止修改：

- `story_planner_impl.py`
- `segment_flow_impl.py`
- `runners.py`
- `state_store.py`
- `graph_api.py`
- `prompt_compiler_impl.py`
- `quality_inspector_impl.py`
- `shot_director_impl.py`
- `agents/director_graph.py`

目标：

- 确认 `director_showrunner_node` 和 `scene_analyst_node` 完整实现位于 `planning_context_impl.py`。
- 确认 `nodes.py` 只 delegation 到 `planning_context_impl.py`。
- 确认 `legacy_impl.py` 兼容保留。
- 去掉不必要的 `agents.director_graph` 反向依赖。

验收命令：

```powershell
python -m compileall agents\director_graph_package\planning_context_impl.py agents\director_graph_package\nodes.py agents\director_graph_package\legacy_impl.py
python -m pytest tests\test_director_showrunner_orchestration.py tests\test_scene_vision_analyst.py -q
```

### C. Story Planner 线

允许修改：

- `agents/director_graph_package/story_planner_impl.py`
- `tests/test_story_planner_*.py`

禁止修改：

- 其他 `_impl.py`
- `agents/director_graph.py`
- `runners.py`
- `state_store.py`

目标：

- 收紧 story planner 对包内 `llm/prompting/state_store/helpers` 的依赖。
- 保持 schema / validator 行为不被重写。
- 不顺手修 shot director 旧测试。

验收命令：

```powershell
python -m compileall agents\director_graph_package\story_planner_impl.py
python -m pytest tests\test_story_planner_*.py -q
```

### D. Segment Flow 线

允许修改：

- `agents/director_graph_package/segment_flow_impl.py`
- segment flow / video bridge 专属测试

禁止修改：

- `story_planner_impl.py`
- `planning_context_impl.py`
- `runners.py`
- `agents/director_graph.py`

目标：

- `wait_for_segment_request_node` / `segment_complete_node` 不反向依赖 `legacy_impl` 或 `agents.director_graph`。
- tail-frame / video bridge helper 留在 segment flow 边界内。

验收命令：

```powershell
python -m compileall agents\director_graph_package\segment_flow_impl.py agents\director_graph_package\nodes.py
python -m pytest tests\test_video_bridge_handoff.py tests\test_phase2_resume_direct.py tests\test_clear_segment.py -q
```

### E. Runner 线

允许修改：

- `agents/director_graph_package/runners.py`
- `agents/director_graph_package/state_store.py`
- `agents/director_graph_package/graph_api.py`
- runner / phase2 专属测试

禁止修改：

- 所有节点 `_impl.py`
- `agents/director_graph.py`

目标：

- `run_phase_1_planning`、`run_phase_2_compile_segment`、`run_full_pipeline` 走 package graph。
- `_invoke_graph` / `_normalise_graph_result` 不回跳到 legacy 节点实现。
- `route_after_qc` / `route_after_segment` 委托到对应新模块。

验收命令：

```powershell
python -m compileall agents\director_graph_package\runners.py agents\director_graph_package\state_store.py agents\director_graph_package\graph_api.py
python -m pytest tests\test_phase2_resume_direct.py -q
```

### F. Prompt Compiler 线

允许修改：

- `agents/director_graph_package/prompt_compiler_impl.py`
- `tests/test_prompt_compiler_*.py`

禁止修改：

- 其他 `_impl.py`
- `runners.py`
- `agents/director_graph.py`

目标：

- 使用包内 `.llm`、`.prompting`、`.state_store`。
- 不反向依赖 `agents.director_graph`。
- `legacy_impl` 仅作为无法本轮迁走的兼容 helper 来源，不作为节点执行入口。

验收命令：

```powershell
python -m compileall agents\director_graph_package\prompt_compiler_impl.py
$files = Get-ChildItem tests -Filter 'test_prompt_compiler_*.py' | ForEach-Object { $_.FullName }; python -m pytest $files
```

### G. Quality Inspector 线

允许修改：

- `agents/director_graph_package/quality_inspector_impl.py`
- quality inspector 专属测试

禁止修改：

- `prompt_compiler_impl.py`
- 其他 `_impl.py`
- `runners.py`
- `agents/director_graph.py`

目标：

- `quality_inspector_node` / `qc_router_node` 直接使用包内 state store。
- `route_after_qc` 路径清晰。
- 不为了小 helper 拉入 monolith。

验收命令：

```powershell
python -m compileall agents\director_graph_package\quality_inspector_impl.py
python -m pytest tests\test_quality_inspector_merge.py -q
```

### H. Shot Director 线

本轮默认冻结。

允许动作：

- 只读盘点。
- 只修 import / compile 阻塞。

禁止动作：

- 不重写 deterministic review board。
- 不恢复旧三阶段 schema。
- 不为了通过旧测试重做架构。

验收命令：

```powershell
python -m compileall agents\director_graph_package\shot_director_impl.py
```

## 6. 智能体通用规则

每个智能体必须遵守：

- 只改自己允许范围内的文件。
- 看到范围外 dirty 文件，不要 revert，不要格式化。
- 不新增任务线。
- 不修“看起来顺手”的旧测试。
- 不删除 `legacy_impl.py` 里的兼容函数。
- 汇报必须包含：修改文件、验证命令、通过/失败、失败归因。

## 7. 完成汇报模板

```text
任务线：

修改文件：
- ...

未修改但只读核查：
- ...

完成项：
- ...

验证：
- command -> result

剩余失败：
- 无 / 与本线无关，原因：...
```

## 8. 最终收口清单

最终收口只看这些结果：

- `nodes.py` 10 个节点 delegation 全部正确。
- `agents/director_graph.py` 是 shim，不承载业务节点实现。
- `legacy_impl.py` 兼容保留，不作为新路径主入口。
- `compileall` 全 package 通过。
- 每条线的最小测试通过。
- 旧 shot director 测试失败如仍存在，单独列为历史债，不阻塞本轮拆分。

