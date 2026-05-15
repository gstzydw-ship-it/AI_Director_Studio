from __future__ import annotations

import os
import sys

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from agents.director_graph_package import story_planner_impl as spi  # noqa: E402
from agents.director_graph_package import llm as llm_mod  # noqa: E402
from agents.director_graph_package.story_planner_impl import (  # noqa: E402
    _extract_segments,
    _extract_yaml_sections,
    _normalise_story_planner_output,
    _parse_story_planner_agent_validation,
    _run_story_planner_with_schema_repair,
    _story_planner_fragment_count_instruction,
    _story_planner_fragment_granularity_issues,
    _story_planner_granularity_rules,
    _story_planner_soft_validation_issues,
    _story_planner_rhythm_boundary_rules,
    _validate_story_planner_output,
)


LIGHTWEIGHT_YAML = """
- fragment_id: F01
  duration_target: "10-12s"
  dramatic_unit: "Shang enters and the lobby freezes"
  source_script_events:
    - "Shang walks into the lobby."
    - "The employees stand straight."
  cast:
    active:
      - "SUBJ_SHANG"
      - "employees"
    must_not_show:
      - "SUBJ_QIAO"
  continuity:
    entry: "Lobby is quiet before Shang enters."
    exit: "Shang is moving toward the elevator."
  reaction_plan: "The pressure reaction is absorbed within this fragment."
  director_brief: "Keep the beat about Shang's authority landing in the lobby."
"""


def test_story_planner_accepts_lightweight_schema_without_shot_fields():
    issues = _validate_story_planner_output(
        LIGHTWEIGHT_YAML,
        "Shang walks into the lobby.\nThe employees stand straight.",
    )

    assert issues == []
    assert "main_shots" not in LIGHTWEIGHT_YAML
    assert "camera_setup_type" not in LIGHTWEIGHT_YAML
    assert "sub_shots" not in LIGHTWEIGHT_YAML


def test_story_planner_accepts_minimal_chinese_handoff_schema():
    planner_output = """
- 片段编号: F01
  目标时长: "8-10秒"
  施工剧本原文事件:
    - "乔熙拿起书包。"
    - "照片从书包里滑落。"
  出现人物:
    - "乔熙"
  入场状态: "乔熙手边有书包，照片仍在书包内。"
  出场状态: "照片滑落到地面，乔熙看到照片。"
  承接要求: "照片揭示反应留在本段尾部，下一段承接乔熙受击状态。"
"""

    issues = _validate_story_planner_output(
        planner_output,
        "乔熙拿起书包。\n照片从书包里滑落。",
    )

    assert issues == []
    assert _extract_segments(planner_output) == (1, ["片段01"])


def test_story_planner_rejects_overlong_urgent_short_action():
    planner_output = """
- 片段编号: F01
  目标时长: "8-10秒"
  施工剧本原文事件:
    - "乔熙急促小跑进门。"
    - "她推开门。"
  出现人物:
    - "乔熙"
  入场状态: "乔熙在门外。"
  出场状态: "乔熙已经进入室内。"
  承接要求: "无需独立反应。"
"""

    issues = _validate_story_planner_output(
        planner_output,
        "乔熙急促小跑进门。\n她推开门。",
    )

    assert any("急促短动作" in issue for issue in issues)
    assert any("2-5秒" in issue for issue in issues)


def test_rhythm_story_planner_allows_long_merged_unit_with_bounded_internal_fast_beat(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "玻璃茶几上的闹钟响起，旁边的手机正开着免提通话。",
            "乔熙一手按住小豆丁乱蹬的腿，一手把衣服往她身上套，几次被小豆丁扭开。",
            "乔熙：Kiki, cover for me. I'll be right there!",
            "乔熙按断通话，把手机留在茶几上，立刻腾出双手去扣小豆丁的衣服。",
            "小豆丁缩起胳膊，往沙发边躲，衣服只穿上一半。",
            "小豆丁：I don't want to go to school!",
            "乔熙停住追她的动作，蹲下挡住她继续躲开的方向，压低语速哄她。",
            "乔熙：Sweetie. I'll get you some strawberry cake later, okay?",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "合并完成公寓内赶时间、孩子抗拒、照片触发旧情情绪，并把四年前银杏树下的承诺与亲吻回忆一次性落到。"
  目标时长: "13-15秒"
  节奏类型: "快节奏"
  事件密度判断: "前半段是高密度短动作与问答，后半段转入低密度情绪回忆；属于同一戏剧单元内的节奏转折，不拆成平级片段。"
  片段内节奏分配: "0-6秒：闹钟、免提通话、按住孩子乱蹬腿、孩子打开、乔熙Kiki台词和按断通话一次性紧凑落到；6-15秒：孩子拒绝台词、乔熙安抚和情绪反应落点放慢完成。"
  动作节奏指导: "前半急急忙忙、动作叠压；后半压住语速处理孩子拒绝和乔熙哄劝。"
  施工剧本原文事件:
    - "玻璃茶几上的闹钟响起，旁边的手机正开着免提通话。"
    - "乔熙一手按住小豆丁乱蹬的腿，一手把衣服往她身上套，几次被小豆丁扭开。"
    - "乔熙：Kiki, cover for me. I'll be right there!"
    - "乔熙按断通话，把手机留在茶几上，立刻腾出双手去扣小豆丁的衣服。"
    - "小豆丁缩起胳膊，往沙发边躲，衣服只穿上一半。"
    - "小豆丁：I don't want to go to school!"
    - "乔熙停住追她的动作，蹲下挡住她继续躲开的方向，压低语速哄她。"
    - "乔熙：Sweetie. I'll get you some strawberry cake later, okay?"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "公寓清晨；闹钟响起，手机开着免提通话，小豆丁正在抗拒穿衣。"
  出场状态: "小豆丁被安抚，乔熙完成从急促动作到哄劝的节奏转折。"
  承接要求: "同一生活戏剧任务内完成快慢变化，不因单个动作另起片段。"
  镜头导演交接: "前6秒压缩急促动作链，后段保留孩子拒绝和乔熙哄劝的情绪落点。"
"""

    issues = spi._validate_story_planner_output(
        planner_output,
        script,
        require_rhythm_fields=True,
    )

    assert issues == []


def test_rhythm_story_planner_rejects_long_fast_unit_without_internal_fast_budget(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "乔熙急忙按掉闹钟。",
            "乔熙把手机夹在肩与耳之间。",
            "小豆丁缩起胳膊拒绝穿衣。",
            "乔熙停住动作后蹲下哄她。",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "乔熙急忙处理闹钟、通话和孩子穿衣抗拒。"
  目标时长: "13-15秒"
  节奏类型: "快节奏"
  事件密度判断: "短动作密集，但没有拆分。"
  片段内节奏分配: "全段按13-15秒处理乔熙的忙乱和孩子抗拒。"
  动作节奏指导: "乔熙急急忙忙，动作叠压。"
  施工剧本原文事件:
    - "乔熙急忙按掉闹钟。"
    - "乔熙把手机夹在肩与耳之间。"
    - "小豆丁缩起胳膊拒绝穿衣。"
    - "乔熙停住动作后蹲下哄她。"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "闹钟响起。"
  出场状态: "乔熙仍在处理孩子抗拒。"
  承接要求: "下一段承接孩子让步。"
  镜头导演交接: "保留忙乱和抗拒。"
"""

    issues = spi._validate_story_planner_output(
        planner_output,
        script,
        require_rhythm_fields=True,
    )

    assert any("片段内节奏分配" in issue for issue in issues)
    assert any("急促动作小节拍压到 5-6秒以内" in issue for issue in issues)


def test_story_planner_requires_only_planning_handoff_fields():
    planner_output = """
- fragment_id: F01
  duration_target: "10s"
  dramatic_unit: "Shang enters"
  source_script_events:
    - "Shang walks into the lobby."
  reaction_plan: "No separate reaction is needed; keep it internal."
  director_brief: "Authority enters the room."
"""

    issues = _validate_story_planner_output(planner_output, "Shang walks into the lobby.")

    assert any("出现人物" in issue for issue in issues)
    assert any("入场状态" in issue for issue in issues)
    assert any("出场状态" in issue for issue in issues)
    assert not any("main_shots" in issue for issue in issues)
    assert not any("boundary_reason" in issue for issue in issues)


def test_story_planner_autofills_missing_reaction_plan():
    planner_output = """
- fragment_id: F06
  duration_target: "8s"
  dramatic_unit: "Qiao's internal line lands as a reaction beat"
  source_script_events:
    - "Qiao thinks, Good? My ass!"
  cast:
    active:
      - "SUBJ_QIAO"
    must_not_show: []
  continuity:
    entry: "Qiao is inside the elevator."
    exit: "Qiao has swallowed the line without speaking aloud."
  director_brief: "Let the next director choose the visible reaction detail."
"""

    normalised = _normalise_story_planner_output(planner_output)
    issues = _validate_story_planner_output(normalised, "Qiao thinks, Good? My ass!")

    assert "承接要求:" in normalised
    assert "下游镜头导演负责决定具体反应镜头与动作落点" in normalised
    assert not any("reaction_plan" in issue for issue in issues)


def test_story_planner_autofills_shot_director_handoff_fields():
    planner_output = """
- fragment_id: F01
  duration_target: "8s"
  source_script_events:
    - "Qiao grabs the coat."
  cast:
    active:
      - "Qiao"
      - "Kid"
    must_not_show: []
  continuity:
    entry: "Qiao is beside the bed."
    exit: "The kid is still resisting."
"""

    normalised = _normalise_story_planner_output(planner_output, "Qiao grabs the coat.")
    issues = _validate_story_planner_output(normalised, "Qiao grabs the coat.")

    assert "片段任务:" in normalised
    assert "镜头导演交接:" in normalised
    assert "目标时长：8s" in normalised
    assert issues == []


def test_story_planner_splits_merged_adjacent_source_events():
    script = "\n".join(
        [
            "▲商北琛转身进入电梯，就在电梯门即将关闭之际——",
            "乔熙：Wait a second!",
            "▲乔熙像风一般冲进电梯，一个刹不住，整个人直扑到商北琛身上。",
        ]
    )
    planner_output = """
- fragment_id: F01
  duration_target: "8s"
  dramatic_unit: "Elevator collision"
  source_script_events:
    - "▲商北琛转身进入电梯，就在电梯门即将关闭之际——乔熙：Wait a second!"
    - "▲乔熙像风一般冲进电梯，一个刹不住，整个人直扑到商北琛身上。"
  cast:
    active: ["商北琛", "乔熙"]
    must_not_show: []
  continuity:
    entry: "电梯门正在关闭。"
    exit: "乔熙已经撞进电梯。"
  reaction_plan: "受击与错愕留在本片段内部承接。"
  director_brief: "保留重逢前一拍的门缝悬点。"
"""

    normalised = _normalise_story_planner_output(planner_output, script)
    issues = _validate_story_planner_output(normalised, script)

    assert '    - "▲商北琛转身进入电梯，就在电梯门即将关闭之际——"' in normalised
    assert '    - "乔熙：Wait a second!"' in normalised
    assert '    - "▲商北琛转身进入电梯，就在电梯门即将关闭之际——乔熙：Wait a second!"' not in normalised
    assert issues == []


def test_story_planner_ignores_markdown_fences_and_preface():
    planner_output = f"""Here is the split:

```yaml
{LIGHTWEIGHT_YAML.strip()}
```
"""

    sections = _extract_yaml_sections(planner_output)
    normalised = _normalise_story_planner_output(planner_output)
    issues = _validate_story_planner_output(
        normalised,
        "Shang walks into the lobby.\nThe employees stand straight.",
    )

    assert len(sections) == 1
    assert 'fragment_id: "F01"' in normalised
    assert issues == []


def test_story_planner_normalises_complex_fragment_ids_to_runtime_contract():
    planner_output = """
- fragment_id: "F2-1A"
  duration_target: "8s"
  dramatic_unit: "First beat"
  source_script_events:
    - "A enters."
  cast:
    active: ["A"]
    must_not_show: []
  continuity:
    entry: "A is outside."
    exit: "A is inside."
  reaction_plan: "No independent reaction is needed."
  director_brief: "Entrance beat."

- fragment_id: "F2-1B"
  duration_target: "8s"
  dramatic_unit: "Second beat"
  source_script_events:
    - "B answers."
  cast:
    active: ["B"]
    must_not_show: []
  continuity:
    entry: "B waits."
    exit: "B has answered."
  reaction_plan: "The response stays inside this fragment."
  director_brief: "Answer beat."
"""

    normalised = _normalise_story_planner_output(planner_output)

    assert 'fragment_id: "F01"' in normalised
    assert 'fragment_id: "F02"' in normalised
    assert "F2-1A" not in normalised
    assert "F2-1B" not in normalised
    assert _extract_segments(normalised) == (2, ["片段01", "片段02"])


def test_story_planner_repairs_short_non_yaml_output(monkeypatch):
    calls = {"n": 0, "repair_prompt": ""}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "I will split this later."
        calls["repair_prompt"] = user_prompt
        return LIGHTWEIGHT_YAML

    monkeypatch.setattr(spi, "call_llm", fake_call_llm)

    output, attempts = _run_story_planner_with_schema_repair(
        system_prompt="system",
        user_prompt="initial",
        original_script="Shang walks into the lobby.\nThe employees stand straight.",
        scene_output="current_main_action: Shang enters the lobby.",
        rhythm_guidance="段尾停在 F01 尾帧，普通受击反应留在片段内部。",
    )

    assert calls["n"] == 2
    assert "必须修复的问题" in calls["repair_prompt"]
    assert "节奏总控施工指令" in calls["repair_prompt"]
    assert "普通受击反应留在片段内部" in calls["repair_prompt"]
    assert "镜头" in calls["repair_prompt"]
    assert "场景空间记忆卡" not in calls["repair_prompt"]
    assert attempts[0]["status"] == "invalid_schema"
    assert attempts[1]["status"] == "success"
    assert "fragment_id" in output


def test_story_planner_reports_connection_failure_after_upstream_504(monkeypatch):
    script = "\n".join(f"Script event {index}." for index in range(1, 10))

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        raise RuntimeError("LLM 接口返回 HTTP 504（agent=story_planner）")

    monkeypatch.setattr(spi, "call_llm", fake_call_llm)

    with pytest.raises(RuntimeError, match="节奏拆片导演大模型连接不成功"):
        _run_story_planner_with_schema_repair(
            system_prompt="system",
            user_prompt="initial",
            original_script=script,
            scene_output="current_main_action: scripted events continue.",
        )


def test_story_planner_retry_budget_has_stability_floor():
    assert llm_mod._effective_retry_budget("story_planner", 1) == 3
    assert llm_mod._effective_retry_budget("story_planner", 5) == 5


def test_story_planner_rejects_source_events_not_in_script(monkeypatch):
    planner_output = """
- fragment_id: F01
  duration_target: "8s"
  dramatic_unit: "Lobby authority beat"
  source_script_events:
    - "Shang walks into the lobby."
    - "The secretary clutches a file until her knuckles turn white."
  cast:
    active: ["SUBJ_SHANG"]
    must_not_show: []
  continuity:
    entry: "Lobby is quiet."
    exit: "Shang has entered."
  reaction_plan: "No independent reaction is needed."
  director_brief: "Authority lands."
"""

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("source_script_events must be checked locally")

    monkeypatch.setattr(spi, "call_llm", fail_if_called)

    issues = _validate_story_planner_output(
        _normalise_story_planner_output(planner_output),
        "Shang walks into the lobby.",
    )

    assert any("must quote original script verbatim" in issue for issue in issues)
    assert any("secretary clutches" in issue for issue in issues)


def test_story_planner_rejects_paraphrased_source_events_without_llm(monkeypatch):
    planner_output = """
- fragment_id: F01
  duration_target: "6s"
  dramatic_unit: "Qiao dresses the child"
  source_script_events:
    - "Qiao helps the child get dressed."
  cast:
    active: ["Qiao", "child"]
    must_not_show: []
  continuity:
    entry: "Qiao is rushing."
    exit: "The child is ready."
  reaction_plan: "No independent reaction is needed."
  director_brief: "Morning rush."
"""

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("source_script_events must be checked locally")

    monkeypatch.setattr(spi, "call_llm", fail_if_called)

    issues = _validate_story_planner_output(
        _normalise_story_planner_output(planner_output),
        "Qiao is hurriedly buttoning the child's shirt while making a phone call.",
    )

    assert any("must quote original script verbatim" in issue for issue in issues)


def test_story_planner_accepts_legacy_cast_and_continuity_aliases():
    planner_output = """
- fragment_id: F01
  duration_target: "8s"
  dramatic_unit: "Legacy output shape"
  source_script_events:
    - "A enters."
  active_cast:
    - "A"
  offscreen_cast: []
  state_contract:
    entry_state: "A is outside."
    exit_state: "A is inside."
  reaction_plan: "No independent reaction is needed."
  director_brief: "Entry handoff."
"""

    assert _validate_story_planner_output(planner_output, "A enters.") == []


def test_story_planner_dense_source_events_are_soft_not_blocking():
    events = [f"Event {i}." for i in range(1, 13)]
    planner_output = "\n".join(
        [
            "- fragment_id: F01",
            '  duration_target: "12s"',
            '  dramatic_unit: "Dense but coherent dialogue beat"',
            "  source_script_events:",
            *[f'    - "{event}"' for event in events],
            "  cast:",
            '    active: ["A", "B"]',
            "    must_not_show: []",
            "  continuity:",
            '    entry: "A starts the exchange."',
            '    exit: "B has heard the answer."',
            '  reaction_plan: "The response stays inside this fragment."',
            '  director_brief: "Keep the exchange as one continuous beat."',
        ]
    )

    hard_issues = _validate_story_planner_output(planner_output, "\n".join(events))
    soft_issues = _story_planner_soft_validation_issues(planner_output)

    assert hard_issues == []
    assert any("source_script_events" in issue for issue in soft_issues)


def test_story_planner_fragment_count_instruction_uses_dramatic_units_not_line_count():
    script = "\n".join(f"Event {index}." for index in range(1, 52))

    instruction = _story_planner_fragment_count_instruction(script)

    assert "51 条非空原文行" in instruction
    assert "只是 source_script_events 覆盖清单" in instruction
    assert "不是片段数量公式" in instruction
    assert "必须先识别戏剧单元" in instruction
    assert "7-13 段" not in instruction
    assert "输出超过 13 段会被运行时拒绝" not in instruction


def test_story_planner_does_not_reject_by_raw_source_event_count_alone():
    events = [f"Event {i}." for i in range(1, 52)]
    fragments: list[str] = []
    cursor = 0
    for index in range(15):
        take = 4 if index < 6 else 3
        fragment_events = events[cursor : cursor + take]
        cursor += take
        fragments.extend(
            [
                f"- fragment_id: F{index + 1:02d}",
                '  duration_target: "5-8s"',
                f'  dramatic_unit: "Dramatic task {index + 1}"',
                "  source_script_events:",
                *[f'    - "{event}"' for event in fragment_events],
            ]
        )
    planner_output = "\n".join(fragments)

    granularity_issues = _story_planner_fragment_granularity_issues(planner_output)

    assert granularity_issues == []


def test_story_planner_normalises_missing_intra_fragment_rhythm():
    planner_output = """
- 片段编号: F01
  片段任务: "乔熙在闹钟和电话催促下给小豆丁穿衣。"
  目标时长: "5-6秒"
  节奏类型: "快节奏"
  事件密度判断: "短时间密集事件。"
  动作节奏指导: "乔熙急急忙忙，动作叠压。"
  施工剧本原文事件:
    - "玻璃茶几上的闹钟响起，旁边的手机正开着免提通话。"
    - "乔熙一手按住小豆丁乱蹬的腿，一手把衣服往她身上套，几次被小豆丁扭开。"
    - "乔熙：Kiki, cover for me. I'll be right there!"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "闹钟响起。"
  出场状态: "小豆丁仍在抗拒。"
  承接要求: "急促处理留在本段内部完成。"
  镜头导演交接: "保留通话和穿衣抗拒。"
"""

    normalised = _normalise_story_planner_output(planner_output)

    assert "片段内节奏分配:" in normalised
    assert "同一片段内部控制快慢" in normalised


def test_story_planner_rejects_line_by_line_overfragmentation():
    events = [f"Event {i}." for i in range(1, 76)]
    fragments: list[str] = []
    for index, event in enumerate(events[:25]):
        fragments.extend(
            [
                f"- fragment_id: F{index + 1:02d}",
                '  duration_target: "2-3s"',
                f'  dramatic_unit: "Beat {index + 1}"',
                "  source_script_events:",
                f'    - "{event}"',
                "  cast:",
                '    active: ["A", "B"]',
                "    must_not_show: []",
                "  continuity:",
                f'    entry: "Beat {index + 1} starts."',
                f'    exit: "Beat {index + 1} ends."',
                '  reaction_plan: "The reaction stays inside this fragment."',
                f'  director_brief: "Keep beat {index + 1} clear."',
            ]
        )
    planner_output = "\n".join(fragments)

    hard_issues = _validate_story_planner_output(planner_output, "\n".join(events))
    granularity_issues = _story_planner_fragment_granularity_issues(planner_output)

    assert any("按动作行切分" in issue for issue in hard_issues)
    assert granularity_issues


def test_story_planner_granularity_rules_state_merge_policy():
    rules = _story_planner_granularity_rules()

    assert "15 秒以内" in rules
    assert "4-8 条" in rules
    assert "普通停顿、受击反应、信息揭示默认留在当前片段内部" in rules
    assert "明确结尾悬念、段尾停在未完成状态、尾帧承接" in rules


def test_story_planner_agent_validator_can_release_soft_density_warning(monkeypatch):
    events = [f"Event {i}." for i in range(1, 13)]
    dense_yaml = "\n".join(
        [
            "- fragment_id: F01",
            '  duration_target: "12s"',
            '  dramatic_unit: "Dense but coherent dialogue beat"',
            "  source_script_events:",
            *[f'    - "{event}"' for event in events],
            "  cast:",
            '    active: ["A", "B"]',
            "    must_not_show: []",
            "  continuity:",
            '    entry: "A starts the exchange."',
            '    exit: "B has heard the answer."',
            '  reaction_plan: "The response stays inside this fragment."',
            '  director_brief: "Keep the exchange as one continuous beat."',
        ]
    )
    calls = {"story": 0, "validator": 0}

    def fake_agent_configured(agent_name):
        return agent_name == "validator"

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        agent_name = kwargs.get("agent_name")
        if agent_name == "validator":
            calls["validator"] += 1
            return "总体评级：提醒\n问题清单：\n- 片段偏密，但仍可交给后续镜头导演。"
        calls["story"] += 1
        return dense_yaml

    monkeypatch.setattr(spi, "_agent_configured", fake_agent_configured)
    monkeypatch.setattr(spi, "call_llm", fake_call_llm)

    output, attempts = _run_story_planner_with_schema_repair(
        system_prompt="system",
        user_prompt="initial",
        original_script="\n".join(events),
        scene_output="current_main_action: A and B exchange dialogue.",
    )

    assert calls == {"story": 1, "validator": 1}
    assert attempts[0]["status"] == "success"
    assert attempts[0]["agent_validation"]["status"] == "warn"
    assert attempts[0]["soft_validation_issues"]
    assert "fragment_id" in output


def test_story_planner_agent_validation_parser_understands_chinese_statuses():
    status, issues = _parse_story_planner_agent_validation(
        "总体评级：失败\n问题清单：\n- 片段边界混乱，后续无法接住。"
    )

    assert status == "fail"
    assert issues == ["片段边界混乱，后续无法接住。"]


def test_story_planner_rhythm_boundary_rules_limit_rewrite_permissions():
    rules = _story_planner_rhythm_boundary_rules()

    assert "只负责把当前施工剧本拆成" in rules
    assert "不定义镜头语言" in rules
    assert "不能被当成新剧情事件来源" in rules
    assert "当前施工剧本" in rules
    assert "承接要求只能写结构判断" in rules
    assert "beat_design / reaction_plan" not in rules


def test_story_planner_prompt_uses_current_script_with_slim_rule_digest(monkeypatch):
    captured: dict[str, object] = {}

    def fake_record_knowledge_metadata(state, agent_name, context_hint, retrieval_meta):
        captured["agent_name"] = agent_name
        captured["context_hint"] = context_hint
        captured["retrieval_meta"] = retrieval_meta
        return {}

    monkeypatch.setattr(spi, "_record_knowledge_metadata", fake_record_knowledge_metadata)
    monkeypatch.setattr(spi, "_validate_story_planner_output", lambda *args, **kwargs: [])
    monkeypatch.setattr(spi, "_persist_update", lambda state, payload: {**state, **payload})
    monkeypatch.setattr(
        spi,
        "query_rule_registry",
        lambda query, agent_name, n_results: [
            {
                "rule_id": "SEG-NOT-EQUAL-002",
                "title": "片段不是时间均分块",
                "text": (
                    "[SEG-NOT-EQUAL-002] 片段不是时间均分块\n"
                    "执行指令: 片段边界必须围绕戏剧完整性、动作段和发言单元微调，而不是机械按秒数或字数均分。\n"
                    "例外边界: 没有明显戏剧边界时，可用时间上限作为辅助约束。"
                ),
            }
        ],
    )

    def fake_run_story_planner(**kwargs):
        captured["system_prompt"] = kwargs["system_prompt"]
        captured["user_prompt"] = kwargs["user_prompt"]
        captured["rhythm_guidance"] = kwargs["rhythm_guidance"]
        return LIGHTWEIGHT_YAML, [{"status": "success"}]

    monkeypatch.setattr(spi, "_run_story_planner_with_schema_repair", fake_run_story_planner)

    result = spi.story_planner_node(
        {
            "script": "增强后施工剧本：乔熙拿起书包，照片滑落。",
            "director_brief": "主线保护: 不改变人物关系\n节奏总控交接: 照片滑落后必须保护人物反应。",
            "atmosphere_strategy": "拆片边界建议: 照片滑落后不拆；尾帧承接: 乔熙低头停住。",
            "agent_outputs": {"scene_analyst": "道具锚点: 书包在乔熙手边。"},
            "aspect_ratio": "9:16",
        }
    )

    prompt = str(captured["user_prompt"])
    assert "【当前施工剧本】" in prompt
    assert "增强后施工剧本" in prompt
    assert "【给结构规划师的节奏操作单】" in prompt
    assert "【知识库极简规则】" in prompt
    assert "SEG-NOT-EQUAL-002" in prompt
    assert "片段任务" in prompt
    assert "镜头导演交接" in prompt
    assert "只做分段" in str(captured["system_prompt"])
    assert "施工剧本原文事件" in prompt
    assert "剧情增强导演契约" not in prompt
    assert "场景空间记忆卡" not in prompt
    assert "按原始剧本" not in prompt
    assert captured["agent_name"] == "story_planner"
    assert "纯拆片" in captured["context_hint"]
    assert captured["retrieval_meta"]["retrieval_mode"] == "rule_registry_slim"
    assert captured["retrieval_meta"]["matched_sources"] == ["rule_registry.yaml"]
    assert captured["retrieval_meta"]["registry_rule_ids"] == ["SEG-NOT-EQUAL-002"]
    assert "照片滑落后不拆" in captured["rhythm_guidance"]


def test_rhythm_story_planner_node_merges_rhythm_and_planning(monkeypatch):
    captured: dict[str, object] = {}
    planner_yaml = """
- 片段编号: F01
  片段任务: "乔熙在闹钟和电话催促下急忙处理小豆丁外套。"
  目标时长: "5-6秒"
  节奏类型: "快节奏"
  事件密度判断: "多个短动作连续发生，属于短时间密集事件。"
  片段内节奏分配: "0-3秒：闹钟、电话和够外套动作链急促完成；3-6秒：小豆丁抗拒和乔熙压制落地。"
  动作节奏指导: "乔熙必须急急忙忙、多任务并行，动作短促叠压；禁止慢悠悠完成每个动作。"
  施工剧本原文事件:
    - "闹钟响，乔熙一把按掉。"
    - "乔熙把手机夹在肩与耳之间，腾出双手去够小豆丁的外套。"
    - "小豆丁坐在沙发边缘，身体往后缩，两条腿乱蹬。"
    - "乔熙：Kiki, cover for me. I'll be right there!"
    - "乔熙单手扯开外套拉链，另一只手试图按住小豆丁的肩。"
    - "小豆丁整个人扭向沙发靠背。"
  出现人物:
    - "乔熙"
    - "小豆丁"
  入场状态: "闹钟催促，乔熙正在赶时间。"
  出场状态: "小豆丁扭向沙发靠背，乔熙仍在边通话边处理外套。"
  承接要求: "急促处理留在本段内部完成。"
  镜头导演交接: "必须拍完整乔熙同时处理电话和孩子；可以压缩拿外套和拉拉链完整过程；最多主镜头2-3个，辅助插入0-1个；结尾停在小豆丁扭向沙发靠背。"
"""

    monkeypatch.setattr(spi, "_persist_update", lambda state, payload: {**state, **payload})
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(spi, "_record_knowledge_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        spi,
        "query_rule_registry",
        lambda query, agent_name, n_results: [
            {
                "rule_id": "RHYTHM-SHORT-ACTION-TEST",
                "title": "急促短动作预算",
                "text": "急促短动作应压缩到 2-5秒，多个短动作可用 5-6秒紧凑段。",
            }
        ],
    )

    def fake_run_story_planner(**kwargs):
        captured["system_prompt"] = kwargs["system_prompt"]
        captured["user_prompt"] = kwargs["user_prompt"]
        captured["rhythm_guidance"] = kwargs["rhythm_guidance"]
        return planner_yaml, [{"status": "success"}]

    monkeypatch.setattr(spi, "_run_story_planner_with_schema_repair", fake_run_story_planner)

    result = spi.rhythm_story_planner_node(
        {
            "script": "\n".join(
                [
                    "闹钟响，乔熙一把按掉。",
                    "乔熙把手机夹在肩与耳之间，腾出双手去够小豆丁的外套。",
                    "小豆丁坐在沙发边缘，身体往后缩，两条腿乱蹬。",
                    "乔熙：Kiki, cover for me. I'll be right there!",
                    "乔熙单手扯开外套拉链，另一只手试图按住小豆丁的肩。",
                    "小豆丁整个人扭向沙发靠背。",
                ]
            ),
            "director_brief": "保护乔熙赶时间的状态。",
            "agent_outputs": {},
            "aspect_ratio": "9:16",
        }
    )

    prompt = str(captured["user_prompt"])
    assert "节奏拆片导演" in str(captured["system_prompt"])
    assert "短时间 + 密集有效事件" in prompt
    assert "5-6秒" in prompt
    assert "片段内节奏分配" in prompt
    assert "动作节奏指导" in prompt
    assert "禁止输出任何镜头设计字段" in prompt
    assert "story_planner" in result["agent_outputs"]
    assert "rhythm_rewrite_director" in result["agent_outputs"]
    assert "给镜头导演" in result["atmosphere_strategy"]
    assert "0-3秒" in result["atmosphere_strategy"]
    assert "急急忙忙" in result["atmosphere_strategy"]
    assert result["total_segments"] == 1


def test_rhythm_story_planner_rejects_split_domestic_scramble_cluster(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "闹钟响，乔熙一把按掉。",
            "乔熙把手机夹在肩与耳之间，腾出双手去够小豆丁的外套。",
            "小豆丁坐在沙发边缘，身体往后缩，两条腿乱蹬。",
            "乔熙：Kiki, cover for me. I'll be right there!",
            "乔熙单手扯开外套拉链，另一只手试图按住小豆丁的肩。",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "乔熙关闹钟并接电话。"
  目标时长: "5-6秒"
  节奏类型: "快节奏"
  事件密度判断: "闹钟和电话连续发生。"
  动作节奏指导: "急急忙忙、动作叠压。"
  施工剧本原文事件:
    - "闹钟响，乔熙一把按掉。"
    - "乔熙：Kiki, cover for me. I'll be right there!"
  出现人物: ["乔熙"]
  入场状态: "闹钟响。"
  出场状态: "乔熙接通电话。"
  承接要求: "下一段承接乔熙通话。"
  镜头导演交接: "完整保留台词，压缩无信息停顿。"

- 片段编号: F02
  片段任务: "乔熙夹手机并处理小豆丁外套。"
  目标时长: "5-6秒"
  节奏类型: "快节奏"
  事件密度判断: "手机、外套和孩子抗拒连续发生。"
  动作节奏指导: "急急忙忙、动作叠压。"
  施工剧本原文事件:
    - "乔熙把手机夹在肩与耳之间，腾出双手去够小豆丁的外套。"
    - "小豆丁坐在沙发边缘，身体往后缩，两条腿乱蹬。"
    - "乔熙单手扯开外套拉链，另一只手试图按住小豆丁的肩。"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "乔熙正在通话。"
  出场状态: "小豆丁仍在抗拒。"
  承接要求: "无独立反应。"
  镜头导演交接: "外套和孩子抗拒连续处理，不拖慢。"
"""

    issues = spi._validate_story_planner_output(
        planner_output,
        script,
        require_rhythm_fields=True,
    )

    assert any("同一晨间穿衣/通话/孩子抗拒戏剧单元" in issue for issue in issues)


def test_rhythm_story_planner_rejects_split_domestic_scramble_even_when_second_beat_is_normal(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "玻璃茶几上的闹钟响起，旁边的手机正开着免提通话。",
            "乔熙一手按住小豆丁乱蹬的腿，一手把衣服往她身上套，几次被小豆丁扭开。",
            "乔熙：Kiki, cover for me. I'll be right there!",
            "乔熙按断通话，把手机留在茶几上，立刻腾出双手去扣小豆丁的衣服。",
            "小豆丁缩起胳膊，往沙发边躲，衣服只穿上一半。",
            "小豆丁：I don't want to go to school!",
            "乔熙停住追她的动作，蹲下挡住她继续躲开的方向，压低语速哄她。",
            "乔熙：Sweetie. I'll get you some strawberry cake later, okay?",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "乔熙一边通话一边给小豆丁穿衣但被持续抗拒。"
  目标时长: "5-6秒"
  节奏类型: "快节奏"
  事件密度判断: "短时间密集事件。"
  片段内节奏分配: "0-3秒：闹钟/电话/穿衣动作链急促完成；3-6秒：孩子抗拒持续。"
  动作节奏指导: "乔熙急急忙忙，动作叠压。"
  施工剧本原文事件:
    - "玻璃茶几上的闹钟响起，旁边的手机正开着免提通话。"
    - "乔熙一手按住小豆丁乱蹬的腿，一手把衣服往她身上套，几次被小豆丁扭开。"
    - "乔熙：Kiki, cover for me. I'll be right there!"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "闹钟响起，手机免提。"
  出场状态: "乔熙即将按断通话。"
  承接要求: "下一段承接按断通话。"
  镜头导演交接: "保留通话和穿衣抗拒。"

- 片段编号: F02
  片段任务: "乔熙按断通话后双手穿衣失败，小豆丁明确说不想上学，乔熙停下哄劝。"
  目标时长: "8-10秒"
  节奏类型: "正常承接"
  事件密度判断: "完整发言单元。"
  片段内节奏分配: "0-3秒：按断通话和扣衣失败；3-10秒：孩子拒绝和乔熙哄劝。"
  动作节奏指导: "前半段急急忙忙，后半段慢处理。"
  施工剧本原文事件:
    - "乔熙按断通话，把手机留在茶几上，立刻腾出双手去扣小豆丁的衣服。"
    - "小豆丁缩起胳膊，往沙发边躲，衣服只穿上一半。"
    - "小豆丁：I don't want to go to school!"
    - "乔熙停住追她的动作，蹲下挡住她继续躲开的方向，压低语速哄她。"
    - "乔熙：Sweetie. I'll get you some strawberry cake later, okay?"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "乔熙刚结束通话。"
  出场状态: "小豆丁被安抚。"
  承接要求: "孩子拒绝和乔熙哄劝保留。"
  镜头导演交接: "保留两句台词。"
"""

    issues = spi._validate_story_planner_output(
        planner_output,
        script,
        require_rhythm_fields=True,
    )

    assert any("同一晨间穿衣/通话/孩子抗拒戏剧单元" in issue for issue in issues)


def test_rhythm_story_planner_rejects_split_two_person_dialogue_unit(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "小豆丁站在门口，拽住乔熙的衣角。",
            "小豆丁：妈妈，你今天会早点回来吗？",
            "乔熙蹲下，替他整理书包肩带。",
            "乔熙：会，等你放学我就来接你。",
            "小豆丁抬头看她，还是不放心。",
            "小豆丁：那你不要再忘了。",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "小豆丁拉住乔熙并问她是否会早点回来。"
  目标时长: "6-8秒"
  节奏类型: "正常承接"
  事件密度判断: "母子对话的起问与安抚前置动作。"
  动作节奏指导: "正常承接，动作轻缓。"
  施工剧本原文事件:
    - "小豆丁站在门口，拽住乔熙的衣角。"
    - "小豆丁：妈妈，你今天会早点回来吗？"
    - "乔熙蹲下，替他整理书包肩带。"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "小豆丁站在门口拉住乔熙。"
  出场状态: "乔熙蹲下准备回应。"
  承接要求: "下一段承接乔熙回应。"
  镜头导演交接: "保持母子关系连续。"

- 片段编号: F02
  片段任务: "乔熙回应小豆丁，小豆丁继续确认。"
  目标时长: "6-8秒"
  节奏类型: "正常承接"
  事件密度判断: "同一段母子问答继续。"
  动作节奏指导: "正常承接，保留孩子不放心的反应。"
  施工剧本原文事件:
    - "乔熙：会，等你放学我就来接你。"
    - "小豆丁抬头看她，还是不放心。"
    - "小豆丁：那你不要再忘了。"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "乔熙蹲在小豆丁面前。"
  出场状态: "小豆丁仍在确认承诺。"
  承接要求: "同一问答关系内承接。"
  镜头导演交接: "完整保留问答和反应。"
"""

    issues = spi._validate_story_planner_output(
        planner_output,
        script,
        require_rhythm_fields=True,
    )

    assert any("同一对话戏剧单元" in issue for issue in issues)
