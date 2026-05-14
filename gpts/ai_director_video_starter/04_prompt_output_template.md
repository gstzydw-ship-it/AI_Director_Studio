# 当前片段输出模板

用于给用户输出单个 segment 的视频生成任务。

重要：这个模板不是只给字段名。正式输出时必须把 `compiled_video_prompt` 写成可直接复制到视频模型的完整自然语言 prompt，并额外输出英文 `storyboard_designer_prompt` 和 `quality_gate`。

```yaml
segment_package:
  segment_id: "SEG_01"
  title: ""
  duration: "0-12s"
  aspect_ratio: "9:16"
  target_model: "Seedance"

  source_script_events:
    - ""

  exact_dialogue_units:
    - speaker: ""
      line: ""

  scene_lock:
    location: ""
    time_of_day: ""
    lighting: ""
    wardrobe: ""
    props: []
    axis: ""
    gaze_network: ""

  state_contract:
    entry_state: ""
    exit_state: ""
    object_state_transitions:
      - ""
    forbidden_continuity:
      - ""

  active_cast:
    - ""
  offscreen_cast:
    - ""

  reference_bindings:
    - image: "@image1"
      role: "character_identity | scene_space | style | tailframe | prop"
      use_for: ""
      do_not_use_for: ""

shot_plan:
  main_shots:
    - shot_id: "F01-S01"
      subject: ""
      shot_size: "MS | MLS | MCU | CU | WS"
      camera_height: "eye_level | low | high | chest_level"
      angle: "front | 3/4_front | side_profile | over_shoulder"
      movement: "static | slow_push | follow | pan | tilt"
      lens: "24mm | 28mm | 35mm | 50mm"
      coverage_role: ""
      cut_reason: ""
      visible_action: ""
      dialogue_coverage: ""
      tailframe_role: "none | action_peak | reaction_peak | state_handoff"

  sub_shots:
    - parent_shot_id: "F01-S01"
      shot_id: "F01-S01A"
      trigger: ""
      subject: ""
      shot_size: ""
      cut_point: ""
      action_phase: "start | mid_action | impact | aftermath"
      duration_hint: ""
      state_delta: ""
      emotion_anchor: ""

compiled_video_prompt:
  spatial_and_first_frame_control: >
    写清场景、画幅、首帧人物位置、参考图职责、轴线侧和上一段尾帧继承。

  timeline:
    - time: "0-3s"
      prompt: >
        每段第一句先立分镜基底：主体、景别、机位高度、角度、运镜至少三项。
    - time: "3-7s"
      prompt: >
        再写动作、对白落点、状态变化，不新增剧本外事实。
    - time: "7-12s"
      prompt: >
        写尾帧状态，为下一段留下可续接关系。

  reference_binding_notes:
    - ""

  continuity_constraints:
    - ""

  negative_constraints:
    - "不要字幕、屏幕文字、LOGO、水印。"
    - "不要出现 offscreen_cast 中的人物。"
    - "不要改变角色服装、场景、门/道具状态和轴线。"

  compiler_self_check:
    current_segment_only: true
    dialogue_matches_exact_units: true
    no_unapproved_characters_props_or_locations: true
    reference_roles_not_polluted: true
    entry_exit_state_present: true
```

## 可复制成片 Prompt 必须另起代码块

```text
【可复制到 Seedance / 视频模型的 Prompt】
画幅：9:16 竖屏。场景为……

0-3s：
摄影机……。乔熙……。小豆丁……。台词“……”落点在……

3-7s：
……

7-12s：
……

尾帧：
……

参考图：
@乔熙人物图 只用于乔熙身份、脸型、发型、服装关键件；
@小豆丁人物图 只用于小豆丁身份、服装关键件；
@公寓场景图 只用于卧室空间、陈设、晨光；
@风格参考图 只用于整体光影和美术气质。

负约束：
不要字幕、不要屏幕文字、不要 LOGO、水印；不要新增人物；不要改变卧室空间、服装、道具状态；不要让照片里的男人真人出现在本段画面中。
```

## Storyboard Designer Prompt 模板

图像分镜 prompt 应使用英文：

```text
Create a single professional storyboard sheet for SEG_01 in vertical 9:16 production.
Arrange panels in chronological order. Each panel must show shot number, duration,
framing, camera angle, camera movement arrow, subject action, emotional beat, and cut marker.
Keep character identity, wardrobe, scene layout, lighting, and prop state consistent with the reference bindings.
Do not add new characters, props, locations, subtitles, logos, or screen text.

Panel 1 / F01-S01 / 0-3s:
...

Panel 2 / F01-S02 / 3-7s:
...

Style: clean cinematic storyboard, readable composition, precise camera arrows,
not a comic page, no speech bubbles, no extra story events.
```
