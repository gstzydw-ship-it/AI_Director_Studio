# HANDOFF — agents/director_graph.py 拆分任务（2026-04-28）

## 1. 当前任务目标

将 `agents/director_graph.py`（6577 行单文件）渐进拆分为 `agents/director_graph_package/` 目录结构，**保证功能零变更、每次迁移都经过行为一致性校验**。

**当前状态：已进入"内部 helper 下沉与 monolith 减重"阶段。**

---

## 2. 文件结构现状

### 2.1 旧主文件（未动，仍包含全部原始实现）
- `agents/director_graph.py` — 6577 行，仍为单文件 monolith。所有节点、runner、graph API、内部 helper 均在此文件中。
- 未来阶段会逐渐削减其长度，但目前**不可删除或改名**（下游 `ai_director_integration.py`、`ai_director_core.py` 等仍在直接 `from agents.director_graph import xxx`）。

### 2.2 新 package（已创建并正在填充）

```
agents/director_graph_package/
├── __init__.py      # 惰性导出 graph_api / nodes / runners，修复循环导入
├── types.py         # DirectorState, LLMSettings, constants — 已完整实现
├── llm.py           # call_llm, resolve_llm_settings, _get_llm_settings — 已完整实现
├── state_store.py   # load_state, save_state, clear_state — 已完整实现
├── prompting.py     # build_system_prompt + 多个 prompt helpers — 已真实实现
├── helpers.py       # 轻量状态 / 视频连续性 / 节奏校验 helper — 大部分已真实实现
├── graph_api.py     # create_director_graph — 已完整实现
├── nodes.py         # 全部公开 nodes 已真实实现；无直接 monolith 依赖
└── runners.py       # 所有公开 runner 均已为真实实现
```

---

## 3. 迁移策略（必须遵守）

1. **零行为变更**：每次把函数体从旧文件迁到新模块时，先完整复制源码，不做任何修改。
2. **依赖复用**：迁出的函数如果依赖旧文件的内部 helper（如 `_agent_outputs`、`_persist_update`、`_combined_prompt`），可以继续从旧文件 import，不必急于把 helper 也迁出。
3. **逐函数验证**：迁完后，必须在运行时逐项比对旧函数 vs 新函数的返回值（如 `route_after_qc` 的各分支），确保 `True` 才能提交。
4. **不可修改旧文件的导出**：旧文件中的函数定义暂不可删除，否则直接引用者会崩溃。等所有下游都切到 `agents.director_graph_package` 后再统一清理。

---

## 4. 关键注意事项

### 4.1 旧文件仍被直接引用
多个下游文件（如 `agents/ai_director_integration.py`、`agents/ai_director_core.py`）仍然直接 `from agents.director_graph import ...`。
在旧文件尚未被清空之前，**不可删除旧文件中的任何函数定义**，否则这些下游会崩溃。

### 4.2 LangGraph 注册
`create_director_graph` 中通过 `graph.add_node(...)` 和 `graph.add_conditional_edges(...)` 注册节点与路由。
因此迁 `create_director_graph` 时，必须确保它引用的是 **package 内已经存在的同名节点/路由符号**，否则会出现"表面迁出成功，但 graph 仍在跑旧实现"的假迁移。

---

## 5. helpers.py 当前 monolith 直接 import 状态（2026-04-29 22:23）

`_compiler_guard_report` 已完成真实下沉：
- `agents/director_graph_package/helpers.py` 保留真实实现；
- `agents/director_graph.py` 已改为 `from agents.director_graph_package.helpers import _compiler_guard_report`；
- monolith 内重复定义已删除；
- 快速验证通过：`py_compile` ✓，`agents.director_graph._compiler_guard_report.__module__ == 'agents.director_graph_package.helpers'` ✓。

剩余 4 个 wrapper / 间接依赖点均为"重执行链"大型函数（建议按整条执行链迁移）：

| 函数名 | 类型 | 依赖 monolith 函数 |
|--------|------|-------------------|
| `_run_story_planner_with_schema_repair` | 重执行链 | `_run_story_planner_with_schema_repair` |
| `_run_shot_director_single_pass` | 重执行链 | `_run_shot_director_single_pass` |
| `_run_llm_quality_inspector` | 重执行链 | `_run_llm_quality_inspector` |
| `_run_shot_director_review_board` | 重执行链 | `_run_shot_director_review_board` |

---

## 6. 编译/导入校验结果（2026-04-29）

- `python -m py_compile agents/director_graph_package/*.py` 级别快速编译通过 ✓
- `import agents.director_graph_package.helpers as h` ✓
- `import agents.director_graph_package.nodes as n` ✓
- `import agents.director_graph_package.runners as r` ✓
- `get_agent_knowledge_files` 新旧实现行为一致（`scene_analyst` 全量/critical 两种模式均 True）✓
- `_clean_shot_director_output` 新旧实现行为一致（示例输入 True）✓
- `_validate_story_planner_output` 新旧实现行为一致（3 组样例 True）✓
- `nodes.py` 不含 `from agents.director_graph import` 或 `__import__("agents.director_graph", ...)` 形式的直接依赖 ✓
- `_validate_shot_director_output` 新旧实现行为一致（4 组样例 PASS，issue count 完全一致）✓
- `_validate_shot_director_dialogue_coverage` 新旧实现行为一致（4 组样例 PASS）✓
- `_validate_shot_director_script_fidelity` 新旧实现行为一致（4 组样例 PASS）✓
- `_validate_shot_director_source_event_coverage` 新旧实现行为一致（3 组样例 PASS）✓

---

## 7. 各符号迁移状态一览

### 已完全脱离旧文件的符号（package 真实实现）

**types / llm / state_store / prompting（独立子模块）：**
`DirectorState`, `LLMSettings`, `call_llm`, `resolve_llm_settings`, `_get_llm_settings`, `build_system_prompt`, `_truncate_for_prompt`, `_scene_memory_card`, `_current_segment_event_card`, `_combined_prompt`, `_segment_block`, `_extract_segments`, `_derive_segments_from_planner_output`, `_timeline_blocks`, `_normalise_llm_quality_issues`, `_layout_stage_contract_rules`, `load_state`, `save_state`, `clear_state`, `_persist_update`

**helpers（本地实现）：**
`_agent_outputs`, `_fragment_line_pattern`, `_clean_shot_director_output`, `_validate_shot_director_output`, `_validate_shot_director_dialogue_coverage`, `_validate_shot_director_script_fidelity`, `_validate_shot_director_source_event_coverage`, `_collect_shot_director_issues`, `_is_soft_shot_director_issue`, `_hard_shot_director_issues`, `_agent_runtime_trace`, `_merge_state_update`, `_speed_mode`, `_extract_tail_frame_from_video`, `_analyze_tail_frame`, `_analyze_video_segment`, `_cleanup_rhythm_abstract_language`, `_clean_rhythm_rewritten_script`, `_normalise_script_lines`, `_validate_rhythm_structure_lock`, `_rhythm_insert_continuity_rules`, `_extract_line_subject`, `_detect_inserted_prop_ownership_jump`, `_validate_rhythm_insert_continuity`, `_validate_story_planner_output`

**nodes（无直接 monolith 依赖）：**
`segment_complete_node`, `route_after_qc`, `route_after_segment`, `create_director_graph`, `rhythm_rewrite_director_node`, `director_showrunner_node`, `scene_analyst_node`, `story_planner_node`, `shot_director_node`, `wait_for_segment_request_node`, `prompt_compiler_node`, `quality_inspector_node`, `qc_router_node`

**runners：**
`run_phase_1_planning`, `run_phase_2_compile_segment`, `run_shot_director_resume_from_partial`, `run_shot_director_restart_from_story_plan`, `run_full_pipeline`, `_invoke_graph`

**helpers（跨模块引用，非 monolith）：**
`get_agent_knowledge_files` → 直接引用 `agents.knowledge_base`

### 仍在通过 wrapper 间接复用 monolith 的符号（4 个 wrapper，见上表）

---

## 8. 下一步待办

### Phase D.2：收尾剩余 4 个 monolith wrapper / 间接依赖点（深水区）
这 4 个 wrapper / 间接依赖点背后都是大函数（重执行链含完整 LLM 调用循环），建议整体迁移：
1. `_run_story_planner_with_schema_repair`
2. `_run_shot_director_single_pass`
3. `_run_llm_quality_inspector`
4. `_run_shot_director_review_board`

### Phase E：旧文件缩减
当所有符号完成迁移后，旧文件缩减为仅保留向后兼容的 re-export（或彻底删除）。

---

## 9. 一句话结论

**拆分已进入收尾阶段：graph 层、node 层、runner 层、prompting 层、大部分 helpers 层均已真实迁移至 package。本轮（2026-04-29 22:23）继续完成 `_compiler_guard_report` 真实下沉：monolith 已改为导入 package helper，旧重复定义已删除，`py_compile` 与运行时模块归属验证均通过。当前只剩 4 个重型执行链 wrapper，下一步建议优先处理 `_run_story_planner_with_schema_repair`。**
