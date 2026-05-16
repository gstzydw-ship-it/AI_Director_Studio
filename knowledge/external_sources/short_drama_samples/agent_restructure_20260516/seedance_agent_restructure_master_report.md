---
doc_id: SHORT-DRAMA-SEEDANCE-AGENT-RESTRUCTURE-MASTER-20260516
title: Seedance 2.0 全能参考模式下的 94 集短剧 Agent 重构总报告
doc_type: research_report
status: candidate_plan
runtime_retrieval: false
created_at: 2026-05-16
sample_dir: H:\样片
analysis_dir: output/short_drama_analysis_full_20260516_105744
---

# Seedance 2.0 全能参考模式下的 94 集短剧 Agent 重构总报告

本报告整合四个并行分析结果：

- `scene_storyboard_restructure_report.md`
- `showrunner_storyplanner_restructure_report.md`
- `prompt_qc_restructure_report.md`
- `agent_contract_integration_report.md`

前置基准：

- `knowledge/rules/shared/SEEDANCE20-OMNI-CAPABILITY-MATRIX-001.md`
- `knowledge/rules/shot_director/SEEDANCE20-COVERAGE-WHITELIST-001.md`
- `knowledge/external_sources/short_drama_samples/rhythm_control_template_library_v1.yaml`
- `knowledge/external_sources/short_drama_samples/shot_coverage_template_library_v1.yaml`

## 1. 样片统计基线

- 样片：`H:\样片`，94 集，全部 9:16 竖屏。
- 总时长：约 10966.56 秒。
- 检测镜头：3410 个。
- 镜头平均时长：3.21 秒。
- 镜头中位时长：1.92 秒。
- P25/P75：0.96 秒 / 3.84 秒。
- `<=1.2s` 短切：880 个，占 25.8%。
- `1.2-3.0s` 常规镜头：1499 个，占 44.0%。
- `>3.0s` 长镜头：1031 个，占 30.2%。
- 三人及以上镜头：167 个，占 4.9%。
- 景别粗估：半身、关系、环境类镜头占主导；CU/ECU 只约 72 个。

关键结论：样片不是靠“全程大特写 + 复杂运镜”成立，而是靠关系景、半身景、道具/身份信息落点、受击反应、尾帧钩子形成短剧密度。Seedance 2.0 生产应默认控制在 4-8 秒、1-2 名主要角色、一个核心动作、一个情绪落点、明确参考绑定和可继承尾帧。

## 2. 总体重构方向

不建议新增大量 agent。应把 Seedance 2.0 能力矩阵作为跨 agent 合同层注入现有流程。

新的分层：

1. 上游短剧信号层：`scene_analyst`、`director_showrunner`、`rhythm_rewrite_director`
2. 中游生成单元层：`story_planner`、`shot_director` 三阶段、`storyboard_designer`
3. 下游 Seedance 编译层：`prompt_compiler`
4. 质检闭环层：`quality_inspector`

上游只产事实、空间、爽点、节奏信号；中游只产可生成单元和白名单 coverage；下游只编译；质检只仲裁和路由。任何下游 agent 不得反向发明剧情、人物、道具或镜头。

## 3. Agent 重构结论

| Agent | 结论 | 新定位 | 必须输出 | 禁止 |
|---|---|---|---|---|
| `scene_analyst` | 重构 | 可控空间与参考资产合同生产者 | `scene_contract`、`space_anchor`、`active_cast`、`prop_state`、`blocking_risk`、`reference_needs` | 不拆片、不写镜头、不改剧情 |
| `director_showrunner` | 保留但收窄 | 短剧爽点/冲突/反转/尾钩总控 | `dramatic_signal`、`conflict_type`、`reversal_target`、`emotion_landing` | 不写 coverage、不写运镜、不新增不可控事件 |
| `rhythm_rewrite_director` | 保留 | 时间预算、密度、不可省略落点、尾帧要求 | `rhythm_diagnosis`、`segment_duration_policy`、`non_omittable_beats` | 不写机位、不指定 coverage |
| `story_planner` | 核心重构 | Seedance 生成单元规划器 | `generation_unit`、`event_atom`、`emotion_delta`、`reaction_handoff`、`complexity_score`、`split_required`、`tail_state_required` | 不把文学段落直接交给镜头导演 |
| `shot_director_layout` | 保留并收紧 | 白名单主覆盖骨架 | `coverage_template_id`、`coverage_role`、`space_anchor`、`main_subject` | 未测试真人手法不得升级为生产模板 |
| `shot_director_blocking` | 保留并收紧 | 动作预算与反应覆盖 | `action_budget`、`reaction_coverage`、`reference_need` | 不新增剧本外动作，不让多人同动 |
| `shot_director_guard` | 强化 | 最小修复与尾帧合同守门 | `tail_state_card`、`template_level`、`guard_result` | 不重写结构，不扩大动作 |
| `storyboard_designer` | 弱化/转型 | 首帧/关键帧控制卡 | `first_frame_lock`、`keyframe_locks`、`tail_frame_lock` | 不重排镜头、不新增剧情 |
| `prompt_compiler` | 强化 | Seedance 2.0 合同编译器 | `compiled_prompt`、`reference_role_map`、`compiler_guards`、复杂度复评 | 不新增剧情/镜头/人物/台词 |
| `quality_inspector` | 强化 | 短剧精品感 + AI 可控性双质检 | `qc_result`、`failed_rule_id`、`repair_route`、`required_repair` | 不跨层直接重写上游事实 |

## 4. 场景与首帧控制结论

样片最适合 Seedance 默认生产的 `W1` 场景：

- 宅邸/卧室/客厅家庭压力。
- 门口/玄关入场并停住。
- 双人室内半身对峙。
- 道具信息插入和人物反应。
- 单人胸部以上反应停顿。

需要谨慎的 `W2` 场景：

- 会议桌/茶桌/办公室。
- 宴会厅/发布会/舞台。
- 车门/车内/到场揭示。
- 走廊、电梯、酒店大厅。
- 户外仪式、墓地、婚礼区。

必须 `R1` 或 `X` 的场景：

- 打斗、摔倒、推搡、抢夺。
- 夜景车灯危险、刀具、抱扶。
- 强特效、法术、能量光。
- 多人跨空间一镜到底。
- 15 秒内多事件多镜头蒙太奇。

`scene_analyst` 必须先锁空间、入口、人物、道具和风险；`storyboard_designer` 必须给首帧、关键帧和尾帧。没有这些锁定，不应进入 Seedance prompt 编译。

## 5. Story Planner 结论

`story_planner` 不再输出传统文学段落，而是输出 Seedance 生成单元。

统一字段：

```yaml
generation_unit_id: EP12_U01
signal_type: hook | pressure | misunderstanding | identity_reveal | prop_reveal | reaction_hold | tail_hook | other
duration_target: "4-6s"
event_atom: "一个可见事件，不写镜头"
emotion_delta:
  from: calm
  to: shocked_alert
reaction_handoff:
  next_subject: actor_b
  handoff_state: "看向门口，等待对方入场"
complexity_score: 0
split_required: false
split_reason: ""
reference_needs:
  - identity_reference
  - scene_reference
tail_state_required:
  character_positions: "女主仍站在门边"
  gaze_or_attention: "看向画外声源"
  prop_state: "无变化"
  unresolved_question: "谁回来了"
```

短剧信号候选：

- `hook`
- `pressure`
- `misunderstanding`
- `identity_reveal`
- `prop_reveal`
- `reaction_hold`
- `tail_hook`

必须拆分的剧情单元：

- 同时包含入场、质问、抢夺、身份揭示、群体反应。
- 三人以上每人都有动作。
- 道具被多人抢夺或归属改变。
- 反应停顿中又哭、转身、离开、反击。
- 尾钩同时揭示结果和制造新危机。

## 6. Prompt Compiler 与 QC 结论

`prompt_compiler` 的新职责是把合同编译为 Seedance 2.0 全能参考可执行 prompt。

编译硬规则：

- 默认 4-8 秒；8-12 秒只允许低复杂度；12-15 秒必须是建立/过渡/参考视频驱动。
- 默认 1-2 名主要角色；3 人以上只允许 1 个行动主体，其余静态反应。
- 每个时间段一个主驱动动作。
- 单段默认 1-3 个有效镜头；超过 3 个必须拆分或 R1 参考驱动。
- 每个参考资产只能有一个主职责：identity、scene、prop、motion、camera、audio。
- 每段必须有可继承尾帧：人物位置、视线、道具、门/车/电梯状态、距离关系。
- 禁止依赖字幕、屏幕文字、文件文字完成剧情关键证据。

`quality_inspector` 的硬 fail 条件：

- 单段超过 8 秒且包含 3 个以上事件。
- 单段 `complexity_score >= 5`。
- `R1` 模板没有视频/关键帧/动作参考。
- `X` 模板进入 prompt。
- 未使用 `template_id`。
- 3 人以上同动。
- 复杂动作、复杂运镜、强对白嘴型、多人反应同时出现。
- 尾帧人物、道具或门状态不可继承。
- 抽象导演词没有翻译为可见动作。

## 7. 跨 Agent 修改权

| 字段 | 生产者 | 消费者 | 有权修改者 |
|---|---|---|---|
| `scene_contract` | `scene_analyst` | 全链路 | `scene_analyst` |
| `dramatic_signal` | `director_showrunner` | `story_planner`, `shot_director`, `quality_inspector` | `director_showrunner` |
| `rhythm_diagnosis` | `rhythm_rewrite_director` | `story_planner`, `shot_director`, `prompt_compiler`, `quality_inspector` | `rhythm_rewrite_director` |
| `generation_unit` | `story_planner` | `shot_director`, `storyboard_designer`, `prompt_compiler`, `quality_inspector` | `story_planner` |
| `coverage_template_id` | `shot_director` | `storyboard_designer`, `prompt_compiler`, `quality_inspector` | `shot_director` |
| `action_budget` | `shot_director_blocking` | `prompt_compiler`, `quality_inspector` | `shot_director_blocking`, `shot_director_guard` 最小修复 |
| `tail_state_card` | `shot_director_guard` | `prompt_compiler`, `quality_inspector`, 下一段 | `shot_director_guard` |
| `first_frame_lock` | `storyboard_designer` | `prompt_compiler`, `quality_inspector` | `storyboard_designer` |
| `compiled_prompt` | `prompt_compiler` | `quality_inspector`, runtime | `prompt_compiler` |
| `qc_result` / `repair_route` | `quality_inspector` | `runners`, UI, 用户复审 | `quality_inspector` |

原则：下游发现上游问题只能打回或提出修复请求，不能直接发明上游事实。

## 8. 后续代码落地顺序

第一阶段，低风险：

1. 保持现有代码不动，把本报告与 schema/candidate 文件作为外部候选资料。
2. 为 `story_planner`、`prompt_compiler`、`quality_inspector` 写合同测试样例。
3. 建 Seedance 测试记录表：`candidate -> test_status -> whitelist/failure`。

第二阶段，中风险：

1. 修改 `types.py` 增加结构化合同字段。
2. 修改 `story_planner_impl.py`，强制输出 `generation_unit` 与 `complexity_score`。
3. 修改 `shot_director_impl.py`，强制输出 `coverage_template_id`、`action_budget`、`tail_state_card`。
4. 修改 `prompt_compiler_impl.py`，加入 Seedance profile gate。
5. 修改 `quality_inspector_impl.py`，加入复杂度、模板等级、参考绑定、尾帧状态质检。

第三阶段，高风险：

1. 修改 `graph_api.py` 和 `runners.py`，把 per-segment 链路显式化为 `shot_director -> storyboard_designer(optional) -> prompt_compiler -> quality_inspector`。
2. 调整人工 review、resume、rerun 和 downstream clear 行为。

所有代码改动前必须按项目要求先跑 GitNexus impact analysis。

## 9. 样片继续学习入库流程

94 集样片后续只产 candidate，不直接变 runtime 规则。

流程：

1. `candidate`: 从样片中抽取真人短剧手法，记录 episode、shot、信号、观察到的 coverage。
2. `degraded_seedance_version`: 降级成 4-8 秒、1-2 人、一个动作、明确参考与尾帧的版本。
3. `seedance_test`: 用 Seedance 2.0 全能参考实测，记录 pass / pass_with_limits / fail。
4. `whitelist`: pass 才能升级为 W1/W2；pass_with_limits 只能 W2/R1；fail 进入 failure mode 或 X。
5. `runtime rule`: 只有多次实测稳定的模板才能写入运行时规则卡。

## 10. 交付文件

本轮交付：

- `seedance_agent_restructure_master_report.md`
- `agent_restructure_contract_schema_v1.yaml`
- `scene_storyboard_candidate_registry_v1.yaml`
- `episode_profile_selection.json`
- `representative_shot_selection.csv`
- `contact_sheet_*.jpg`
- `episode_*_sequence_sheet.jpg`
- 四份并行子报告

本轮没有修改现有代码；新增的规则卡和候选报告已通过知识库检查。
