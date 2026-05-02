---
rule_id: PROMPT-DIRECTOR-JARGON-TRANSLATION-001
title: 导演调度口语必须翻译成可见画面语言
doc_type: rule_card
rule_type: prompt_language
agent_scope:
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/07_Seedance输出词典与模型适配.md
  - knowledge/rules/prompt_compiler/PROMPT-NATURAL-SENTENCE-001.md
  - knowledge/rules/shot_director/MOTION-MODALITY-001.md
conflicts_with: []
supersedes: []
applies_to:
  - 导演调度
  - Seedance Prompt
  - 运镜
  - 受击反应
---

# 导演调度口语必须翻译成可见画面语言

## 规则

`prompt_compiler` 不得把上游导演口语原样输出给 Seedance。最终 prompt 必须把调度意图翻译成模型可见的画面自然句：主体、景别、机位、运镜方向、人物动作、视线和结束状态。

## 禁止

```text
稳定器在同一运动里带到严飞和主管胸部以上受压反应。
顺势带到众员工被权力压住。
空气收紧，沉默就是回应。
```

## 改写方向

```text
稳定缓慢横移镜头，从商北琛冷峻正面开始，带过严飞和几名主管的胸部以上画面；严飞微微低头，主管们肩膀收紧、屏住呼吸、避开商北琛视线。
```

## 翻译表

- `稳定器在同一运动里带到` -> `稳定缓慢横移镜头 / 平稳跟拍 / 镜头切至同侧反应`
- `受压反应` -> `低头 / 屏住呼吸 / 肩膀收紧 / 眼神回避 / 身体僵住`
- `权力压住 / 空气收紧` -> `停顿 0.5-1 秒 / 无人说话 / 人群停步 / 让开通道`

