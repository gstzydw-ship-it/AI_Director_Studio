# scene_analyst 与 storyboard_designer 重构报告

生成日期：2026-05-16  
样片目录：`H:\样片`  
分析产物：`D:\AI_Director_Studio\output\short_drama_analysis_full_20260516_105744`  
适用对象：`scene_analyst`、`storyboard_designer`、首帧/关键帧控制器  

## 0. 样片证据摘要

本轮只使用已有分析产物与 keyframes 做归纳，不修改现有代码。

量化证据来自 `shot_records.csv` 与 `episode_meta.csv`：

| 指标 | 数值 |
|---|---:|
| 样片集数 | 94 |
| 总时长 | 10966.56s |
| 检测镜头数 | 3410 |
| 单集平均时长 | 116.67s |
| 单集镜头数均值 | 36.28 |
| 镜头时长中位数 | 1.92s |
| 镜头时长 P25 / P75 / P90 | 0.96s / 3.84s / 6.72s |
| `<=1.2s` 快切占比 | 25.8% |
| `1.2-3.0s` 常规短镜头占比 | 44.0% |
| `>3.0s` 长镜头占比 | 30.2% |
| 推断景别最多 | MS half-body 1070；relation/environment 920；LS/MLS relation 756；MCU chest-up 592 |
| 人脸数量 | 1 人镜头 1824；2 人镜头 499；3 人及以上镜头 167；0 人/不可识别 920 |
| 运动标签 | high_cut_or_handheld_motion 1988；active_motion_or_reframe 1352；mostly_static/gentle_motion 70 |

代表性证据：

- 高密度宴会/发布会/仪式空间反复出现：ep20 shot001/051/067，ep21 shot016/031，ep36 shot001/039，ep81 shot001，ep89 shot024/047。
- 宅邸、卧室、客厅、门口空间反复出现：ep10 shot001/020/038，ep11 shot001/033/065，ep12 shot001/038/075，ep93 shot001/030/058。
- 会议桌、茶桌、办公室对峙反复出现：ep50 shot017/033，ep51 shot014/027，ep52 shot001/023/044，ep64 shot014。
- 车门/车内/到场揭示反复出现：ep43 shot017/033，ep44 shot001/028，ep45 shot001/030。
- 门口、走廊、电梯、入口打断反复出现：ep12 shot075，ep20 shot001，ep32 shot026，ep61 shot001/022，ep92 shot001/028/055。
- 打斗、摔倒、推搡、特效、强运动镜头存在但不可直接交给 Seedance 单段生成：ep23 shot051，ep24 shot044，ep26 shot038，ep37 shot016，ep40 shot040，ep58 shot021，ep61 shot042，ep62 shot032，ep73 shot015。

## 1. 可控场景/空间类型分级

分级沿用 Seedance 2.0 全能参考模式生产边界：`W1` 可默认生产，`W2` 谨慎生产，`R1` 参考驱动，`X` 禁止直接单段生成。

| 场景/空间类型 | 常见样片信号 | Seedance 可控性 | 关键证据 | scene_analyst 必须锁定 |
|---|---|---|---|---|
| 宅邸客厅/卧室/梳妆/洗衣区 | 家庭压力、起床、收拾、隐忍、床边对峙 | W1 | ep10 shot001/020/038；ep11 shot001/033/065；ep12 shot038 | 房间锚点、床/沙发/门、人物坐站关系、手中物/衣物状态 |
| 门口/玄关/房门打断 | 闯入、撞见、救场、回头停住 | W1 | ep12 shot075；ep20 shot001；ep32 shot026；ep92 shot055 | 门状态、入口方向、入场者与场内人距离、尾帧门开/关 |
| 双人室内对峙半身空间 | 质问、误会、压迫、忍住、反击前停顿 | W1 | ep4 shot001/015/030；ep30 shot021；ep39 shot029 | 双人朝向、轴线、谁是动作主体、谁只反应 |
| 道具信息插入空间 | 手机、文件、照片、盒子、茶杯、药瓶、戒指 | W1 | ep5 shot036；ep21 shot031；ep47 shot001；ep91 shot043 | 道具来源、持有人、落点、可读信息是否依赖画面文字 |
| 会议桌/茶桌/办公室 | 长辈施压、商务谈判、身份确认 | W2 | ep50 shot017；ep51 shot014；ep52 shot023/044；ep64 shot014 | 桌面锚点、主说话人、旁听者静态化、茶杯/文件状态 |
| 宴会厅/发布会/舞台正面 | 新老板到场、公开羞辱、身份揭示、群体围观 | W2 | ep20 shot067；ep21 shot016；ep36 shot039；ep81 shot001 | 台/屏/红毯/人群边界、主角位置、群演只做静态反应 |
| 酒店/大厅/走廊/电梯 | 到场、擦肩、近距离逼问、封闭空间尴尬 | W2 | ep20 shot001；ep32 shot026；ep61 shot001；ep62 shot001 | 入口/出口、走向、是否跨空间、是否需要跟拍 |
| 车内/车门/下车揭示 | 豪车身份、接送、车边对峙 | W2 | ep43 shot017；ep44 shot001；ep45 shot001 | 车门开合、坐/站关系、下车动作是否拆为单向状态 |
| 户外仪式/墓地/婚礼区 | 多人站位、公开见证、情绪压迫 | W2/R1 | ep15 shot001/028；ep16 shot001/058；ep19 shot001/026 | 主体与围观者层级、白布/桌台/花等锚点、风/裙摆/人群不应同动 |
| 夜间外景/雨地/车灯背光 | 追逐、晕倒、抱扶、刀具、危险感 | R1 | ep73 shot004/008/015；ep94 shot001/013/025/037 | 光源方向、危险道具、人物倒地/扶抱状态、必须要 motion/video reference |
| 打斗/摔倒/推搡/抢夺 | 身体接触、跌倒、多人冲突、混乱走位 | R1/X | ep23 shot051；ep26 shot038；ep37 shot016；ep58 shot021；ep62 shot032 | 只能标记风险与拆分需求，不能输出单段复杂动作 |
| 舞台特效/法术/强光/超自然 | 能量光、舞台烟雾、角色变装、奇幻效果 | R1/X | ep2 shot046；ep4 shot059；ep40 shot040；ep61 shot042；ep67 shot051 | 特效来源、主体姿态、是否后期处理；默认要求参考视频或拆分 |
| 多人宴会全场调度 | 5 人以上同动、围观、跪倒、群体反应 | X | ep20 shot067；ep33 shot021；ep56 shot015/028；ep81 shot001；ep89 shot047 | 只能作为人群静态锚点或后期/人工调度，不给 Seedance 单段生成 |

## 2. scene_analyst 新输出合同

`scene_analyst` 的任务应从“描述场景”升级为“交付可生成的空间状态合同”。输出必须结构化，供 `story_planner`、`shot_director`、`storyboard_designer`、`prompt_compiler` 继承。

### 2.1 必填字段

```yaml
scene_contract_version: "scene_spatial_contract_v1"
scene_id: string
scene_type: enum
seedance_scene_grade: W1 | W2 | R1 | X
space_anchor:
  primary_anchor: string
  secondary_anchors: [string]
  camera_safe_viewpoints: [string]
  forbidden_viewpoints: [string]
entrance_exit:
  entrances: [string]
  exits: [string]
  door_or_vehicle_state: string
  crossing_risk: low | medium | high
active_cast:
  - character_id: string
    screen_role: main_actor | pressure_source | listener | witness | background
    start_position: string
    facing: string
    action_budget: string
offscreen_cast:
  - character_id: string
    relation_to_visible_action: speaking_offscreen | waiting_to_enter | implied_witness | none
prop_state:
  - prop_id: string
    owner_or_source: string
    start_state: string
    allowed_state_change: none | place | pick_up | reveal | drop | hand_over
    end_state_required: string
blocking_risk:
  cast_count_risk: low | medium | high
  contact_risk: none | hand_contact | body_contact | fight_or_fall
  movement_risk: static | one_direction | cross_space | chase_or_crowd
  axis_risk: low | medium | high
  text_dependency_risk: low | medium | high
reference_needs:
  identity_reference: required | optional | forbidden
  scene_reference: required | optional
  prop_reference: required | optional
  motion_reference: none | keyframe_sequence | video_reference_required
  camera_reference: none | optional | required
  audio_reference: none | optional | required
scene_tail_state:
  character_positions: string
  prop_positions: string
  entrance_exit_state: string
  continuity_warning: string
quality_flags:
  - string
evidence:
  sample_episode_shots:
    - "ep12 shot075 keyframes/12/shot_075_..."
  statistics_refs:
    - string
```

### 2.2 字段约束

- `scene_type` 应使用受控枚举，例如 `domestic_bedroom_pressure`、`domestic_living_room_pressure`、`doorway_entrance_stop`、`meeting_table_pressure`、`banquet_public_reveal`、`vehicle_arrival_reveal`、`corridor_or_elevator_pressure`、`outdoor_ceremony_witness`、`night_danger_confrontation`、`fight_or_fall_risk`。
- `space_anchor.camera_safe_viewpoints` 只能写真实机位语言：如“客厅侧面平视”“门口正面关系景”“从A肩后看向B”“会议桌一端平视”。禁止“空间关系视角”“尾帧承接视角”等抽象机位。
- `active_cast` 中最多允许 1 个行动主体；其他人物默认 `listener` 或 `witness`。如果 3 人以上都要动作，`seedance_scene_grade` 必须至少为 `R1`，多数情况下为 `X`。
- `offscreen_cast` 用来承接短剧常见“画外人压迫/即将闯入”。不要把画外人强行生成在画面里。
- `prop_state.allowed_state_change` 单段只允许一个单向变化。抢夺、撕碎、多人同时伸手，应标记 `blocking_risk.contact_risk=fight_or_fall` 并要求拆分。
- `reference_needs.motion_reference=video_reference_required` 时，下游不得直接编译为纯文本 Seedance prompt。

## 3. storyboard_designer / 首帧控制器新输出合同

`storyboard_designer` 应从“画面描述”升级为“首帧/关键帧锁定卡”。每个生成单元至少输出首帧与尾帧；R1 片段还要输出中间关键帧序列或声明参考视频。

### 3.1 每个生成单元必填字段

```yaml
storyboard_unit_contract_version: "storyboard_frame_lock_v1"
unit_id: string
source_scene_id: string
coverage_template_id: string
seedance_complexity_grade: W1 | W2 | R1 | X
duration_s: number
first_frame_lock:
  visible_cast:
    - character_id: string
      exact_screen_position: left | center | right | foreground | background
      pose: string
      gaze_target: string
      hands_state: string
      expression_start: string
  space_anchor_visible: [string]
  entrance_exit_visible_state: string
  prop_visible_state:
    - prop_id: string
      position: string
      owner: string
  camera_lock:
    shot_size: LS_MLS_relation | MS_half_body | MCU_chest_up | CU_shoulder_up | ECU_CU_face_dominant | prop_insert
    angle: eye_level | slight_low | slight_high
    viewpoint: string
    motion_policy: fixed | slow_push | slow_follow | reference_driven
  lighting_color_lock: string
  reference_bindings:
    identity_reference: [string]
    scene_reference: [string]
    prop_reference: [string]
    motion_reference: [string]
keyframe_locks:
  - keyframe_time_s: number
    event_state: string
    changed_state_only: string
tail_frame_lock:
  character_positions: string
  prop_positions: string
  gaze_and_emotion: string
  entrance_exit_state: string
  next_unit_handoff: string
compiler_guards:
  - string
failure_if:
  - string
evidence:
  sample_episode_shots:
    - string
```

### 3.2 首帧/关键帧必须锁的信息

- 人物：谁在画内、谁在画外、谁是行动主体、谁只能静态反应。
- 位置：左/中/右、前景/背景、坐/站/跪/倒地，避免下一段左右翻转。
- 视线：看向谁、是否避开、是否画外声触发。
- 手部：空手、持手机/文件/茶杯/刀具、手放桌上、是否已松开。
- 道具：来源、持有人、落点、尾帧是否仍可见。
- 入口/出口：门、车门、电梯门、走廊尽头、舞台入口的开合/占用状态。
- 镜头：景别、平视/过肩/正面关系景，不写抽象机位。
- 尾帧：必须给下一生成单元可继承的“人物位置 + 道具位置 + 入口状态 + 情绪状态”。

### 3.3 与现有逻辑的对齐点

GitNexus 显示 `storyboard_designer_node` 已调用 `_build_storyboard_continuity_notes`，且测试覆盖“同场景上一尾帧提示下一首帧承接”。本报告建议把该连续性能力前置为显式合同字段：`tail_frame_lock.next_unit_handoff` 与 `first_frame_lock` 必须成对校验。

## 4. 不能直接交给 Seedance 的真人短剧手法

以下手法在样片中存在，但不应作为单个纯文本生成单元交给 Seedance。处理方式只能是拆分、参考视频驱动、后期或人工处理。

| 手法 | 风险原因 | 样片证据 | 处理 |
|---|---|---|---|
| 多人同动宴会全景 | 3 人以上动作、群演方向、轴线和身份关系容易崩 | ep20 shot067；ep33 shot021；ep81 shot001；ep89 shot047 | 拆为主角关系景 + 群体静态反应 + 尾帧复位 |
| 打斗、摔倒、推搡、跪倒 | 身体接触、跌落物理、动作顶点难控 | ep23 shot051；ep26 shot038；ep37 shot016；ep58 shot021；ep62 shot032 | R1 视频参考；无参考则拆 W1 动作前/动作后 |
| 抢夺手机/文件/杯子 | 多手接触和道具归属易错 | ep21 shot031；ep56 shot028；ep67 shot040 | 拆为“道具展示”“伸手前停住”“道具已换手尾帧” |
| 同段跨空间追逐/快跑 | 运动方向、背景连续、人物身份稳定难控 | ep60 shot016/021；ep73 shot013/015 | 必须视频参考或改为入口停住/反应镜 |
| 强特效/法术/能量光 | 特效形态与人物动作耦合，模型容易吞主体 | ep2 shot046；ep4 shot059；ep40 shot040；ep61 shot042；ep67 shot051 | 后期或参考视频；Seedance 只生成主体定帧 |
| 车灯背光晕倒/抱扶 | 强光、倒地、身体接触、夜景噪声叠加 | ep73 shot004/008/015；ep94 shot037 | 拆为背光建立、倒地后状态、救援者反应 |
| 15s 内多镜头蒙太奇 | 快切、跨轴、剧情反转和口型对话叠加 | 高运动 0.48s 镜头大量存在，1988 条 high_cut_or_handheld_motion | 只保留 1-3 个有效镜头；超过则由剪辑/参考视频驱动 |
| 依赖屏幕/文件/字幕文字传递证据 | 文本渲染不可靠，信息不可读 | ep21 shot031 手机画面；多处屏幕/字幕叠加 | 用道具来源和人物反应传达，不依赖画内文字 |
| 亲密抱扶/贴身/扛抱 | 肢体接触和相对位置容易错 | ep43 shot033；ep44 shot028；ep94 shot037 | 参考视频或拆成“靠近前”“已扶住后”静态尾帧 |

## 5. 后续模板库 candidate

以下仅为 candidate，不等同于白名单生产模板。进入模板库前需补 `seedance_test_status`、失败样例与参考资产绑定规则。

| template_id | 场景/手法 candidate | 适用信号 | Seedance 复杂度 | 参考需求 | 尾帧承接 |
|---|---|---|---|---|---|
| SCN-SD20-W1-DOMESTIC-BED-REACTION | 卧室/床边单人受击停顿 | 起床、隐忍、误会、病弱 | W1 | identity + scene；可选 prop | 人物仍在床/床边，视线方向明确 |
| SCN-SD20-W1-DOORWAY-INTERRUPT | 门口入场并停住 | 闯入、撞见、救场、听到真相 | W1 | identity + scene | 门状态、入场者站位、场内人朝向清楚 |
| SCN-SD20-W1-TWO-SHOT-PRESSURE | 双人固定半身压迫 | 质问、误会、身份压迫 | W1 | identity + scene | 双方距离和轴线不变，下一镜可反打 |
| SCN-SD20-W1-PROP-REVEAL-STOP | 道具揭示后人物停住 | 手机、照片、文件、戒指、茶杯 | W1 | prop + identity；scene optional | 道具落点/持有人清楚，人物反应稳定 |
| SCN-SD20-W1-REACTION-HOLD-CHEST | 胸部以上反应停顿 | 听到真相、忍住、眼神转冷 | W1 | identity | 表情和视线锁住，不新增动作 |
| SCN-SD20-W2-MEETING-TABLE-PRESSURE | 茶桌/会议桌对峙 | 长辈施压、商务谈判、签字/递杯 | W2 | scene + prop + identity | 桌面道具归属清楚，旁听者静态化 |
| SCN-SD20-W2-BANQUET-PUBLIC-REVEAL | 宴会厅公开揭示 | 新老板、公开羞辱、身份曝光 | W2 | scene + identity；群体参考可选 | 主角和压力源站位清楚，群演只做背景 |
| SCN-SD20-W2-STAGE-ANNOUNCEMENT | 舞台/发布会宣布 | 台上发言、台下反应、公开认亲 | W2 | scene + identity + optional camera | 台上/台下层级明确，尾帧回关系景 |
| SCN-SD20-W2-VEHICLE-ARRIVAL-REVEAL | 车门旁到场揭示 | 豪车到场、下车、接送 | W2 | scene + vehicle/prop + identity | 车门开合状态和人物站位可继承 |
| SCN-SD20-W2-CORRIDOR-SLOW-FOLLOW | 走廊单人慢跟 | 走向门口、离开、压迫逼近 | W2 | scene + identity；motion optional | 人物停在明确门/走廊锚点前 |
| SCN-SD20-W2-ELEVATOR-CLOSE-PRESSURE | 电梯/封闭空间近距对峙 | 尴尬、逼问、沉默 | W2 | scene + identity | 人物距离与门状态清楚，避免贴身接触 |
| SCN-SD20-W2-OUTDOOR-CEREMONY-WITNESS | 户外仪式/墓地静态见证 | 婚礼、墓地、公开见证 | W2/R1 | scene + identity；多人需 keyframe | 主体与见证者层级清楚，群体不运动 |
| SCN-SD20-R1-FIGHT-FALL-BEAT | 打斗/摔倒动作顶点 | 被打、摔倒、跪倒、推搡 | R1 | video motion reference required | 只承接动作后状态，不能继续打斗 |
| SCN-SD20-R1-PROP-SCRAMBLE | 多手抢夺道具 | 抢手机、抢文件、夺杯 | R1 | motion reference + prop | 道具最终归属明确，手部不再纠缠 |
| SCN-SD20-R1-NIGHT-BACKLIGHT-DANGER | 夜景车灯/危险道具 | 晕倒、刀具、救援、追击 | R1 | scene + motion/video + prop | 倒地/扶住状态明确，光源不再变化 |
| SCN-SD20-R1-FANTASY-EFFECT-POSE | 法术/强光/舞台特效定帧 | 能量光、变装、奇幻压迫 | R1/X | effect/video reference or post | 只锁主体姿态，特效建议后期 |
| SCN-SD20-X-CROWD-CROSS-SPACE-ONE-SHOT | 多人跨空间一镜到底 | 群体冲突、全场调度、多人倒地 | X | 不进入纯 Seedance prompt | 必须拆为 W1/W2 小单元 |

## 6. 重构落地建议

1. `scene_analyst` 先输出 `scene_contract_version=scene_spatial_contract_v1`，再允许下游设计镜头。没有 `space_anchor`、`active_cast`、`prop_state`、`blocking_risk` 的场景，不应进入 `storyboard_designer`。
2. `storyboard_designer` 每个生成单元输出 `first_frame_lock`、`keyframe_locks`、`tail_frame_lock`。首帧必须继承上一单元尾帧，尤其是门/车门/道具/人物左右位置。
3. `shot_director` 可继续使用现有 coverage 白名单，但所有真人样片新手法先以 candidate 进入库，不直接升级为 W1/W2。
4. `prompt_compiler` 应拒绝 `seedance_complexity_grade=X`，并对 `R1` 检查是否存在 `motion_reference` 或关键帧序列。
5. 质量检查新增硬规则：3 人以上同动、身体接触、跨空间追逐、强特效、依赖画内文字，任何一项未拆分即 fail。

## 7. 结论

94 集样片的可复用核心不是复杂真人调度，而是“空间锚点 + 单一动作预算 + 明确尾帧”的短剧生成单元。最适合 Seedance 默认生产的是宅邸/门口/双人压迫/道具揭示/单人反应；宴会厅、会议桌、车门、走廊属于 W2，需要更严格首帧和尾帧；打斗、摔倒、抢夺、强特效、夜景危险和多人跨空间调度必须进入 R1/X，不能由纯文本 prompt 直接承担。
