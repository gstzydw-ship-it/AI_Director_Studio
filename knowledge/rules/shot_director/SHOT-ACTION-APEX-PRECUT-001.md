---
rule_id: SHOT-ACTION-APEX-PRECUT-001
title: 动作顶点前切入
doc_type: rule_card
rule_type: shot_timing
agent_scope:
- story_planner
- shot_director
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- shot-action-apex-precut-001
- signals.action_coverage
- signals.continuity_lock
- events.cut
- scene_types.action
applies_when:
- 动作顶点
- 切镜时机
- 主分镜
avoid_when: []
signals:
- action_coverage
- continuity_lock
scene_types:
- action
events:
- cut
applies_to:
- 动作顶点
- 切镜时机
- 主分镜
- 子分镜
- 机位变化
- 动作省略
source_files:
- knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes: []
---

# 动作顶点前切入

## 规则

需要切换主分镜/子分镜时，优先在动作正在进行、尚未完成的时刻切入，而不是等动作完成后再切。

动作顶点是动作最明确的完成瞬间，例如：

- 穿衣：衣服完全套好。
- 伸脚：脚完全伸到鞋前。
- 拿书包：书包完全提起。
- 照片滑落：照片完全落地。
- 捡照片：照片完全翻正。
- 回头：脸完全转向目标。

更好的切点通常在顶点前半拍：

- 小豆丁开始伸脚，但脚还没完全停稳时，切到低机位脚步景。
- 乔熙手刚拎起书包、照片边角刚被带出来时，切到书包侧面或地面关系景。
- 照片正在滑落、还未完全落地时，切到地面低机位。
- 乔熙手指刚碰到照片边缘、照片还没完全翻正时，切到手与照片景。

## 目的

动作顶点前切可以让观众自动补完动作过程，省略无意义位移，同时让两个镜头之间更有节奏。

## 禁止

- 动作完成后才切，导致新镜头只是在补拍结果。
- 每个动作都等到完全做完再进入子分镜。
- 用特写替代切点设计。

## Agent执行

- story_planner：识别每个动作单元的动作顶点。
- shot_director：把子分镜切点放在顶点前半拍，优先用机位、景别或主体关系变化承接动作。
- prompt_compiler：在时间轴中写清“正在”“刚要”“即将”“还未完全”等顶点前状态。
- quality_inspector：如果所有切镜都发生在动作完成后，判为节奏迟钝。

