# TASK MEMORY — 2026-04-29 — director_graph 拆分续接

## 1. 本文用途
这是一份给下一台电脑/下一轮对话直接续接用的任务记忆文档。
恢复上下文时，请与主交接文档 **`HANDOFF_20260428_DIRECTOR_GRAPH_SPLIT.md`** 一起提供给新对话中的 AI。

---

## 2. 当前拆分总状态
`agents/director_graph.py` 的 package 化拆分已经进入**收尾阶段**。

已基本完成真实迁移的模块：
- `graph_api`
- `nodes`
- `runners`
- `prompting`

`helpers.py` 也已经承接了大部分轻/中型函数，近期新增下沉并验证通过的函数包括：
- `_script_character_names`
- `_event_coverage_terms`
- `_canonicalize_subject_aliases`
- `_has_unmapped_latin_subject_alias`
- `_validate_shot_director_script_fidelity`
- `_validate_shot_director_source_event_coverage`

重要结果：
- `_collect_shot_director_issues` 已**完全脱离**之前那条 monolith 间接依赖链。

---

## 3. 本轮最新实际变更（很重要）
本轮没有继续推进新的重型 wrapper 真实迁移，而是先修了一个**真实运行断点**：

### 已修复问题
`agents/director_graph_package/helpers.py` 中 `_run_shot_director_single_pass` forwarding stub 曾被误删，
但 `nodes.py` / package 调用链仍然依赖这个符号，导致 helpers 导出与调用侧不一致。

### 本轮修复动作
已在 `helpers.py` 中恢复以下 forwarding wrapper：
- `_run_shot_director_single_pass(...)`

它当前仍是这种安全过渡模式：
- `helpers.py` 中保留同名函数
- 内部 `from agents.director_graph import _run_shot_director_single_pass as _impl`
- 再 `return _impl(...)`

也就是说：
- **调用链已恢复可运行**
- 但这还不是“真实源码迁移完成”，只是先把 package 拉回一致、可编译状态

### 已验证
已执行：

```bat
py -3 -m py_compile agents\director_graph_package\helpers.py agents\director_graph_package\nodes.py agents\director_graph_package\runners.py
```

结果：**通过（exit code 0）**。

这说明当前 package 至少在语法/导入层面重新稳定。

---

## 4. 当前剩余未完成的重型 wrapper
目前还剩这 5 个重型 wrapper 需要继续处理：
- `_compiler_guard_report`
- `_run_story_planner_with_schema_repair`
- `_run_shot_director_single_pass`
- `_run_llm_quality_inspector`
- `_run_shot_director_review_board`

注意：
- `_run_shot_director_review_board` 目前在 `helpers.py` 里**仍是 forwarding stub**。
- `_run_shot_director_single_pass` 目前也**仍是 forwarding stub**，只是这轮把它补回来了，避免 import/call break。

---

## 5. 下一步建议优先级
### 最推荐优先项
1. `_compiler_guard_report`
2. `_run_story_planner_with_schema_repair`

原因：
- 这两个函数边界相对更清晰
- 迁移收益高
- 比直接动 `_run_shot_director_single_pass` / `_run_shot_director_review_board` 风险更低

### 不建议下一步立刻做的事
- 不建议第一刀就直接重构 `_run_shot_director_single_pass`
- 不建议先删除 monolith 中旧定义
- 不建议先做“优化式改写”或逻辑重组

当前最佳策略仍然是：
**复制源码原样迁移 → 新旧实现样例对比验证 → 保留旧定义不删**。

---

## 6. 必须继续遵守的迁移规则
后续 AI 必须继续遵守以下约束：

1. **复制源码原样迁移**
   - 先把 monolith 中目标函数完整复制到 package 对应模块
   - 不要顺手重构，不要先“美化”

2. **补齐依赖，不做大改写**
   - 若迁移函数依赖其他 helper，继续把依赖下沉到 package
   - 优先保持行为一致，而不是追求结构完美

3. **新旧实现做对比验证**
   - 用样例输入同时跑旧实现和新实现
   - 确认输出一致或至少关键行为一致

4. **不要删除旧文件定义**
   - `agents/director_graph.py` 里的旧定义先保留
   - package 中可以先通过 forwarding stub / 新实现并行过渡

5. **先保运行，再求彻底迁移**
   - 如果 package import/call 链断了，优先修复一致性
   - 本轮就是这种情况：先恢复 stub，避免工程处于半拆半坏状态

---

## 7. 可直接复用的验证脚本
这些验证脚本已就位，新电脑可直接复用：
- `_tmp_verify_dialogue_coverage.py`
- `_tmp_verify_script_fidelity.py`
- `_tmp_verify_source_event_coverage.py`

它们主要用于最近这批 shot_director validator / helper 下沉后的行为核对。

---

## 8. 建议给新对话 AI 的简短摘要
可直接复制下面这段：

```javascript
当前 director_graph 拆分已进入收尾阶段。graph_api / nodes / runners / prompting 基本完成真实迁移，helpers 也已迁入大部分轻中型函数。此前新增并验证通过的函数包括：_script_character_names、_event_coverage_terms、_canonicalize_subject_aliases、_has_unmapped_latin_subject_alias、_validate_shot_director_script_fidelity、_validate_shot_director_source_event_coverage。_collect_shot_director_issues 已完全脱离 monolith 间接依赖链。

本轮未继续迁移新的重型 wrapper，而是先修复了一个真实断点：helpers.py 里的 _run_shot_director_single_pass forwarding stub 曾被误删，但 nodes/package 调用链仍依赖它。现已恢复该 stub，并已用 py_compile 校验 helpers.py / nodes.py / runners.py 通过，package 重新回到可编译状态。注意：这只是恢复运行一致性，不代表该函数已完成真实迁移。

当前剩余 5 个重型 wrapper：_compiler_guard_report、_run_story_planner_with_schema_repair、_run_shot_director_single_pass、_run_llm_quality_inspector、_run_shot_director_review_board。下一步建议优先处理 _compiler_guard_report 或 _run_story_planner_with_schema_repair，并继续遵守“复制源码原样迁移 + 新旧实现样例对比验证 + 不删除旧文件定义”的策略。
```

---

## 9. 恢复上下文时建议一起提供的文件
新电脑/新对话建议至少同时提供：
- `TASK_MEMORY_20260429_DIRECTOR_GRAPH_SPLIT.md`
- `HANDOFF_20260428_DIRECTOR_GRAPH_SPLIT.md`

如果还要继续 validator 相关验证，再补充：
- `_tmp_verify_dialogue_coverage.py`
- `_tmp_verify_script_fidelity.py`
- `_tmp_verify_source_event_coverage.py`
