# Handoff Prompt - Agent Optimization 2026-05-11

Copy the prompt below into the next Codex session when continuing this task.

```text
你正在继续 E:\AI_Director_Studio_Pack_20260417\AI_Director_Studio 的 agent 优化任务。

当前目标：
优化短剧 AI 导演流水线里的 story_planner 和 shot_director，让前者只负责“分段/拆片段”，后者负责“片段内多镜头剪辑与镜头语言设计”，同时减少无关知识库投喂。

已经完成的改动：

1. story_planner 已简化为纯拆片 agent
- 只输出片段，不做分镜/镜头/机位。
- 输出 7 个中文字段：
  片段编号、目标时长、施工剧本原文事件、出现人物、入场状态、出场状态、承接要求。
- 使用轻量 rule_registry_slim 规则摘要，不再吃大段镜头知识库。
- 增加 15 秒剧情片段判断规则：普通对白 6-8 个事件，动作密集 2-4 个事件，长对白按完整意思切；不在半句话、半个动作、未完成反应处硬切。
- 相关文件：
  agents/director_graph_package/story_planner_impl.py
  tests/test_story_planner_schema_guard.py

2. shot_director 已按“节奏联动 + 剪辑策略 + 镜头语言变化”优化
- 内部工作流现在是：
  事实提取 -> 节奏意图读取 -> 剪辑策略判断 -> 戏剧任务判断 -> 镜头骨架 -> 镜头语言变化 -> 动作与子镜头 -> 切镜时机 -> 冲突裁决 -> 最小修复 -> 最终交付。
- 节奏总控不再被当成硬镜头模板，只提供快慢、停顿、反应归属、卡断、尾帧意图。
- 冲突优先级：
  原剧本事实 > story_planner 片段边界 > 连续性/空间安全 > 节奏总控建议 > 镜头美学。
- 新增/强化知识召回信号：
  editing_ellipsis、shot_variety、rhythm_alignment。
- 新增镜头库任务：
  editing_ellipsis：无用动作省略、上车/开门/走路/进入新空间只保留关键瞬间。
  shot_language_variety：避免连续重复同一景别/机位/主体。
  rhythm_alignment：把节奏总控转译为镜头时长、停顿、反应归属、切点和尾帧。
- 新增 guard：
  同一片段 3 个及以上镜头时，若连续重复同一种镜头语言，会被 _validate_shot_director_variety 抓出；除非节奏总控明确要求固定机位压迫/长镜头。
- 相关文件：
  agents/director_graph_package/shot_director_impl.py
  tests/test_shot_director_workflow_contract.py

已验证：
- python -m compileall agents\director_graph_package\story_planner_impl.py tests\test_story_planner_schema_guard.py
- python -m pytest tests\test_story_planner_schema_guard.py -q
- python -m compileall agents\director_graph_package\shot_director_impl.py tests\test_shot_director_workflow_contract.py
- python -m pytest tests\test_shot_director_workflow_contract.py -q
- python -m pytest tests\test_shot_director_guards.py tests\test_shot_director_workflow_contract.py tests\test_story_planner_schema_guard.py -q
最终相关测试：53 passed。

GitNexus：
- 编辑前对 story_planner_node、_story_planner_repair_prompt、_shot_director_workflow_contract、_build_shot_director_signal_retrieval_profile、_shot_library_signal_task_card、_run_shot_director_single_pass_impl、_collect_shot_director_issues 做过 impact，风险 LOW。
- 提交前 detect_changes 显示当前工作区整体 risk_level low，affected_count 0。

注意：
- 当前仓库在开始前已经有很多其他未提交改动，例如 AGENTS.md、CLAUDE.md、llm.py、planning_context_impl.py、types.py、ui/*、config/settings.yaml 等。不要随便回退这些文件。
- 本任务提交只应包含：
  agents/director_graph_package/story_planner_impl.py
  tests/test_story_planner_schema_guard.py
  agents/director_graph_package/shot_director_impl.py
  tests/test_shot_director_workflow_contract.py
  HANDOFF_20260511_AGENT_OPTIMIZATION.md

下一步建议：
1. 用一段真实剧本跑一次 story_planner -> shot_director 的 LLM 实际输出，看 shot_director 是否真的会：
   - 省略无用位移；
   - 长台词中间切给听者/反应；
   - 照片/身份/新老板揭示有信息镜头和反应镜头；
   - 不连续重复同一景别/机位；
   - 节奏总控建议不覆盖原剧本事实和拆片边界。
2. 如果实际输出仍然不稳，再考虑把 shot_director 内部的“剪辑策略判断”拆成独立 editing_planner agent；目前不建议先拆 agent。
3. 下一个可优化 agent 很可能是 storyboard_designer 或 prompt_compiler，重点检查它是否会重新发明镜头逻辑，是否只编译 shot_director 已确定的镜头。
```

