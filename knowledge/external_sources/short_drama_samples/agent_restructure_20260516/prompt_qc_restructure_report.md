# prompt_compiler / quality_inspector Seedance 2.0 全能参考模式重构报告

生成日期：2026-05-16  
样片来源：`H:\样片`，94 集竖屏短剧样片  
分析目录：`output/short_drama_analysis_full_20260516_105744`

## 1. 结论摘要

`prompt_compiler` 应从“续写/美化 prompt 的创作 agent”收窄为“合同编译器”：只接收上游已锁定的剧情事实、拆片边界、coverage 白名单模板、状态合同和参考资产清单，编译为 Seedance 2.0 全能参考模式可执行 prompt；不得新增剧情、镜头、人物、台词、道具状态或情绪反转。

`quality_inspector` 应从“格式质检”升级为“双质检”：同时检查短剧精品感和 AI 可控性。短剧精品感检查注意力、节奏、受击反应、道具信息、尾帧钩子是否成立；AI 可控性检查 Seedance 2.0 的人物数、动作预算、参考绑定、尾帧状态、字幕/屏幕文字、跨轴/多镜头和复杂度是否超限。

核心重构方向：`shot_director` 负责选择白名单 coverage 和降级镜头合同，`prompt_compiler` 负责把合同翻译成自然中文执行 prompt，`quality_inspector` 负责阻断任何绕过白名单、参考绑定和复杂度预算的输出。

## 2. 样片统计基准

来自 `shot_records.csv`、`episode_meta.csv`、`analysis_summary.json` 与 `short_drama_shot_director_report.md`：

| 指标 | 统计 |
|---|---:|
| 视频数 | 94 |
| 竖屏比例 | 94/94，全部 9:16 |
| 检测镜头数 | 3410 |
| 单集平均时长 | 116.67s |
| 单集时长范围 | 61.44s - 243.52s |
| 单集平均镜头数 | 36.3 |
| 镜头平均时长 | 3.21s |
| 镜头中位时长 | 1.92s |
| P25 / P75 | 0.96s / 3.84s |
| P90 / P95 | 6.72s / 9.60s |
| <=1.2s 短切 | 880，25.8% |
| 1.2-3.0s 常规镜头 | 1499，44.0% |
| >3.0s 长镜头 | 1031，30.2% |
| >8s 镜头 | 250，7.3% |
| >12s 镜头 | 104，3.0% |
| >15s 镜头 | 70，2.1% |

景别粗估分布：

| 景别 | 数量 | 占比 |
|---|---:|---:|
| MS half-body | 1070 | 31.4% |
| relation_or_environment_unknown | 920 | 27.0% |
| LS/MLS relation | 756 | 22.2% |
| MCU chest-up | 592 | 17.4% |
| CU shoulder-up | 69 | 2.0% |
| ECU/CU face-dominant | 3 | 0.1% |

人物数粗估：

| 单镜可见人脸数 | 数量 | 占比 |
|---|---:|---:|
| 0 人 | 920 | 27.0% |
| 1 人 | 1824 | 53.5% |
| 2 人 | 499 | 14.6% |
| >=3 人 | 167 | 4.9% |
| >=4 人 | 45 | 1.3% |

运动强度：

| 运动分类 | 数量 | 占比 |
|---|---:|---:|
| high_cut_or_handheld_motion | 1988 | 58.3% |
| active_motion_or_reframe | 1352 | 39.6% |
| mostly_static | 39 | 1.1% |
| gentle_motion | 31 | 0.9% |

样片启发不是“把实拍复杂镜头照搬进模型”，而是：

- 短剧节奏快，但常规镜头仍占 44.0%，中位镜头 1.92s，不能把精品感等同于无控制短切。
- 关系/环境/半身类镜头合计约 2746 个，是短剧叙事主体；`prompt_compiler` 应优先保留关系景、半身景、可见站位和尾帧状态。
- CU/ECU 仅约 72 个，应只用于信息炸点、受击反应、道具状态，不应覆盖完整对白。
- 三人及以上镜头只有 4.9%，说明 AI 生成单元默认应控制在 1-2 名主要角色；三人以上必须是低动作预算或拆分。
- >8s 镜头仅 7.3%，>12s 仅 3.0%；Seedance 2.0 单段 8s 以上必须降低复杂度或改用参考驱动。

## 3. 现有规则文件的重构依据

### 3.1 Seedance 2.0 全能参考能力矩阵

`knowledge/rules/shared/SEEDANCE20-OMNI-CAPABILITY-MATRIX-001.md` 已给出 P0 边界：

- 全能参考不是“无限复杂 prompt 执行器”，而是“多模态参考绑定 + 短时长生成单元”。
- 官方时长上限可到 4-15s，但项目生产默认：精品短剧优先 4-8s；8-12s 只给低复杂度段；12-15s 只给建立、过渡或参考视频驱动段。
- 单段默认 1-3 个有效镜头；超过 3 个必须拆分或由视频参考驱动。
- 默认只允许一个核心动作链；打斗、推搡、抢夺、多人接触必须拆分。
- 主要角色 1-2 人最稳；3 人以上进入谨慎区。
- 参考资产必须有唯一主职责：`identity_reference`、`scene_reference`、`prop_reference`、`motion_reference`、`camera_reference`、`audio_reference`。
- 复杂度 0-2 可进白名单模板，3-4 必须降级或拆成两个生成单元，5 及以上禁止单段生成。

### 3.2 Coverage 白名单

`knowledge/rules/shot_director/SEEDANCE20-COVERAGE-WHITELIST-001.md` 已定义生产模板等级：

- `W1`：生产默认模板，可直接用于短剧生成。
- `W2`：谨慎模板，只能在低复杂度、短时长、参考明确时使用。
- `R1`：参考驱动模板，必须有视频参考或关键帧参考，否则拆分。
- `X`：禁用模板，不得交给 `prompt_compiler` 生成。

白名单要求每个 coverage 输出 `template_id`、适用信号、主体、动作预算、时长、参考需求、尾帧状态和失败保护。这意味着 `prompt_compiler` 不应再临时判断“这个镜头怎么拍”，而应只翻译这些字段。

### 3.3 样片模板库

`rhythm_control_template_library_v1.yaml` 给出样片节奏统计：平均镜头 3.21s，中位 1.92s，短切 25.8%，常规 44.0%，长镜头 30.2%，并区分紧凑生活压力、高压揭示、封闭空间对峙、道具揭示情绪停顿、低切情绪停留等节奏带。

`shot_coverage_template_library_v1.yaml` 给出 coverage role：`establish_relation`、`dialogue_pressure`、`impact_reaction`、`action_apex`、`information_reveal`、`relation_recover`、`tailframe_hold`，并要求最后 0.5s 有可继承尾帧，严禁字幕、屏幕文字、英文字幕和文字浮层。

### 3.4 既有 Prompt/QC 规则

`knowledge/07_Seedance输出词典与模型适配.md` 已要求：

- 最终输出顺序为角色参考总控、空间与首帧总控、风格锚点、时间轴、约束、参考调用。
- 每个时间段先立主体分镜基底，再进入动作。
- 一镜一主动作。
- 核心角色尽量 1-2 人。
- 含对白必须禁止字幕、屏幕文字、英文字幕、文字浮层。
- 每张参考图必须写死职责，人物图不污染场景，尾帧图优先于文字复述。

`knowledge/17_结果质检与回溯修正规则.md` 已要求：

- QC 覆盖 `prompt_compiler` 输出的最终 Seedance prompt。
- 检查主体+景别、动作执行、运镜、空间连续性、状态合同、当前戏份角色残留、门/电梯状态单调、字幕与碰撞误读、节奏安全、对白完整性、cliffhanger 与反转兑现。
- `fail` 必须包含 `target_agent`、`issue`、`suggested_fix`。

## 4. prompt_compiler 新职责

### 4.1 职责定义

`prompt_compiler` 是 Seedance 2.0 全能参考模式的执行 prompt 编译器。

输入：

- `scene_analyst` 的空间合同：场景、入口/出口、固定物、道具、人物站位。
- `story_planner` 的剧情合同：`fragment_id`、`source_script_events`、`exact_dialogue_units`、`active_cast`、`offscreen_cast`、`state_contract`。
- `rhythm_rewrite_director` 或节奏模板的节奏合同：`rhythm_band`、`target_duration_s`、`shots_per_5s`、`min_reaction_hold_s`。
- `shot_director` 的白名单 coverage 合同：`template_id`、`template_level`、`coverage_role`、`action_budget`、`reference_need`、`tail_state`、`compiler_guard`。
- `storyboard_designer` 或资产系统的参考资产清单：`image_id` / `video_id` / `audio_id`、`role`、`target_id`、`scope`。

输出：

- 单个 Seedance 2.0 全能参考可执行 prompt。
- 输出必须是上游合同的编译结果，不是新的导演方案。

禁止：

- 不新增剧情事件、人物、台词、道具、镜头、情绪转折。
- 不把 `candidate`、`X`、未测试复杂实拍 coverage 直接写成生产 prompt。
- 不用抽象词替代可见动作，例如只写“情绪崩溃”“压迫感拉满”“高级感”。
- 不在时间轴里复读禁止事项；硬约束集中写在【约束】。

### 4.2 编译步骤

1. 验证上游合同完整性：缺 `template_id`、`state_contract`、`reference_binding`、`tail_state` 时不编译，返回可执行缺字段错误。
2. 读取 `template_level`：`W1/W2` 可编译；`R1` 必须检查参考；`X` 直接阻断。
3. 计算或继承 `model_complexity_score`：超过等级阈值则降级/拆分，不尝试用长 prompt 兜底。
4. 绑定参考资产职责：每个参考只承担一个主职责，按角色身份、场景空间、道具状态、动作节奏、运镜/风格、音频节奏分离。
5. 编译时间轴：每个时间段先主体+景别+视角/稳定性，再主动作，再反应/台词/道具落点，再尾帧状态。
6. 编译约束：只写物理、连续性、字幕/文字、人物残留、道具/门状态，不写“镜头锁定”等会覆盖导演切镜的约束。
7. 输出参考调用：引用已绑定资产，不在结尾首次绑定。

## 5. quality_inspector 新职责

### 5.1 双质检模型

`quality_inspector` 必须同时输出两个维度：

1. 短剧精品感质检：
   - 注意力是否集中在当前戏剧信号。
   - 3 秒内是否释放关系压力、动作启动、信息钩子或必要空间建立。
   - 高价值信息后是否保留受击反应窗口。
   - 道具、身份揭示、关系压迫是否有可读落点。
   - 尾帧是否保留下一段可继承的关系、空间、道具或动作顶点。

2. AI 可控性质检：
   - 是否使用白名单 `template_id`。
   - `template_level` 是否允许生产。
   - 时长、人物数、动作预算、切镜数、运镜模态是否超限。
   - `R1` 是否有视频/关键帧参考。
   - 参考资产职责是否唯一且绑定到目标。
   - 是否出现字幕、屏幕文字、可读文件文字依赖。
   - 是否跨轴、人物左右互换、尾帧不清或状态回弹。

### 5.2 QC 输出原则

- `pass`：短剧精品感与 AI 可控性均通过。
- `warn`：可优化但不阻断，如 8s 以下低复杂度段缺少更强视角机会。
- `fail`：任何 P0/P1 控制边界命中，必须阻断生成，并给自动返修指令。

QC 不重写 prompt，不新增镜头，只输出定位明确的返修任务。

## 6. prompt 编译硬规则

### 6.1 时长

| 场景 | 编译规则 |
|---|---|
| 4-8s | 默认生产区，允许 W1/W2 低复杂度模板 |
| 8-12s | 只允许低复杂度、低动作密度、参考明确的段落 |
| 12-15s | 只允许建立、过渡、低切情绪停留或视频参考驱动 |
| >15s | 不编译为单段 Seedance prompt，必须拆分 |

硬规则：

- 单段 >8s 且包含 3 个以上事件，fail。
- 单段 >8s 且 `model_complexity_score >= 3`，必须拆分或降级。
- >12s 且无参考视频/关键帧序列，默认 fail。
- 时间轴内部镜头数默认 1-3 个；超过 3 个必须拆分或标记 `R1-MULTI-SHOT-MONTAGE` 且有参考。

### 6.2 人物数

- 默认 1-2 名主要角色。
- 3 人以上必须满足：只有 1 名行动主体，其余是静态反应/背景关系点。
- 3 人以上且每人都有动作，fail。
- 4 人以上默认拆分，除非是无动作群体反应关系景且 `W2-GROUP-STATIC-REACTION` 条件满足。

### 6.3 动作预算

- 每个时间段一个主驱动动作。
- 其他动作只能是表情、视线、局部手部落点或承接动作。
- 打斗、推搡、抢夺、摔倒、拥抱、亲密接触、多人手部纠缠：必须 `R1` 且有动作/视频参考；无参考则拆分或 fail。
- 主体快、镜头快、环境复杂三者只能快一个维度；三快叠加 fail。

### 6.4 参考资产绑定

每个资产必须有：

- `asset_id`
- `asset_type`: image / video / audio
- `reference_role`
- `target_id`
- `scope`: global / segment / shot
- `first_appearance_segment`
- `allowed_use`
- `forbidden_use`

规则：

- 人物参考图只锁身份、五官、发型、体态、服装，不锁场景背景。
- 场景参考图只锁空间、门窗、家具、光线方向、色调，不锁人物外貌。
- 上一段尾帧图优先作为下一段首帧、构图、光线、空间和已成立状态锚点，不长篇文字复述。
- 一个参考不得同时承担身份、场景、动作、运镜、风格五种职责。
- `R1` 模板必须至少有 `motion_reference`、`video_reference` 或关键帧序列。

### 6.5 尾帧状态

每个 prompt 必须有可继承尾帧：

- 人物位置。
- 朝向/视线。
- 手中或落点道具。
- 门/车门/电梯状态。
- 距离关系。
- 下一段从哪里承接。

禁止：

- 尾帧停在无空间信息的眼神、手部、黑场、抽象空镜。
- 尾帧继续新增动作或新事件。
- 尾帧人物与当前 `active_cast/offscreen_cast` 矛盾。

### 6.6 字幕 / 屏幕文字限制

- 含对白时，【约束】必须明确：禁止字幕、屏幕文字、英文字幕、文字浮层；台词只作为声音或口型存在。
- 不依赖文件文字、手机屏幕文字、字幕或可读标牌传递关键剧情。
- 道具信息可通过“谁递出/谁看见/谁停住/道具落点”传递，不要求模型生成可读文字。

### 6.7 跨轴 / 多镜头限制

- 单段默认锁定同一空间轴线，不写“反打至左/右侧”造成左右互换。
- `W2-SHOT-REVERSE-SAFE` 最多 2 个切点，且必须有清楚站位和空间锚点。
- 禁止单段内跨轴反打、空间翻面、人物左右位置互换。
- 超过 3 个有效镜头必须拆分或用 `R1-MULTI-SHOT-MONTAGE` 且有参考。

## 7. QC fail 条件与自动返修模板

### 7.1 复杂度超限

Fail 条件：

- `model_complexity_score >= 5`。
- 单段 >8s 且包含 3 个以上事件。
- 同时要求复杂动作、复杂运镜、对白口型和情绪反转。

自动返修模板：

```yaml
status: fail
target_agent: shot_director
failed_rule_id: SD20_COMPLEXITY_BUDGET
issue: 当前生成单元复杂度超出 Seedance 2.0 全能参考生产边界。
repair_instruction: 将该段拆成 2 个以上生成单元；每个单元只保留 1 个核心可见事件、1 个主动作链、1 个尾帧状态。若保留复杂动作，必须改为 R1 并提供 motion/video reference。
```

### 7.2 未使用 template_id

Fail 条件：

- `coverage_plan` 或 prompt 元数据缺 `template_id`。
- `template_id` 为 candidate 或自由文本。

自动返修模板：

```yaml
status: fail
target_agent: shot_director
failed_rule_id: COVERAGE_TEMPLATE_REQUIRED
issue: 未提供可生产白名单 template_id，prompt_compiler 无法判断动作预算和尾帧职责。
repair_instruction: 从 COV-SD20-W1/W2/R1 白名单中选择一个 template_id；补齐 duration_s、main_subject、action_budget、reference_need、tail_state、compiler_guard。不能新增剧情或镜头。
```

### 7.3 R1 无参考

Fail 条件：

- `template_level: R1` 但无 `motion_reference`、`video_reference` 或关键帧序列。
- 使用打斗、追逐、强口型、多镜头 montage 等 R1 模板但只给文字。

自动返修模板：

```yaml
status: fail
target_agent: shot_director
failed_rule_id: R1_REFERENCE_REQUIRED
issue: R1 参考驱动模板缺少必要视频/关键帧/动作参考。
repair_instruction: 二选一：1) 补充 motion_reference/video_reference/keyframe_sequence 并绑定 target_id 与 scope；2) 降级为 W1/W2 小单元，把复杂动作拆成固定关系景、动作顶点、受击反应、尾帧复位。
```

### 7.4 X 禁用模板

Fail 条件：

- 命中 X 模板：跨轴反打、穿越多人/房间一镜到底、多快叠加、无参考打斗/摔倒/亲密接触、依赖屏幕文字。

自动返修模板：

```yaml
status: fail
target_agent: shot_director
failed_rule_id: X_TEMPLATE_BLOCKED
issue: 当前 coverage 属于 Seedance 2.0 生产禁用模板，不得交给 prompt_compiler。
repair_instruction: 将 X 手法拆成白名单 W1/W2 片段；保留原剧情事实，只改镜头承载方式。每个拆分单元必须有 template_id、单一主动作、清楚尾帧。
```

### 7.5 尾帧不清

Fail 条件：

- 无 `tail_state` 或 `tailframe_role`。
- 尾帧停在眼神/手部/黑场/抽象空镜，无法继承空间。
- 尾帧人物、门、道具状态与下一段入口状态冲突。

自动返修模板：

```yaml
status: fail
target_agent: prompt_compiler
failed_rule_id: TAILFRAME_STATE_REQUIRED
issue: 最终 prompt 未给出可继承尾帧状态。
repair_instruction: 在时间轴最后 0.5-1.0 秒补为关系景或关键主体半身景；写清人物位置、朝向、手部/道具、门/电梯/车门状态和下一段承接点。不得新增动作或新事件。
```

### 7.6 抽象情绪词未落到可见动作

Fail 条件：

- 只写“压迫感、崩溃、震惊、情绪拉满、电影感、高级感”。
- 反转/羞辱/信息炸点后无眼神、下颌、呼吸、手指、肩背等可见反应。

自动返修模板：

```yaml
status: fail
target_agent: prompt_compiler
failed_rule_id: VISIBLE_EMOTION_ANCHOR_REQUIRED
issue: 抽象情绪词未转译为可见动作或表情锚点。
repair_instruction: 保留原戏剧含义，将抽象词改为 1 个可见身体/表情锚点，例如下颌收紧、眼神停住、手指松开、呼吸停顿、肩背僵住。不要新增台词、哭喊或第二个动作。
```

### 7.7 字幕 / 屏幕文字违规

Fail 条件：

- 有对白但【约束】未禁止字幕/屏幕文字/英文字幕/文字浮层。
- 剧情关键证据依赖手机、文件、屏幕或字幕的可读文字。

自动返修模板：

```yaml
status: fail
target_agent: prompt_compiler
failed_rule_id: NO_SUBTITLE_SCREEN_TEXT
issue: prompt 依赖或诱发画面文字。
repair_instruction: 在【约束】集中写明禁止字幕、屏幕文字、英文字幕、文字浮层；把文字证据改为道具来源、递出动作、人物识别反应和停顿落点。台词只作为声音或口型存在。
```

### 7.8 参考绑定错误

Fail 条件：

- 人物参考图被用于场景背景。
- 尾帧图被长篇文字复述替代，或同时重复调用场景图造成冲突。
- 当前无戏份人物因参考图残留在画面。

自动返修模板：

```yaml
status: fail
target_agent: prompt_compiler
failed_rule_id: REFERENCE_ROLE_BINDING
issue: 参考资产职责混用或超出 scope。
repair_instruction: 为每个 reference_asset 写唯一 reference_role、target_id、scope、allowed_use、forbidden_use；删除当前 active_cast 之外的人物正向站位。上一段尾帧图只作为首帧/空间/光线/已成立状态锚点。
```

## 8. 新增或强化字段 schema

### 8.1 prompt_compiler 输入合同

```yaml
prompt_compiler_input_contract:
  schema_version: prompt_compiler_seedance20_omni_v1
  fragment_id: string
  target_model: Seedance 2.0
  generation_mode: omni_reference
  aspect_ratio: "9:16"
  source_script_events:
    - event_id: string
      text: string
      locked: true
  exact_dialogue_units:
    - speaker: string
      text: string
      source_span: string
  active_cast:
    - character_id: string
      display_name: string
      reference_asset_id: string|null
  offscreen_cast:
    - character_id: string
      reason: string
      negative_binding: string
  state_contract:
    entry_state: string
    object_state_transitions:
      - object_id: string
        from_state: string
        to_state: string
        visible_action: string
    exit_state: string
    forbidden_continuity:
      - string
  rhythm_contract:
    rhythm_band: string
    target_duration_s: number
    shots_per_5s_max: number
    min_reaction_hold_s: number
    non_omittable:
      - string
  coverage_contract:
    template_id: string
    template_level: W1|W2|R1|X
    coverage_role: string
    duration_s: string
    main_subject: string
    supporting_subjects:
      - string
    camera_base: string
    action_budget:
      max_main_actions: 1
      allowed_secondary_actions:
        - facial_reaction
        - eyeline_shift
        - hand_detail
        - breathing_pause
      forbidden_actions:
        - string
    reference_need:
      - identity_reference
      - scene_reference
      - prop_reference
      - motion_reference
      - camera_reference
      - audio_reference
    tail_state:
      position: string
      eyeline: string
      prop_state: string
      door_vehicle_state: string|null
      next_segment_handoff: string
    compiler_guard:
      - string
  reference_assets:
    - asset_id: string
      label: string
      asset_type: image|video|audio
      reference_role: identity_reference|scene_reference|prop_reference|motion_reference|camera_reference|audio_reference|previous_tailframe
      target_id: string
      scope: global|segment|shot
      first_appearance_segment: string
      allowed_use:
        - string
      forbidden_use:
        - string
      auth_status: verified|internal|unknown
  model_complexity:
    score: integer
    triggers:
      - string
    decision: compile|degrade|split|block
```

### 8.2 prompt_compiler 输出元数据

```yaml
compiled_prompt_metadata:
  schema_version: compiled_prompt_seedance20_omni_v1
  fragment_id: string
  compiled_from_template_id: string
  template_level: W1|W2|R1
  duration_s: number
  effective_shot_count: integer
  main_character_count: integer
  model_complexity_score: integer
  reference_bindings:
    - asset_id: string
      reference_role: string
      target_id: string
      scope: string
      first_bound_in_section: character_reference_control|space_first_frame_control|timeline|reference_call
  action_budget_used:
    main_actions: integer
    secondary_actions:
      - string
    over_budget: boolean
  dialogue_text_policy:
    has_dialogue: boolean
    no_subtitle_constraint_present: boolean
    screen_text_dependency: boolean
  tailframe_contract:
    tailframe_role: tailframe_reset|tailframe_action_peak|tailframe_object_anchor|tailframe_hold
    readable_for_next_segment: boolean
    visible_state_summary: string
  compiler_changes:
    added_story: false
    added_shot: false
    added_character: false
    added_dialogue: false
```

### 8.3 quality_inspector 输入/输出 schema

```yaml
quality_inspector_result:
  schema_version: quality_inspector_seedance20_omni_v1
  fragment_id: string
  status: pass|warn|fail
  short_drama_quality:
    director_taste_score: number
    attention_clarity: pass|warn|fail
    rhythm_legibility: pass|warn|fail
    reaction_window: pass|warn|fail
    prop_information_readability: pass|warn|fail
    tail_hook_or_handoff: pass|warn|fail
    notes:
      - string
  ai_controllability:
    template_id_present: pass|fail
    template_level_allowed: pass|fail
    complexity_budget: pass|warn|fail
    reference_binding: pass|warn|fail
    r1_reference_check: pass|fail|not_applicable
    action_budget: pass|warn|fail
    character_count_budget: pass|warn|fail
    subtitle_screen_text: pass|fail
    axis_multishot_control: pass|warn|fail
    tailframe_readability: pass|warn|fail
    visible_emotion_anchors: pass|warn|fail
  failed_checks:
    - failed_rule_id: string
      severity: P0|P1|P2
      target_agent: scene_analyst|story_planner|shot_director|prompt_compiler
      source_field: string
      issue: string
      evidence: string
      repair_instruction: string
  auto_repair_directives:
    - directive_id: string
      target_agent: string
      operation: bind_reference|degrade_template|split_segment|rewrite_visible_action|add_tail_state|remove_screen_text_dependency
      constraints:
        no_new_story: true
        no_new_dialogue: true
        no_new_character: true
      instruction: string
```

## 9. Agent 边界建议

### prompt_compiler

必须强化：

- `template_id` 强依赖：无白名单模板不编译。
- `model_complexity_score` 强依赖：超过阈值不靠长 prompt 兜底。
- `reference_assets` 强绑定：每个参考资产唯一职责。
- `state_contract` 强继承：入口、单向道具变化、尾帧状态必须进入 prompt。
- `no_new_content` 自检：输出元数据声明未新增剧情/镜头/角色/台词。

### quality_inspector

必须强化：

- 不只查格式，必须给短剧精品感评分。
- 必须把 `template_id`、`template_level`、`model_complexity_score`、`reference_binding` 作为 P0/P1 可控性检查。
- 对 `R1` 无参考、`X` 模板、尾帧不清、字幕/屏幕文字、抽象情绪词、三快叠加等直接 fail。
- fail 结果必须可自动返修，不能只写“整体不够好”。

## 10. 推荐落地顺序

1. 先在 `shot_director` 输出中强制补齐白名单字段：`template_id`、`template_level`、`action_budget`、`reference_need`、`tail_state`、`compiler_guard`。
2. 再让 `prompt_compiler` 校验合同完整性，缺字段直接返回结构化错误。
3. 增加 `compiled_prompt_metadata`，让 QC 不必从自然语言里猜复杂度和参考绑定。
4. 将 `quality_inspector` 输出拆成 `short_drama_quality` 与 `ai_controllability` 两块，并把 fail 指令模板标准化。
5. 用 94 集样片统计校准阈值：默认 4-8s、1-2 人、1 主动作、1-3 有效镜头、最后 0.5-1.0s 可读尾帧。

