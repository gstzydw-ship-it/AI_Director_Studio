---
rule_id: SHOT-SUBJECT-OWNERSHIP-009
title: 拍摄主体必须归属于观众注意力焦点
doc_type: rule_card
rule_type: subject_ownership
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
pipeline_stage: shot_selection
runtime_retrieval: true
retrieval_key:
- shot-subject-ownership-009
- signals.viewer_attention
- signals.continuity_lock
- signals.action_coverage
- events.reaction
- events.reveal
- events.cut
- risks.random_shot_choice
- risks.subject_overload
- risks.action_discontinuity
applies_when:
- 每镜拍摄主体
- 主镜头列表
- 镜头逻辑审查
avoid_when:
- metadata_only_task
failure_mode:
- "拍摄主体写成人物、道具和环境的清单，导致视频模型不知道本镜该拍谁。"
output_contract: "每个 shot 的拍摄主体只能是本镜观众注意力主焦点；其他可见人物、道具和空间状态写进必须承载或连续性。"
example_good: "拍摄主体: 乔熙和小豆丁；必须承载: 手机仍在乔熙耳边，书包在沙发边。"
example_bad: "拍摄主体: 乔熙、小豆丁、闹钟、手机、外套、草莓蛋糕、书包。"
signals:
- viewer_attention
- continuity_lock
- action_coverage
events:
- reaction
- reveal
- cut
risks:
- random_shot_choice
- subject_overload
- action_discontinuity
---

# 拍摄主体必须归属于观众注意力焦点

## 核心规则

拍摄主体不是“这一镜里可能出现的所有东西”，而是观众此刻最需要看的主焦点。

每个主镜头只能选择以下之一：

- 单人主体：当前行动者、受击者、发现者或被压迫者。
- 双人/多人关系主体：当前戏剧任务依赖站位、距离、接触或攻防关系。
- 唯一关键物主体：照片、文件、屏幕、项链等本镜必须看清的信息载体。

其他人物、道具、家具和空间锚点必须写进 `必须承载`、`同场人物位置`、`状态变化` 或 `连续性`，不能堆进 `拍摄主体`。

## 按任务选择主体

- 建立关系：拍双人关系或多人关系，不拍单个道具。
- 动作阻力：拍行动者 + 受阻者；手、衣服、鞋子默认并入关系镜。
- 信息揭示：先拍发现者或视线，再拍关键物，随后拍人物反应。
- 情绪受击：拍受击者；说话者可作为画外音、过肩前景或边缘存在。
- 尾帧复位：拍可继承的关系主体，保留人物位置和道具状态。

## 禁止

- 把“乔熙、小豆丁、闹钟、手机、外套、草莓蛋糕、书包”写成同一个拍摄主体。
- 因为某个道具出现在剧本里，就让它成为主镜头主体。
- 单人镜不说明另一位同场人物仍在何处。
- 局部手部、脚、衣角、手机默认升级成主镜头。

## 自检

删掉这个主体后，观众是否还知道此刻该看谁？
如果答案是“主体太多无法判断”，必须重选主体。
