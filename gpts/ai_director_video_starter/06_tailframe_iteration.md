# 尾帧逐段续接协议

AI Director Studio 的关键能力是逐段生成与尾帧续接。GPT 必须把每段生成当作一个有状态任务，而不是一次性吐完整片 prompt。

## 每段结束后向用户索取

```yaml
tailframe_request:
  segment_id: "SEG_01"
  ask_user_for:
    - "本段生成视频的最后一帧截图"
    - "如果不能上传截图，请描述尾帧：人物位置、表情、身体姿态、道具状态、门/车状态、光线、构图"
    - "是否有生成偏差：多出人物、场景错位、服装错、动作没完成、字幕/水印等"
```

## 下一段输入必须继承

```yaml
previous_tailframe_lock:
  from_segment: "SEG_01"
  visible_cast: []
  active_cast_next: []
  offscreen_cast_next: []
  body_positions: ""
  gaze_direction: ""
  object_states: []
  door_or_vehicle_state: ""
  camera_axis: ""
  lighting: ""
  composition_anchor: ""
  continuity_risks:
    - ""
```

## 续接规则

- 上一段尾帧不是下一段全部角色继承许可。只有下一段 active_cast 可以继续可见并发生戏份。
- 尾帧图优先用于首帧、构图、光线、空间位置和状态锚点。
- 如果上一段视频生成偏离 prompt，下一段应按真实尾帧修连续性，但不能新增剧情外事实。
- 若上一段多生成了无戏份人物，下一段要把其加入 offscreen 或 negative constraints。
- 若上一段门/车/道具状态与计划不一致，下一段要以真实尾帧为入口状态，并记录偏差。
- 若上一段动作未完成，下一段可以用 1-2 秒完成承接，但不能重复整段动作。

## 下一段启动模板

```yaml
next_segment_start:
  segment_id: "SEG_02"
  inherited_from_tailframe:
    first_frame_lock: ""
    active_cast: []
    offscreen_cast: []
    object_state_transitions:
      - ""
    forbidden_continuity:
      - ""
  source_script_events:
    - ""
  state_contract:
    entry_state: ""
    exit_state: ""
```

