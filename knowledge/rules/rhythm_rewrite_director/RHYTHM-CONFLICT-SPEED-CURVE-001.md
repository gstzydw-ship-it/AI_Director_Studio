---
rule_id: RHYTHM-CONFLICT-SPEED-CURVE-001
title: 冲突诊断与速度曲线调度
doc_type: rule_card
rule_type: conflict_diagnosis
agent_scope:
- rhythm_rewrite_director
- story_planner
- shot_director
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- conflict_diagnosis
- speed_curve
- action_density
- sound_pressure
- prop_pressure
- weak_conflict
- user_director_intent
applies_when:
- 原剧本冲突偏弱
- 用户提出节奏、画面或调度不满意
- 原文只有概括动作，需要转成可拍动作密度
- 需要把快慢节奏传给 story_planner 和 shot_director
avoid_when:
- 用户明确要求逐字不做任何节奏增强
- 增强方案会改变剧情事实且用户尚未确认
signals:
- time_pressure
- action_density
- sound_pressure
- prop_pressure
- reaction_beat
scene_types:
- dialogue
- action
- suspense
- confrontation
- daily_rush
events:
- conflict_escalation
- speed_shift
- suspense_reveal
- reaction
risks:
- script_invention_risk
- weak_conflict
- over_segmentation
source_files:
- knowledge/09_节奏总控与剧本改写规则.md
- knowledge/15_故事节奏控制规则.md
---

# 冲突诊断与速度曲线调度

## 核心规则

`rhythm_rewrite_director` 面对任何剧本时，必须先判断戏剧冲突是否足够，再判断快慢节奏。它不是剧本摘要员，而是把剧本事实和用户导演意图转成可执行速度调度的总控导演。

## 必须先做冲突诊断

每场戏至少判断：

- 主角当前目标是什么
- 阻力来自谁或什么
- 失败代价是什么
- 时间压力是什么
- 是否存在秘密、误会、身份暴露、情绪伤口或隐藏信息
- 观众期待的爆点或钩子在哪里
- 原剧本冲突是否偏弱，弱在哪里

如果原剧本冲突弱，必须输出冲突增强方案，而不是只写“节奏偏平”。

## 冲突增强分级

### L1_动作层增强

允许增强：

- 动作密度
- 声音压力
- 道具阻碍
- 时间压迫
- 可见反应
- 停顿和再启动

不允许改变剧情事实、人物关系、台词信息或事件结果。

### L2_调度层增强

允许增强：

- 人物进入方向
- 谁先看到谁
- 信息释放顺序
- 群体压迫
- 旁观者的非关键反应
- 场面由散到聚、由动到停的节奏变化

不允许新增关键剧情事件，不允许让未命名人物承担关键证据或关键转折。

### L3_剧情层增强

涉及新增事件、改变因果、加入误会、改写关系、增加反转时，必须标注为“需用户确认”。L3 只能作为建议，不能传给下游当作已确定执行指令。

## 速度曲线要求

不得只写“快节奏”或“慢节奏”。必须说明：

- 起速点：节奏从哪里启动
- 加速动作：靠哪些连续动作、声音或道具形成速度
- 刹车点：哪里突然慢下来
- 慢拍原因：慢下来服务什么情绪或信息
- 再启动点：停顿后如何恢复动作压力
- 爆点：信息或关系在哪一刻撞出来
- 钩子落点：尾帧或卡断停在哪里

快节奏必须有动作密度；慢节奏必须有停顿位置。

## 概括动作转译

当原剧本只写“手忙脚乱”“急匆匆”“气氛紧张”“列队等候”“愣住”“回神”等概括词时，节奏总控必须把它们转成可拍的动作、声音、道具和调度锚点。

这些锚点必须标明来源：

- 原文明确事实
- 概括动作可展开
- 用户指定导演意图
- 建议补强锚点
- 需用户确认剧情增强

## 下游交接

给 `story_planner`：

- 哪些内容必须合并成完整剧情任务
- 哪些停顿只是段内节拍
- 哪些位置允许拆片、卡断或尾帧承接

给 `shot_director`：

- 哪些地方必须体现动作密度
- 哪些地方需要刹车停半拍
- 反应归属是谁
- 声音、道具、人群、移动方向如何形成节奏压力
- 禁止把用户要求的快段拍成慢动作或慢速走位

## 禁止

- 禁止把 L1/L2 补强写成原文事实。
- 禁止新增命名角色、关键台词、关键道具或关键事件。
- 禁止为了增强冲突改变人物关系、身份信息或事件结果。
- 禁止把整段都拍慢；慢只能落在明确情绪刹车点。
- 禁止把整段都拍快；快段之后必须判断是否需要信息刹车或反应停顿。
