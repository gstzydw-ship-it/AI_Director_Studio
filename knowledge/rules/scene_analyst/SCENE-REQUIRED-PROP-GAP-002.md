---
rule_id: SCENE-REQUIRED-PROP-GAP-002
title: 剧本关键道具缺口必须交接给剧情增强
doc_type: rule_card
rule_type: scene_analysis
owner_agent: scene_analyst
agent_scope:
- scene_analyst
- director_showrunner
- story_planner
- shot_director_layout
- quality_inspector
priority: P0
status: active
pipeline_stage: scene_analysis
runtime_retrieval: true
retrieval_key:
- scene-required-prop-gap-002
- signals.reference_binding
- signals.continuity_lock
- events.object_handoff
- events.action_peak
- risks.missing_required_prop
- risks.spatial_jump
applies_when:
- 剧本出现关键道具
- 参考图缺少关键道具
- 首帧空间锚定
avoid_when:
- "关键道具已在参考图或场景卡中清楚可见。"
- "该物件不是剧本动作、台词、因果或尾帧继承所需。"
failure_mode:
- "参考图缺失闹钟、书包、照片等剧本关键道具时，下游自由脑补位置，导致首帧站位和动作跳变。"
output_contract: "scene_analyst 必须输出关键道具缺口和可补道具约束，交给 director_showrunner、story_planner 与 shot_director_layout。"
example_good: "关键道具缺口: 闹钟来自原剧本，参考图不可见；可补在沙发旁台面或茶几边缘，首帧需可见。"
example_bad: "参考图没有闹钟，下游仍直接写乔熙拍停闹钟但不交代闹钟在哪里。"
signals:
- reference_binding
- continuity_lock
scene_types:
- interior
- constrained_space
- domestic_scene
events:
- object_handoff
- action_peak
risks:
- missing_required_prop
- spatial_jump
applies_to:
- 关键道具缺口
- 场景参考图
- 首帧锁定
source_files:
- knowledge/11_场景分析输入卡与导演意图提取.md
- knowledge/06_连续性与安全规则.md
- knowledge/rules/director_showrunner/SHOWRUNNER-STORY-ENHANCE-001.md
conflicts_with: []
supersedes: []
---

# 剧本关键道具缺口必须交接给剧情增强

## 规则

`scene_analyst` 必须对照原剧本和参考图，识别“剧本需要但参考图里缺失或不可确认”的关键道具。这里的关键道具包括：

- 触发动作的道具：闹钟、门把、钥匙、手机、按钮、杯子。
- 改变剧情理解的道具：照片、文件、合同、书包、信封。
- 影响尾帧继承的道具：被拿起、放下、滑落、交接或露出的物件。

如果参考图缺少这些道具，不能让后续 agent 直接在动作里使用而不说明位置。必须输出：

```yaml
关键道具缺口:
  - 道具: 闹钟
    剧本锚点: 乔熙拍停闹钟
    参考图状态: 缺失或不可确认
    可补位置: 沙发旁台面、茶几边缘、床头柜等当前场景合理可见空间
    交接要求: 剧情增强可把它作为剧本已有道具补入动作前置状态；镜头摆位首帧需让它可见
可补道具约束:
  - 只能补原剧本已出现或台词明确暗示的道具
  - 补入位置必须依附当前场景内已有家具或可见台面
  - 不得补成新的剧情证据或新增反转
```

## 禁止

- 禁止把参考图缺少的剧本关键道具当成“剧本外新增道具”直接阻断。
- 禁止完全不交接缺口，让 `director_showrunner`、`story_planner` 或 `shot_director_layout` 自己猜位置。
- 禁止把缺口补到不可见、不可触达或跨空间的位置。

## Agent 执行

- `scene_analyst`：负责发现缺口并输出可补空间，不做剧情增强。
- `director_showrunner`：可把该道具作为剧本已有道具写入动作前置状态和因果链。
- `story_planner`：拆片时保留该道具的出现、使用和去向。
- `shot_director_layout`：首帧或首次动作前必须让人物、道具和空间关系可读。
