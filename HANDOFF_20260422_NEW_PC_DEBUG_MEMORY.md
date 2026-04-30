# 2026-04-22 换电脑继续调试记忆文档

本文档用于在新电脑上继续调试 AI Director Studio。不要把 API key 写进公开文档；本项目当前真实配置在 `config/private/settings.local.yaml`，迁移时单独拷贝或重新填写。

## 当前结论

当前主线问题不是前端单纯显示错误，而是流水线已经多次推进到不同阶段后中断：

1. `story_planner` 旧结构校验太严格的问题已经处理过，当前可以通过。
2. 旧的 `source_script_events` 超过 10 条硬错误已经改成柔性校验，不再直接卡死。
3. 三段镜头导演最初还在用 `claude-opus-4-6-thinking`，导致 524；已经切到 `claude-sonnet-4-6`。
4. 最新一次任务已经跑过节奏改写、场景分析、结构规划，并进入镜头导演。
5. 日志显示 `shot_director_layout` 曾完成，用时约 97.9 秒，但最终没有写入 `agent_outputs`。
6. 后端进程在镜头导演阶段断开，任务没有进入 Prompt 编译，所以没有最终 Seedance Prompt。

最新会话状态：

```text
会话号：web_e97e09f7-4216-4f83-9091-fe6d19355dba
状态：error
步骤：error
开始时间：2026-04-22T14:40:25.941415
当前片段：1
总片段数：4
已有输出：rhythm_rewrite_director, scene_analyst, story_planner
没有输出：shot_director, shot_director_layout, shot_director_blocking, shot_director_guard, prompt_compiler, quality_inspector
```

状态文件位置：

```text
output/sessions/web_e97e09f7-4216-4f83-9091-fe6d19355dba/pipeline_state.json
```

当前提示语：

```text
执行中断：上次任务在镜头导演阶段断开，尚未生成最终 Prompt；已保留节奏改写、场景分析和结构规划输出。
```

## 已做改动

### 1. 简化 story_planner 输出结构

文件：

```text
agents/director_graph.py
tests/test_story_planner_schema_guard.py
```

核心调整：

- `story_planner` 不再负责具体镜头规划。
- 取消对这些字段的硬要求：`main_shots`、`shot_id`、`camera_setup_type`、`primary_subject`、`action_unit`、`line_unit`、`sub_shots`、`sub_shot_strategy`、`beat_design`、`boundary_reason`。
- 当前硬结构主要保留：
  - `fragment_id`
  - `duration_target`
  - `dramatic_unit`
  - `source_script_events`
  - `cast` 或旧 `active_cast`
  - `continuity` 或旧 `state_contract`
  - `reaction_plan`
  - `director_brief`

目的：

- 前面的结构规划师只做“故事段落切分、戏剧任务、连续性、给后面导演的简要意图”。
- 具体镜头、机位、动作拆解、子镜头策略交给后面的镜头导演三段式处理。

### 2. 把 story_planner 的部分硬校验改成柔性 agent 校验

文件：

```text
agents/director_graph.py
```

新增/调整过的逻辑：

- `_story_planner_soft_validation_issues`
- `_parse_story_planner_agent_validation`
- `_run_story_planner_agent_validator`
- `_validate_story_planner_output`
- `_run_story_planner_with_schema_repair`

现在的校验策略：

- 真正结构缺失、源剧本事件不匹配，仍然硬失败。
- “某段事件数量略多”“全局片段密度偏高”“reaction_plan 偏笼统”等，先作为提醒交给校验 agent 判断。
- 如果配置里没有 `validator`，会回退使用 `script_event_validator`。

最新任务中，`story_planner` 的柔性校验通过了。日志里出现过：

```text
agent_validation status: pass
agent_name: script_event_validator
```

说明新思路有效。

### 3. 切换镜头导演模型

文件：

```text
config/private/settings.local.yaml
```

以下 agent 已经切换为：

```text
claude-sonnet-4-6
```

列表：

```text
shot_director
shot_director_layout
shot_director_blocking
shot_director_guard
```

同时去掉了这些镜头导演原来的 `extra_params.thinking` 超长思考参数，避免继续触发网关 524 或不兼容。

当前配置已确认：

```text
shot_director          claude-sonnet-4-6  temperature 0.4  timeout 180
shot_director_layout   claude-sonnet-4-6  temperature 0.4  timeout 180
shot_director_blocking claude-sonnet-4-6  temperature 0.4  timeout 180
shot_director_guard    claude-sonnet-4-6  temperature 0.4  timeout 180
```

### 4. 前端状态同步修复

文件：

```text
ui/templates/index.html
```

修复点：

- 前端轮询只有在后端明确返回 `running...` 状态时，才继续计时和推进步骤。
- 如果后端返回 `idle`、`error` 或其他非运行状态，立刻停表，不再按时间把“质检导演”假亮成运行中。
- 新增“没有最终 Prompt 时展示已有中间输出”的逻辑：
  - 如果已有最终 Prompt，展示 Seedance Prompt。
  - 如果没有最终 Prompt，但有 `story_planner`，默认展示结构规划。
  - 否则回退到场景分析、节奏改写等已有输出。

新增函数：

```text
selectResultTab
showBestAvailableResult
resetStepBadges
```

注意：

- 浏览器可能缓存旧前端脚本。换电脑后第一次打开建议强刷。
- 原电脑上可用 `Ctrl + F5` 强制刷新。

## 已运行过的验证

曾经通过：

```text
py -m py_compile agents\director_graph.py tests\test_story_planner_schema_guard.py
py -m pytest tests/test_story_planner_schema_guard.py -q
```

结果：

```text
13 passed
```

在更早阶段还跑过：

```text
py -m pytest tests/test_three_stage_pipeline.py tests/test_call_llm_network.py -q
```

当时结果：

```text
15 passed
```

但注意：后面又改过前端和配置，换电脑后建议重新跑一遍关键测试。

## 当前 WebUI 与进程

当前原电脑 WebUI：

```text
http://127.0.0.1:8686/
```

最后确认的 WebUI 进程：

```text
D:\Python311-64\python.exe main.py ui
PID: 26280
```

新电脑上启动：

```powershell
py main.py ui
```

如果 `py` 指到错误 Python，使用 64 位 Python 3.11 更稳。

## 知识库说明

用户明确说过：

```text
不要旧的向量库了，那个已经不需要了
```

当前实际运行使用的是项目内新缓存库：

```text
agents/.bm25_cache/vectordb/chroma_data/vectordb.json
```

旧根目录：

```text
vectordb/
```

不要再依赖它。

## 最新一次任务过程

脚本是第 2 集，主要场景：

- 天御集团大堂
- 天御集团顶层
- 角色：乔熙、商北琛、苏小可、严飞、众员工、秦悦等

最新一次运行进度：

1. `rhythm_rewrite_director` 成功。
2. `scene_analyst` 成功。
3. `story_planner` 成功，拆成 4 个片段。
4. `script_event_validator` 对 story_planner 的软问题判定通过。
5. 进入 `shot_director`。
6. 日志显示 `shot_director_layout completed in 97.9s`。
7. 后端进程随后断开，完整镜头设计没有落盘。
8. 最终没有进入 `prompt_compiler`。

日志位置：

```text
output/webui_codex_stdout.log
output/webui_codex_stderr.log
```

状态/检查点：

```text
output/sessions/web_e97e09f7-4216-4f83-9091-fe6d19355dba/pipeline_state.json
output/sessions/web_e97e09f7-4216-4f83-9091-fe6d19355dba/director_graph.sqlite
output/sessions/web_e97e09f7-4216-4f83-9091-fe6d19355dba/director_graph.sqlite-wal
```

## 下一步优先排查

### 首要目标

继续抓“镜头导演阶段进程为什么断开”。

重点不是 `story_planner`，它已经通了。也不是 `shot_director_layout` 的模型连通性，因为它至少完成过一次。重点是：

- layout 完成后结果是否过大？
- layout 输出是否没有被流式写入 `agent_outputs`？
- blocking / guard 调用前是否出现内存、序列化、检查点写入、YAML 解析异常？
- WebUI 后台线程异常是否没有写入 `pipeline_state.json`？
- 进程是否被外部杀掉或崩在 native 库层？

### 建议加的临时日志

在 `agents/director_graph.py` 的 `shot_director_node` 或三段镜头导演调用处加更细日志：

```text
开始 shot_director_layout
layout 返回，字符数是多少
layout 已写入临时状态
开始 shot_director_blocking
blocking 返回，字符数是多少
开始 shot_director_guard
guard 返回，字符数是多少
合并 shot_director 输出开始
合并完成，准备 persist
persist 完成
```

更稳的做法：

- 每个子导演完成后立刻 `_persist_update`。
- 不要等三段都完成后才把完整 `shot_director` 写入状态。
- 可以把中间输出写到：

```text
agent_outputs.shot_director_layout
agent_outputs.shot_director_blocking
agent_outputs.shot_director_guard
```

这样即使进程断了，也能看到是哪一段断的。

### 建议的恢复策略

现在前端显示“镜头设计无输出”是正确的，因为状态文件里确实没有镜头设计输出。

下一轮调试建议：

1. 开 WebUI。
2. 提交同一任务。
3. 盯 `output/webui_codex_stdout.log`。
4. 一旦进入 `shot_director_layout`，记录开始时间。
5. 如果 layout 完成后又断，优先看它完成后的下一行日志。
6. 如果没有下一行，说明断在 layout 返回后的处理/落盘处。

## 常用命令

查看当前会话状态：

```powershell
@'
import json, urllib.request
sid='web_e97e09f7-4216-4f83-9091-fe6d19355dba'
with urllib.request.urlopen(f'http://127.0.0.1:8686/api/status?session_id={sid}', timeout=5) as r:
    obj=json.loads(r.read().decode('utf-8'))
print(json.dumps({
    'status': obj.get('status'),
    'step': obj.get('step'),
    'message': obj.get('message'),
    'started_at': obj.get('started_at'),
    'current_segment_index': obj.get('current_segment_index'),
    'total_segments': obj.get('total_segments'),
    'agent_keys': list((obj.get('agent_outputs') or {}).keys()),
}, ensure_ascii=False, indent=2))
'@ | py -
```

查看 WebUI 进程：

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*main.py ui*' } |
  Select-Object ProcessId,CreationDate,CommandLine |
  Format-List
```

查看端口：

```powershell
Get-NetTCPConnection -LocalPort 8686 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess,CreationTime |
  Format-Table -AutoSize
```

启动 WebUI：

```powershell
py main.py ui
```

如果需要后台启动并写日志：

```powershell
$out='output\webui_codex_stdout.log'
$err='output\webui_codex_stderr.log'
Start-Process -FilePath 'D:\Python311-64\python.exe' `
  -ArgumentList @('main.py','ui') `
  -WorkingDirectory (Get-Location).Path `
  -RedirectStandardOutput $out `
  -RedirectStandardError $err
```

跑测试：

```powershell
py -m py_compile agents\director_graph.py tests\test_story_planner_schema_guard.py
py -m pytest tests/test_story_planner_schema_guard.py -q
```

## 迁移到新电脑时要带的东西

必须带：

```text
agents/
config/
knowledge/
tests/
ui/
main.py
requirements.txt
pyproject.toml
models.json
reference_images/
output/sessions/web_e97e09f7-4216-4f83-9091-fe6d19355dba/
HANDOFF_20260422_NEW_PC_DEBUG_MEMORY.md
```

如果要复现这次任务，还要带 `output/sessions/...` 里的会话文件和参考图。

如果要让新电脑直接连模型，需要处理：

```text
config/private/settings.local.yaml
```

这个文件里有密钥，不要公开提交。

## 最重要的下一句

下一台电脑不要从 `story_planner` 继续纠结。现在应该集中抓：

```text
shot_director_layout 完成之后，为什么完整 shot_director 没有落盘，并且 WebUI 后端进程断开。
```

## 2026-04-22 新电脑继续处理记录

已按本文档接手并确认当前 session：

```text
session_id: web_e97e09f7-4216-4f83-9091-fe6d19355dba
status: error
step: error
total_segments: 4
agent_outputs: rhythm_rewrite_director, scene_analyst, story_planner
shot_director runtime: null
```

本轮发现的代码层原因：

- 三段镜头导演原本是在 `_run_shot_director_three_stage()` 内部连续跑完三段后才统一返回。
- `shot_director_layout` 完成后只存在局部变量 `stage_outputs["layout"]` 中，没有立刻写入 `pipeline_state.json`。
- 如果进程在 layout 完成后、blocking/guard 期间断开，状态文件会完全看不到 `shot_director_layout`。
- WebUI 的异常处理还会用内存中的旧 `task_state` 保存 error 状态，可能覆盖掉 graph 节点已经写到磁盘的中间产物。

已修复：

```text
agents/director_graph.py
```

- `_run_shot_director_three_stage()` 新增 `stage_callback`。
- layout / blocking / guard 每段完成并校验后，立即回调保存。
- `shot_director_node()` 新增 `persist_stage()`：
  - 保存 `agent_outputs.shot_director_layout`
  - 保存 `agent_outputs.shot_director_blocking`
  - 保存 `agent_outputs.shot_director_guard`
  - guard 完成时同步保存 `agent_outputs.shot_director`
  - 同步写入 `knowledge_metadata.shot_director.runtime`
  - 同步写入 `knowledge_metadata.shot_director.stage_retrieval`

```text
ui/app.py
```

- 新增 `_merge_latest_disk_state_for_session()`。
- Phase 1 / Phase 2 后台线程异常保存 error 前，先合并磁盘上的最新状态。
- 避免 UI 报错时覆盖掉刚刚由 graph 节点保存的 `shot_director_layout` 等中间输出。

新增/更新测试：

```text
tests/test_three_stage_pipeline.py
tests/test_session_state_isolation.py
```

- `test_three_stage_persists_layout_before_blocking_failure`
- `test_ui_error_state_merge_preserves_latest_disk_outputs`

已运行验证：

```powershell
python -m py_compile agents\director_graph.py ui\app.py tests\test_three_stage_pipeline.py tests\test_session_state_isolation.py
python -m pytest tests/test_three_stage_pipeline.py tests/test_session_state_isolation.py tests/test_call_llm_network.py -q
python -m pytest tests/test_story_planner_schema_guard.py tests/test_knowledge_runtime_policy.py -q
```

结果：

```text
20 passed
34 passed
```

当前配置复核，未打印密钥：

```text
story_planner          claude-sonnet-4-6  temp 0.3  timeout 180  max_tokens 16384
shot_director          claude-sonnet-4-6  temp 0.4  timeout 180  max_tokens 16384
shot_director_layout   claude-sonnet-4-6  temp 0.4  timeout 180  max_tokens 16384
shot_director_blocking claude-sonnet-4-6  temp 0.4  timeout 180  max_tokens 16384
shot_director_guard    claude-sonnet-4-6  temp 0.4  timeout 180  max_tokens 16384
prompt_compiler        gpt-5.4            temp 0.2              max_tokens 16384
```

WebUI 已启动：

```text
http://127.0.0.1:8686/
PID: 42268
```

下一步：

1. 从 WebUI 重新提交同一任务或只跑当前 session 的 shot_director 阶段。
2. 如果后端再次断开，先看 `pipeline_state.json` 是否已经出现：
   - `shot_director_layout`
   - `shot_director_blocking`
   - `shot_director_guard`
3. 如果只出现 `shot_director_layout`，说明断在 blocking 前/期间。
4. 如果出现 layout + blocking，说明断在 guard 前/期间。
5. 如果三者都出现但没有 `shot_director`，说明断在最终合并/落盘附近。

## 2026-04-22 晚：前后端进度同步与 UI Agent 命名修复

新增修复：

```text
ui/app.py
```

- `/api/status` 现在以 LangGraph 已写盘的 `step/message` 为准。
- 修复了后台线程仍在运行时，状态接口把磁盘中的真实进度覆盖回旧内存快照的问题。
- 修复了活任务运行中但磁盘状态没有 `thread_id` 时，被误判为旧残留并切成 `idle` 的问题。

```text
ui/templates/index.html
ui/static/style.css
```

- 前端流水线从 5 个显示节点改为 6 个真实职责节点：
  - 节奏总控：`rhythm_rewrite_director`
  - 场景分析：`scene_analyst`
  - 结构规划：`story_planner`
  - 三段镜头导演：`shot_director_layout / shot_director_blocking / shot_director_guard`
  - Seedance 编译：`prompt_compiler`
  - 质检导演：`quality_inspector`
- 移除了按运行时间猜测进度的前端逻辑。
- 前端步骤状态改为只根据后端 `status/step/message/agent_outputs` 渲染。
- 错误状态会把真正卡住的阶段标红，例如当前旧会话会定位到“三段镜头导演”。
- “三段镜头”结果标签会优先显示最新已落盘的 `shot_director_guard / blocking / layout`，方便判断断在三段式导演的哪一段。

新增测试：

```text
tests/test_session_state_isolation.py
```

- `test_status_refresh_uses_disk_progress_for_live_task`

已运行验证：

```powershell
node -e "const fs=require('fs'); const html=fs.readFileSync('ui/templates/index.html','utf8'); const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n'); new Function(scripts); console.log('frontend script syntax ok');"
python -m py_compile ui\app.py tests\test_session_state_isolation.py
python -m pytest tests/test_session_state_isolation.py -q
python -m pytest tests/test_three_stage_pipeline.py tests/test_call_llm_network.py -q
python -m pytest tests/test_story_planner_schema_guard.py -q
python -m pytest tests/test_knowledge_runtime_policy.py -q
```

结果：

```text
frontend script syntax ok
5 passed
16 passed
13 passed
21 passed
```

当前 WebUI：

```text
http://127.0.0.1:8686/
PID: 42268
```

## 2026-04-22 晚：新提交任务监控结果

监控 session：

```text
legacy_migrate_test
```

阶段推进：

```text
22:20:09  running_phase_1 / step_1_analyze
          节奏总控导演正在改写剧本...（1/6）

22:22:05  rhythm_rewrite_director 已落盘
          节奏改写完成，场景分析师正在分析...（2/6）

22:22:57  scene_analyst 已落盘
          结构规划师正在拆片规划...（3/6）

22:24:23  story_planner 已落盘
          total_segments = 4
          segment_names = 片段01, 片段02, 片段03, 片段04
          进入 shot_director_layout

22:28:21  shot_director_layout 已落盘
          output_chars = 8256
          elapsed_seconds = 218.636
          进入 shot_director_blocking

22:31:02  error
          shot_director_blocking 调用期间 LLM 网络连接失败
```

本轮真实卡点：

```text
三段镜头导演的第二段：shot_director_blocking
```

状态文件中已有输出：

```text
rhythm_rewrite_director
scene_analyst
story_planner
shot_director_layout
```

状态文件中没有：

```text
shot_director_blocking
shot_director_guard
shot_director
```

错误关键内容：

```text
RuntimeError: LLM 网络连接失败（已重试 2 次）。
httpx.ConnectError / httpcore.ConnectError:
[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)

Traceback 指向：
_run_shot_director_three_stage
  -> _call_shot_director_stage
  -> call_llm
  -> shot_director_blocking
```

判断：

- story_planner 正常。
- shot_director_layout 正常，并且已经落盘。
- WebUI 后端进程没有断，错误来自上游 LLM HTTPS/TLS 连接。
- 当前最该修的是 `shot_director_blocking` 这类中间阶段失败后的恢复/重试策略：
  - 可以复用已落盘的 `shot_director_layout`，只重跑 `shot_director_blocking`；
  - 或增加 blocking/guard 阶段级别的重试与恢复入口；
  - 或把 `call_llm` 的 SSL/TLS 连接错误重试次数、退避时间、代理策略单独调高。
