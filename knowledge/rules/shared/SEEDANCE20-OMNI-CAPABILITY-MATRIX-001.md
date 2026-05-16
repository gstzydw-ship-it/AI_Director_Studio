---
rule_id: SEEDANCE20-OMNI-CAPABILITY-MATRIX-001
title: Seedance 2.0 全能参考能力矩阵与生产保守边界
doc_type: rule_card
rule_type: model_capability_profile
owner_agent: prompt_compiler
agent_scope:
- scene_analyst
- director_showrunner
- rhythm_rewrite_director
- story_planner
- shot_director
- shot_director_layout
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
- storyboard_designer
priority: P0
status: active
pipeline_stage: model_capability_gate
runtime_retrieval: true
retrieval_key:
- seedance2.0
- seedance2.0_omni_reference
- 全能参考
- 模型能力矩阵
- AI视频可控性
- 生成单元
- 镜头白名单
- 复杂度评分
applies_when:
- "目标视频模型是 Seedance 2.0"
- "使用全能参考模式"
- "需要把短剧规则转成 AI 视频可控生成单元"
avoid_when:
- "目标模型不是 Seedance 系列，且没有兼容 profile"
failure_mode:
- "上游按真人实拍导演思维输出复杂剧情/复杂镜头，prompt_compiler 直接交给视频模型，导致人物漂移、动作失控、空间翻面或短剧爆点不可读。"
output_contract: "所有 agent 必须先按本矩阵判断片段复杂度，再决定保留、降级、拆分或打回。"
example_good: "6秒双人对峙：固定中景，女主向前半步，男主沉默后退半步，切到女主反应特写。"
example_bad: "15秒内完成多人闯入、抢夺文件、环绕运镜、三次情绪反转和集体反应。"
source_files:
- knowledge/external_sources/SEEDANCE20_OFFICIAL_SOURCES_2026-05-16.md
conflicts_with: []
supersedes: []
---

# Seedance 2.0 全能参考能力矩阵与生产保守边界

## 核心原则

Seedance 2.0 全能参考模式不是“无限复杂 prompt 执行器”，而是“多模态参考绑定 + 短时长生成单元”。本系统以精品短剧为目标，所有 agent 必须优先保证可控、可复现、可质检。

官方能力说明可作为上限参考；生产默认边界必须更保守。

## 已确认能力

| 维度 | 官方确认 | 本项目生产默认 |
|---|---|---|
| 输入模态 | 文字、图片、音频、视频 | 全能参考开启时，必须给每个参考资产明确职责 |
| 参考输入上限 | 最多 9 张图片、3 段视频、3 段音频 | 短剧单段优先 1-4 个参考，超过 4 个必须说明绑定关系 |
| 时长 | 4-15 秒 | 精品短剧优先 4-8 秒；8-12 秒只给低复杂度段；12-15 秒只给建立/过渡/参考视频驱动段 |
| 图像参考 | 可参考主体、元素、场景、构图 | 最适合锁角色身份、服装、空间、道具、首帧构图 |
| 视频参考 | 可参考镜头语言、运镜、复杂动作、音效 | 复杂动作、快速运动、群体调度必须优先要求视频参考 |
| 音频参考 | 可参考音乐、声音、节奏和音画同步 | 短剧对白可写意图，但嘴型/方言/唱段必须降级或专项测试 |
| 多镜头 | 支持 15 秒多镜头音视频输出 | 单段默认 1-3 个有效镜头；超过 3 个必须拆分或视频参考驱动 |
| 复杂动作 | 官方展示复杂运动能力提升 | 生产默认只允许一个核心动作链；打斗、推搡、抢夺、多人接触必须拆分 |
| 主体一致性 | 官方称主体一致性提升 | 两个主要角色以内最稳；3 人以上进入谨慎区；多人群众戏默认拆分 |
| 文字渲染 | 官方仍提示文字渲染需优化 | 禁止依赖画面内文字/字幕完成剧情信息 |

## 复杂度评分

每个生成单元从 0 分开始，命中一项加 1 分：

- 超过 2 名主要角色。
- 有手部接触、抢夺、推搡、拥抱、打斗或身体碰撞。
- 有快速移动、奔跑、跌倒、骑行、舞蹈或大幅转身。
- 同一段里有运镜变化。
- 同一段里有 2 个以上情绪转折。
- 需要对白嘴型、歌唱、方言或强音画同步。
- 场景状态发生变化，如门开关、道具破碎、灯光突变、人群散开。
- 时长超过 8 秒。
- 使用 4 个以上参考资产。

裁决：

- 0-2 分：可直接进入白名单模板。
- 3-4 分：必须降级或拆成两个生成单元。
- 5 分及以上：禁止单段生成，必须拆分、改用视频参考或交给人工/后期。

## Agent 使用合同

`scene_analyst` 必须输出可控空间：场景类型、入口出口、固定物、主道具、角色数量、角色站位关系。

`director_showrunner` 只输出短剧爽点、冲突类型、反转目标和情绪落点，不输出复杂镜头。

`story_planner` 必须把剧情拆成 AI 可生成单元：每段只有一个核心可见事件、一个反应承接、一个情绪落点。

`shot_director` 只能从白名单 coverage 模板中选择镜头结构；未入白名单的真人短剧手法只能标记为 candidate，不得直接用于生产。

`storyboard_designer` 优先生成首帧/关键帧控制卡，锁定人物位置、空间锚点、表情起点和道具状态。

`prompt_compiler` 必须按目标模型 profile 降级：短句、明确主体、明确动作、明确空间、明确尾帧状态。

`quality_inspector` 必须同时检查短剧爽点和 AI 可控性；复杂度超限、未绑定参考、未使用白名单模板时必须 fail。

## 全能参考绑定规则

每个参考资产必须有唯一主职责：

- `identity_reference`: 角色脸、发型、服装、年龄感。
- `scene_reference`: 空间、门窗、家具、灯光方向、色调。
- `prop_reference`: 手机、文件、戒指、病历、酒杯等剧情物。
- `motion_reference`: 跑、转身、推门、下跪、打伞、递物等动作节奏。
- `camera_reference`: 镜头运动、景别变化、拍摄角度。
- `audio_reference`: 背景音乐、环境音、节奏、旁白或对白声线。

禁止一个参考同时承担身份、场景、动作、运镜、风格五种职责。职责冲突时，优先级为：角色身份 > 场景空间 > 道具状态 > 动作节奏 > 运镜风格 > 色调。

## 硬失败条件

命中以下任一项，质量检查必须阻断：

- 单段超过 8 秒且包含 3 个以上事件。
- 单段出现 3 名以上主要角色且每个人都有动作。
- 同时要求复杂动作、复杂运镜、对白嘴型、情绪反转。
- 让模型在同一生成段内完成跨轴反打、空间翻面或人物左右互换。
- 依赖画面内字幕、屏幕文字、文件文字来传达关键剧情。
- 使用真人人像参考但没有授权/验证说明。
- 未说明参考资产绑定关系，却要求角色一致、场景一致和动作一致。

## 94 集样片学习入库标准

样片分析只负责发现候选模板。候选模板必须补齐以下字段后才能进入生产白名单：

- `dramatic_signal`: 短剧信号，如压迫、误会、反击、认亲、揭穿、沉默。
- `template_id`: 对应白名单或 candidate 编号。
- `model_complexity_score`: 复杂度评分。
- `reference_needs`: 需要哪些参考资产职责。
- `seedance_test_status`: untested / pass / pass_with_limits / fail。
- `failure_modes`: 常见失败原因。
- `agent_consumers`: 哪些 agent 可以使用。
