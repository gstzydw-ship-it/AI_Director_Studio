---
rule_id: SEEDANCE20-COVERAGE-WHITELIST-001
title: Seedance 2.0 精品短剧 coverage 模板白名单
doc_type: rule_card
rule_type: shot_coverage_template
owner_agent: shot_director
agent_scope:
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
pipeline_stage: shot_template_selection
runtime_retrieval: true
retrieval_key:
- seedance2.0
- coverage白名单
- 镜头模板白名单
- 短剧镜头模板
- 竖屏短剧
- 可控镜头
- reaction_coverage
- shot_template_id
applies_when:
- "shot_director 为 Seedance 2.0 设计短剧片段"
- "需要从样片短剧手法中筛选可生成 coverage"
avoid_when:
- "目标模型不是 Seedance 2.0，且另有模型专用白名单"
failure_mode:
- "shot_director 直接复制真人短剧复杂覆盖法，导致 prompt_compiler 无法降级，视频模型生成失败。"
output_contract: "shot_director 必须输出 template_id、适用信号、主体、动作预算、时长、参考需求、尾帧状态和失败保护。"
example_good: "template_id: COV-SD20-W1-REACTION-HOLD；主体=女主；动作=下颌收紧并停顿；时长=4秒；尾帧=仍看向男主。"
example_bad: "镜头环绕两人，穿过人群，切到文件特写，再反打每个人的震惊反应。"
source_files:
- knowledge/external_sources/SEEDANCE20_OFFICIAL_SOURCES_2026-05-16.md
- knowledge/rules/shared/SEEDANCE20-OMNI-CAPABILITY-MATRIX-001.md
conflicts_with: []
supersedes: []
---

# Seedance 2.0 精品短剧 coverage 模板白名单

## 白名单等级

- `W1`: 生产默认模板。可直接用于短剧生成，仍需填写主体、动作、空间、尾帧。
- `W2`: 谨慎模板。只能在低复杂度、短时长、参考明确时使用。
- `R1`: 参考驱动模板。默认视为不可直接生产；只有上游真实提供 `reference_bindings` / `reference_asset` / `video_path` / `keyframe_path` 等绑定时才允许使用，否则必须拆分为 W1/W2。
- `X`: 禁用模板。不得交给 prompt_compiler 生成，只能拆分、后期或人工处理。

## 模板输出格式

每个镜头 coverage 必须输出：

```yaml
template_id: COV-SD20-W1-REACTION-HOLD
template_name: 单人反应停顿特写
dramatic_signal: 压迫后的沉默/受击/反击前停顿
duration_s: 3-5
main_subject: 女主
supporting_subjects: 男主可在离焦背景或画外
camera: 固定中近景或轻微缓推
action_budget: 一个小幅表演动作
reference_need: identity_reference + scene_reference
tail_state: 女主仍看向男主，下颌收紧，身体未离开原位
compiler_guard: 禁止加入第二个动作或跨轴反打
```

## W1 生产默认模板

### COV-SD20-W1-TWO-SHOT-PRESSURE

双人固定中景压迫。

- 适用：质问、威胁、误会对峙、身份压迫。
- 时长：4-7 秒。
- 角色：2 名主要角色。
- 镜头：固定中景、双人关系景、轻微缓推三选一。
- 动作预算：一人向前半步或抬眼，另一人停住/后退半步。
- 尾帧：两人距离和朝向清楚，方便下一段继承。
- 禁止：同段内抢夺、推搡、第三人闯入、环绕运镜。

### COV-SD20-W1-REACTION-HOLD

单人反应停顿特写。

- 适用：受击、忍住、眼神闪躲、反击前停顿、听到真相。
- 时长：3-5 秒。
- 角色：1 名主体，其他人在画外或离焦背景。
- 镜头：固定中近景、肩部以上特写、轻微缓推。
- 动作预算：下颌收紧、眼神停住、手指松开、呼吸停顿等一个小动作。
- 尾帧：表情和视线方向稳定。
- 禁止：同段说完整长台词、哭到崩溃再反击、转身离开。

### COV-SD20-W1-PROP-INSERT

道具信息插入镜。

- 适用：文件、手机、戒指、病历、照片、酒杯、钥匙。
- 时长：2-4 秒。
- 角色：手部或道具为主体，人物脸可不出现。
- 镜头：固定近景/特写。
- 动作预算：放下、递出、按亮屏幕、手指停在道具旁。
- 尾帧：道具位置、朝向、持有人明确。
- 禁止：抢夺、撕碎、复杂文字阅读、多人同时伸手。

### COV-SD20-W1-DOORWAY-ENTRANCE-STOP

门口入场并停住。

- 适用：闯入、撞见、救场、打断对话。
- 时长：4-6 秒。
- 角色：1 人入场，场内 1 人可静止反应。
- 镜头：门口固定中景或空间关系景。
- 动作预算：推门/跨入/停住三段小动作，不再追加质问或争抢。
- 尾帧：门状态、人物站位、视线方向明确。
- 禁止：多人陆续进门、人群散开、边冲边喊边抢道具。

### COV-SD20-W1-STEP-IN-POWER-SHIFT

向前半步的权力转移。

- 适用：女主反击、男主压迫、身份揭穿前的逼近。
- 时长：3-5 秒。
- 角色：1-2 人。
- 镜头：固定中近景或轻微缓推。
- 动作预算：主体向前半步，另一方只做微反应。
- 尾帧：距离变化清楚，不发生身体接触。
- 禁止：逼近后推人、扇耳光、拥抱、转身离开。

### COV-SD20-W1-TAILSTATE-RESET

尾帧关系复位镜。

- 适用：每个生成段末尾，需要给下一段保留空间和人物状态。
- 时长：2-4 秒。
- 角色：1-2 人。
- 镜头：固定关系景。
- 动作预算：停住、看向某人、道具留在手里/桌上。
- 尾帧：角色位置、手中道具、门状态、视线方向全部明确。
- 禁止：在尾帧继续运动或制造新事件。

## W2 谨慎模板

### COV-SD20-W2-SHOT-REVERSE-SAFE

低风险正反应切换。

- 适用：两人短对白、一问一答、听者反应。
- 时长：6-9 秒。
- 镜头：最多 2 个切点，保持同侧轴线。
- 条件：两人站位和空间锚点必须由 scene_analyst 提供。
- 失败保护：prompt_compiler 必须避免“反打至左/右侧”这类相对方位词。
- 超限处理：超过 2 次切换时拆成两个生成段。

### COV-SD20-W2-GROUP-STATIC-REACTION

三人静态反应。

- 适用：旁观者震惊、家族压迫、办公室围观。
- 时长：4-6 秒。
- 角色：最多 1 名行动主体 + 2 名静态反应者。
- 镜头：固定中景或关系景。
- 条件：静态反应者只能看向主体，不得各自动作。
- 超限处理：三人以上都有动作时拆分。

### COV-SD20-W2-SLOW-FOLLOW

单人慢速跟拍。

- 适用：走近门口、走向桌边、转身离开。
- 时长：4-7 秒。
- 角色：1 名主体。
- 镜头：正面平稳跟拍、背后平稳跟拍、侧向轻跟三选一。
- 条件：只能有一个移动方向，不跨空间。
- 禁止：边走边转身、边争抢、边切反应。

## R1 参考驱动模板

这些模板只有在提供视频参考或关键帧序列时才可使用：

- `COV-SD20-R1-FIGHT-BEAT`: 打斗、推搡、扇耳光、摔倒。
- `COV-SD20-R1-DANCE-RHYTHM`: 舞蹈、集体动作、节奏性身体表演。
- `COV-SD20-R1-FAST-CHASE`: 奔跑、追逐、骑行、快速穿越空间。
- `COV-SD20-R1-MULTI-SHOT-MONTAGE`: 9 秒以上多镜头蒙太奇。
- `COV-SD20-R1-LIP_SYNC_DIALOGUE`: 强嘴型对白或唱段。

没有真实绑定参考资产时，这些模板必须拆成 W1/W2 的小单元；不能只在 `reference_need` 里写 `motion_reference` 冒充已有参考。

## X 禁用模板

以下短剧手法在 Seedance 2.0 生产默认禁止：

- 单段内跨轴反打或让人物左右位置翻转。
- 一镜到底穿越多人、人群、房间、楼梯并完成剧情反转。
- 同时要求复杂动作、复杂运镜、强对白嘴型和多人反应。
- 抢夺文件/手机时多只手纠缠在一起。
- 打斗、摔倒、拥抱、亲密接触没有动作参考。
- 15 秒内塞入开门、质问、抢夺、哭戏、反击、第三人闯入。
- 依赖屏幕文字、文件文字、字幕作为剧情关键证据。
- 使用未经授权的真人人像作为角色参考。

## 样片学习入库流程

94 集短剧分析时，任何真人 coverage 只能先入 `candidate`：

1. 标记短剧信号：压迫、受击、打脸、误会、揭穿、认亲、救场。
2. 映射到 W1/W2/R1/X。
3. 写出降级版本：时长、主体、动作预算、参考需求、尾帧状态。
4. 用 Seedance 2.0 全能参考测试。
5. 通过后才升级到 W1/W2；失败则写入失败模式或 X 禁用区。

## 下游质检点

quality_inspector 必须检查：

- 是否给出 `template_id`。
- 是否超过模板时长。
- 是否超过动作预算。
- 是否说明参考资产职责。
- 是否写清尾帧状态。
- 是否把 R1 模板在无参考情况下直接交给 prompt_compiler。
- 是否命中 X 禁用模板。
