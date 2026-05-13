---
rule_id: SCREEN-POSITION-NAMED-SUBJECT-001
title: 站位关系具名化与简洁表达规则
doc_type: rule_card
rule_type: prompt_compilation
owner_agent: prompt_compiler
agent_scope:
- prompt_compiler
- shot_director
- quality_inspector
priority: P0
status: active
pipeline_stage: shot_relation_translation
runtime_retrieval: true
retrieval_key:
- screen-position-named-subject-001
- signals.action_coverage
- risks.privacy_body
- scene_types.elevator
- scene_types.action
- scene_types.intimacy_privacy
applies_when: 描述人物关系、朝向和距离
avoid_when:
- "不描述人物关系、朝向或距离。"
failure_mode:
- "使用无主体方位词，模型无法判断谁面对谁、谁在压迫谁、两人距离如何。"
output_contract: "站位必须写成角色名 + 关系动作 + 朝向对象 + 可见距离。"
example_good: "商北琛在桌后看着乔熙，乔熙站在桌前正面承接压力，两人隔着办公桌保持对峙距离。"
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
instruction: 站位关系必须用“角色名 + 关系动作 + 朝向对象 + 距离”结构，禁止使用无主语的抽象方位。
---

# 站位关系具名化与简洁表达规则

## 核心规则
1. **禁止抽象无主体方位**：绝对禁止写“左侧朝右，右侧朝左”或“左侧朝右，右侧朝前”这种缺乏执行主体的抽象描述，视频模型无法正确分配目标。
2. **具名化三要素**：任何站位描述必须同时包含：
   - **具体角色名**（如“商北琛”、“乔熙”）
   - **关系位置**（如“桌后”、“桌前”、“门口内外”、“同侧过肩”）
   - **相对朝向或动作对象**（如“看着乔熙”、“正面承接商北琛的压力”）
3. **距离可见性**：在双人构图时，必须明确两人之间的空间关系（如“隔着办公桌对峙”、“保留半步距离”、“没有肢体接触”）。
4. **禁用坐标模板**：不要把镜头句写成坐标说明。站位关系优先用剧情对象和阻隔物表达。

## 反例（禁止）
```
左侧朝右，右侧朝左，保持距离。
左侧朝右，右侧朝前。
只用坐标和方位描述两人关系，缺少剧情阻隔物和明确对峙动作。
```

## 正例（推荐）
```
商北琛在桌后看着乔熙，乔熙站在桌前正面承接压力，两人隔着办公桌保持对峙距离。
```
