# 视频任务输入卡模板

当用户开始一个新任务时，先把信息整理为下面的结构。缺失字段可以标记为 `待确认`，但不要因为缺字段而停止推进，除非会导致连续性或安全无法判断。

```yaml
project_brief:
  title: ""
  video_type: "短剧 | 广告 | 剧情片 | MV | 产品视频 | 教学 | 其他"
  total_duration: ""
  segment_duration_target: "10-15s"
  aspect_ratio: "9:16 | 16:9 | 1:1"
  target_model: "Seedance | Veo | Runway | 可灵 | Sora | 未指定"
  tone: ""
  visual_style: ""
  language: "中文"
  user_constraints: []

source_material:
  synopsis: ""
  script: ""
  must_keep_lines: []
  forbidden_changes: []

cast:
  - character_id: ""
    name: ""
    role: ""
    appearance: ""
    wardrobe: ""
    personality_or_performance_note: ""
    reference_image: ""

scene:
  location: ""
  time_of_day: ""
  lighting: ""
  props: []
  spatial_layout: ""
  camera_axis_hint: ""
  safety_or_generation_risks: []

reference_assets:
  - asset_id: "image_01"
    type: "character | scene | style | tailframe | prop"
    description: ""
    binding_role: ""
    do_not_use_for: []

output_expectation:
  need_scene_card: true
  need_segment_plan: true
  need_shot_plan: true
  need_storyboard_prompt: true
  need_video_prompt: true
  need_quality_check: true
```

## 参考图职责

- 人物图：只锁定身份、脸型、发型、服装关键件，不继承背景。
- 场景图：只锁定空间、光线、陈设、色彩，不改写人物身份。
- 尾帧图：优先锁定下一段首帧、人物位置、构图比例、光线、空间锚点。
- 风格图：只锁定美术气质、色彩和质感，不新增人物、道具或场景事实。
- 道具图：只锁定道具外观、大小、状态，不自动引入持有者。

## 最少可启动信息

用户只要提供以下 4 项，就可以先启动：

1. 一句话故事或剧本片段。
2. 目标时长和画幅。
3. 主要人物和场景。
4. 目标模型或“暂不指定”。

