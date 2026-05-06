---
rule_id: RHYTHM-SIGNAL-REWRITE-001
title: 戏剧微粒驱动的节奏改写
doc_type: rule_card
rule_type: rhythm_rewrite
agent_scope:
- rhythm_rewrite_director
- quality_inspector
- story_planner
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- rhythm-signal-rewrite-001
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.collision
- events.reaction
- risks.script_invention_risk
- risks.blood_avoidance
- dialogue_types.long_dialogue_compression
- dialogue_types.reaction_beat
- scene_types.dialogue
- scene_types.action
- scene_types.suspense
applies_when:
- atmosphere_strategy
- 权力反转
- 悬念揭晓
avoid_when: []
signals:
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- suspense
events:
- collision
- reaction
risks:
- script_invention_risk
- blood_avoidance
dialogue_types:
- long_dialogue_compression
- reaction_beat
applies_to:
- atmosphere_strategy
- 权力反转
- 悬念揭晓
- 误解错位
- 情绪极点
- Cliffhanger
source_files:
- knowledge/09_节奏总控与剧本改写规则.md
- knowledge/24_戏剧微粒识别与节奏触发规则.md
- knowledge/15_故事节奏控制规则.md
conflicts_with: []
supersedes: []
---

# 戏剧微粒驱动的节奏改写

## 规则

`rhythm_rewrite_director` 改写前必须先识别当前段落的主戏剧微粒，再决定 atmosphere_strategy 如何建议下游。  
改写层只允许调整“辅助氛围可视化层”和“逻辑承接层”，不动主线事件层和台词层。

## 执行要求

- `power_reversal`：
  - 优先补“秩序被翻面”的可见证据
  - 写谁停住、谁失控、谁重新掌握场面
  - 不把反转写成纯解释

- `suspense_reveal`：
  - 先写命中前半拍，再写揭示，再写受击
  - 不提前把答案讲穿

- `misunderstanding`：
  - 优先保留听者受击、视线躲闪、关系发冷
  - 不替角色过早澄清

- `emotional_peak`：
  - 优先少说、多留、少动作
  - 把情绪落在呼吸、眼神、手部、姿态或群体静止上

- `cliffhanger`：
  - 只写到阻断点
  - 明确提示下游不要补缓和尾巴

- 所有改写都必须写成可拍、可见、可验证的真实反应：
  - 视线变化、停顿、呼吸、手部动作、姿态变化
  - 当前场景内未命名龙套或群体的简短反应
  - 可见的信息落点、空间关系与动作承接

- 若原剧本存在轻微逻辑断口，允许补写辅助承接：
  - 关键台词前后的短停顿、动作卡顿、视线落点
  - 当前场景内合理存在的未命名旁观者反应
  - 对节奏无帮助的概括性、重复性、不可拍描述可删减

- 单个反应拍只保留 1 个主反应锚点：
  - 优先姿态或站位变化
  - 其次视线变化
  - 再次呼吸或停顿
  - 最后才是手部或道具细节

- 如果姿态、视线或停顿已经能成立当前情绪，不再继续堆叠手指、发梢、衣角、杯沿、工牌等次级细节。
- 除非该细节承担连续性锚点、关键道具因果或当前唯一受击锚点，否则不写成独立强调信息。

## 禁止

- 不得把 atmosphere_strategy 写成命令式镜头清单。
- 不得使用抽象隐喻、文学化心理描写或拟人化气氛句替代真实反应。
- 不得把同一拍拆成“眼神 + 手指 + 道具 + 局部落点”的微动作清单。
- 不得因为命中高权重信号，就臆造新人物、新事件或新道具。
- 不得新增命名角色，不得让未命名龙套承担关键证据、关键判断或剧情转折功能。
- 不得改写、压缩或重排原剧本台词。
- 不得改变主线剧情、关键事件顺序、角色认知状态、关键道具因果或下一段连续性状态。
