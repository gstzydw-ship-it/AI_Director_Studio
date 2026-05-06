---
rule_id: SHOT-DIRECTOR-STEPWISE-PIPELINE-001
title: Shot Director stepwise pipeline contract
doc_type: rule_card
rule_type: shot_calling
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
- shot_director_guard
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- shot-director-stepwise-pipeline-001
- signals.vertical_framing
- signals.dialogue_coverage
- signals.action_coverage
- signals.continuity_lock
- events.reaction
- events.cut
- risks.axis_confusion
- risks.vertical_closeup_overuse
- risks.script_invention_risk
- dialogue_types.argument_escalation
- dialogue_types.reaction_beat
- scene_types.dialogue
- scene_types.action
- scene_types.suspense
applies_when: []
avoid_when: []
signals:
- vertical_framing
- dialogue_coverage
- action_coverage
- continuity_lock
scene_types:
- dialogue
- action
- suspense
events:
- reaction
- cut
risks:
- axis_confusion
- vertical_closeup_overuse
- script_invention_risk
dialogue_types:
- argument_escalation
- reaction_beat
aspect_ratios:
- '9:16'
conflicts_with: []
supersedes: []
id: SHOT-DIRECTOR-STEPWISE-PIPELINE-001
---

# SHOT-DIRECTOR-STEPWISE-PIPELINE-001

## 规则目标

Shot Director 不得一次性读完规则后直接生成最终镜头表。必须先内部完成分阶段导演流水线，再输出当前调用方要求的最终格式。

## 执行顺序

1. 剧本事实提取
   - 只提取当前片段的人物、地点、动作、道具及状态、对白、情绪/冲突的可见事实、禁止新增内容。
   - 禁止设计镜头、景别、机位、运镜、光影、声音桥或补戏。

2. 戏剧任务判断
   - 判断片段任务：建立关系 / 承载对白 / 冲突升级 / 权力反转 / 悬念揭示 / 情绪极点 / 动作推进。
   - 判断节奏类型：平稳 / 紧张 / 压迫 / 爆发 / 留白。
   - 给出建议镜头数与重点落点：台词 / 动作 / 道具 / 反应。
   - 禁止直接生成完整镜头、复杂光影或蒙太奇炫技。

3. 主镜头骨架设计
   - 先决定镜头数量、每个镜头拍谁、承担什么作用、必须承载哪些信息。
   - 只处理主体、作用、必须承载，不写过细动作、复杂构图、光影、声音桥。

4. 填写镜头字段
   - 为每个镜头补齐景别、机位/视角、运镜。
   - 同一组对话镜头必须保持人物左右关系一致。
   - 正反打不能让人物视线方向突然反过来。
   - 禁止无过渡越轴。
   - 9:16 竖屏优先半身、中近景、双人中景；避免整段特写过密。

5. 填写画面动作与对白
   - 动作必须可见。
   - 反应必须落到具体人物。
   - 道具状态必须连续。
   - 台词只能来自原剧本。
   - 长台词要拆给说话者和听者反应。
   - 高冲击台词可以压到听者反应上。
   - 禁止用抽象情绪词代替画面，例如：破防、震惊、气氛凝固、关系崩塌、众人哗然。

6. 填写切点与节奏
   - 优先切在台词意群结束后、情绪变化出现时、动作即将完成前、反应出现后、关键道具看清后。
   - 每次切镜必须有信息变化。
   - 禁止为了快而碎切。

7. 可选增强层
   - 光影色彩、声音桥、J-cut、L-cut、匹配剪辑、蒙太奇、呼吸节奏只在片段确实需要时使用。
   - 不要每个镜头都加增强字段。

8. 最终校验与修复
   - 最后单独检查并最小修复：剧本外人物/台词/动作/道具、主体抽象、镜头字段缺失、场景名+景别、特写过密、越轴、视线混乱、长台词无听者反应、反应未落到具体人物、动作/道具跳变、切点无信息变化、抽象情绪词。
   - 发现问题时必须修复后再输出最终镜头方案。
   - 不要只说“已检查无误”。

## 规则复杂度分层

硬规则：

- 不得新增剧本外内容。
- 台词必须来自原剧本。
- 主体不能是抽象空间。
- 镜头字段必须能拆为景别、机位/视角、运镜。
- 不能越轴。
- 反应必须落到具体人物。
- 道具状态不能跳变。
- 动作状态不能跳变。

强建议：

- 9:16 竖屏优先半身、中近景、双人中景。
- 长台词要有听者反应。
- 高冲击台词压到反应上。
- 特写不能过密。
- 切点要落在动作、台词、情绪变化处。
- 镜头数量按时长控制。

增强规则：

- 光影色彩。
- 声音桥。
- J-cut / L-cut。
- 匹配剪辑。
- 蒙太奇。
- 呼吸节奏。
- 构图意图。

