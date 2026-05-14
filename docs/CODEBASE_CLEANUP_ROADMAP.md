# 代码债治理路线图

这份路线图的目标不是一次性重写系统，而是让每次 AI 改动都变小、可审、可回滚。先把入口守住，再一块一块拆。

## 阶段 0：先装护栏

状态：已开始。

- PR 必须写清目标、风险文件、测试结果和未测试事项。
- Danger 负责提醒 PR 过大、高风险文件、缺测试、临时脚本外溢。
- reviewdog/ruff 负责把新增代码里的高信号 Python 问题标到 PR 行内。
- pytest 守门测试先覆盖配置密钥、知识检索策略、shot director、prompt compiler 边界。
- GitNexus 负责改前 impact 和改后 detect-changes。

验收标准：

- 新 PR 不再靠“相信 AI”合并。
- 人只需要看目标、风险、测试和残留问题。

## 阶段 1：清理根目录临时脚本

目标：把根目录里大量 `fix_*.py`、`scratch_*.py`、`_tmp_*.py`、`test_*.txt` 从日常视野里移走。

做法：

- 先列清单，按“仍有用 / 可归档 / 可删除”分类。
- 仍有用的脚本移入 `tools/`，文件名改成明确用途。
- 仅作历史排查的材料移入 `_session_artifacts/` 或文档归档区。
- 无用文件分批删除，每批都只删同一类。

验收标准：

- 根目录只保留项目入口、配置、说明和少量必要脚本。
- Danger 不再看到新增根目录临时脚本。

## 阶段 2：冻结高风险模块的行为

目标：重构前先把行为钉住，避免 AI 越修越偏。

优先模块：

- `agents/knowledge_base.py`
- `agents/director_graph_package/shot_director_impl.py`
- `agents/director_graph_package/prompt_compiler_impl.py`
- `agents/director_graph_package/helpers.py`

做法：

- 每个模块先写“当前行为契约”文档或测试。
- 只补缺口测试，不先重构。
- 每次改动前跑 GitNexus impact。
- 每次改动后跑对应守门测试。

验收标准：

- 高风险模块的关键路径都有测试或明确人工验收步骤。
- AI 改这些文件时必须说明影响范围和测试。

## 阶段 3：拆大文件，但不改业务行为

目标：把超长文件拆成职责清楚的小模块。

做法：

- 一次只抽一个职责，例如“标签归一化”“profiled rerank”“critical fallback”。
- 先移动函数和测试，不同时改逻辑。
- 每次拆分都保留原入口兼容。
- 拆完再做行为优化。

验收标准：

- 单个 PR 只做一次机械拆分。
- 拆分前后测试结果一致。
- GitNexus detect-changes 显示影响范围符合预期。

## 阶段 4：把知识库治理自动化

目标：让规则卡/案例卡质量不靠手工记忆。

做法：

- 增加 frontmatter schema 检查。
- 检查 `runtime_retrieval`、`agent_scope`、`priority`、`scene_types`、`events`、`risks` 等字段。
- 检查 P5 case 是否有 rule anchor。
- 检查外部参考区是否保持 `runtime_retrieval: false`。

验收标准：

- 新增知识卡没有标签就会被 CI 提醒。
- 外部资料不会进入运行时检索。

## 阶段 5：AI 二审常态化

目标：让另一个 AI 专门挑问题，而不是同一个 AI 自夸完成。

做法：

- PR-Agent 或类似工具只按需运行。
- 它只回答：行为回归、缺测试、职责混乱、安全风险、是否建议合并。
- 不让 AI reviewer 自动改代码，除非另开修复任务。

验收标准：

- 复杂 PR 至少有一次独立 review。
- review 结论能落到文件、风险和测试，不是泛泛而谈。

## 每次清理的固定节奏

1. 选一个小目标。
2. 改前跑 GitNexus impact。
3. 只改允许范围。
4. 跑对应测试。
5. 让 Danger/reviewdog/pytest 先审。
6. 人只看结论、风险和产品行为。

这套节奏比“大重构”慢一点，但不会把系统再次推成不可控状态。
