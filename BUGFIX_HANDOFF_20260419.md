# Bugfix Handoff - AI Director Studio Production Flow

Date: 2026-04-19

Workspace:

`E:\AI_Director_Studio_Pack_20260417\AI_Director_Studio`

Primary Web UI:

`http://127.0.0.1:8686`

Python used during debugging:

`D:\Python311-64\python.exe`

## Current State

The current active browser/session id used during debugging:

`web_54eb5750-9f23-4ff9-ac8e-326041cd323e`

Current verified API state:

```text
status: done
step: ""
current_segment_index: 4
active_segment_index: 3
total_segments: 3
last_qc_status: warn
message: 全部片段 Prompt 已生成完成。
compiled_segment_3: present
error: ""
```

Current Web service was restarted after the final patch and was listening on port `8686`.

Latest verified uploaded video used to generate segment 3:

`output\uploaded_segment_videos\20260419_104238_5.mp4`

## User-Visible Symptoms

The user saw several repeating failures:

```text
当前工作流并非处于挂起等待状态，无法执行单段编译。
```

```text
片段 2 自动返修后仍未通过质检，请查看质检报告后清除上一段重跑，或重新启动导演流水线。
```

Later the UI appeared stuck at:

```text
等待上一段视频输入（片段 3）
```

while the pipeline stepper still showed the quality inspector as running.

Finally, the user said they had already uploaded the video. That was true: the video upload and video analysis had succeeded, but segment 3 was not compiled because of a state/checkpoint split.

## Root Causes Found

### 1. Errors Were Persisted To The Wrong Session

In `ui/app.py`, exception handlers previously persisted failures after `request_scope(session_id=...)` had exited. That caused errors to write into the default `local` session instead of the active `web_*` session.

Effect:

- The active Web session looked like it was still running.
- The real error was hidden in `output\sessions\local\pipeline_state.json`.
- The user saw tasks sit on a step for hours.

Fix:

- Added `_save_task_state_for_session(session_id, state, runtime_config=None)`.
- Exception handlers now persist inside the correct `request_scope`.
- Added live task tracking with `active_task_threads`.

### 2. UTF-8 BOM Broke State Loading

Some `pipeline_state.json` files had a UTF-8 BOM. `json.load(..., encoding="utf-8")` failed with:

```text
Unexpected UTF-8 BOM (decode using utf-8-sig)
```

The Web API swallowed the exception, then returned default in-memory `idle`.

Fix:

- `agents/director_graph.py` now reads state with `encoding="utf-8-sig"`.
- State saving now uses temp file + `os.replace()` to avoid partial JSON reads.

### 3. QC Rules Misread Negative Constraints As Positive Actions

Segment 2 prompt contained valid constraints like:

```text
严飞已退出画面，不再出现。
禁止重新打开、再次打开、被冲开。
不拍成拥抱、怀里、贴身暧昧或亲密对视。
```

Old QC treated those as:

- Yan Fei still visible.
- Elevator door reopened.
- Collision romanticized.

Fix:

- Added negative-clause filtering.
- Added `_positive_continuity_text()`.
- Added `_has_door_rebound()`.
- Relaxed upstream old-asset rebound to warning if final prompt is correct.
- Added `_normalise_compiled_prompt()` to clean deterministic prompt damage before QC.

### 4. Frontend Showed Waiting State As Running

Backend was correctly in:

```text
waiting_for_user_input
```

but the UI stepper saw `step_5_inspect` and marked "质检导演" as running.

Fix:

- Added frontend `markWaitingForInput(state)`.
- Waiting state now marks the inspect step as `等待输入`.
- The message now says the real next action:

```text
片段 2 已完成，请上传片段 2 完整视频后生成片段 3
```

### 5. Critical Final Root Cause: State File And LangGraph Checkpoint Diverged

This was the most important production bug.

The state file had been repaired to:

```text
waiting_for_user_input, current_segment_index=3
```

but the LangGraph sqlite checkpoint was still stuck at the old segment 2 auto-repair failure.

When `/api/resume` called:

```python
_invoke_graph(Command(resume=payload), thread_id)
```

LangGraph resumed from the old checkpoint and dragged the workflow back to segment 2. This caused:

- Uploaded video was accepted.
- Tail frame/video analysis ran.
- `compiled_segment_3` never appeared.
- UI went back to waiting for segment 3.

Final fix:

- `run_phase_2_compile_segment()` no longer depends on old LangGraph checkpoint resume for phase 2.
- It now uses the state file as source of truth and executes phase 2 directly:

```text
video analysis -> prompt_compiler_node -> quality_inspector_node -> qc_router_node -> segment_complete_node
```

This avoids stale checkpoint rollback.

## Files Changed

### `agents/director_graph.py`

Important changes:

- `QC_RULE_VERSION = 2`
- `load_state()` uses `utf-8-sig`
- `save_state()` uses temp file + `os.replace`
- `_normalise_compiled_prompt()`
- `_without_negative_clauses()`
- `_positive_continuity_text()`
- `_has_door_rebound()`
- `quality_inspector_node()` normalizes prompt before QC
- `quality_inspector_node()` writes `qc_rule_version`
- `recover_repairable_pipeline_state()`
- `run_phase_2_compile_segment()` no longer resumes stale LangGraph checkpoint for single-segment phase 2
- `wait_for_segment_request_node()` clears `last_qc_status` when starting a new segment

### `ui/app.py`

Important changes:

- `active_task_threads`
- `RUNNING_STATUSES`
- `BLOCKING_STATUSES`
- `_has_live_task()`
- `_register_task_thread()`
- `_unregister_task_thread()`
- `_save_task_state_for_session()`
- `_recover_stale_running_state()`
- `_refresh_task_state_from_disk()` calls `recover_repairable_pipeline_state()` only when there is no live task
- `api_run()` and `api_resume()` register background threads
- exception handlers persist errors to the correct session
- `api_resume()` blocks duplicate resumes while a live task exists

### `ui/templates/index.html`

Important changes:

- Added `markWaitingForInput(state)`
- Waiting-for-user-input UI no longer shows inspector as running
- Waiting message now clearly tells which completed segment video to upload

## Current Verification Commands

Check current status:

```powershell
@'
import urllib.request, json
sid='web_54eb5750-9f23-4ff9-ac8e-326041cd323e'
with urllib.request.urlopen(f'http://127.0.0.1:8686/api/status?session_id={sid}', timeout=5) as r:
    data=json.loads(r.read().decode('utf-8'))
print(data.get('status'), data.get('step'), data.get('current_segment_index'), data.get('active_segment_index'), data.get('total_segments'), data.get('last_qc_status'))
print(repr(data.get('message')))
print('has compiled3', bool((data.get('agent_outputs') or {}).get('compiled_segment_3')))
print('error', repr(data.get('error')))
'@ | D:\Python311-64\python.exe -
```

Expected now:

```text
done  4 3 3 warn
'全部片段 Prompt 已生成完成。'
has compiled3 True
error ''
```

Check server:

```powershell
Get-NetTCPConnection -LocalPort 8686 -ErrorAction SilentlyContinue |
  Where-Object State -eq 'Listen' |
  Select-Object LocalAddress,LocalPort,State,OwningProcess |
  Format-Table -AutoSize
```

Restart Web UI:

```powershell
$p = Get-NetTCPConnection -LocalPort 8686 -ErrorAction SilentlyContinue |
  Where-Object State -eq 'Listen' |
  Select-Object -First 1 -ExpandProperty OwningProcess
if ($p) { Stop-Process -Id $p -Force; Start-Sleep -Seconds 1 }
$out = Join-Path (Get-Location) 'output\webui_restart_stdout.log'
$err = Join-Path (Get-Location) 'output\webui_restart_stderr.log'
Start-Process -FilePath 'D:\Python311-64\python.exe' `
  -ArgumentList 'main.py','ui' `
  -WorkingDirectory (Get-Location) `
  -RedirectStandardOutput $out `
  -RedirectStandardError $err `
  -PassThru
```

Syntax check:

```powershell
@'
import ast
from pathlib import Path
for p in [Path('agents/director_graph.py'), Path('ui/app.py')]:
    ast.parse(p.read_text(encoding='utf-8'))
    print(f'AST OK {p}')
'@ | D:\Python311-64\python.exe -
```

Frontend script check:

```powershell
$script = (Get-Content -LiteralPath ui\templates\index.html -Raw -Encoding UTF8) `
  -replace '(?s)^.*<script>', '' `
  -replace '(?s)</script>.*$', ''
$script | node --check -
```

## Important State Files

Active session state:

`output\sessions\web_54eb5750-9f23-4ff9-ac8e-326041cd323e\pipeline_state.json`

Default local state:

`output\sessions\local\pipeline_state.json`

Uploaded videos:

`output\uploaded_segment_videos\`

Auto extracted tail frames:

`output\auto_tail_frames\`

The sqlite checkpoint can be stale:

`output\sessions\<session_id>\director_graph.sqlite`

Do not trust it for phase 2 debugging. The final fix deliberately avoids depending on it for single-segment compile.

## How To Continue On Another Computer

Copy the whole project folder if possible, including:

- source code
- `output\sessions`
- `output\uploaded_segment_videos`
- `output\auto_tail_frames`
- any config files required for API access

If copying only the patch scope, copy these files:

- `agents\director_graph.py`
- `ui\app.py`
- `ui\templates\index.html`

Also copy current state/output if you need the same completed run:

- `output\sessions\web_54eb5750-9f23-4ff9-ac8e-326041cd323e`
- `output\uploaded_segment_videos\20260419_104238_5.mp4`
- generated tail frame files under `output\auto_tail_frames`

After copying:

1. Start Web UI with:

```powershell
D:\Python311-64\python.exe main.py ui
```

2. Open:

```text
http://127.0.0.1:8686
```

3. If the page shows stale UI state, hard refresh:

```text
Ctrl + F5
```

4. Verify API status with the command above.

## Things To Watch For

- If the UI says waiting for upload but the user already uploaded, inspect `tail_frame_analysis`.
  - If `tail_frame_analysis` exists but `compiled_segment_N` does not, suspect phase 2 progression.
  - This should now be fixed by removing checkpoint dependency in phase 2.

- If state says `running_phase_2` but no live thread exists, `_recover_stale_running_state()` may convert it to error.
  - But if QC already finished as warn/pass, `recover_repairable_pipeline_state()` should now complete it.

- If old QC fail appears again, check `qc_rule_version`.
  - Old failures with no `qc_rule_version` should be re-evaluated.
  - New failures under `QC_RULE_VERSION=2` should remain real failures unless rules are changed again.

- If prompt has broken text like `Wait a` or `【风格锚点` without bracket, `_normalise_compiled_prompt()` should repair known deterministic damage before QC.

## Last Known Good Result

The final direct phase 2 test generated segment 3 successfully using:

`output\uploaded_segment_videos\20260419_104238_5.mp4`

Observed successful result:

```text
RESULT done  4 3 warn
MSG 全部片段 Prompt 已生成完成。
HAS3 True
QC3 总体评级：warn
```

The `warn` items were non-blocking legacy upstream-asset warnings, mostly missing `active_cast`, `offscreen_cast`, and `state_contract` in older planner/director outputs.

