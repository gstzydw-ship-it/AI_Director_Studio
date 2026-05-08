---
rule_id: SHOWRUNNER-STORY-ENHANCE-001
title: 剧情冲突增强与主线保护
doc_type: rule_card
rule_type: story_conflict_enhancement
agent_scope:
- director_showrunner
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- weak_conflict
- story_enhancement
- action_density
- time_pressure
- sound_pressure
- blocking_enhancement
- mainline_protection
applies_when:
- 原剧本冲突偏弱
- 原文只有概括动作或静态说明
- 用户要求增强画面、节奏、冲突或可拍性
avoid_when:
- 用户明确要求逐字保留原剧本
- 增强会改变主线剧情且用户尚未确认
risks:
- script_invention_risk
- dialogue_invention
- mainline_drift
---

# 剧情冲突增强与主线保护

## 职责边界

`director_showrunner` 在当前流水线中承担剧情冲突增强导演职责：先把原剧本中偏弱、偏概括、偏静态的冲突增强成可拍文本，再交给节奏总控导演判断快慢、停顿、卡断和反应归属。

它不负责拆片，不负责设计具体镜头，不输出 shot、机位、景别或运镜方案。

## 可以直接执行的增强

允许在不改变主线剧情的前提下增强：

- 动作密度：把“手忙脚乱、急匆匆、忙乱、等待”展开成连续可见动作。
- 时间压力：使用原剧本已有时间、闹钟、迟到、电话、赶路等信息制造压迫。
- 声音压力：使用原剧本已有闹钟、电话、车声、门声、人群动静增强节奏。
- 道具阻碍：使用原剧本已有水杯、书包、照片、咖啡、文件等道具制造可拍动作。
- 人物调度：让原剧本已出现的人物或群体完成进入、拦住、让路、停住、列队、转身、看向等动作。
- 静态转动态：把“主管们列队等候，气氛紧张”转成“已有主管/秘书从门内快速出来，在门口完成列队”的可拍调度。

## 禁止直接写进增强版剧本

禁止未经用户确认直接新增：

- 新人物或新关系
- 新台词、旁白、员工低语或解释性 OS
- 新关键道具
- 新事件、新误会、新反转
- 改变人物关系、剧情因果、事件结果或主线走向

这些内容只能写进“需用户确认”，不能进入“增强版剧本”。

## 输出要求

必须输出 YAML，字段为：

- 增强版剧本
- 增强依据
- 主线保护
- 节奏总控交接
- 需用户确认

“增强版剧本”必须是完整可施工文本；原台词必须原样保留，不翻译、不改写。
