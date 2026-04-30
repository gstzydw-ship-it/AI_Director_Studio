---
type: index
status: active
runtime_retrieval: false
---

# Agent 规则索引

## Prompt Compiler

```dataview
TABLE rule_id, title, priority, status, applies_to
WHERE contains(agent_scope, "prompt_compiler") OR contains(agent_scope, "shared")
SORT priority ASC, rule_id ASC
```

## Shot Director

```dataview
TABLE rule_id, title, priority, status, applies_to
WHERE contains(agent_scope, "shot_director") OR contains(agent_scope, "shared")
SORT priority ASC, rule_id ASC
```

## Story Planner

```dataview
TABLE rule_id, title, priority, status, applies_to
WHERE contains(agent_scope, "story_planner") OR contains(agent_scope, "shared")
SORT priority ASC, rule_id ASC
```

## Scene Analyst

```dataview
TABLE rule_id, title, priority, status, applies_to
WHERE contains(agent_scope, "scene_analyst") OR contains(agent_scope, "shared")
SORT priority ASC, rule_id ASC
```

## Quality Inspector

```dataview
TABLE rule_id, title, priority, status, applies_to
WHERE contains(agent_scope, "quality_inspector") OR contains(agent_scope, "shared")
SORT priority ASC, rule_id ASC
```
