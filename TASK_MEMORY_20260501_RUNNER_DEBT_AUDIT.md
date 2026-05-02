# Runner 清债审计 — 2026-05-01

## 一、runners.py 对 legacy_impl 的依赖清单

### 1. `_sync_package_graph_api()` 内联替换（安全）
| 调用 | 归属 | 备注 |
|---|---|---|
| `_impl.create_director_graph = create_director_graph` | **已由 graph_api.py 提供** | `_sync_package_graph_api()` 在调用前注入 |
| `_impl.shot_director_node = shot_director_node` | **已由 shot_director_impl.py 提供** | 同上 |

### 2. 通过 `_impl` 代理的转发函数
| 代理函数 | 底层依赖 | 推荐归属 | 风险 |
|---|---|---|---|
| `_config()` | `legacy_impl._config`（仅 `{"configurable":{"thread_id":thread_id}}`） | **state_store.py**（可独立，无状态） | 🟢 低 |
| `_invoke_graph()` | `legacy_impl._invoke_graph` → `create_director_graph` + `SqliteSaver` + `_normalise_graph_result` + `_config` | **graph_api.py**（图构建） + state_store（checkpointer 路径） | 🟡 中（SqliteSaver 需迁移） |
| `_normalise_graph_result()` | `legacy_impl._normalise_graph_result` → `save_state` + `_combined_prompt` | **state_store.py**（save_state 已独立）+ **segment_flow_impl** 或 **helpers.py**（_combined_prompt） | 🟡 中（_combined_prompt 位置待定） |
| `_merge_state_update()` | `legacy_impl._merge_state_update` → 纯 dict 合并，无外部依赖 | **state_store.py**（state_store 有独立实现 `_persist_update`，但逻辑不同） | 🟢 低（纯函数，可直接迁） |
| `_prepare_phase_2_compile_state()` | `legacy_impl._prepare_phase_2_compile_state` → `_persist_update` + `_analyze_tail_frame` + `_analyze_video_segment` + `_extract_tail_frame_from_video` | **state_store.py**（_persist_update 已独立） + **segment_flow_impl**（3个分析 helper 已在 segment_flow_impl.py 中转发） | 🟢 低（_persist_update 已独立） |

### 3. 直接调用 `_impl.<fn>`（不含转发）
| 调用点 | 函数 | 推荐归属 | 风险 |
|---|---|---|---|
| `run_phase_1_planning()` 内部 | `clear_state()` | **state_store.py**（已有同名函数） | 🟢 低 |
| `run_phase_1_planning()` 内部 | `save_state()` | **state_store.py**（已有同名函数） | 🟢 低 |
| `run_phase_1_planning()` 内部 | `load_state()` | **state_store.py**（已有同名函数） | 🟢 低 |
| `_rerun_shot_director()` 内部 | `load_state()` | state_store.py | 🟢 低 |
| `_rerun_shot_director()` 内部 | `save_state()` | state_store.py | 🟢 低 |
| `_rerun_shot_director()` 内部 | `_agent_outputs(state)` | **helpers.py**（纯 dict 访问，无状态） | 🟢 低 |
| `run_phase_2_compile_segment()` 内联逻辑 | `load_state()` | state_store.py | 🟢 低 |
| `run_phase_2_compile_segment()` 内联逻辑 | `_agent_outputs(state)` | helpers.py | 🟢 低 |
| `run_phase_2_compile_segment()` 内联逻辑 | `save_state()` | state_store.py | 🟢 低 |
| `_run_phase_2_compile_direct()` 内联逻辑 | `_prepare_phase_2_compile_state` | runners.py 或新建 phase2_compile_impl.py | 🟡 中 |
| `_run_phase_2_compile_direct()` 内联逻辑 | `_merge_state_update` | state_store.py | 🟢 低 |

### 4. 未被 runners.py 直接引用但需迁移的关键函数（为后续清债）
| 函数 | 当前归属 | 推荐归属 | 备注 |
|---|---|---|---|
| `_agent_outputs()` | legacy_impl | **helpers.py** | 纯 dict 访问，零依赖 |
| `_persist_update()` | legacy_impl | **state_store.py**（已有同名函数，内容相同） | 可直接合并 |
| `load_state()` | legacy_impl + state_store.py | **state_store.py**（已有同名函数，内容相同） | 可直接合并 |
| `save_state()` | legacy_impl + state_store.py | **state_store.py**（已有同名函数，内容相同） | 可直接合并 |
| `clear_state()` | legacy_impl + state_store.py | **state_store.py**（已有同名函数，内容相同） | 可直接合并 |
| `_combined_prompt()` | legacy_impl | **segment_flow_impl.py**（已在 segment_flow_impl.py 中转发） | 属于片段流程 helper |
| `_analyze_tail_frame()` | legacy_impl | **segment_flow_impl.py**（已在 segment_flow_impl.py 中转发） | 属于片段流程 helper |
| `_analyze_video_segment()` | legacy_impl | **segment_flow_impl.py**（已在 segment_flow_impl.py 中转发） | 属于片段流程 helper |
| `_extract_tail_frame_from_video()` | legacy_impl | **segment_flow_impl.py**（已在 segment_flow_impl.py 中转发） | 属于片段流程 helper |

---

## 二、推荐迁移顺序（低风险 → 高风险）

### 阶段 1：零依赖纯函数迁移（🟢 无风险）

#### Step 1.1：合并 state_store.py 的同名函数
```
修改文件：state_store.py
- 添加 _agent_outputs(state)     # 从 legacy_impl 迁移
- 添加 _merge_state_update(state, update)  # 从 legacy_impl 迁移
- 添加 _normalise_graph_result(result, thread_id)  # 从 legacy_impl 迁移
- 添加 _config(thread_id)  # 从 legacy_impl 迁移
```
- `_persist_update` 在 state_store.py 和 legacy_impl 各有一份，内容相同，合并后删除 legacy_impl 中的。
- `load_state` / `save_state` / `clear_state` 在两文件各有一份，state_store.py 版本更干净，优先用 state_store.py 版本。
- `_agent_outputs` 纯 dict，无外部依赖，直接迁。
- `_merge_state_update` 纯 dict，无外部依赖，直接迁。
- `_config` 纯 dict，无外部依赖，直接迁。
- `_normalise_graph_result` 依赖 `save_state` 和 `_combined_prompt`；`save_state` 已独立后迁入。

#### Step 1.2：确认 segment_flow_impl.py 的转发已就位
```
segment_flow_impl.py 已包含：
- _combined_prompt          (from .legacy_impl import)
- _analyze_tail_frame       (from .legacy_impl import)
- _extract_tail_frame_from_video  (from .legacy_impl import)
- _analyze_video_segment    (from .legacy_impl import)
```
后续清债时，这些 helper 应固化在 segment_flow_impl.py 内部（不再从 legacy_impl import）。

---

### 阶段 2：runners.py 内部清理（🟡 低-中风险）

#### Step 2.1：runners.py 从 state_store 导入同名函数，移除 `_impl` 代理
```
修改文件：runners.py
- 导入: from .state_store import load_state, save_state, clear_state, _agent_outputs, _merge_state_update, _config, _normalise_graph_result
- 删除: from . import legacy_impl as _impl
- 删除: 所有 _impl.<fn> 转发（_config, _invoke_graph, _normalise_graph_result, _merge_state_update, _prepare_phase_2_compile_state）
```

#### Step 2.2：_run_phase_2_compile_direct 拆分
当前 `_run_phase_2_compile_direct` 引用了 `_prepare_phase_2_compile_state`（仍走 `_impl` 转发）。
建议：`_prepare_phase_2_compile_state` 迁入 **state_store.py**（Phase 2 编译准备属于状态管理层），`_run_phase_2_compile_direct` 完整保留在 runners.py。

```
修改文件：state_store.py
- 添加 _prepare_phase_2_compile_state(state, segment_index, tail_frame_b64, video_path)

修改文件：runners.py
- 移除 from . import legacy_impl as _impl 转发
- _run_phase_2_compile_direct 直接从 state_store 导入
```

---

### 阶段 3：_invoke_graph 迁移（🟡 中风险）

`_invoke_graph` 是最大障碍：
- 依赖 `create_director_graph`（graph_api.py 已提供）
- 依赖 `SqliteSaver.from_conn_string(_checkpoint_file())`
- 依赖 `_config(thread_id)`（state_store.py 提供后无虞）
- 依赖 `_normalise_graph_result`

```
修改文件：graph_api.py（推荐）
- 在 create_director_graph() 旁新建 _create_compiled_app(checkpointer)
- 新建 _invoke_graph(input_value, thread_id) 调用 _create_compiled_app().invoke(...)

或修改文件：state_store.py
- 提供 _checkpoint_conn_string() -> str
- _invoke_graph 在 graph_api.py 中调用

修改文件：runners.py
- _invoke_graph 改为从 graph_api 导入（不再走 _impl）
```

**注意**：`create_director_graph` 在 legacy_impl.py 内部有完整版（包含所有节点）。graph_api.py 的版本是否与 legacy_impl 中的版本一致？需要验证：
- `graph_api.create_director_graph()` 当前使用的节点导入来自：`nodes.py`（已迁移）+ `segment_flow_impl`（已迁移），与 legacy_impl 版本应一致。
- 建议迁移前用 `diff` 或 grep 对比两个 `create_director_graph()` 函数的节点列表。

---

### 阶段 4：run_phase_1_planning / run_full_pipeline 迁移（🟡 中风险）

这两个是高层次的 pipeline 编排函数，核心逻辑：
1. 参数校验
2. 构建 initial_state dict
3. `clear_state()` / `save_state(initial_state)`
4. `uuid.uuid4()` 生成 thread_id
5. `thread_id` 存入 state
6. 调用 `_invoke_graph`

```
推荐归属：runners.py 自身
```

将这两个函数从 `legacy_impl` 完整迁移到 `runners.py`：
- `load_state` → from state_store
- `clear_state` → from state_store
- `save_state` → from state_store
- `_invoke_graph` → from graph_api（阶段3后）
- `uuid` / `datetime` → 内联 import
- `DirectorState` 类型 → from .types

**注意**：迁移后需确认 `agents/director_graph.py` 中对 `run_phase_1_planning` / `run_full_pipeline` 的引用路径不变（通过 `runners.py` 或 `legacy_impl` 兼容导入）。

---

## 三、无法在本包内迁移（暂时保留 legacy_impl）

以下功能依赖 langgraph 内部机制或与 `agents/director_graph.py` 顶层模块深度绑定，必须保留在 legacy_impl 直到顶层模块也完成清债：

| 函数 | 原因 |
|---|---|
| `run_shot_director_resume_from_partial()` | 调用 `shot_director_node(state)` — shot_director_impl.py 的节点函数，legacy_impl 内部引用链路深 |
| `run_shot_director_restart_from_story_plan()` | 同上 |
| `run_phase_2_compile_segment()` | 已在 legacy_impl.py 有完整实现（WebUI 直接调用路径），迁移需同步 WebUI 入口 |

---

## 四、风险等级汇总

| 步骤 | 操作 | 文件 | 风险 |
|---|---|---|---|
| 1.1 | 合并 state_store.py 同名函数 | state_store.py | 🟢 低 |
| 1.2 | 验证 segment_flow_impl.py 转发 | — | 🟢 低（只读确认） |
| 2.1 | runners.py 移除 `_impl` 代理 | runners.py | 🟡 中 |
| 2.2 | `_prepare_phase_2_compile_state` 迁入 state_store | state_store.py | 🟢 低 |
| 3 | `_invoke_graph` 迁入 graph_api.py | graph_api.py | 🟡 中 |
| 4 | `run_phase_1_planning` / `run_full_pipeline` 迁入 runners | runners.py | 🟡 中 |

---

## 五、建议验证命令

```bash
# 1. 语法/导入检查
python -m compileall agents/director_graph_package

# 2. 基础单元测试（不跑完整 pipeline）
python -m pytest tests/test_story_planner_schema_guard.py tests/test_rhythm_supervisor_contract.py -q

# 3. shot_director 相关测试（只验证 import 和基本逻辑）
python -m pytest tests/test_shot_director_guards.py -q

# 4. 编译检查后运行
python -c "from agents.director_graph_package.runners import run_phase_1_planning; print('OK')"
```

---

## 六、明确不跑的测试

以下测试依赖完整的 LLM 调用链路、环境变量、网络连接或 SQLite 文件锁，在 runner 清债阶段**不要运行**，以免因环境问题干扰审计判断：

```
❌ tests/test_three_stage_pipeline.py       # 完整 pipeline，需网络 LLM
❌ tests/test_full_pipeline.py               # 完整 pipeline
❌ tests/test_e2e_quick.py                   # 端到端
❌ tests/test_full_director_pipeline.py      # 端到端
❌ tests/test_scene_vision_analyst.py        # 需网络 LLM + base64 图片
❌ tests/test_director_showrunner_orchestration.py  # 需网络 LLM
❌ tests/test_optimized.py                   # 完整 pipeline
❌ tests/test_long.py                        # 长时间运行
```

---

## 七、关键发现

1. **state_store.py 已有完整的 load_state / save_state / clear_state / _persist_update**，但 legacy_impl 也有同名函数。迁移第一步应统一使用 state_store 版本。

2. **`_agent_outputs`、`_merge_state_update`、`_config`、`_normalise_graph_result`** 是 4 个零外部依赖的纯函数，可安全迁入 state_store.py。

3. **`_invoke_graph`** 是最关键的障碍函数，依赖 `SqliteSaver`（langgraph 内部）和 `create_director_graph`（graph_api 已提供独立版本）。迁移时需确保 graph_api.py 的 `create_director_graph()` 与 legacy_impl 中的版本节点完全一致。

4. **`segment_flow_impl.py`** 已通过 `from .legacy_impl import` 方式持有 `_combined_prompt`、`_analyze_tail_frame` 等 helper 的转发，这为后续清理提供了良好基础——下一轮清债时，这些函数可固化在 segment_flow_impl 内部。

5. **runners.py 当前是thin wrapper**：`run_phase_1_planning`、`run_full_pipeline`、`run_shot_director_resume_from_partial`、`run_shot_director_restart_from_story_plan` 均通过 `_impl` 转发，无实际逻辑。迁移后 runners.py 将成为真正的入口模块。
