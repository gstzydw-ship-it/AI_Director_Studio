---
rule_id: RHYTHM-SAMPLE-TEMPLATE-MINING-004
title: 94集样片节奏档位模板
doc_type: rule_card
rule_type: rhythm
owner_agent: rhythm_rewrite_director
agent_scope:
- rhythm_rewrite_director
- story_planner
- shot_director
- quality_inspector
priority: P0
status: active
pipeline_stage: rhythm_handoff
runtime_retrieval: true
retrieval_key:
- rhythm-sample-template-mining-004
- signals.short_drama_samples
- signals.rhythm_control_contract
- signals.time_budget
- signals.action_density
- scene_types.domestic_scene
- scene_types.elevator
- scene_types.company_arrival
- events.reaction
- events.reveal
- events.prop_reveal
- risks.too_many_cuts
- risks.fake_fast_pacing
applies_when:
- 需要判断短剧片段节奏快慢
- 需要输出片段目标时长
- 需要把样片节奏转成下游可执行边界
- 生活动作压力、身份揭示、封闭空间对峙、道具触发情绪
avoid_when:
- 用户明确要求单镜到底
- 当前任务只做剧本文本润色且不进入镜头生产
failure_mode:
- "把快节奏理解为随机加切镜或连续特写，导致同一观众问题被拆碎。"
output_contract: "节奏导演必须先判节奏档位，再输出目标时长、ASL范围、每5秒镜头密度、可压缩弱拍、不可省略落点和尾帧要求；不得写具体机位。"
example_good: "compact_domestic_pressure: 8-14秒，ASL 1.4-2.6秒，每5秒2-3镜；压缩重复整理，保留催促、抗拒、妥协和尾帧道具状态。"
example_bad: "节奏要快，多切几个特写，动作都拍细一点。"
signals:
- short_drama_samples
- rhythm_control_contract
- time_budget
- action_density
scene_types:
- domestic_scene
- elevator
- company_arrival
- dialogue
events:
- reaction
- reveal
- prop_reveal
risks:
- too_many_cuts
- fake_fast_pacing
source_files:
- knowledge/external_sources/short_drama_samples/README.md
- knowledge/external_sources/short_drama_samples/rhythm_control_template_library_v1.yaml
- knowledge/external_sources/short_drama_samples/shot_coverage_template_library_v1.yaml
conflicts_with: []
supersedes: []
---

# 94集样片节奏档位模板

## 核心结论

94集真人短剧样片全量连续分析显示：检测镜头3410个，平均镜头时长3.21秒，中位镜头时长1.92秒，P25/P75为0.96秒/3.84秒。短切存在，但不是唯一节奏来源。

节奏导演不能把“快”翻译成“乱切特写”。样片中关系景、环境关系景、半身景占主导，特写只在信息爆点、受击反应、情绪顶点使用。

## 必须使用的节奏档位

### compact_domestic_pressure

适用：赶时间、穿衣、收拾、电话催促、孩子抗拒、拿包出门。

施工边界：
- 目标时长：8-14秒。
- 目标ASL：1.4-2.6秒。
- 每5秒：2-3镜。
- 最小反应停留：0.4秒。
- 片段策略：同一生活动作群保持一段，内部写前急后停。

不可省略：催促来源、抗拒动作、妥协或情绪转折、尾帧道具/人物状态。

### high_pressure_reveal

适用：新老板到场、旧人重逢、身份揭示、人群等待或压迫。

施工边界：
- 目标时长：10-16秒。
- 目标ASL：1.6-3.0秒。
- 每5秒：2-3镜。
- 最小反应停留：0.6秒。
- 片段策略：到场动作、揭示主体、主角受击反应应在同一爆点段内完成。

不可省略：压力源出现、关键人物露面、主角识别反应、尾帧身份冲击状态。

### closed_space_dialogue_pressure

适用：电梯、车内、走廊角落、办公室近距离对峙；双人调侃、逼问、沉默、尴尬。

施工边界：
- 目标时长：10-16秒。
- 目标ASL：2.0-3.5秒。
- 每5秒：1.5-2.5镜。
- 最小反应停留：0.7秒。
- 片段策略：问句、受击抬头、二次逼问、尴尬收束按关系-反应-关系-动作-关系闭环。

不可省略：说话者关系位置、被击中反应、身体状态单向变化、结束时距离关系。

### prop_reveal_emotional_stop

适用：照片、戒指、文件、手机内容、亲子物件触发回忆。

施工边界：
- 目标时长：8-13秒。
- 目标ASL：2.0-4.0秒。
- 每5秒：1-2镜。
- 最小反应停留：0.8秒。
- 片段策略：道具出现和人物识别反应不能拆太远，反应后允许停半拍。

不可省略：道具来源、道具落点、人物识别动作、情绪停住。

### low_cut_emotional_hold

适用：等待、隐忍、压抑、长台词解释、慢性对峙。

施工边界：
- 目标时长：10-20秒。
- 目标ASL：4.0-8.0秒。
- 每5秒：0.5-1.2镜。
- 最小反应停留：1.0秒。
- 片段策略：不为制造节奏硬切；用表情、视线、身体停顿和空间压迫撑住。

## 交接格式

节奏导演交给下游时必须写：

```yaml
rhythm_band: compact_domestic_pressure
target_duration_s: 8-14
target_asl_s: 1.4-2.6
shots_per_5s: 2-3
compressible_events:
  - 重复整理动作
non_omittable_events:
  - 催促来源
  - 抗拒动作
  - 妥协落点
tailframe_requirement: 保留下一段必须继承的人物姿态和道具状态
forbidden:
  - 具体机位
  - 具体镜头编号
  - 新剧情动作
  - 新台词
```
