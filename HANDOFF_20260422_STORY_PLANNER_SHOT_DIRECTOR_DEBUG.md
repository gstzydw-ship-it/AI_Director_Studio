# Handoff 2026-04-22: Story Planner / Three-Stage Shot Director Debug

## Current Goal

Verify the split three-stage shot director chain:

1. `shot_director_layout`
2. `shot_director_blocking`
3. `shot_director_guard`

The user only wants to confirm these three shot directors work correctly, not debug the full generation pipeline blindly.

## Main Finding

The three-stage shot director chain itself can run.

The recurring "only one opus call" / "pipeline cannot reach shot director" symptom is mostly caused by failures before the shot director stage, especially `story_planner`.

Old failure evidence from `debug_state.json`:

- `status`: `error`
- `step`: `error`
- `agent_outputs.story_planner`: `随后迅速低下，空气凝固`
- `story_planner` output length: 11 chars
- Validation failed because required planner fields were absent:
  - `fragment_id`
  - `duration_target`
  - `dramatic_unit`
  - `source_script_events`
  - `active_cast`
  - `offscreen_cast`
  - `state_contract`
  - `boundary_reason`
  - `main_shots`
  - `reaction_plan`

Conclusion: that run died in `story_planner`, so `shot_director_layout/blocking/guard` never started.

## What Was Verified Tonight

### Three-Stage Smoke Test

A focused ASCII two-fragment smoke test ran all three stages successfully:

- `shot_director_layout`: completed
- `shot_director_blocking`: completed
- `shot_director_guard`: completed
- final output contained both fragments and full schema

Approximate live timings in that test:

- layout: about 83s
- blocking: about 63s
- guard: about 63s

### Real Chinese State Probe

Using the current `local` state and its real `story_planner` output:

- derived expected segments: `F05`, `F06`
- `shot_director_layout` called `claude-opus-4-6-thinking @ ai.comfly.chat`
- first attempt hit `ReadTimeout`
- retry hit `Server disconnected without sending a response`

Conclusion: in that probe, the first shot director stage stalled at the upstream LLM gateway. `blocking` and `guard` did not run because layout did not return.

### Hanging Probe Process

There was a stray process running `_test_three_stage_probe.py`.

- It held HTTPS connections open for more than 280s.
- One connection entered `CloseWait`.
- It was stopped to avoid generating confusing extra opus call records.

Only the WebUI Python process was left running.

## Code Changes Already Made

### LLM Settings Refactor

File: `agents/director_graph.py`

The old `_get_llm_settings()` complexity was refactored into:

- `LLMSettings`
- `resolve_llm_settings()`
- helper config-layer merge functions

Important behavior now covered:

- `shot_director_layout`
- `shot_director_blocking`
- `shot_director_guard`

inherit parent `shot_director` config correctly unless they override a field.

### `max_tokens` Forwarding / Thinking Budget

File: `agents/director_graph.py`

`call_llm()` now forwards `max_tokens` into the API payload.

For extended thinking models, it also expands automatically:

```text
payload["max_tokens"] = thinking.budget_tokens + 8192
```

Verified current real `story_planner` payload by intercepting `httpx.Client`:

```text
model: claude-opus-4-6-thinking
temperature: 1.0
thinking.budget_tokens: 32000
max_tokens: 40192
```

This means current code is no longer missing `max_tokens`.

### Longer Default Timeout For Thinking Models

File: `agents/director_graph.py`

Added `_default_llm_timeout_seconds()`:

- thinking enabled: 240s
- model name contains `thinking`: 240s
- model name contains `opus`: 180s
- otherwise: 120s

This prevents opus thinking calls from being cut at 120s too early.

### Segment Fallback For Old / Incomplete State

File: `agents/director_graph.py`

Added `_derive_segments_from_planner_output()`.

If `state.segment_names` / `state.total_segments` are missing, `shot_director_node()` now derives expected fragments from the planner YAML.

This prevents a bad state from letting `shot_director` pass even when it only outputs one fragment.

### Guard Output Is Now Explicitly Saved

File: `agents/director_graph.py`

`shot_director_node()` now saves:

- `agent_outputs["shot_director_layout"]`
- `agent_outputs["shot_director_blocking"]`
- `agent_outputs["shot_director_guard"]`
- `agent_outputs["shot_director"]`

Previously the final guard result was only visible as `shot_director`, making it easy to think only one stage ran.

## Tests Added / Updated

File: `tests/test_call_llm_network.py`

Added/updated coverage for:

- child shot director agents inheriting parent config
- missing config validation
- configured timeout forwarding
- longer default timeout for thinking models
- `story_planner` forwarding `max_tokens=40192` with `thinking.budget_tokens=32000`

File: `tests/test_three_stage_pipeline.py`

Added/updated coverage for:

- preserving `shot_director_guard` intermediate output
- deriving missing `segment_names` from planner output

## Verification Commands Run

```powershell
python -m pytest tests/test_call_llm_network.py tests/test_three_stage_pipeline.py -q
```

Result:

```text
15 passed
```

```powershell
python -m pytest tests/test_session_state_isolation.py tests/test_knowledge_runtime_policy.py -q
```

Result:

```text
24 passed
```

## Current WebUI State

WebUI was restarted after the code changes.

URL:

```text
http://127.0.0.1:8686/
```

Smoke check result:

```text
HTTP 200
```

Last observed WebUI process:

```text
python main.py ui
PID: 38176
```

This PID may change after restart.

## Tomorrow's Recommended Debug Plan

1. Submit a fresh task from the WebUI after confirming the server is still running on `http://127.0.0.1:8686/`.
2. Watch whether `story_planner` completes with a valid YAML list.
3. If `story_planner` still returns a short fragment, capture the raw API response metadata:
   - `finish_reason`
   - response JSON shape
   - content length
   - whether the gateway returned partial content without an HTTP error
4. If `story_planner` completes, confirm `agent_outputs` contains:
   - `story_planner`
   - `shot_director_layout`
   - `shot_director_blocking`
   - `shot_director_guard`
   - `shot_director`
5. If `shot_director_layout` stalls again on `claude-opus-4-6-thinking`, test one of these controlled changes:
   - lower `thinking.budget_tokens` for `story_planner` / `shot_director`
   - use a non-thinking model for `shot_director_layout`
   - add explicit retry classification/logging around `RemoteProtocolError` and `ReadTimeout`

## Important Interpretation

If only one opus call appears:

- If the state is still in `story_planner`, the shot directors never ran.
- If the state shows `shot_director_layout` but not `shot_director_blocking`, the first shot director call did not return valid YAML.
- If `shot_director_layout`, `shot_director_blocking`, and `shot_director_guard` all appear, the three-stage director chain did run.

Do not judge the three-stage director split from the raw number of visible opus calls alone; check `agent_outputs` and `knowledge_metadata["shot_director"]["runtime"]`.
