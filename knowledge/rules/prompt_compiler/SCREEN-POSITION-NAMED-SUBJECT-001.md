---
rule_id: SCREEN-POSITION-NAMED-SUBJECT-001
title: 屏幕位置具名化与方位规则
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- shot_director
- quality_inspector
priority: P0
status: active
pipeline_stage: screen_position_translation
runtime_retrieval: true
retrieval_key:
- screen-position-named-subject-001
- signals.action_coverage
- risks.privacy_body
- scene_types.elevator
- scene_types.action
- scene_types.intimacy_privacy
applies_when: 描述人物在画面中的相对位置和朝向
avoid_when:
- "不描述人物在画面中的相对位置、朝向或距离。"
failure_mode:
- "使用无主体方位词，模型无法判断谁在左、谁朝向谁、两人距离如何。"
output_contract: "站位必须写成角色名 + 画面位置 + 朝向对象 + 可见距离。"
example_good: "商北琛位于画面左侧三分之一，身体和视线朝向右侧乔熙。"
example_bad: "左侧朝右，右侧朝左，保持距离。"
signals:
- action_coverage
scene_types:
- elevator
- action
- intimacy_privacy
risks:
- privacy_body
conflicts_with: []
supersedes: []
instruction: 屏幕位置必须用“角色名 + 画面位置 + 朝向对象 + 距离”结构，禁止使用无主语的抽象描述。
---

# 屏幕位置具名化与方位规则

## 核心规则
1. **禁止抽象无主体方位**：绝对禁止写“左侧朝右，右侧朝左”或“左侧朝右，右侧朝前”这种缺乏执行主体的抽象描述，视频模型无法正确分配目标。
2. **具名化三要素**：任何站位描述必须同时包含：
   - **具体角色名**（如“商北琛”、“乔熙”）
   - **绝对屏幕坐标**（如“画面左侧三分之一”、“画面右边缘”）
   - **相对朝向或动作对象**（如“身体和视线朝向画面右侧的乔熙”）
3. **距离可见性**：在双人构图时，必须明确两人之间的空间关系（如“保留清晰可见的半步距离”、“中间可见电梯轿厢背景”）。

## 反例（禁止）
```
左侧朝右，右侧朝左，保持距离。
左侧朝右，右侧朝前。
```

## 正例（推荐）
```
商北琛位于画面左侧三分之一，身体和视线朝向画面右侧的乔熙；乔熙位于画面右侧三分之一，身体和视线朝向画面左侧的商北琛。两人之间保留清晰可见的半步距离，中间可见电梯轿厢背景。
```
