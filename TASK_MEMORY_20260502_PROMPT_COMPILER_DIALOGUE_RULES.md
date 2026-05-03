# Prompt Compiler Dialogue Coverage Memory - 2026-05-02

## 1. 今日任务目标

本次工作聚焦于 `agents/director_graph_package/prompt_compiler_impl.py` 中的**对白覆盖规则文案校正**，目标不是改业务逻辑，而是把容易误导模型/使用者的镜头语言改成更符合连续视频生成约束的表述。

核心背景：

- 原规则里存在“必要时切回”“后半句以画外音/L-cut 压在听者画面上/砸在听者画面上”这类表达。
- 这些表述容易被理解成：
  1. 可以像传统剪辑一样切回已经完成动作链的旧镜头；
  2. 可以使用偏抽象、偏术语化、缺少直接画面感的描述。
- 用户明确指出这两点都有问题，需要修正文案。

---

## 2. 今日实际完成的修改

### 修改文件

- `agents/director_graph_package/prompt_compiler_impl.py`

### 修改位置

1. `_compiler_guard_report()` 内的长台词/高压对白报错提示文案
2. `prompt_compiler_node()` 中注入给 compiler 的 `5a. dialogue_coverage` 规则文案

### 修改前的问题表述

旧文案核心是：

- “说话者起句 -> 镜头切至同侧听者反应或过肩 -> 后半句画外音/L-cut -> 必要时切回”
- “后半句以画外音/OS/L-cut 砸在听者画面上”

这些问题在于：

1. **“必要时切回”有误导性**
   - 容易被写成切回“镜头1”的旧状态。
   - 但连续视频生成不是非线性剪辑，前一个镜头里的动作、站位、手势、空间状态已经向前推进，不能默认无代价回切。

2. **“压在/砸在听者画面上”过于抽象**
   - 对规则设计者也许能理解，对最终写 prompt 的执行端不够直观。
   - 这类表达更像剪辑/声音术语，不够像直接的画面调度语言。

3. **“被听见”仍偏机制描述**
   - 虽然比“压在画面上”好一些，但还是更像在解释声音通道，而不是在规定镜头如何写。

### 修改后的最终表述

现在统一改为更具体的表达：

> 说话者起句、同侧听者反应/过肩；镜头停留在听者脸部或过肩画面，说话者后半句在画外继续。若后续还有新动作、新信息点或新的主体重心，必须另起新镜头承接，禁止偷写成切回前一个已完成动作链的镜头，也禁止单段反打。

以及 guard 提示中的对应版本：

> 请在对白内部加入“说话者起句，切至同侧听者反应或过肩；镜头停留在听者脸部或过肩画面，说话者后半句在画外继续；若后续还有新动作或新信息点，必须另起新镜头承接”的覆盖变化。

---

## 3. 这次修改真正确认下来的规则意图

这轮不是在新增复杂规则，而是在**把意图说准确**：

### A. 对白覆盖可以变化，但不能伪装成“回到旧镜头”

允许：

- 说话者先起句
- 切到同侧听者反应
- 镜头留在听者脸上时，让说话者后半句继续说完

不允许：

- 写成“必要时切回镜头1”
- 写成切回一个已经完成动作链、已经发生状态推进的旧镜头
- 把连续视频生成误当成可随便倒回的传统剪辑时间线

### B. 规则文案要优先使用直观画面语言

优先写：

- 镜头停留在谁的脸部
- 画面是听者反应还是过肩
- 谁的后半句在画外继续

尽量避免写成：

- 压在画面上
- 砸在画面上
- 被听见
- 仅靠 OS/L-cut 等缩写解释机制而缺少画面主体

### C. 新动作/新信息点必须由新镜头承接

一旦对白后半段不只是声音连续，而是出现：

- 新动作
- 新信息点
- 新的主体重心

就必须：

- 另起新镜头承接
- 明确新的镜头主体、机位或信息落点
- 不能继续偷挂在前一个听者反应镜头上

---

## 4. 今日提交记录

已提交 commit：

- `d86dd2d` `refine(prompt_compiler): 修正对白覆盖规则文案`

提交内容概述：

- 去掉“必要时切回”
- 去掉“砸在听者画面上”等抽象声音描述
- 改为“镜头停留在听者脸部或过肩画面，说话者后半句在画外继续”

---

## 5. 当前工作区状态

在本次提交完成后，目标改动已入本地 commit。

建议下一台电脑先执行：

```powershell
git fetch --all --prune
git checkout 拆分
git pull --rebase origin 拆分
git log --oneline -5
```

应确认最近提交里包含：

- `d86dd2d refine(prompt_compiler): 修正对白覆盖规则文案`

---

## 6. 下一台电脑的接续重点

下一步不是继续随意改规则，而是做**小范围验收与扩散检查**：

1. 检查项目里是否还有类似“必要时切回”“砸在听者画面上”“压在听者画面上”这种旧表述残留。
2. 重点搜索：
   - `prompt_compiler_impl.py`
   - 相关 prompt compiler tests
   - 可能的规则文档/记忆文档
3. 如要继续优化，原则是：
   - 不改业务逻辑
   - 只改误导性的规则文案
   - 优先改成直接画面语言
4. 如果要跑验证，建议先跑与 prompt compiler 规则最相关的测试，而不是全仓大回归。

推荐检查命令：

```powershell
git status --short
git grep -n "必要时切回"
git grep -n "砸在听者画面上"
git grep -n "压在听者画面上"
git grep -n "在画外继续"
python -m pytest tests/test_prompt_compiler_dialogue_cutting.py -q
python -m pytest tests/test_prompt_compiler_camera_language.py -q
python -m pytest tests/test_prompt_compiler_timeline_continuity.py -q
```

---

## 7. 给另一台电脑的无缝衔接 Prompt

下面这段可直接复制给下一台电脑上的助手：

```text
请先阅读：
1. TASK_MEMORY_20260502_PROMPT_COMPILER_DIALOGUE_RULES.md
2. TASK_MEMORY_20260502_DIRECTOR_GRAPH_SPLIT.md
3. agents/director_graph_package/prompt_compiler_impl.py

当前分支：拆分
当前重点：prompt_compiler 对白覆盖规则文案验收，不做大范围重构。

你需要先执行：
- git status --short
- git log --oneline -5
- git grep -n "必要时切回"
- git grep -n "砸在听者画面上"
- git grep -n "压在听者画面上"
- git grep -n "在画外继续"

已知今天已经完成的核心修改：
- 在 prompt_compiler_impl.py 中，把“必要时切回”改掉，避免误导成切回已完成动作链的旧镜头。
- 把“后半句以画外音/OS/L-cut 砸在/压在听者画面上”改成更直接的画面语言：
  “镜头停留在听者脸部或过肩画面，说话者后半句在画外继续”。
- 已提交 commit：d86dd2d refine(prompt_compiler): 修正对白覆盖规则文案

你的任务目标：
1. 确认上述文案修改已经存在且工作区干净。
2. 搜索项目内是否还有相同或近似的旧表述残留。
3. 如果有残留，只做同类文案清理，不改业务逻辑。
4. 运行最小必要测试：
   - python -m pytest tests/test_prompt_compiler_dialogue_cutting.py -q
   - python -m pytest tests/test_prompt_compiler_camera_language.py -q
   - python -m pytest tests/test_prompt_compiler_timeline_continuity.py -q
5. 输出一份简短验收报告：
   - 发现了哪些残留
   - 改了哪些文件
   - 测试结果
   - 是否可以停止本任务线

重要限制：
- 不要顺手扩写规则体系。
- 不要改 story_planner / shot_director / quality_inspector 的业务逻辑。
- 不要把“连续视频生成”重新写回传统剪辑式“切回旧镜头”的语义。
- 如果需要新增文案，优先使用直接画面语言，而不是抽象术语语言。
```

---

## 8. 简短结论

今天这条线的成果很明确：

- 把对白覆盖规则从“剪辑术语化、容易误解”的表达，改成了“连续视频生成可执行、画面主体明确”的表达。
- 最重要的认知收口是：**可以切到听者反应，但不能偷写成切回已完成动作链的旧镜头；可以让说话者后半句继续，但规则文案必须优先描述画面，而不是描述抽象声音机制。**
