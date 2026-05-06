---
rule_id: PHYSICAL-DISTANCE-CONTRACT-001
title: 物理距离与亲密接触冲突消解规则
doc_type: rule_card
rule_type: prompt_compilation
agent_scope:
- prompt_compiler
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- physical-distance-contract-001
- signals.continuity_lock
- events.waist_support
- risks.romanticize_collision
- dialogue_types.argument_escalation
- scene_types.intimacy_privacy
applies_when: 处理包含“零亲密接触”或“物理距离”等距离契约的片段
avoid_when: ''
signals:
- continuity_lock
scene_types:
- intimacy_privacy
events:
- waist_support
risks:
- romanticize_collision
dialogue_types:
- argument_escalation
conflicts_with: []
supersedes: []
instruction: 如果约束要求“零亲密接触”或“保持距离”，编译器必须自动过滤或替换时间轴内可能产生歧义的亲密接触词汇。
---

# 物理距离与亲密接触冲突消解规则

## 核心规则
1. **零亲密约束凌驾性**：如果在剧本分析、状态契约或风格定义中出现了“零亲密接触”或“保持物理距离”的要求，该契约具有最高优先级，不得在时间轴内出现违背该契约的动词或状态形容词。
2. **歧义词汇一律替换**：一旦生效距离契约，必须立刻排查并替换以下容易诱发视频模型生成拥抱/亲吻的敏感词汇：
   - 替换 `极近脸距` / `极近的脸距` -> `保留半步距离的压迫感`
   - 替换 `贴着` / `贴身` -> `保持半步距离`
   - 替换 `怀里` / `胸膛` -> `身前` / `两人胸前可见空隙`
   - 替换 `亲密对视` -> `视线对峙`
   - 替换 `扶腰` -> `手停在自己身前` / `手停在半空`
   - 替换 `仍未松开的近身状态` -> `稳定的对峙距离`
3. **消除模糊抓取**：避免“像是刚刚抓住又忘了收回”中带有“抓住”这类模型可能误解的词。直接描述最终物理状态：“乔熙的手悬停在两人之间的半空中”。

## 冲突示例与化解
**冲突原文**：
> 商北琛位于左侧，零亲密接触。他向前迈步逼近，极近的脸距带来压迫感，乔熙退无可退，仍未松开的近身状态让她紧张。

**化解后（状态归一化）**：
> 商北琛位于左侧三分之一。他向前迈步逼近，两人保留半步距离的压迫感，乔熙退无可退，稳定的对峙距离让她紧张，两人胸前可见明显空隙。
