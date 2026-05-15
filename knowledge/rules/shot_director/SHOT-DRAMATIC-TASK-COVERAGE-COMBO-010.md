---
rule_id: SHOT-DRAMATIC-TASK-COVERAGE-COMBO-010
title: 按戏剧任务选择镜头组合与下一镜
doc_type: rule_card
rule_type: shot_sequence_grammar
owner_agent: shot_director
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
pipeline_stage: shot_sequence
runtime_retrieval: true
retrieval_key:
- shot-dramatic-task-coverage-combo-010
- signals.viewer_attention
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.reveal
- events.reaction
- events.cut
- risks.random_shot_choice
- risks.axis_confusion
- risks.action_discontinuity
applies_when:
- 镜头组合
- 下一镜选择
- 单片段镜头规划
avoid_when:
- metadata_only_task
failure_mode:
- "镜头像随机景别拼接，没有按戏剧任务形成建立、动作、信息、反应、复位的覆盖链。"
output_contract: "每个 fragment 先选择戏剧任务镜头组合，再决定每镜主体、景别和切点；下一镜必须由注意力问题或状态变化触发。"
example_good: "生活压力=双人关系建立→连续动作阻力→孩子拒绝落点/母亲安抚→书包尾帧。"
example_bad: "特写闹钟→特写手机→脚部特写→衣服特写→脸部特写。"
signals:
- viewer_attention
- dialogue_coverage
- action_coverage
- continuity_lock
events:
- reveal
- reaction
- cut
risks:
- random_shot_choice
- axis_confusion
- action_discontinuity
---

# 按戏剧任务选择镜头组合与下一镜

## 核心规则

镜头导演不能先随机挑景别。必须先判断当前片段的戏剧任务，再选择对应的覆盖链。
“下一镜接什么”由观众注意力问题决定：观众需要看清空间、动作阶段、信息载体、受击反应，还是尾帧复位。

## 常用镜头组合

### 生活压力/赶时间

关系建立 → 连续动作阻力 → 台词或情绪转折 → 尾帧复位。

- 用人物动作紧张、动作叠压、台词压力表现快节奏。
- 手、手机、衣服、鞋子默认并入关系镜，不连续开局部碎镜。
- 下一镜只有在动作阶段变化、孩子拒绝命中、母亲安抚开始或需要尾帧交接时才切。

### 信息揭示/关键道具

发现前停顿或视线 → 关键物可读 → 发现者反应 → 关系/尾帧复位。

- 关键物镜头必须短而清楚。
- 关键物之后不能随机接另一个道具，必须接人物反应或让信息带入下一段。

### 对白攻防/长对白

关系建立 → 说话者起句 → 听者受击或过肩反应 → 关系复位/回应前切。

- 不按每句台词机械切。
- 高冲击句可以让后半句以画外音落在听者反应上。
- 正反切必须保持视线和轴线一致。

### 权力压迫/反转

空间权力关系 → 压迫者推进或占位 → 受压者反应 → 关系冻结或尾帧复位。

- 不只拍赢方说话。
- 近景和特写只给受击、反转命中或情绪极点。

### 动作位移/接触

起点关系 → 动作中段或顶点前切 → 接触/结果 → 终点复位。

- 切在动作 50%-70% 比动作完成后更顺。
- 人物从坐到站、从沙发到茶几、从门内到门外，必须看见路径或写清承接。

## 下一镜合法触发

- 注意力主体变化。
- 信息已经看清。
- 台词压力落到听者。
- 动作阶段从起点到中段/结果。
- 空间关系需要复位。
- 尾帧需要交接给下一个片段。

## 禁止

- 为了“更快”连续切手、脚、手机、衣服、脸。
- 建立镜后随机接一个无信息局部特写。
- 反应镜后停在不可继承的脸部/手部局部。
- 不写承接，直接让人物凭空换位置。
