# director_showrunner / story_planner 短剧重构报告

生成时间：2026-05-16  
样片来源：`H:\样片`，94 集竖屏短剧  
分析产物：`D:\AI_Director_Studio\output\short_drama_analysis_full_20260516_105744`  
本报告只补充 showrunner 与 story_planner 的职责边界和剧情信号库候选，不重复节奏控制模板与镜头 coverage 模板。

## 1. 样片统计基线

- 视频规模：94 集，全部为 720x1280 竖屏，合计 10966.56s。
- 镜头规模：3410 个镜头；单集镜头数 min/median/mean/max = 3 / 36 / 36.28 / 75。
- 单集时长 min/median/mean/max = 61.44s / 113.90s / 116.67s / 243.52s。
- 镜头时长分布：P10=0.56s，P25=0.96s，P50=1.92s，P75=3.84s，P90=6.72s，P95=9.60s。
- 874/3410 个镜头 <=1s，占 25.6%；1464/3410 个镜头 <=1.5s，占 42.9%；1865/3410 个镜头 <=2s，占 54.7%；736/3410 个镜头 >=4s，占 21.6%。
- inferred_scale：MS half-body 1070，relation_or_environment_unknown 920，LS/MLS relation 756，MCU chest-up 592，CU shoulder-up 69，ECU/CU face-dominant 3。
- inferred_motion：high_cut_or_handheld_motion 1988，占 58.3%；active_motion_or_reframe 1352，占 39.6%；mostly_static 39；gentle_motion 31。
- 人脸粗检：0 人脸 920，1 人脸 1824，2+ 人脸 666。

直接启发：短剧不是“文学段落 -> 镜头化”的线性转换，而是由高频信息触发、反应停顿、尾部钩子组成的事件链。director_showrunner 应定义事件链中的爽点/压力/误会/揭示/尾钩；story_planner 应把这些信号切成 Seedance 2.0 可生成单元，交给 shot_director 再选择 coverage。

## 2. director_showrunner 新职责

director_showrunner 只输出短剧高层信号，不下沉到镜头、机位、正反打、coverage 或运镜。

应负责：

- 定义本集/本段的爽点目标：羞辱反击、身份压迫、误会升级、道具证据、被迫选择、公众打脸、关系翻盘。
- 定义冲突类型：权力压迫、亲密关系误判、身份阶层错位、证据被隐藏/亮出、旁观者施压。
- 定义反转目标：谁被误判、谁掌握信息、什么身份/道具/关系将改变局面。
- 定义情绪落点：震惊、忍住、羞辱、恐惧、冷静反击、群体错愕、尾部悬念。
- 输出信号顺序，而不是镜头顺序：例如 `pressure -> misunderstanding -> prop_reveal -> reaction_hold -> identity_reveal -> tail_hook`。
- 给 story_planner 的约束：每个高层信号必须能落成一个或多个可见事件原子；不能要求同一生成单元内同时完成多人入场、抢夺、强对白、反转和群体反应。

不应负责：

- 不写镜头模板、景别、coverage、轴线、正反打、蒙太奇。
- 不写“拍一个长镜头完成全部冲突”的指令。
- 不把字幕、文件文字、手机屏幕文字当成唯一剧情证据。

## 3. story_planner 新职责

story_planner 的核心职责不是把剧情拆成传统文学段落，而是拆成 Seedance 2.0 可生成单元。

每个生成单元只允许包含：

- 一个核心可见事件：人物逼近、停住、交出/亮出道具、听到真相后的反应、转身入场、旁观者静态反应等。
- 一个情绪变化：例如 `defensive -> shaken`、`humiliated -> controlled`、`confused -> alerted`。
- 一个反应交接点：明确下一单元由谁接、接什么视线/道具/位置/情绪。
- 一个尾帧状态：人物站位、视线、门/道具状态必须能被下一个生成单元继承。

story_planner 应输出生成单元，而不是文学段落。例如：

```yaml
generation_unit_id: EP12_U01
signal_type: hook
duration_target: 4-6s
event_atom: 女主突然听见熟悉的人回来了，侧脸停住并看向声源
emotion_delta: calm -> shocked_alert
reaction_handoff: 交给男主/归来者的入场或被点名反应
complexity_score: 1
split_required: false
reference_needs: [identity_reference, scene_reference]
tail_state_required: 女主仍看向画外声源，嘴唇微张，身体未移动
```

## 4. 样片证据与剧情/情绪信号库候选

### hook

定义：开场 10 秒内抛出身份、归来、撞见、危险或强问题，先给观众“为什么继续看”。

证据：

- 前 10 秒共有 377 个镜头，平均 3.50s，41.1% <=1.5s，62.3% 为 high_cut_or_handheld_motion。
- Episode 1 前 10 秒实际覆盖 10 个镜头，连续出现 0.96s、0.48s、1.44s、0.96s、0.48s 的快速信息切换。
- Episode 12 前 10 秒有 9 个镜头，shot 1 为 0.00-1.92s，ECU/CU face-dominant，关键帧 `keyframes/12/shot_001_000.00s.jpg` 可见女主侧脸惊讶，字幕信息为“你怎么就回来了”，是典型归来/撞见 hook。

story_planner 字段建议：

- `generation_unit_id`
- `duration_target`: 4-6s，若保留样片 0.5-2s 的短切效果，应由后续 shot_director/剪辑层处理，不在 story_planner 内写多镜头。
- `event_atom`: 一个可见触发，例如“听到归来者声音后停住看向门口”。
- `emotion_delta`: neutral/calm -> shocked/alerted。
- `reaction_handoff`: 交给归来者、被撞见者或旁观者。
- `complexity_score`: 0-2。
- `split_required`: 若 hook 同时包含入场、质问、抢夺、身份揭示，则 true。
- `reference_needs`: identity_reference + scene_reference；若 hook 依赖物件则加 prop_reference。
- `tail_state_required`: 角色视线方向和身体停留位置。

### pressure

定义：权力、身份、群体或亲密关系造成的压迫，常表现为两人/多人站位对峙、短句质问、被迫回应。

证据：

- 2+ 人脸镜头 666 个；LS/MLS relation 756、MS half-body 1070，说明压迫常建立在关系景/半身关系上，而不是纯大特写。
- Episode 4 前 10 秒：shot 1 为 0.00-2.88s，3 人 LS/MLS relation；shot 2 为 2.88-1.44s，2 人 MS；shot 3 为 4.32-0.48s，1 人 MCU。开场先给关系压力，再切受压反应。
- Episode 21 尾部 shot 26，93.12-94.56s，5 人 LS/MLS relation，关键帧 `keyframes/21/shot_026_093.12s.jpg` 可见多人公开场合对峙，字幕为“若真有人能拔出此剑”，属于群体压力/资格挑战。

story_planner 字段建议：

- `duration_target`: 4-7s。
- `event_atom`: 一方逼问/宣布限制/公开挑战，另一方只做一个反应。
- `emotion_delta`: controlled -> pressured 或 confident -> cornered。
- `reaction_handoff`: 被压迫者的单人反应或下一句反击。
- `complexity_score`: 1-3；3 人以上静态可 3，若每人都有动作则必须拆分。
- `split_required`: 三人以上均行动、边走边争吵、同时插入道具时 true。
- `reference_needs`: identity_reference + scene_reference；群体场面需要明确主次。
- `tail_state_required`: 压迫双方距离、朝向、旁观者是否静止。

### misunderstanding

定义：角色基于不完整信息误判关系/身份/动机，是短剧冲突继续升级的发动机。

证据：

- Episode 12 shot 1 的“你怎么就回来了”属于归来造成的关系误判入口；后续 9 个前 10 秒短镜头说明误会不是一段长对白，而是触发、反应、补充信息的连续单元。
- Episode 2 前 10 秒只有 5 个镜头，但 shot 4 为 8.64-9.60s MCU chest-up，随后 shot 5 为 9.60-17.76s 的 8.16s 单人 MCU，说明误会触发后会给角色较长的受击/消化空间。

story_planner 字段建议：

- `duration_target`: 4-8s。
- `event_atom`: 一个误会触发，例如“看见某人和错误对象站在一起”或“听到半句话后误解”。
- `emotion_delta`: trust -> doubt / calm -> defensive。
- `reaction_handoff`: 交给被误解者解释或反击。
- `complexity_score`: 1-2。
- `split_required`: 若误会需要展示 A 看到 B、B 递出道具、C 插话三件事，必须拆三单元。
- `reference_needs`: identity_reference + scene_reference；涉及道具则加 prop_reference。
- `tail_state_required`: 谁误会谁、视线落点、被误解者是否已察觉。

### identity_reveal

定义：真实身份、关系、权力来源被说出或被角色认出，通常改变压迫关系。

证据：

- Episode 73 shot 12，77.76-111.36s，33.60s，1 人 MCU chest-up，关键帧 `keyframes/73/shot_012_077.76s.jpg` 可见男角色在暗场中低头反应，字幕为人名“林燃”。这类身份/姓名点名在样片中会被长时间保留反应空间，但 Seedance 2.0 不应在单元内承载 33s 复杂表演。
- Episode 91 尾部 shot 57，105.12-105.92s，1 人 MCU，mostly_static，关键帧 `keyframes/91/shot_057_105.12s.jpg` 可见红衣女主静止凝视，是身份/关系翻盘后的尾部定格候选。

story_planner 字段建议：

- `duration_target`: 4-6s 揭示 + 3-5s 反应停顿，通常拆成两个单元。
- `event_atom`: “某人被点名/被称呼真实身份/旁人意识到其身份”。
- `emotion_delta`: superior -> threatened / confused -> recognition / humiliated -> empowered。
- `reaction_handoff`: 交给被揭示者或压迫者反应。
- `complexity_score`: 2-4。
- `split_required`: 身份揭示同时伴随入场、群体震惊、道具展示或反击台词时 true。
- `reference_needs`: identity_reference 必需；若身份由物件证明，加 prop_reference。
- `tail_state_required`: 揭示后谁掌握主动权、谁看向谁。

### prop_reveal

定义：证据、信物、文件、手机、戒指、剑等道具被亮出，改变场内信息结构。

证据：

- shot_records 中 `relation_or_environment_unknown` 有 920 个，很多为无脸或低脸占比镜头，说明样片存在大量环境/物件/手部信息插入空间。
- Episode 21 shot 26 公开挑战“拔出此剑”把“剑”作为资格/身份验证道具，后续 0.48s 快切 shot 28-30 形成结果前的悬念。
- 基准规则明确 prop_reference 是独立参考职责，不能让一个参考同时承担身份、场景、动作、运镜和风格。

story_planner 字段建议：

- `duration_target`: 3-5s。
- `event_atom`: “某人把证据放到桌上/举起信物/把剑指向众人可见处”。
- `emotion_delta`: denial -> exposed / uncertain -> confirmed。
- `reaction_handoff`: 交给看见道具的人。
- `complexity_score`: 1-3。
- `split_required`: 抢夺、摔碎、多手争抢、多人同时伸手时 true。
- `reference_needs`: prop_reference 必需；需要持有人时加 identity_reference。
- `tail_state_required`: 道具位置、持有人、朝向、是否仍在手中。

### reaction_hold

定义：信息击中后让角色停住，保留情绪消化、忍住或反击前的空气。

证据：

- 全部镜头中 >=4s 的有 736 个，占 21.6%，长停顿并不少见。
- 低运动且有人脸的长镜头候选包括：Episode 1 shot 26，34.56-54.72s，20.16s，1 人 MS；Episode 19 shot 23，96.96-120.96s，24.00s，2 人 MCU；Episode 73 shot 12，33.60s；Episode 94 shot 21，83.52-150.24s，66.72s。
- 这些长镜头说明真人短剧会保留情绪消化，但 Seedance 2.0 生产边界要求拆成 4-8s 低复杂度单元，长反应只作为“连续 reaction_hold 链”，不是单段生成。

story_planner 字段建议：

- `duration_target`: 3-5s，最多 6s。
- `event_atom`: “角色听完后停住，眼神变化/下颌收紧/手松开”。
- `emotion_delta`: shocked -> contained / hurt -> restrained / fear -> resolve。
- `reaction_handoff`: 交给反击、解释、旁观者反应或尾钩。
- `complexity_score`: 0-1。
- `split_required`: 若同一停顿里又哭、转身、离开、反击或说完整长台词，必须拆。
- `reference_needs`: identity_reference + scene_reference。
- `tail_state_required`: 表情、视线、身体是否仍在原位。

### tail_hook

定义：集尾/段尾留下未解决的问题、身份翻盘、道具结果或即将爆发的动作。

证据：

- 尾 10 秒共有 458 个镜头，平均 3.09s，57.4% <=1.5s，56.8% 为 high_cut_or_handheld_motion，尾部比开场更偏短切。
- Episode 6 尾 10 秒含 9 个镜头，其中 111.84s 后连续出现 0.48s、2.88s、0.96s、0.48s、0.48s、0.68s，典型尾部提速。
- Episode 21 尾部 shot 24-31 形成 5.28s 关系景、3.36s MCU、1.44s 5 人关系景、2.40s MCU、三个 0.48s 快切、0.52s 收尾，适合抽象为“挑战 -> 反应 -> 悬念动作前停住”。
- Episode 91 尾 10 秒含 9 个镜头，最后 shot 57 为 0.80s 单人 MCU mostly_static，关键帧 `keyframes/91/shot_057_105.12s.jpg` 可作为尾部身份/决心定格证据。

story_planner 字段建议：

- `duration_target`: 4-6s 作为生成单元；剪辑上的 0.48s 快切不在 story_planner 直接要求。
- `event_atom`: “关键人物停在门口/看向证据/听见名字/准备拔剑但结果未出”。
- `emotion_delta`: tension -> unresolved / exposed -> suspended。
- `reaction_handoff`: 下一集/下一段开场承接对象。
- `complexity_score`: 1-3。
- `split_required`: 尾钩同时包含结果揭示和新危机时 true，应拆成 reveal + tail_hook。
- `reference_needs`: identity_reference + scene_reference；道具尾钩加 prop_reference。
- `tail_state_required`: 必填，记录下集续接的视线、站位、道具状态和未完成动作。

## 5. story_planner 统一输出字段

每个信号落地为一个生成单元，字段必须统一：

```yaml
generation_unit_id: string
signal_type: hook | pressure | misunderstanding | identity_reveal | prop_reveal | reaction_hold | tail_hook | other
duration_target: "4-6s"
event_atom: "一个可见事件，不写镜头"
emotion_delta:
  from: string
  to: string
reaction_handoff:
  next_subject: string
  handoff_state: string
complexity_score: 0-5
split_required: true | false
split_reason: string
reference_needs:
  - identity_reference
  - scene_reference
  - prop_reference
  - motion_reference
tail_state_required:
  character_positions: string
  gaze_or_attention: string
  prop_state: string
  unresolved_question: string
```

字段解释：

- `generation_unit_id`：供 shot_director、storyboard_designer、prompt_compiler 追踪，不应等同于文学段落编号。
- `duration_target`：优先 4-8s；8-12s 只允许低复杂度；超过 12s 必须拆或依赖参考视频。
- `event_atom`：必须是画面可见或可被表演的一个动作/状态变化。
- `emotion_delta`：只写一个情绪转折，禁止同单元内连续三次情绪翻转。
- `reaction_handoff`：标明下一单元接谁、接什么状态，避免断裂。
- `complexity_score`：按 Seedance 2.0 能力矩阵估分。
- `split_required`：story_planner 自行先判定，不把超限复杂段丢给 shot_director。
- `reference_needs`：只写参考职责，不写具体镜头模板。
- `tail_state_required`：所有单元都应有；tail_hook、identity_reveal、prop_reveal 必填且更详细。

## 6. 必须拆分的剧情单元

以下剧情单元必须拆分：

- 单元超过 8s 且包含 2 个以上可见事件。样片中 Episode 73 shot 12 为 33.60s，Episode 94 shot 21 为 66.72s，只能作为长反应链证据，不能直接作为单生成单元。
- 同时出现身份揭示、群体反应、反击台词。应拆为 `identity_reveal -> reaction_hold -> pressure/反击`。
- 三人以上都有动作或台词目标。Episode 21 shot 26 的 5 人公开挑战适合作为压力关系单元，但后续每个关键反应必须拆出。
- 道具被抢夺、摔碎、多手争抢、从画外进入再触发群体震惊。应拆为 `prop_reveal -> prop_contact/attempt -> reaction_hold`，复杂接触需要 motion_reference。
- 入场同时质问、撞见、揭示身份、引发群体反应。应拆为 `entrance/hook -> pressure -> reaction_hold -> reveal`。
- 误会需要三个信息点才能成立，例如“看见 A 与 B、听到半句话、发现道具”。每个信息点是单独 event_atom。
- 尾钩既给出结果又抛出新危机。应拆为 `result_reveal -> tail_hook`，否则下集续接状态不清。
- 依赖屏幕文字、文件文字或字幕才能理解关键剧情。应改为可见道具状态 + 角色反应，不能把文字阅读作为唯一事件。

## 7. 可以合并的剧情单元

以下可以合并为一个生成单元：

- 两人静态压力对峙 + 一个轻微表情反应，时长 4-7s，复杂度 1-2。
- 单人听到信息后的 reaction_hold + 一个小动作，例如下颌收紧、抬眼、手松开，时长 3-5s。
- 道具被放下/举起 + 持有人保持静止，时长 3-5s。
- 误会触发 + 误会者一个视线变化，时长 4-6s。
- 身份被点名 + 被点名者短暂停住，时长 4-6s；若还要群体震惊，群体反应另拆。
- 尾钩中的“未完成动作前停住”，例如准备拔剑、推门前停住、看向画外来人，时长 4-6s。
- 2 人以内、无身体接触、无复杂运镜、无道具状态变化的短对白承接。

## 8. 重构结论

1. director_showrunner 的产物应是“短剧信号编排”，不是镜头设计。它负责决定本段靠什么爽、什么误会升级、哪个身份/道具翻盘、尾部留下什么问题。
2. story_planner 的产物应是“Seedance 2.0 生成单元列表”，不是文学段落。每个单元必须有一个 event_atom、一个 emotion_delta、一个 reaction_handoff 和一个 tail_state_required。
3. 样片证据显示，开场和尾部都大量依赖短切，但 story_planner 不应复制短切节奏；它只保留可生成事件原子和状态交接。
4. 长 reaction_hold 在样片中常见，但对 Seedance 2.0 应拆成多个 3-6s 低复杂度反应单元。
5. identity_reveal、prop_reveal、tail_hook 是 showrunner 与 story_planner 的关键交界：showrunner 定义揭示/尾钩的戏剧意义，story_planner 定义可见事件、参考需求、复杂度和拆分。
6. shot_director 之后才选择 coverage 白名单；本报告不新增、不复制 rhythm template 或 coverage template。
