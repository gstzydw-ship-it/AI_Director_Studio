---
rule_id: SHOWRUNNER-SCENE-TASK-ENHANCEMENT-003
title: 剧情增强必须先判断戏剧任务而不是堆动作
doc_type: rule_card
rule_type: story_conflict_enhancement
owner_agent: director_showrunner
agent_scope:
- director_showrunner
- rhythm_rewrite_director
- story_planner
- quality_inspector
priority: P0
status: active
pipeline_stage: story_conflict_enhancement
runtime_retrieval: true
retrieval_key:
- showrunner-scene-task-enhancement-003
- signals.story_enhancement
- signals.action_density
- events.escalation
- events.reaction
- risks.overwritten_micro_actions
- risks.flat_emotion
applies_when:
- 剧情增强
- 弱冲突
- 动作过碎
- 情绪表达
avoid_when:
- "用户明确要求逐字保留，且不允许任何动作增强。"
failure_mode:
- "剧情增强把简单任务写成一串微动作，动作很多但戏剧任务、人物目标、阻碍和转折不清。"
output_contract: "增强前先写清场景任务、人物目标、阻碍、转折、节奏类型和粗颗粒原则；增强事件只服务这些任务。"
example_good: "赶时间戏的任务是时间压力下完成照顾孩子；穿衣保持一句话，用书本掉地顾不上捡来体现慌乱。"
example_bad: "把穿衣写成套袖、拉裤腿、抓脚踝、整理下摆等微动作，但没有新的节奏压力。"
signals:
- story_enhancement
- action_density
scene_types:
- action_scene
- dialogue_scene
- emotional_turning_point
- domestic_scene
events:
- escalation
- reaction
- decision
risks:
- overwritten_micro_actions
- flat_emotion
applies_to:
- 剧情增强
- 戏剧任务
- 动作密度
- 情绪表达
source_files:
- knowledge/rules/director_showrunner/SHOWRUNNER-STORY-ENHANCE-001.md
- knowledge/15_故事节奏控制规则.md
external_sources:
- https://hollywoodwritersgroup.com/quicksheets-scene-building-screenwriting/
- https://screencraft.org/blog/anatomy-of-a-scene-how-to-make-action-sequences-matter/
- https://www.backstage.com/magazine/article/what-are-beats-in-acting-76101/
conflicts_with: []
supersedes: []
---

# 剧情增强必须先判断戏剧任务而不是堆动作

## 判断顺序

`director_showrunner` 不能先想“能补哪些动作”，必须先判断当前片段的戏剧任务：

1. `场景任务`：这段存在的叙事原因是什么，是推进事件、揭示信息、建立关系、升级冲突，还是给反应和情绪落点。
2. `人物目标`：主角此刻想立刻完成什么。
3. `阻碍`：谁或什么让目标变难，可以是人物、时间、环境、道具、信息差或心理抗拒。
4. `转折`：片尾和片头相比，人物关系、情绪、信息或物理状态必须发生什么变化。
5. `可见动作`：只选择能服务上述四项的动作，不为“丰富画面”堆微动作。
6. `粗颗粒原则`：判断哪些主动作必须保持一句话级别，哪些地方可以加轻量节奏阻碍。

## 增强类型

按戏剧任务选择增强方式：

- `赶时间/任务压力`：用时间源、电话、闹钟、门口、书包、文件、场景自然存在的轻阻碍制造压力；主动作保持粗颗粒，阻碍只负责表现“顾不上”。
- `照顾/安抚/关系修复`：用动作力度变化、停顿、眼神回到对方、语速放缓、触碰减轻表现情绪，不要只写口头解释。
- `冲突/对抗`：用目标相反、阻挡、退让、打断、沉默和策略变化增强，不要新增剧本外台词。
- `揭示/发现`：用视线命中、道具露出、反应停顿、随后选择体现信息变化。
- `情绪反应`：保留短暂停顿、呼吸、视线、手部控制等可拍行为；不要把所有反应拆成多个动作。
- `慢节奏/压抑/余韵`：用动作中断、无人说话、没有立刻回应、物件停在手里、关系距离不变来增强；不要加忙乱阻碍。

## 轻新增边界

允许少量原剧本未写的轻新增，但它必须同时满足：

- 场景中自然会有，例如书、本子、门口人流、提示声、散开的文件、桌边杯子。
- 没有信息功能，不传递身份、秘密、证据、误会、反转。
- 可删掉也不改变主线剧情、人物关系、台词信息和关键因果。
- 只用于体现节奏，例如赶时间、顾不上、被打断、人物停了一秒、没人接话。
- 必须写成日常可见动作或可听声音，例如“手机又响了一声”“门外有人经过”“书掉到地上没人捡”“她蹲下来哄孩子”。禁止写“催促感”“压迫感”“紧张感”“空气变静”“压住急躁”“把衣服放低”。
- 必须在角色当前注意力和任务链内。角色正在处理什么，就只能加会自然影响这件事的压力源；不要加角色不会注意、不会处理的背景声音。例如屋里给孩子穿衣时，不要写走廊脚步声让她看门口；应使用闹钟、手机、时间、孩子、书包等强相关元素。

禁止把轻新增写成新关键道具、新证据、新人物反应、新台词或下一段必须继承的因果。

## 动作密度上限

每 5 秒最多给 2-3 个核心节拍。核心节拍指会改变状态、目标、关系、节奏压力或信息的事件。

低价值微动作不得连续堆叠：

- 摸头发、整理衣角、看窗、低头、抿嘴、转身、停顿，如果不改变目标或关系，只能作为一个核心动作的附属表演。
- 同一情绪不要连写三种身体反应；选最能拍出来的一种。
- 简单主动作不要拆成身体部位级操作。穿衣、拿包、开门、坐下、递文件、看照片、端咖啡通常只保留结果动作。
- 不写为了“表现情绪”而设计的摆拍动作。能写“她蹲下来哄孩子”，就不要写“她把衣服放低后压住急躁”。

## 输出要求

增强输出中必须让下游看出：

- 这段的主任务。
- 这段的节奏类型。
- 哪些动作必须保留。
- 哪些只是可省略的过渡。
- 哪些轻新增只负责节奏、不会变成主线因果。
- 片尾状态相对片头改变了什么。

如果增强后删掉任意一个动作，剧情仍完全不变，说明动作增强过碎，必须合并或删除。
