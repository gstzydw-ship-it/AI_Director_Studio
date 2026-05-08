---
reference_id: RUFLO-AGENT-ORCHESTRATION-REFERENCE
title: Ruflo Multi-Agent Orchestration Architecture Reference
doc_type: external_architecture_reference
status: active
runtime_retrieval: false
source_repository: ruvnet/ruflo
source_url: https://github.com/ruvnet/ruflo
source_readme: https://raw.githubusercontent.com/ruvnet/ruflo/main/README.md
source_package: https://raw.githubusercontent.com/ruvnet/ruflo/main/package.json
reviewed_at: "2026-05-07"
served_agents:
  - scene_analyst
  - rhythm_rewrite_director
  - story_planner
  - shot_director
  - prompt_compiler
  - quality_inspector
  - shared
rule_type: architecture_reference
priority: P5
applies_when:
  - agent_orchestration_design
  - retrieval_audit_design
  - background_worker_design
  - safety_gate_design
avoid_when:
  - runtime_prompt_context
  - direct_framework_install
  - mcp_stack_replacement
  - hook_autowiring
signals:
  - orchestration_ledger
  - executor_agent
  - memory_before_after_task
  - pluginized_capability
  - background_audit_worker
  - safety_gate
risks:
  - tool_sprawl
  - hook_conflict
  - mcp_overlap
  - daemon_state_drift
  - external_framework_lock_in
reusable_pattern:
  - orchestrator_as_ledger_executor_does_work
  - opt_in_capability_registry
  - memory_lifecycle_before_after_task
  - safety_gate_as_first_class_agent
  - background_audit_workers
---

# Ruflo Multi-Agent Orchestration Architecture Reference

Ruflo is a broad agent orchestration stack for Claude Code/Codex-style development workflows. For this project, use it as an architecture reference only. Do not install it, run its init commands, or register its MCP/hooks inside this repository.

## What To Borrow

### 1. Orchestrator As Ledger, Agents As Executors

Borrow the separation between a coordination layer and execution agents:

- The orchestration layer records intent, selected agent, input profile, retrieved knowledge, output summary, validation status, and retry reason.
- Specialized agents do the work and return structured results.
- The orchestrator should not become a second director; it should preserve task state, route responsibility, and make retries explainable.

Local mapping:

- `scene_analyst` extracts facts and scene constraints.
- `rhythm_rewrite_director` sharpens beats without changing facts.
- `story_planner` owns fragment boundaries and state contracts.
- `shot_director` owns executable shot construction.
- `prompt_compiler` translates approved shot intent into model-safe prompt language.
- `quality_inspector` acts as the blocking safety and continuity gate.

### 2. Capability Registry Instead Of Tool Sprawl

Borrow the idea of agent capabilities, but represent them as local YAML/contracts rather than a dynamic plugin layer.

Local mapping:

- Keep `knowledge/agent_retrieval_contracts.yaml` as the source of truth for which tags each agent should receive.
- Add future capability fields only when they change routing or validation behavior.
- Avoid registering extra MCP servers for capabilities already handled by local code or GitNexus.

### 3. Memory Lifecycle Around Each Task

Borrow the before/during/after task memory lifecycle:

- Before task: load only the relevant profile, active state contract, and matched P0/P1 rules.
- During task: record the chosen pattern, rejected alternatives, and continuity assumptions.
- After task: store validation failures, reusable fixes, and retrieval misses as audit material.

Local mapping:

- Store durable knowledge as rule cards/case cards, not free-form chat memory.
- Use audit records to propose new tags or missing rule cards.
- Keep runtime retrieval small; do not use memory as a catch-all context dump.

### 4. Safety Gate As A First-Class Agent

Borrow the idea that quality/security checks are not optional postscript text.

Local mapping:

- `quality_inspector` should keep priority over P5 case patterns.
- Hard failures should block completion when state contracts, privacy, subtitle bans, unsafe contact, or model-generability constraints are violated.
- Safety feedback should produce minimal repair instructions rather than re-authoring the whole scene.

### 5. Background Audit Workers

Borrow background maintenance, but keep it local and non-invasive.

Good candidates:

- Tag coverage audit for rules/cases.
- Duplicate case chunk detection.
- Retrieval regression checks for aspect ratio, collision, dialogue, continuity, and hard-fail queries.
- Missing rule anchor detection for P5 case retrieval.

Do not run background daemons that edit prompts, hooks, or MCP config automatically.

## What Not To Borrow

- Do not run `npx ruflo init` in this repo.
- Do not install its hook stack or daemon stack into `.claude`, `.codex`, or project config.
- Do not replace GitNexus with Ruflo MCP.
- Do not let Ruflo-style generated agents rewrite the local director graph.
- Do not import its full command/agent set; this system already has a domain-specific agent boundary.

## Concrete Adoption Path

1. Keep this file as a non-runtime external reference.
2. Add any accepted idea to `knowledge/agent_retrieval_contracts.yaml` or a local rule card only after review.
3. Implement background audits as explicit scripts under `tools/`, with tests and no auto-edit behavior by default.
4. Use GitNexus impact/detect-changes for code modifications; use retrieval regression tests for knowledge routing changes.

## Open Design Hooks

- Add a lightweight run ledger only if debugging multi-agent retries remains hard after the current retrieval-profile work.
- Add an audit script for `runtime_retrieval: false` external references so they never leak into agent context.
- Add a retrieval-miss report that turns failed queries into candidate tags or candidate rule cards.
