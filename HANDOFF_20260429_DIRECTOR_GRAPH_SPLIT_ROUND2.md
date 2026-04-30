# 交接文档：director_graph.py 继续拆分 Round 2

**日期**：2026/4/29
**操作人**：Claude Code
**目标**：继续清理 monolith 中的重复实现，推进 package 化

---

## 本轮操作摘要

### 1. `_run_llm_quality_inspector` 去重 ✓

**状态**：已完成

**改动内容**：

1. **导入区添加**：
```python
from agents.director_graph_package.helpers import (
    _compiler_guard_report,
    _run_llm_quality_inspector,  # ← 新增
    _run_story_planner_with_schema_repair,
)
```

2. **删除 monolith 中的重复定义**（原 6110-6221 行，约 112 行）：
   - 删除了整个 `def _run_llm_quality_inspector(...)` 函数
   - 该函数已完整迁移至 `agents/director_graph_package/helpers.py`
   - `quality_inspector_node` 调用点保持不变，直接走导入实现

**验证结果**：
- `python -m py_compile` 语法检查通过 ✓
- `_run_llm_quality_inspector` 仅在导入区和调用点出现 ✓
- monolith 中无重复定义 ✓

---

## monolith 残留大型函数清单（供后续轮次参考）

| 函数名 | 行号范围 | 估计行数 | package 侧状态 | 建议 |
|--------|----------|----------|----------------|------|
| `_run_shot_director_single_pass` | 5164-5528 | ~365 | `runners.py` 已是 wrapper，调用 monolith | 需确认是否可完全迁移 |
| `_run_story_planner_with_schema_repair` | ~5800-6000 | ~200 | 已导入使用中 | 已在 helpers.py，monolith 无重复 |
| `shot_director_node` | ~5529-6109 | ~580 | 调用 `_run_shot_director_single_pass` | 暂不动 |
| `quality_inspector_node` | ~6224-6290 | ~66 | 调用 `_run_llm_quality_inspector`（现为导入） | 暂不动 |
| `prompt_compiler_node` | ~6291-6699 | ~409 | 仍在 monolith | 可拆分但逻辑较重 |

---

## 下一步建议

### 高优先级（安全、可控）

1. **`_run_shot_director_single_pass` 完全迁移**
   - 当前状态：`runners.py` 是 wrapper，调用 monolith 中的完整实现
   - 建议：把 `_run_shot_director_single_pass` 完整实现移入 `runners.py`
   - 风险：低（`runners.py` 已有 wrapper 结构，只需替换为完整实现）
   - 预计减少：~365 行

2. **`_run_story_planner_with_schema_repair` 已完成**
   - 已在 `helpers.py`，monolith 仅做导入
   - 无需进一步操作

### 中优先级（需要更多分析）

3. **`prompt_compiler_node` 拆分**
   - 约 409 行，逻辑较重
   - 建议：先分析哪些子逻辑可抽到 helpers
   - 风险：中等（需确认所有辅助函数引用关系）

4. **规则字符串函数批量清理**
   - `_shot_director_rule_block`、`_dialogue_coverage_contract_rules` 等
   - 可移入 `rules.py` 或合并到现有 prompting 模块
   - 风险：低（纯字符串函数，无外部依赖）

### 低优先级（暂缓）

5. **`quality_inspector_node` 本身可进一步精简**
   - 目前约 66 行，规则质检部分可抽为 helpers 函数
   - 风险：低

---

## 关键风险提示

1. **回滚风险**：拆分过程中若有 bug，建议通过 git stash 回滚
2. **测试建议**：每次拆分后运行 `_tmp_verify_*.py` 测试文件
3. **包导入循环**：确保 `director_graph.py` 不循环导入 `director_graph_package`
4. **`_run_shot_director_single_pass`**：建议单独成模块（如 `runners.py` 中的 `_shot_director_single_pass_impl`），避免与现有 `run_shot_director_*` 函数名冲突

---

## 文件变更记录

| 文件 | 变更类型 | 行数变化 |
|------|----------|----------|
| `agents/director_graph.py` | 删除 `_run_llm_quality_inspector` 定义 | -112 行 |
| `agents/director_graph.py` | 导入区添加 `_run_llm_quality_inspector` | +1 行 |

**monolith 当前总行数**：约 6650 行（删除前 ~6762 行）
