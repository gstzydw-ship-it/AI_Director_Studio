# HANDOFF — 2026-04-30 — director_graph 拆分收尾记忆文档

## 1. 本文用途
这是一份给下一台电脑/下一轮对话直接续接用的最新记忆文档。

如果要恢复上下文，建议至少同时提供：
- `HANDOFF_20260430_DIRECTOR_GRAPH_PACKAGE_FINAL_WRAP.md`（本文）
- `HANDOFF_20260428_DIRECTOR_GRAPH_SPLIT.md`
- `HANDOFF_20260429_DIRECTOR_GRAPH_SPLIT_ROUND2.md`
- `TASK_MEMORY_20260429_DIRECTOR_GRAPH_SPLIT.md`

---

## 2. 今晚任务目标与结论
### 今晚目标
只做一件事：

让 `agents/director_graph_package` **不再反向依赖** monolith `agents/director_graph.py`，尤其是清掉 `helpers.py` 中这两个 wrapper 对 monolith 的回调：
1. `_run_shot_director_single_pass`
2. `_run_shot_director_review_board`

### 今晚结论
**已完成验收目标。**

验收标准已经满足：
- `director_graph_package/*.py` 不再反向 import `agents.director_graph`
- `_run_shot_director_single_pass` 真实归属 `agents.director_graph_package.helpers`
- `_run_shot_director_review_board` 真实归属 `agents.director_graph_package.helpers`
- `py_compile` 通过
- 旧入口/新入口导入验证通过

---

## 3. 本轮实际改动

### 3.1 package 侧状态
根据本轮验收结果，可以确认：
- `agents/director_graph_package/helpers.py` 中：
  - `_run_shot_director_single_pass`
  - `_run_shot_director_review_board`
  - `_run_story_planner_with_schema_repair`
  - `_run_llm_quality_inspector`
  这四个函数的 `__module__` 都已经是：
  `agents.director_graph_package.helpers`

这意味着 package 运行时已经不再需要回头调用 monolith 里的这几个重型实现。

### 3.2 monolith 侧状态
`agents/director_graph.py` 已被改为**兼容壳（shim）**，不再保留之前的重型单文件实现。

当前这个文件的职责是：
- 继续兼容旧导入，例如：
  - `from agents.director_graph import run_phase_1_planning`
  - `from agents.director_graph import run_phase_2_compile_segment`
- 通过 re-export + `__getattr__`，把符号转发到 `agents.director_graph_package` 及其子模块
- 供老调用方继续工作，但**package 自己不再依赖它**

换句话说：
- package → monolith 的反向依赖已经切断
- monolith → package 的兼容壳方向已经建立

---

## 4. 本轮唯一明确修改的文件

### `agents/director_graph.py`
已重写为薄兼容层，核心结构如下：
- 顶部直接从 `agents.director_graph_package` / `graph_api` / `llm` / `runners` / `state_store` / `types` 导入核心公开符号
- `_MODULES` 中维护 package 子模块列表
- 通过 `__getattr__(name)` 从 package 子模块动态转发旧符号
- 通过 `__dir__()` 暴露兼容可见符号
- `__all__` 提供核心稳定导出

### 未在本轮扩大的范围
本轮**没有**做以下事情：
- 没有继续重构业务逻辑
- 没有改 prompt 规则
- 没有改视频逻辑
- 没有改质检逻辑
- 没有做“大拆大改”
- 没有新增临时脚本留在仓库里
- 没有用 `git reset --hard`

---

## 5. 验证命令与结果

> 注意：当前 IDE shell 是 `cmd.exe`，而用户给出的原始验证命令是 PowerShell 风格。
> 因此本轮验证时，部分命令改成了 **等价但更稳的执行形式**，避免 here-string / 通配符在 `cmd.exe` 下失效。

### 5.1 反向依赖扫描
执行：

```powershell
powershell -NoProfile -Command "$env:PYTHONDONTWRITEBYTECODE='1'; Select-String -Path .\agents\director_graph_package\*.py -Pattern 'agents\.director_graph|from agents import director_graph|__import__\(.*director_graph' -Encoding UTF8"
```

结果：
- exit code 0
- **无命中输出**

结论：
`director_graph_package/*.py` 已无反向 import `agents.director_graph`。

---

### 5.2 `py_compile` 验证
原始用户命令为：

```powershell
py -3 -m py_compile .\agents\director_graph.py .\agents\director_graph_package\*.py
```

但在当前 `cmd.exe` 环境下，`*.py` 不会按期望传给 `py_compile`，会直接报：
`[Errno 22] Invalid argument: '.\\agents\\director_graph_package\\*.py'`

因此本轮改用等价 Python 展开方式：

```bat
set PYTHONDONTWRITEBYTECODE=1 && py -3 -c "import pathlib, py_compile; py_compile.compile(r'agents/director_graph.py', doraise=True); [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('agents/director_graph_package').glob('*.py')]; print('py_compile ok')"
```

结果：
- exit code 0
- 输出：`py_compile ok`

结论：
- `agents/director_graph.py` 编译通过
- `agents/director_graph_package/*.py` 编译通过

---

### 5.3 helpers 归属验证
执行：

```bat
set PYTHONDONTWRITEBYTECODE=1 && py -3 -c "import agents.director_graph_package.helpers as h; names=['_run_shot_director_single_pass','_run_shot_director_review_board','_run_story_planner_with_schema_repair','_run_llm_quality_inspector']; [print(name, getattr(h, name).__module__) for name in names]"
```

结果输出：

```text
_run_shot_director_single_pass agents.director_graph_package.helpers
_run_shot_director_review_board agents.director_graph_package.helpers
_run_story_planner_with_schema_repair agents.director_graph_package.helpers
_run_llm_quality_inspector agents.director_graph_package.helpers
```

附带环境提示：
- `resource module not available on Windows`

说明：
这个提示不影响归属验证结果。

---

### 5.4 旧入口兼容导入验证
执行：

```bat
set PYTHONDONTWRITEBYTECODE=1 && py -3 -c "from agents.director_graph import run_phase_1_planning, run_phase_2_compile_segment; from agents.director_graph_package.runners import run_phase_1_planning as p1, run_phase_2_compile_segment as p2; import agents.director_graph_package.nodes as n; import agents.director_graph_package.helpers as h; print('imports ok')"
```

结果：
- exit code 0
- 输出：`imports ok`

附带环境提示：
- `langchain_core` 在 Python 3.14 下的 Pydantic V1 warning
- `resource module not available on Windows`

说明：
这些提示不影响导入兼容结论。

---

## 6. 现在的真实架构状态

### 6.1 package 已经是什么状态
从本轮结果看，`agents/director_graph_package` 已经具备以下性质：
- graph / nodes / runners / prompting / helpers 的主执行路径都在 package 内
- package 运行时不再反向依赖 monolith
- 旧 `agents/director_graph.py` 只剩兼容壳角色

### 6.2 monolith 已不再是运行核心
`agents/director_graph.py` 现在不是原来的“真实执行中心”，而是：
- 向后兼容层
- 对 package 的 re-export 门面
- 旧代码入口适配器

如果后续要进一步清理，这个文件已经非常接近“最终兼容壳”状态。

---

## 7. 本轮未完成项 / 风险说明
### 7.1 没完成的不是今晚验收项
本轮曾额外尝试做一个“最小业务流 monkeypatch 验证”，想确认节点执行路径命中 package helper。

但该临时验证先后被以下原因拦下：
1. 一次是把 node 返回的 update 误当完整 state 使用
2. 一次是 `story_planner_node` 的 verbatim 校验拦下 stub 数据

这两个问题都属于**临时验证脚本构造不够贴近真实状态**，不是今晚拆分验收失败。

### 7.2 当前真正风险很低
按照今晚的验收标准，风险已经很低：
- 反向 import 清零已验证
- 函数真实归属已验证
- 编译通过已验证
- 导入兼容已验证

如果要继续推进，重点已经不再是“切断 package → monolith 依赖”，因为这一步已经完成。

---

## 8. 下一个人接手时最重要的判断
### 已经完成的事
不要再重复做下面这些：
- 不要再去找 `helpers.py` 里是否仍有 `_run_shot_director_single_pass` / `_run_shot_director_review_board` 的 monolith wrapper
- 不要再把“清掉 package 对 monolith 的反向 import”当作待办
- 不要再把 `agents/director_graph.py` 当作重型 monolith 修补

因为这些事情本轮已经完成。

### 如果继续做，建议方向
后续如果还要继续收尾，建议优先考虑：
1. 检查 `agents/director_graph.py` 兼容壳是否还缺少某些历史导出符号
2. 扫描项目内其它老调用方是否仍然依赖一些非常冷门的 monolith 私有符号
3. 决定是否要给兼容壳补一轮“常用旧符号回归导入清单”
4. 在真实业务流里补一次更接近生产状态的 smoke test

但这些已经是**下一阶段优化/稳固**，不是今晚验收阻塞项。

---

## 9. 给下一轮 AI 的超短摘要
可直接复制：

```text
2026-04-30 已完成 director_graph 拆分收尾的关键验收项：agents/director_graph_package/*.py 已不再反向 import agents.director_graph，helpers.py 中 _run_shot_director_single_pass / _run_shot_director_review_board 的真实归属已在 agents.director_graph_package.helpers。agents/director_graph.py 已被改成兼容壳（re-export + __getattr__ 转发 package 子模块），保留旧入口兼容，但 package 运行时不再调用 monolith。已验证：反向依赖扫描无命中、等价 py_compile 通过、四个 helper 的 __module__ 全为 agents.director_graph_package.helpers、旧入口/新入口 imports ok。下一步如果继续做，不是再清 package→monolith 依赖，而是检查兼容壳是否还缺历史导出，或补真实业务流 smoke test。
```

---

## 10. 本轮一句话结论
**今晚的收尾目标已经完成：`director_graph_package` 不再反向依赖 `agents.director_graph`，两个 shot director 重型函数真实归属 `agents.director_graph_package.helpers`，而 `agents/director_graph.py` 现已收敛为向后兼容壳。**
