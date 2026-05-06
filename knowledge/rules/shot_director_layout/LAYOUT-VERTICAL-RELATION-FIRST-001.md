---
rule_id: LAYOUT-VERTICAL-RELATION-FIRST-001
title: 竖屏摆位优先关系镜头而不是特写堆叠
doc_type: rule_card
rule_type: vertical_layout
agent_scope:
- shot_director_layout
- quality_inspector
priority: P0
status: active
runtime_retrieval: true
retrieval_key:
- layout-vertical-relation-first-001
- signals.vertical_framing
- risks.vertical_closeup_overuse
applies_when:
- 9:16竖屏
- 主镜头摆位
- 景别主力
avoid_when: []
signals:
- vertical_framing
risks:
- vertical_closeup_overuse
aspect_ratios:
- '9:16'
applies_to:
- 9:16竖屏
- 主镜头摆位
- 景别主力
source_files:
- knowledge/25_镜头摆位主分镜骨架规则.md
- knowledge/02_焦段景深与景别画幅策略.md
- knowledge/22_多机位分镜与镜头多样性规则.md
conflicts_with: []
supersedes: []
---

# 竖屏摆位优先关系镜头而不是特写堆叠

## 规则

在 9:16 竖屏里，镜头摆位阶段优先用：

- 半身镜头
- 中景镜头
- 双人关系镜头

只有当剧情真的需要逼近信息或情绪顶点时，才允许把其中一个主镜头压成特写。

如果主镜头骨架已经能交代人物关系和空间位置，就不要再把多个主镜头都做成脸部特写。

## 禁止

- 一个片段从头到尾用特写类主镜头堆满
- 默认把面部特写当成最安全答案
- 为了“精致”把掌心、鞋尖、嘴唇、眼角等微细节升成主镜头
