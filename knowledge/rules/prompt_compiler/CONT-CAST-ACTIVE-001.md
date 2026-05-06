---
rule_id: CONT-CAST-ACTIVE-001
title: 尾帧可见人物不等于当前戏份人物
doc_type: rule_card
rule_type: cast_continuity
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- cont-cast-active-001
- signals.tailframe_lock
- signals.dialogue_coverage
- signals.action_coverage
- signals.reference_binding
- events.rush_in
- events.door_state
- events.tailframe
- events.reference_binding
- risks.door_state_jump
- risks.reference_misuse
- scene_types.elevator
- scene_types.dialogue
- scene_types.action
applies_when:
- 尾帧人物
- 当前戏份
- offscreen_cast
avoid_when: []
signals:
- tailframe_lock
- dialogue_coverage
- action_coverage
- reference_binding
scene_types:
- elevator
- dialogue
- action
events:
- rush_in
- door_state
- tailframe
- reference_binding
risks:
- door_state_jump
- reference_misuse
applies_to:
- 尾帧人物
- 当前戏份
- offscreen_cast
source_files:
- knowledge/06_连续性与安全规则.md
- knowledge/07_Seedance输出词典与模型适配.md
conflicts_with: []
supersedes: []
---

# 尾帧可见人物不等于当前戏份人物

## 规则

上一段尾帧或视频分析只提供首帧空间事实，不自动把尾帧里所有人物继承为下一段可见人物。

当前片段真正允许出现的人物，以当前 `source_script_events`、`main_shots` 和 `active_cast` 为准。

如果尾帧里可见的人在当前片段没有动作或台词：

- 不调用他的参考图。
- 不写他留在门外、侧后方、前景、背景或画外声。
- 可以在约束中写负绑定：`严飞不再出现，不保留在电梯门外或侧后方。`

## 判例

严飞在上一段大堂中可见，只说明上一段空间关系；若下一段剧本只写商北琛进电梯、乔熙冲入，则严飞必须退出画面，不得保留为电梯门外侧后方人物。

