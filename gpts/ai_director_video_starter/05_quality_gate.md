# 质检门

每段 prompt 输出后必须进行质检。质检只判断硬伤、连续性、可生成性和结构，不为了审美重写全部内容。

## 输出格式

```yaml
quality_gate:
  status: "pass | needs_repair | fail"
  failed_rule_id:
    - ""
  evidence:
    - ""
  severity: "P0 | P1 | P2 | hard | style"
  checks:
    script_fidelity:
      pass: true
      note: ""
    continuity:
      pass: true
      note: ""
    reference_binding:
      pass: true
      note: ""
    axis:
      pass: true
      note: ""
    timing_and_pacing:
      pass: true
      note: ""
    model_generability:
      pass: true
      note: ""
    negative_constraints:
      pass: true
      note: ""
    schema:
      pass: true
      note: ""
  required_repairs:
    - ""
```

## 必查项

### 剧本忠实

- 是否只使用 `source_script_events` 中的事实。
- 是否只使用 `exact_dialogue_units` 中的台词。
- 是否新增人物、道具、地点、身体接触或剧情结论。

### 连续性

- 是否有 active_cast / offscreen_cast / state_contract。
- entry_state 是否进入首帧。
- exit_state 是否进入尾帧或最后时间段。
- 道具、门、车、身体接触是否单向推进。
- offscreen_cast 是否被错误复活。

### 参考图

- 人物图是否只管身份和服装关键件。
- 场景图是否只管空间和光线。
- 尾帧图是否优先承担下一段首帧锚定。
- 风格图是否没有新增事实。

### 轴线和构图

- 单片段内是否保持同一轴线侧。
- 是否避免把“反打至”写成连续生成动作。
- 首尾帧是否有主体位置、背景锚点或构图比例。

### Prompt 可执行性

- 是否是自然导演句，不是关键词堆砌。
- 每个时间段第一句是否先立分镜基底。
- 是否避免过多微细节、过密动作、不可生成复杂调度。
- 是否提供负约束：无字幕、无屏幕文字、无水印、无无戏份人物。

## 最小返修原则

- 字段缺失：补字段。
- 轴线冲突：统一轴线，不改剧情。
- 人物复活：删除无戏份人物和错误参考图调用。
- 参考图污染：改绑定或删错图。
- 首帧跳位：补像素锚点。
- 对白错误：恢复原文和顺序。
- 节奏拖沓：删除无叙事增量位移，缩短首镜或补受击反应窗口。

