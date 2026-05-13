---
rule_id: RHYTHM-CUTTING-TEMPO-HANDOFF-002
title: 快切、慢叙述与弹性片段时长交接
doc_type: rule_card
rule_type: rhythm_cutting_tempo_handoff
owner_agent: rhythm_rewrite_director
agent_scope:
- rhythm_rewrite_director
- story_planner
- shot_director
- quality_inspector
priority: P0
status: active
pipeline_stage: rhythm_handoff
runtime_retrieval: true
retrieval_key:
- rhythm-cutting-tempo-handoff-002
- fast_cut_windows
- slow_narration_windows
- long_take_windows
- time_compression_windows
- segment_duration_policy
- cutting_on_action
- jump_cut
- montage
- micro_pause
- shot_duration
- cutting_frequency
- scene_types.action
- scene_types.dialogue
- scene_types.suspense
applies_when:
- 节奏总控需要把快慢传给拆片和镜头导演
- 当前片段包含冲突升级、动作压入、悬念揭示、情绪极点或钩子结尾
- 15秒默认片段与实际戏剧速度发生冲突
avoid_when:
- "用户明确要求固定片段时长或一镜到底。"
- "快切会破坏剧本事实、空间轴线或动作连续性。"
failure_mode:
- "只写快/慢，不说明下游具体要做哪些任务。"
- "把快切误解成所有镜头都快速运镜、快速动作或慢动作。"
- "把慢叙述误解成拖长无信息走路、空镜或重复表情。"
output_contract: "输出 segment_duration_policy、story_planner_tasks、shot_director_tasks、quality_check_tasks；下游字段只能写任务清单，不写解释段落。"
example_good: "story_planner_tasks: 拆 0-6 秒快切段；shot_director_tasks: S01 1.5秒动作起点，S02 1秒动作中点切，S03 2秒受击结果。"
example_bad: "这里节奏快一点，那里慢一点。"
signals:
- action_density
- dialogue_coverage
- reaction_beat
- tailframe_lock
- hook_weight
- suspense_reveal
scene_types:
- action
- dialogue
- suspense
- confrontation
- daily_rush
events:
- conflict_escalation
- power_reversal
- suspense_reveal
- emotional_peak
- cliffhanger
- collision
- reaction
- cut
risks:
- over_segmentation
- vertical_closeup_overuse
- axis_break
- prompt_cut_budget_exceeded
- meaningless_motion
source_files:
- knowledge/05_剧本拆分与15秒片段规划规则.md
- knowledge/15_故事节奏控制规则.md
- knowledge/24_戏剧微粒识别与节奏触发规则.md
- knowledge/rules/rhythm_rewrite_director/RHYTHM-CONFLICT-SPEED-CURVE-001.md
- knowledge/rules/shot_director/SHOT-RHYTHM-SIGNAL-MAPPING-001.md
external_sources:
- https://www.backstage.com/magazine/article/film-rhythm-editing-guide-77147/
- https://www.filmsupply.com/articles/cutting-on-action-editing/
- https://www.adobe.com/creativecloud/video/hub/ideas/what-is-continuity-editing-in-film.html
- https://www.mediacollege.com/video/editing/time/compression.html
- https://learnaboutfilm.com/film-language/sequence/180-degree-rule/
conflicts_with:
- TIME-SEGMENT-MULTISHOT-001
- DOC-STORY-SPLIT-005
conflict_resolution: "15秒是默认容量，不是硬性长度。普通段仍优先 13-15 秒；命中高密度快切、钩子阻断、动作压入或切镜预算超载时，允许 4-10 秒短段，但必须写 short_segment_reason 与 script_basis。"
supersedes: []
---

# 快切、慢叙述与弹性片段时长交接

## 核心判断

`rhythm_rewrite_director` 不能只把片段标成“快”或“慢”。必须把快慢翻译成下游能执行的剪辑节奏：

- 快节奏 = 短时间内有效事件密集 + 人物动作/表情紧张 + 有边界的镜头快切辅助。前两项是主因，快切是辅助手段。
- 快切 = 更短的镜头停留、更高的切换频率、只保留动作顶点和信息增量；不是所有人物都快走、不是摄影机乱甩。
- 慢叙述 = 更长的镜头停留、更少动作、更明确的停顿或注视；不是拖长无信息位移。
- 长镜头 = 一个连续动作段内部靠演员走位、视线、焦点或空间调度变化推进；每一秒都必须有信息、关系或情绪变化。
- 时间压缩 = 省略没有叙事价值的中间过程，用出画/入画、动作中点切、局部插入、B-roll 或跳切保留起点、变化点和终点。

快节奏任务必须先确认事件密度和人物紧张态：是否有连续信息增量、动作顶点、表情/姿态突变、抢话/打断/回头/停住等紧张反应。若只有普通移动或普通操作，不得仅靠密集切镜伪装成快节奏。

镜头快切必须有观感边界：优先 2-3 个高价值镜头，必要时才增加 1 个辅助插入镜头；不得把每个微动作、每个眼神和每个道具细节都单独开镜。快切必须服务事件密度和人物紧张态，不能压过信息可读性、动作连续性和人物第一反应。

## 给下游的输出格式

节奏总控给下游的交接只写任务清单，不写解释性段落，不写“为什么高级/为什么有张力”的分析。

每条任务必须回答：

- 下游 agent 要做什么。
- 用哪几秒做。
- 保留哪些画面节点。
- 省略哪些过程。
- 切点或停顿落在哪里。
- 尾帧交给下一段什么状态。

推荐结构：

```yaml
editing_tempo_directive:
  segment_duration_policy:
    default: "13-15秒仍是普通导演片段容量"
    allow_short_segment_when: "快切窗口、钩子阻断、动作压入、切镜预算超载、独立受击反应"
  story_planner_tasks:
    - task: "拆成 0-6秒快切段"
      script_basis: "引用原文/增强版剧本依据"
      boundary: "从动作启动开始，到受击结果停住结束"
      duration: "6秒"
      keep_events: ["动作起点", "动作顶点", "受击结果"]
      omit_events: ["无信息走路", "重复整理", "解释性过渡"]
      short_segment_reason: "事件密度高，13-15秒会拖慢或超切镜预算"
    - task: "保留 6-9秒慢停段"
      script_basis: "引用信息命中或情绪命中依据"
      boundary: "从信息命中开始，到可继承尾帧结束"
      duration: "3秒"
      keep_events: ["人物停住", "视线/姿态变化", "尾帧状态"]
      forbid_events: ["新增解释", "空镜拖时长", "无信息慢走"]
  shot_director_tasks:
    - task: "执行快切"
      shot_count: "2-3个镜头"
      shot_duration: "每镜1-2秒"
      shot_order:
        - "镜头1：动作起点，拍清主体和方向"
        - "镜头2：动作50%-70%处切出，下一镜从30%-50%接续"
        - "镜头3：切受击者/关键道具/动作结果，只拍结果不补过程"
      cut_points: ["动作中点", "冲突顶点", "受击落点"]
      continuity: "保持同侧轴线、运动方向、道具状态连续"
      forbid: ["快速推拉摇移叠加", "每个细节都开镜", "无依据特写堆叠", "用过密切镜替代事件密度和人物紧张态"]
    - task: "执行慢叙述"
      shot_count: "1个稳定主镜头，必要时1个反应镜头"
      shot_duration: "主停顿1.5-3秒"
      shot_order:
        - "稳住半身/中景/双人关系景"
        - "减少动作，只拍呼吸、视线、姿态或道具状态变化"
        - "尾帧停在可继承站位"
      cut_points: ["信息命中后", "人物停住后", "尾帧状态清楚后"]
      forbid: ["空泛空镜", "重复表情", "无信息慢走", "提前解释情绪"]
  quality_check_tasks:
    - "检查是否只写了快/慢但没有任务清单"
    - "检查短段是否有 short_segment_reason"
    - "检查快切是否破坏轴线、动作匹配或道具连续性"
    - "检查慢叙述是否变成空镜拖时长"
```

禁止输出给下游：

- “这里要更紧张。”
- “这里节奏慢一点。”
- “这里需要电影感。”
- “这里用高级镜头语言。”

必须改成：

- “0-2秒拍动作起点；2秒在动作中点切；3-4秒切受击者停住。”
- “揭示后留 2秒，只拍人物停住、视线下移、手放回桌面。”
- “本段 6秒短段，理由：cliffhanger 已命中，继续拍会泄压。”

## 何时需要快切

优先使用快切或短段：

- 冲突升级：施压动作、反击动作、身体碰撞、争抢、追逐、闯入。
- 动作压入：上一反应还没消化，新事件已经物理进入。
- 时间压力：迟到、倒计时、电话催促、车门/电梯门/房门即将关闭。
- 混乱或慌乱：手忙脚乱、多人同时移动、找东西、收拾、躲避。
- 信息搜寻或准备蒙太奇：训练、准备、赶路、寻找、快速排查。
- 喜剧节拍：连续错误、反复失败、突然打断、反差反应。
- Cliffhanger 前 0.5-2 秒：命中动作顶点或威胁尾音后干净阻断。

快切任务必须具体：

- “先确认本段有事件密度和人物紧张态，再给有限快切；普通动作不要切碎。”
- “在动作 50%-70% 处切出，下一镜从动作 30%-50% 接续。”
- “只保留推门起点、撞上顶点、两人停住结果。”
- “每镜约 1-2 秒，最多 3 个高价值镜头。”
- “用切反应/切道具/切结果压缩过程。”
- “明确告诉 story_planner：这里可拆 4-8 秒短段，或并入 13-15 秒段内的 2-3 个短镜头。”
- “明确告诉 shot_director：镜头数、每镜秒数、切点、反应归属、尾帧状态。”

快切边界：

- 不为普通顺畅动作增加切镜密度。
- 不把人物第一反应剪掉；快段也要给观众读懂受击、发现或关系变化的最短停留。
- 不超过信息可读性的镜头密度；若 2-3 个镜头已经能表达动作起点、顶点和结果，就不要继续加插入镜头。
- 不用快速推拉摇移叠加人物快速动作和快速剪辑，避免“三快叠加”造成观感负担。

## 何时需要慢慢叙述

优先使用慢叙述、停顿或更长镜头：

- 情绪极点：人物被击中后需要观众读到身体停住、呼吸、眼神或姿态变化。
- 悬念揭示：发现前半拍、目标物可读、揭示后反应必须稳。
- 权力压迫：强者不急、弱者被迫停住，节奏慢本身就是权力。
- 关系冻结：误解、冷场、尴尬、沉默对峙、谁先移开视线。
- 道德选择或关键决定：角色还没行动，观众要看他如何决定。
- 尾帧承接：下一段必须继承的人物位置、道具状态、门状态需要看清。

慢叙述任务必须具体：

- “揭示后留 1.5-3 秒，不急着解释。”
- “稳住半身/双人关系景，动作减少，只看视线和姿态。”
- “少切，不插无关局部，不补空泛空镜。”
- “尾帧必须留下可继承站位和道具状态。”
- “明确告诉 story_planner：慢停属于段内反应窗口还是独立短段。”
- “明确告诉 shot_director：慢停期间只允许哪些可见动作，不允许补哪些解释动作。”

## 何时用长镜头

长镜头适合：

- 空间关系必须连续看清：穿门、绕桌、从人群中穿过、进入阈值空间。
- 悬念靠实时推进：角色一步步接近答案、危险或门口。
- 权力压迫靠“不切”成立：强者稳定推进，弱者无处可躲。
- 情绪崩塌需要连续体验：人物从压住到失控，不能用碎切替代。
- 群体调度有清晰层次：人群让路、聚拢、分开，观众需要看懂秩序变化。

长镜头禁用：

- 每秒没有新信息，只是在走路。
- 画面主体不清，既有大动作又有长台词又有多人交互。
- 需要多个关键反应归属，但镜头无法看清谁被击中。
- Seedance 单段切镜预算已超载，却用“同一机位继续”伪装切镜。

## 弹性片段时长

15 秒是默认导演施工容量，不是硬性尺子。

普通段：

- 普通对白、关系推进、动作承接仍优先 13-15 秒。
- 能在同一动作段内完成的受击、反应、收束，不要为了快而拆碎。

允许短段（4-10 秒）：

- `fast_cut_windows` 中事件密度高，13-15 秒会拖慢。
- `cliffhanger` 已命中，继续拍会泄压。
- 动作压入需要另起段，避免一个 prompt 内塞太多主体和切镜。
- 切镜预算超载，需要把 13 秒拆成 8 秒 + 5 秒或类似结构。
- 独立受击反应本身就是新戏剧动作，且超过 3-5 秒。

短段必须写：

- `short_segment_reason`
- `script_basis`
- `boundary_reason`
- `tailframe_state`

## 与现有规则的裁决

- 与 `TIME-SEGMENT-MULTISHOT-001` 不冲突：该规则防止普通戏被拆碎；本卡只允许高密度快切、钩子阻断和切镜预算超载时短段化。
- 与 `PROMPT-CUT-BUDGET-001` 联动：如果一个 13-15 秒段需要超过 3 次显式切镜，优先拆段，不让 prompt_compiler 硬塞。
- 与 `SHOT-RHYTHM-SIGNAL-MAPPING-001` 联动：镜头导演必须把本卡的快切/慢停翻译成 shot 数量、duration、cut_point 和 continuity。
- 剧本事实优先：任何快切、慢停、长镜头都不能新增剧本外事件、台词、关键道具或改变因果。

## 禁止

- 禁止只写“节奏快/节奏慢”。
- 禁止把快切写成“快速推拉摇移 + 人物快速动作 + 复杂背景”三快叠加。
- 禁止把慢叙述写成空镜拖时长、无意义走路、重复凝视。
- 禁止为了短段数量好看，把完整发言单元切断。
- 禁止在 cliffhanger 命中后补释怀、解释、离场或总结。
