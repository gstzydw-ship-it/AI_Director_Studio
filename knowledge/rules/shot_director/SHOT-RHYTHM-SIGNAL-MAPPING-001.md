---
rule_id: SHOT-RHYTHM-SIGNAL-MAPPING-001
title: 戏剧微粒到镜头语言映射
doc_type: rule_card
rule_type: shot_calling
agent_scope:
  - shot_director
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - D:/AI 导演系统工程文档规范.md
  - knowledge/24_戏剧微粒识别与节奏触发规则.md
  - knowledge/15_故事节奏控制规则.md
  - knowledge/21_镜头调用规则与多机位模板.md
  - knowledge/17_结果质检与回溯修正规则.md
conflicts_with: []
supersedes: []
applies_to:
  - rhythm_function
  - shot_language_reason
  - reaction_plan
  - pause_plan
---

# 戏剧微粒到镜头语言映射

## 规则

`shot_director` 必须先读取上游 `rhythm_function / hook_weight / reaction_need / script_basis`，再决定镜头语言。参考《AI 导演系统工程文档规范》的识别表、决策表与决策树：先判断当前片段属于哪一种戏剧微粒，再决定镜头数量、镜头类型和切镜位置。  
输出中至少要能解释：
- `shot_language_reason`
- `rhythm_basis`
- `script_basis`
- `why_not_template`

## 映射要求

- `power_reversal`：
  - 用不对称构图、画面占比、站位高低、轻微高度差或稳定推进表达权力转移
  - 反转命中后必须给失势方可见受击
  - 不得只拍赢方说完话

- `conflict_escalation`：
  - 以 2-3 秒短镜为主
  - 切掉无意义走路和解释
  - 必须覆盖施压、受击和短暂停顿

- `suspense_reveal`：
  - 优先“停顿 / 发现前逼近 -> 线索或目标物 -> 角色反应”
  - 文字、文件、门后信息必须稳，不用花哨快动
  - 省略走近、弯腰、拿起等无信息增量的中间动作

- `misunderstanding`：
  - 提高听者反应镜头频率
  - 用视线、停顿、躲闪和关系冻结表现错位
  - 不要让说话者一直占满画面

- `emotional_peak`：
  - 允许 5-8 秒静态或极轻微推进
  - 但动作、背景和运镜必须简化
  - 反应优先于解释

- `cliffhanger`：
  - 停在动作顶点、威胁尾音、揭示落点或关系悬住处
  - 命中后 0.5-2 秒内阻断
  - 不得补释怀拉远、离场过程或总结性对白

## 节奏执行底线

- 密集对峙、真相揭晓和情绪临界段，必须切出 1.0-2.5 秒 `pause_plan`
- 高潮段 10 秒内最多保留 3 句短台词，剩余压力由反应镜头、关系镜头或道具插入承担
- 首镜若承担 Hook，必须在 3 秒内交代高价值信息、压力或动作启动
- 能用 1 个主镜头讲清的动作，不要硬拆成 3 个细碎镜头；镜头数由节奏任务决定，不由模板决定
- 9:16 竖屏下优先半身、中景和双人关系镜头承载叙事，特写只在炸点、受击、情绪峰值或关键信息出现时启用
- 不要把手指、掌心、袖口、鞋尖、嘴唇、眼角等微细节默认拆成独立镜头；只有它们承载线索、动作前摇或受击结果时才允许插入

## 禁止

- 不得把所有高能段都拍成机械正反打。
- 不得没有 `rhythm_function` 就套用爆点模板。
- 不得在 `cliffhanger` 后追加缓和、解释、离场或情绪释放。
- 不得把黄金停顿写成无动机的空镜拖时长。
- 不得为了显得“电影化”而把每个细节动作都拆成镜头。
