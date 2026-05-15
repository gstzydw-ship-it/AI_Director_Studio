---
case_title: 视频拆片案例：剪辑转场_动作转场与相似动作匹配
doc_type: case_card
served_agents:
- scene_analyst
- story_planner
- shot_director
- shot_director_blocking
- quality_inspector
scene_types:
- 动作匹配转场
- 动作连续转场
- 因果关联转场
- 连锁效应转场
- action
- intimacy_privacy
events:
- door_state
- cut
- match_action
- scene_change
dialogue_types:
- argument_escalation
visual_constraints:
- wide_shot
- medium_shot
- closeup
- over_shoulder
risks:
- privacy_body
reusable_pattern: CASE_剪辑转场_动作转场与相似动作匹配
aspect_ratio: unspecified
runtime_retrieval: false
source_files: []
rule_id: CASE-剪辑转场_动作转场与相似动作匹配
title: 视频拆片案例：剪辑转场_动作转场与相似动作匹配
rule_type: shot_sequence_case
agent_scope:
- shot_director
- shot_director_layout
- shot_director_blocking
priority: reference
status: active
source_video: 剪辑转场_动作转场与相似动作匹配.mp4
extraction_date: '2026-04-24'
extraction_model: gemini-3.1-pro-preview-thinking-high
signals:
- action_coverage
- continuity_lock
---

# 视频拆片案例：剪辑转场_动作转场与相似动作匹配

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
cases:
  - case_title: "相似动作转场-打鼓到打字"
    scene_type: "动作匹配转场"
    emotional_arc: "动感→平静"
    duration_estimate: "4s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，背对镜头打鼓"
        narrative_function: "展示打鼓的动作和节奏，为转场做铺垫"
        cut_reason: "动作达到高潮，准备匹配下一个场景的相似动作"
      - index: 2
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，侧面面对电脑打字"
        narrative_function: "通过相似的敲击动作，将场景从舞台无缝切换到室内工作环境"
        cut_reason: "转场完成，展示新场景"
    pattern_summary:
      rhythm: "快切"
      director_intent: "利用不同场景中相似的肢体动作，实现视觉上的连贯和顺滑过渡"
      reusable_pattern: "相似动作转场=场景A动作高潮→场景B相似动作继续"

  - case_title: "相似动作转场-跳舞到伸懒腰"
    scene_type: "动作匹配转场"
    emotional_arc: "浪漫→轻松"
    duration_estimate: "6s"
    shots:
      - index: 1
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "双人居中，跳舞"
        narrative_function: "展示跳舞的整体动作和氛围"
        cut_reason: "需要更近的景别展示动作细节"
      - index: 2
        duration: "2s"
        scale: "近景"
        angle: "仰拍"
        movement: "固定"
        composition: "女主角面部特写，手臂向上伸展"
        narrative_function: "强调手臂向上伸展的动作，为转场做准备"
        cut_reason: "动作达到顶点，准备匹配下一个场景"
      - index: 3
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主角面部特写，手臂向上伸展（伸懒腰）"
        narrative_function: "通过相似的伸展动作，将场景从舞台切换到居家环境"
        cut_reason: "转场完成，展示新场景"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用手臂向上伸展的相似动作，将浪漫的舞蹈场景与轻松的居家场景巧妙连接"
      reusable_pattern: "相似动作转场=场景A特定动作特写→场景B相似动作特写"

  - case_title: "相似动作转场-床上伸展到水中下潜"
    scene_type: "动作匹配转场"
    emotional_arc: "平静→深邃"
    duration_estimate: "4s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物在床上向后仰倒"
        narrative_function: "展示向后仰倒的动作，为转场做铺垫"
        cut_reason: "动作进行中，准备匹配下一个场景"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物在水中向下潜"
        narrative_function: "通过相似的下落/后仰动作，将场景从卧室切换到水下"
        cut_reason: "转场完成，展示新场景"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用身体向后/向下运动的相似性，创造出一种梦幻或深邃的视觉过渡"
      reusable_pattern: "相似动作转场=场景A身体运动→场景B相似方向身体运动"

  - case_title: "连续动作转场-唱歌转身"
    scene_type: "动作连续转场"
    emotional_arc: "欢快→欢快"
    duration_estimate: "4s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，在田野中唱歌并转身"
        narrative_function: "展示人物在特定场景中的动作，并开始转身动作"
        cut_reason: "转身动作进行到一半，准备在下一个场景中继续"
      - index: 2
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，在街道上完成转身动作并继续唱歌"
        narrative_function: "在新的场景中无缝接续上一个场景的转身动作，实现场景转换"
        cut_reason: "转场完成，继续展示新场景"
    pattern_summary:
      rhythm: "快切"
      director_intent: "利用同一个动作（转身）在不同场景中的连续性，实现场景的快速、无缝切换"
      reusable_pattern: "连续动作转场=场景A动作前半部分→场景B动作后半部分"

  - case_title: "连续动作转场-走路"
    scene_type: "动作连续转场"
    emotional_arc: "平稳→平稳"
    duration_estimate: "2s"
    shots:
      - index: 1
        duration: "1s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物从左向右走过橱窗"
        narrative_function: "展示人物的行走动作和方向"
        cut_reason: "人物走到画面边缘或特定位置，准备在下一个场景中继续"
      - index: 2
        duration: "1s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物在新的场景中继续从左向右走"
        narrative_function: "在新的场景中接续行走动作，保持视觉连贯性"
        cut_reason: "转场完成"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用行走动作的连续性和方向的一致性，实现不同场景间的平滑过渡"
      reusable_pattern: "连续动作转场=场景A行走动作→场景B相同方向行走动作"

  - case_title: "连续动作转场-打喷嚏"
    scene_type: "动作连续转场"
    emotional_arc: "难受→难受"
    duration_estimate: "8s"
    shots:
      - index: 1
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩面部特写，准备打喷嚏"
        narrative_function: "展示打喷嚏的前奏动作"
        cut_reason: "动作即将爆发，切换场景"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 3
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 4
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 5
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 6
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 7
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "动作即将爆发"
      - index: 8
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩打出喷嚏"
        narrative_function: "完成打喷嚏动作，释放累积的势能"
        cut_reason: "动作完成"
    pattern_summary:
      rhythm: "快切"
      director_intent: "将一个完整的动作（打喷嚏）拆分到多个不同的场景中，通过快速剪辑制造喜剧效果和视觉冲击力"
      reusable_pattern: "连续动作转场=动作前奏在多个场景中快切→最终场景完成动作"

  - case_title: "关联动作转场-推倒相框到杯子碎裂"
    scene_type: "因果关联转场"
    emotional_arc: "平静→意外"
    duration_estimate: "5s"
    shots:
      - index: 1
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影，手推倒桌上的相框"
        narrative_function: "展示一个引发后果的动作（推倒物品）"
        cut_reason: "物品倒下，准备展示其引发的关联后果"
      - index: 2
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "玻璃杯在地上碎裂，水花四溅"
        narrative_function: "展示上一个动作（推倒）在另一个场景中引发的视觉后果（碎裂），形成因果关联"
        cut_reason: "后果展示完毕"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用动作之间的因果逻辑（推倒→碎裂），将两个不相关的场景巧妙地联系在一起"
      reusable_pattern: "关联动作转场=场景A引发动作→场景B视觉后果"

  - case_title: "关联动作转场-关门到开门"
    scene_type: "连锁效应转场"
    emotional_arc: "连贯→连贯"
    duration_estimate: "6s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物走进房间并关上门"
        narrative_function: "展示关门动作，结束当前场景"
        cut_reason: "门关上，准备通过开门动作进入下一个场景"
      - index: 2
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "另一扇门打开，人物走出来"
        narrative_function: "通过开门动作接续上一个场景的关门动作，实现场景转换"
        cut_reason: "转场完成"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用关门和开门这一对具有连锁效应的动作，实现场景的自然过渡"
      reusable_pattern: "关联动作转场=场景A关门动作→场景B开门动作"
```

## 原始分析

```yaml
cases:
  - case_title: "相似动作转场-打鼓到打字"
    scene_type: "动作匹配转场"
    emotional_arc: "动感→平静"
    duration_estimate: "4s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，背对镜头打鼓"
        narrative_function: "展示打鼓的动作和节奏，为转场做铺垫"
        cut_reason: "动作达到高潮，准备匹配下一个场景的相似动作"
      - index: 2
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，侧面面对电脑打字"
        narrative_function: "通过相似的敲击动作，将场景从舞台无缝切换到室内工作环境"
        cut_reason: "转场完成，展示新场景"
    pattern_summary:
      rhythm: "快切"
      director_intent: "利用不同场景中相似的肢体动作，实现视觉上的连贯和顺滑过渡"
      reusable_pattern: "相似动作转场=场景A动作高潮→场景B相似动作继续"

  - case_title: "相似动作转场-跳舞到伸懒腰"
    scene_type: "动作匹配转场"
    emotional_arc: "浪漫→轻松"
    duration_estimate: "6s"
    shots:
      - index: 1
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "双人居中，跳舞"
        narrative_function: "展示跳舞的整体动作和氛围"
        cut_reason: "需要更近的景别展示动作细节"
      - index: 2
        duration: "2s"
        scale: "近景"
        angle: "仰拍"
        movement: "固定"
        composition: "女主角面部特写，手臂向上伸展"
        narrative_function: "强调手臂向上伸展的动作，为转场做准备"
        cut_reason: "动作达到顶点，准备匹配下一个场景"
      - index: 3
        duration: "2s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "女主角面部特写，手臂向上伸展（伸懒腰）"
        narrative_function: "通过相似的伸展动作，将场景从舞台切换到居家环境"
        cut_reason: "转场完成，展示新场景"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用手臂向上伸展的相似动作，将浪漫的舞蹈场景与轻松的居家场景巧妙连接"
      reusable_pattern: "相似动作转场=场景A特定动作特写→场景B相似动作特写"

  - case_title: "相似动作转场-床上伸展到水中下潜"
    scene_type: "动作匹配转场"
    emotional_arc: "平静→深邃"
    duration_estimate: "4s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物在床上向后仰倒"
        narrative_function: "展示向后仰倒的动作，为转场做铺垫"
        cut_reason: "动作进行中，准备匹配下一个场景"
      - index: 2
        duration: "2s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物在水中向下潜"
        narrative_function: "通过相似的下落/后仰动作，将场景从卧室切换到水下"
        cut_reason: "转场完成，展示新场景"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用身体向后/向下运动的相似性，创造出一种梦幻或深邃的视觉过渡"
      reusable_pattern: "相似动作转场=场景A身体运动→场景B相似方向身体运动"

  - case_title: "连续动作转场-唱歌转身"
    scene_type: "动作连续转场"
    emotional_arc: "欢快→欢快"
    duration_estimate: "4s"
    shots:
      - index: 1
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，在田野中唱歌并转身"
        narrative_function: "展示人物在特定场景中的动作，并开始转身动作"
        cut_reason: "转身动作进行到一半，准备在下一个场景中继续"
      - index: 2
        duration: "2s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物居中，在街道上完成转身动作并继续唱歌"
        narrative_function: "在新的场景中无缝接续上一个场景的转身动作，实现场景转换"
        cut_reason: "转场完成，继续展示新场景"
    pattern_summary:
      rhythm: "快切"
      director_intent: "利用同一个动作（转身）在不同场景中的连续性，实现场景的快速、无缝切换"
      reusable_pattern: "连续动作转场=场景A动作前半部分→场景B动作后半部分"

  - case_title: "连续动作转场-走路"
    scene_type: "动作连续转场"
    emotional_arc: "平稳→平稳"
    duration_estimate: "2s"
    shots:
      - index: 1
        duration: "1s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物从左向右走过橱窗"
        narrative_function: "展示人物的行走动作和方向"
        cut_reason: "人物走到画面边缘或特定位置，准备在下一个场景中继续"
      - index: 2
        duration: "1s"
        scale: "全景"
        angle: "平视"
        movement: "跟拍"
        composition: "人物在新的场景中继续从左向右走"
        narrative_function: "在新的场景中接续行走动作，保持视觉连贯性"
        cut_reason: "转场完成"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用行走动作的连续性和方向的一致性，实现不同场景间的平滑过渡"
      reusable_pattern: "连续动作转场=场景A行走动作→场景B相同方向行走动作"

  - case_title: "连续动作转场-打喷嚏"
    scene_type: "动作连续转场"
    emotional_arc: "难受→难受"
    duration_estimate: "8s"
    shots:
      - index: 1
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩面部特写，准备打喷嚏"
        narrative_function: "展示打喷嚏的前奏动作"
        cut_reason: "动作即将爆发，切换场景"
      - index: 2
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 3
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 4
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 5
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 6
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "继续累积"
      - index: 7
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩在不同场景中继续打喷嚏的前奏动作"
        narrative_function: "在不同场景中累积打喷嚏的动作势能"
        cut_reason: "动作即将爆发"
      - index: 8
        duration: "1s"
        scale: "近景"
        angle: "平视"
        movement: "固定"
        composition: "男孩打出喷嚏"
        narrative_function: "完成打喷嚏动作，释放累积的势能"
        cut_reason: "动作完成"
    pattern_summary:
      rhythm: "快切"
      director_intent: "将一个完整的动作（打喷嚏）拆分到多个不同的场景中，通过快速剪辑制造喜剧效果和视觉冲击力"
      reusable_pattern: "连续动作转场=动作前奏在多个场景中快切→最终场景完成动作"

  - case_title: "关联动作转场-推倒相框到杯子碎裂"
    scene_type: "因果关联转场"
    emotional_arc: "平静→意外"
    duration_estimate: "5s"
    shots:
      - index: 1
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "人物背影，手推倒桌上的相框"
        narrative_function: "展示一个引发后果的动作（推倒物品）"
        cut_reason: "物品倒下，准备展示其引发的关联后果"
      - index: 2
        duration: "2s"
        scale: "特写"
        angle: "平视"
        movement: "固定"
        composition: "玻璃杯在地上碎裂，水花四溅"
        narrative_function: "展示上一个动作（推倒）在另一个场景中引发的视觉后果（碎裂），形成因果关联"
        cut_reason: "后果展示完毕"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用动作之间的因果逻辑（推倒→碎裂），将两个不相关的场景巧妙地联系在一起"
      reusable_pattern: "关联动作转场=场景A引发动作→场景B视觉后果"

  - case_title: "关联动作转场-关门到开门"
    scene_type: "连锁效应转场"
    emotional_arc: "连贯→连贯"
    duration_estimate: "6s"
    shots:
      - index: 1
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "人物走进房间并关上门"
        narrative_function: "展示关门动作，结束当前场景"
        cut_reason: "门关上，准备通过开门动作进入下一个场景"
      - index: 2
        duration: "3s"
        scale: "全景"
        angle: "平视"
        movement: "固定"
        composition: "另一扇门打开，人物走出来"
        narrative_function: "通过开门动作接续上一个场景的关门动作，实现场景转换"
        cut_reason: "转场完成"
    pattern_summary:
      rhythm: "平稳切换"
      director_intent: "利用关门和开门这一对具有连锁效应的动作，实现场景的自然过渡"
      reusable_pattern: "关联动作转场=场景A关门动作→场景B开门动作"
```
