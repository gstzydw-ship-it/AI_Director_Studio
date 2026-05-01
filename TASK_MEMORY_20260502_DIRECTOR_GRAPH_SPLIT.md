# Director Graph Split Memory - 2026-05-02

## Purpose

This memory file records the current director graph split plan, today's progress, validation results, and exact prompts for continuing tomorrow without relying on chat history.

Primary coordination document:

- `docs/director_graph_split_plan.md`

Current branch:

- `拆分`

Remote:

- `origin https://github.com/gstzydw-ship-it/AI_Director_Studio.git`

## Current Rule

The task is now in **scope freeze and acceptance** mode.

Do not open new split lines. Do not refactor business behavior. Do not chase old shot director tests unless the problem blocks import or compile.

All agents must read `docs/director_graph_split_plan.md` before starting and must state:

1. Task line.
2. Allowed files.
3. Forbidden files.
4. Validation commands.
5. Confirmation that they will not touch out-of-scope dirty files.

## Current Split Map

`agents/director_graph_package/nodes.py` currently delegates:

| Node | Target module | Status |
| --- | --- | --- |
| `rhythm_rewrite_director_node` | `rhythm_rewrite_impl.py` | Delegation OK |
| `director_showrunner_node` | `planning_context_impl.py` | Delegation OK, accepted today |
| `scene_analyst_node` | `planning_context_impl.py` | Delegation OK, accepted today |
| `story_planner_node` | `story_planner_impl.py` | Delegation OK, pending tomorrow's focused acceptance |
| `shot_director_node` | `shot_director_impl.py` | Delegation OK, frozen |
| `wait_for_segment_request_node` | `segment_flow_impl.py` | Delegation OK |
| `segment_complete_node` | `segment_flow_impl.py` | Delegation OK |
| `prompt_compiler_node` | `prompt_compiler_impl.py` | Delegation OK |
| `quality_inspector_node` | `quality_inspector_impl.py` | Delegation OK |
| `qc_router_node` | `quality_inspector_impl.py` | Delegation OK |

`graph_api.create_director_graph()` imports nodes from `.nodes`, not directly from `legacy_impl`.

`legacy_impl.py` still keeps old compatible node functions and route functions. Do not delete them in this phase.

## Today's Completed Work

### Coordination / Plan

- Added `docs/director_graph_split_plan.md`.
- The plan defines task lines, allowed files, forbidden files, validation commands, and completion report format.
- The plan is the mandatory guardrail for Cline, TRAE, Tare, Codex subagents, and any other worker.

### `agents/director_graph.py` Shim

- Converted the top-level compatibility module into a lazy-loading shim.
- Kept old imports such as `from agents.director_graph import call_llm` working.
- Preserved old monkeypatch compatibility for `load_config`, `_get_llm_extra_params`, and `OUTPUT_DIR`-based state tests.
- Validated with LLM config and session isolation tests.

### Planning Context Line

Owner: Cline.

Accepted today:

- `director_showrunner_node` implementation is in `planning_context_impl.py`.
- `scene_analyst_node` implementation is in `planning_context_impl.py`.
- `nodes.py` delegates both nodes to `planning_context_impl.py`.
- `legacy_impl.py` keeps compatible same-name functions.
- `planning_context_impl.py` has no reverse import of `agents.director_graph`.
- `planning_context_impl.py` has no dependency on `legacy_impl`.
- It uses package-local `.helpers`, `.llm`, `.state_store`, `.types`, plus knowledge modules.

Validation reported by Cline:

```powershell
python -m compileall agents/director_graph_package/planning_context_impl.py agents/director_graph_package/nodes.py agents/director_graph_package/legacy_impl.py
python -m pytest tests/test_director_showrunner_orchestration.py tests/test_scene_vision_analyst.py -q
```

Result:

- `8 passed`

### Segment Flow Line

Owner: Tare.

Completed earlier in today's session:

- Removed top-level `legacy_impl` import from `segment_flow_impl.py`.
- Removed reverse import from `wait_for_segment_request_node` / `segment_complete_node` to `agents.director_graph`.
- Switched node state helpers to package-local `state_store._persist_update` / `_agent_outputs`.
- Confirmed `nodes.py` delegation for segment flow nodes.
- Confirmed legacy compatibility identity.

Validation:

```powershell
python -m compileall agents/director_graph_package/segment_flow_impl.py agents/director_graph_package/nodes.py agents/director_graph_package/legacy_impl.py
python -m pytest tests/test_video_bridge_handoff.py -q
python -m pytest tests/test_phase2_resume_direct.py -q
python -m pytest tests/test_clear_segment.py -q
```

Reported result:

- `4 passed`
- `2 passed`
- `14 passed`

### Runner Line

Owner: Bacon.

Completed:

- `runners.py` no longer prioritizes `legacy_impl._invoke_graph` monkeypatches.
- Graph restore now goes through package runner / top-level shim `_invoke_graph`.
- Updated `tests/test_phase2_resume_direct.py` to patch `pkg_runners._invoke_graph`.
- Added coverage that `legacy_impl._invoke_graph` overrides are not used by package runner.

Validation:

```powershell
python -m compileall agents/director_graph_package/runners.py agents/director_graph_package/state_store.py agents/director_graph_package/graph_api.py agents/director_graph.py
python -m pytest tests/test_phase2_resume_direct.py -q
```

Reported result:

- `3 passed`

### Prompt Compiler Line

Owner: Faraday.

Completed:

- `prompt_compiler_impl.py` now directly depends on package-local `.llm.call_llm`.
- `prompt_compiler_impl.py` now directly depends on package-local `.prompting.build_system_prompt`.
- `_agent_outputs` and `_persist_update` now come from package-local `.state_store`.
- Added `tests/test_prompt_compiler_boundaries.py`.
- Confirmed `nodes.prompt_compiler_node` delegates to `prompt_compiler_impl.prompt_compiler_node`.

Validation:

```powershell
python -m compileall agents/director_graph_package
$files = Get-ChildItem tests -Filter 'test_prompt_compiler_*.py' | ForEach-Object { $_.FullName }; python -m pytest $files
```

Reported result:

- `38 passed`

### Quality Inspector Line

Owner: Turing.

Completed:

- Removed direct `legacy_impl` and `prompt_compiler_impl` imports from `quality_inspector_impl.py`.
- `quality_inspector_node` / `qc_router_node` now use package-local `state_store._agent_outputs` / `_persist_update`.
- LLM config detection now uses package-local `llm.load_config`.
- Moved inspector-only `_segment_block` / `_timeline_blocks` helpers into `quality_inspector_impl.py`.
- Added tests for agent config detection, QC retry delegation, and `route_after_qc`.

Validation:

```powershell
python -m compileall -f agents/director_graph_package/quality_inspector_impl.py tests/test_quality_inspector_merge.py
pytest tests/test_quality_inspector_merge.py
```

Reported result:

- `5 passed`

### Shot Director Frozen Audit

Owner: Epicurus.

Completed as strict read-only audit:

- `python -m compileall agents/director_graph_package/shot_director_impl.py` passed.
- `nodes.py` delegates `shot_director_node` to `shot_director_impl.shot_director_node`.
- `legacy_impl.py` still keeps compatibility entry points.
- Old shot director test debt remains frozen.
- No file modifications.

## Combined Validation Already Run

During today's integration, Codex ran:

```powershell
python -m compileall agents/director_graph.py agents/director_graph_package
python -m pytest tests/test_call_llm_network.py tests/test_session_state_isolation.py tests/test_phase2_resume_direct.py tests/test_video_bridge_handoff.py tests/test_clear_segment.py tests/test_prompt_compiler_boundaries.py tests/test_quality_inspector_merge.py -q
```

Result:

- `44 passed`

After Cline's planning context report, it also reported:

- `8 passed` for planning context targeted tests.

## Known Dirty / Risk Areas

The worktree had mixed parallel changes today. Files were attributed as:

| File | Line / owner |
| --- | --- |
| `agents/director_graph.py` | Coordinator shim |
| `docs/director_graph_split_plan.md` | Coordinator plan |
| `TASK_MEMORY_20260502_DIRECTOR_GRAPH_SPLIT.md` | Coordinator memory |
| `agents/director_graph_package/planning_context_impl.py` | Planning Context / Cline |
| `tests/test_director_showrunner_orchestration.py` | Planning Context / Cline |
| `tests/test_scene_vision_analyst.py` | Planning Context / Cline |
| `agents/director_graph_package/story_planner_impl.py` | Story Planner, pending focused acceptance |
| `agents/director_graph_package/segment_flow_impl.py` | Segment Flow / Tare |
| `agents/director_graph_package/runners.py` | Runner / Bacon |
| `tests/test_phase2_resume_direct.py` | Runner / Bacon |
| `agents/director_graph_package/prompt_compiler_impl.py` | Prompt Compiler / Faraday |
| `tests/test_prompt_compiler_boundaries.py` | Prompt Compiler / Faraday |
| `agents/director_graph_package/quality_inspector_impl.py` | Quality Inspector / Turing |
| `tests/test_quality_inspector_merge.py` | Quality Inspector / Turing |

Two files appeared dirty in `git status` but had no normal text diff during audit:

- `agents/director_graph_package/helpers.py`
- `tests/test_shot_director_guards.py`

Treat these as red/yellow flags tomorrow. Do not let business agents touch them unless Coordinator first confirms whether the status is line-ending, metadata, or an actual unstaged change.

## Known Remaining Issues

The delegation audit found that some modules may still have stricter-boundary debt:

- `story_planner_impl.py` may still import `legacy_impl`.
- `prompt_compiler_impl.py` may still keep limited `_legacy` bindings for guard/helper compatibility.
- `rhythm_rewrite_impl.py` may still import helpers from `legacy_impl`.
- `segment_flow_impl.py` may still import some legacy helpers.
- `shot_director_impl.py` still uses top-level `agents.director_graph` in places.
- `runners.py` still imports `legacy_impl` for compatibility checks.

Important:

- These are not all blockers for today's acceptance.
- Tomorrow should not blindly fix all of them.
- Use `docs/director_graph_split_plan.md` to decide which line owns each item.

## Tomorrow: Codex Task Prompt

Use this prompt when starting the next Codex session:

```text
Continue the Director Graph split from TASK_MEMORY_20260502_DIRECTOR_GRAPH_SPLIT.md.

First read:
- docs/director_graph_split_plan.md
- TASK_MEMORY_20260502_DIRECTOR_GRAPH_SPLIT.md

Mode:
- Scope freeze and acceptance.
- Do not open new split lines.
- Do not refactor business behavior.
- Do not chase old shot_director tests unless import/compile is blocked.

Immediate goals:
1. Inspect `git status -sb` and `git diff --name-only`.
2. Confirm whether `agents/director_graph_package/helpers.py` and `tests/test_shot_director_guards.py` have real content diff or only line-ending/metadata noise.
3. Run the final combined validation:
   `python -m compileall agents\director_graph.py agents\director_graph_package`
   `python -m pytest tests\test_director_showrunner_orchestration.py tests\test_scene_vision_analyst.py tests\test_call_llm_network.py tests\test_session_state_isolation.py tests\test_phase2_resume_direct.py tests\test_video_bridge_handoff.py tests\test_clear_segment.py tests\test_prompt_compiler_boundaries.py tests\test_quality_inspector_merge.py tests\test_story_planner_schema_guard.py -q`
4. If validation passes, prepare the final acceptance report from `docs/director_graph_split_plan.md`.
5. If validation fails, only fix failures inside the owning task line's allowed files. If a fix would cross task-line boundaries, stop and report.

Do not modify:
- `shot_director_impl.py`, unless compile/import is blocked.
- Any file outside the owning line's allowed list from `docs/director_graph_split_plan.md`.

Final output should include:
- Validation result.
- Which task lines are accepted.
- Which issues remain as historical debt.
- Whether the worktree is ready for final PR/merge.
```

## Tomorrow: Cline Task Prompt

Use this prompt for Cline:

```text
请按 docs/director_graph_split_plan.md 执行任务前置协议。

本次任务线：Story Planner 线。

开始前必须先阅读：
- docs/director_graph_split_plan.md
- TASK_MEMORY_20260502_DIRECTOR_GRAPH_SPLIT.md

开始前先回复执行声明，不要直接改代码。执行声明必须包含：
1. 本次任务属于 Story Planner 线。
2. 本次允许修改的文件：
   - agents/director_graph_package/story_planner_impl.py
   - tests/test_story_planner_*.py
3. 本次禁止修改的文件：
   - 其他所有 *_impl.py
   - agents/director_graph.py
   - agents/director_graph_package/runners.py
   - agents/director_graph_package/state_store.py
   - agents/director_graph_package/graph_api.py
   - tests/test_shot_director_*.py
4. 本次验收命令：
   - python -m compileall agents/director_graph_package/story_planner_impl.py
   - python -m pytest tests/test_story_planner_*.py -q
5. 确认不会修改范围外 dirty 文件，不会扩展新任务线，不会顺手修 shot_director 历史测试债。

任务目标：
1. 收口 story_planner_impl.py 拆分边界。
2. 确认 story_planner_impl.py 不反向 import agents.director_graph。
3. 确认 nodes.py 中 story_planner_node 只 delegation 到 story_planner_impl.story_planner_node，只读核查即可。
4. 确认 legacy_impl.py 中 story_planner_node 兼容保留，只读核查即可。
5. 保持当前 schema / validator 行为，不重写 story planner 业务规则。
6. 不处理 shot_director_impl.py 或旧 shot director 测试失败。

完成后按这个格式汇报：
任务线：
修改文件：
只读核查文件：
完成项：
验证命令与结果：
剩余失败及归因：
```

## Tomorrow: Do Not Do

- Do not ask Cline to continue Planning Context. It is accepted.
- Do not ask any agent to "clean all legacy imports" globally.
- Do not let multiple agents modify the same test file.
- Do not edit `tests/test_shot_director_guards.py` during acceptance unless Coordinator confirms it is only line-ending cleanup and explicitly owns it.
- Do not delete compatibility functions from `legacy_impl.py`.

