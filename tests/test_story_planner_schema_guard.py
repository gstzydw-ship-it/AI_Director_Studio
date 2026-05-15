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
    _script_emotional_attention_units,
    _story_planner_coarse_fragment_issues,
    _story_planner_fragment_count_instruction,
    _story_planner_fragment_granularity_issues,
    _story_planner_granularity_rules,
    _story_planner_soft_validation_issues,
    _story_planner_rhythm_boundary_rules,
    _target_episode_fragment_count,
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
  片段任务: "乔熙在闹钟和电话催促下给小豆丁穿衣，孩子明确拒绝上学后乔熙停下哄劝。"
  目标时长: "10-12秒"
  节奏类型: "快节奏"
  事件密度判断: "前半段是高密度短动作与通话，后半段转入孩子拒绝和乔熙安抚；共同服务于同一观众注意力问题。"
  片段内节奏分配: "0-4秒：闹钟、免提通话、按住孩子乱蹬腿和乔熙Kiki台词急促落到；4-8秒：按断通话、扣衣失败和孩子拒绝台词形成阻碍；8-12秒：乔熙停住并压低语速哄劝。"
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
  镜头导演交接: "前段压缩急促动作链，后段保留孩子拒绝和乔熙哄劝的情绪落点；切镜方案交给镜头导演。"
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
    assert any("前段急促动作预算" in issue for issue in issues)


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
    assert "必须先识别情绪注意力单元" in instruction
    assert "不固定为 5-6 个" in instruction
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


def test_story_planner_rejects_coarse_multitask_fragment(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "乔熙推开办公室门，停在门口。",
            "商北琛抬头看向她。",
            "乔熙把手机放到桌上。",
            "乔熙：我需要解释昨晚的事。",
            "商北琛：你最好说清楚。",
            "乔熙从包里拿出照片。",
            "商北琛看清照片后沉默。",
            "严飞走到门边挡住外面的人。",
            "乔熙后退半步，手还按在照片上。",
            "商北琛站起身，绕过桌角。",
        ]
    )
    planner_output = f"""
- 片段编号: F01
  片段任务: "乔熙进办公室、解释昨晚、拿出照片并引发商北琛反应。"
  目标时长: "13-15秒"
  节奏类型: "正常承接"
  事件密度判断: "入场、对白、道具揭示和反应混在同一段。"
  片段内节奏分配: "按整体目标时长执行。"
  动作节奏指导: "正常承接。"
  施工剧本原文事件:
{chr(10).join(f'    - "{event}"' for event in script.splitlines())}
  出现人物: ["乔熙", "商北琛", "严飞"]
  入场状态: "乔熙在办公室门口。"
  出场状态: "商北琛站起身。"
  承接要求: "反应留在本段。"
  镜头导演交接: "覆盖全部事件。"
"""

    coarse_issues = _story_planner_coarse_fragment_issues(planner_output)
    hard_issues = _validate_story_planner_output(planner_output, script)

    assert any("疑似粗拆" in issue for issue in coarse_issues)
    assert any("疑似粗拆" in issue for issue in hard_issues)


def test_story_planner_coarse_check_ignores_source_metadata_lines(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    source_events = [
        "1-4 日/外/天御集团门口",
        "人物：乔熙、苏小可、严飞、商北琛",
        "【字幕：One Hour Later】",
        "天御集团旋转门内外的人突然加快动作。秘书和主管们从门口附近急促聚拢，有人停下脚步让出通道，有人转身看向广场。乔熙手里拿着咖啡杯，被人群的动作带得停住。",
        "苏小可从人群里靠近乔熙，压低身体避开前面急着聚拢的人，快速把消息递给她。",
        "苏小可：Sunny, big news—the company's been bought out. New boss is coming!",
        "乔熙握紧咖啡杯，视线从苏小可转向公司门口和广场。",
        "乔熙：What?",
        "广场上，一辆黑色劳斯莱斯幻影驶到台阶前停下。原本还在调整队形的人群立刻停住，声音压下去。",
        "严飞小跑上前，停在车门旁，恭敬拉开车门。",
        "一条被顶级西装裤包裹的长腿迈出，紧接着，一个高大身影俯身而出。",
        "男人穿着剪裁精良的纯黑高定西装，宽肩窄腰，气场强大。他站稳后抬起头。",
        "乔熙看清他的脸，手里的咖啡杯猛地晃了一下。她立刻用另一只手托住杯身，咖啡杯没有掉下去，但她整个人停在原地。",
        "乔熙OS：Nash Pierce? My ex-husband became my new boss!",
        "【本集完】",
    ]
    planner_output = "\n".join(
        [
            "- fragment_id: F06",
            '  dramatic_unit: "完成天御集团门口新老板到场并让乔熙认出前夫的身份揭示单元。"',
            '  duration_target: "10-15秒"',
            '  intra_fragment_rhythm: "0-4秒：人群急促聚拢和苏小可递出收购消息；4-9秒：车辆停下、严飞开门、男人下车形成压迫；9-15秒：乔熙看清脸并托住咖啡杯，身份揭示和受击反应落地。"',
            "  source_script_events:",
            *[f'    - "{event}"' for event in source_events],
            '  cast: ["乔熙", "苏小可", "严飞", "商北琛"]',
            '  continuity: "入场为集团门口等候新老板，出场为乔熙认出商北琛。"',
            '  reaction_plan: "身份揭示和乔熙受击反应留在本段完成。"',
            '  director_brief: "情绪曲线从外部紧张到身份揭示受击；可压缩人群聚拢弱拍，必须保留收购消息、车到、下车和认出前夫。"',
        ]
    )

    assert _story_planner_coarse_fragment_issues(planner_output) == []
    assert not any("疑似粗拆" in issue for issue in _validate_story_planner_output(planner_output, "\n".join(source_events)))


def test_story_planner_reads_list_style_intra_fragment_rhythm(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "闹钟铃声从茶几上传出，乔熙伸手按停。",
            "乔熙：Kiki, cover for me. I'll be right there!",
            "小豆丁：I don't want to go to school!",
            "乔熙：Sweetie. I'll get you some strawberry cake later, okay?",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "完成乔熙赶时间和安抚小豆丁上学抗拒。"
  目标时长: "10-12秒"
  节奏类型: "快节奏"
  事件密度判断: "同一生活冲突单元，前段急促动作，后段留给拒绝和安抚。"
  片段内节奏分配:
    - "0-3秒：闹钟和手机通话急促处理。"
    - "3-6秒：孩子抗拒和乔熙继续赶时间。"
    - "6-12秒：孩子拒绝、乔熙安抚和情绪落点。"
  动作节奏指导: "乔熙急急忙忙、动作叠压，后段转为快速安抚。"
  施工剧本原文事件:
    - "闹钟铃声从茶几上传出，乔熙伸手按停。"
    - "乔熙：Kiki, cover for me. I'll be right there!"
    - "小豆丁：I don't want to go to school!"
    - "乔熙：Sweetie. I'll get you some strawberry cake later, okay?"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "闹钟响，乔熙赶时间。"
  出场状态: "小豆丁被安抚。"
  承接要求: "拒绝和安抚落点留在本段。"
  镜头导演交接: "前6秒压缩急促动作，后段保留拒绝与安抚落点。"
"""

    issues = _validate_story_planner_output(planner_output, script, require_rhythm_fields=True)

    assert not any("标记为快节奏" in issue for issue in issues)


def test_story_planner_dialogue_split_allows_photo_reveal_boundary(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script = "\n".join(
        [
            "小豆丁：I don't want to go to school!",
            "乔熙：Sweetie. I'll get you some strawberry cake later, okay?",
            "小豆丁这才伸出小脚。乔熙迅速整理好衣服，转身拿起书包。",
            "书包被提起时，里面一张照片从开口处滑落到地毯上。",
            "乔熙OS：Why is Nash's photo here?",
            "小豆丁：He is so handsome! Everyone else has a daddy. I want him to be my daddy!",
        ]
    )
    planner_output = """
- 片段编号: F01
  片段任务: "完成孩子拒绝上学到乔熙安抚成功。"
  目标时长: "8-12秒"
  节奏类型: "快节奏"
  事件密度判断: "同一母女上学抗拒问题。"
  片段内节奏分配: "0-5秒：孩子拒绝；5-12秒：乔熙安抚并拿起书包。"
  动作节奏指导: "前段急，后段快速安抚。"
  施工剧本原文事件:
    - "小豆丁：I don't want to go to school!"
    - "乔熙：Sweetie. I'll get you some strawberry cake later, okay?"
    - "小豆丁这才伸出小脚。乔熙迅速整理好衣服，转身拿起书包。"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "孩子仍在抗拒。"
  出场状态: "乔熙拿起书包。"
  承接要求: "下一段直接承接书包被提起后的照片滑落。"
  镜头导演交接: "落点是孩子抗拒暂时解决，尾帧承接书包。"

- 片段编号: F02
  片段任务: "照片滑落并触发乔熙和小豆丁关于爸爸的情绪问题。"
  目标时长: "8-12秒"
  节奏类型: "停顿反应"
  事件密度判断: "照片带来新的情绪注意力问题。"
  片段内节奏分配: "0-4秒：照片滑落和乔熙看清；4-12秒：小豆丁表达想要爸爸，乔熙受击。"
  动作节奏指导: "照片落地后放慢，保留乔熙受击。"
  施工剧本原文事件:
    - "书包被提起时，里面一张照片从开口处滑落到地毯上。"
    - "乔熙OS：Why is Nash's photo here?"
    - "小豆丁：He is so handsome! Everyone else has a daddy. I want him to be my daddy!"
  出现人物: ["乔熙", "小豆丁"]
  入场状态: "乔熙刚拿起书包。"
  出场状态: "乔熙被照片和小豆丁的话击中。"
  承接要求: "下一段承接乔熙被旧情绪拉入回忆。"
  镜头导演交接: "照片是新信息触发点，允许与前段分开。"
"""

    issues = _validate_story_planner_output(planner_output, script, require_rhythm_fields=True)

    assert not any("同一对话戏剧单元" in issue for issue in issues)


def test_story_planner_episode_count_allows_dynamic_lower_band(monkeypatch):
    monkeypatch.setattr(spi, "_target_episode_fragment_count", lambda *args, **kwargs: 6)
    script = "\n".join(f"事件{index}" for index in range(12))

    def planner_with_count(count: int) -> str:
        sections: list[str] = []
        for index in range(1, count + 1):
            sections.extend(
                [
                    f"- fragment_id: F{index:02d}",
                    '  source_script_events:',
                    f'    - "事件{index}"',
                ]
            )
        return "\n".join(sections)

    assert spi._story_planner_episode_unit_count_issues(planner_with_count(4), script) == []
    assert spi._story_planner_episode_unit_count_issues(planner_with_count(3), script)


def test_story_planner_normalises_coarse_multitask_fragment_into_chunks(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script_events = [
        "A enters the apartment.",
        "B turns toward A.",
        "A puts the phone on the table.",
        "A says she needs to explain last night.",
        "B asks for the truth.",
        "A grabs a photo from the bag.",
        "B sees the photo and freezes.",
        "C blocks the door.",
        "A steps back with one hand on the photo.",
        "B stands and walks around the table.",
        "A refuses to leave.",
        "B points at the phone.",
        "The door opens behind them.",
        "A reacts and holds the bag tighter.",
    ]
    planner_output = "\n".join(
        [
            "- fragment_id: F01",
            '  dramatic_unit: "A enters, explains, reveals the photo, triggers B, blocks the door, and starts a conflict turn."',
            '  duration_target: "13-15s"',
            "  source_script_events:",
            *[f'    - "{event}"' for event in script_events],
            "  cast:",
            '    active: ["A", "B", "C"]',
            "    must_not_show: []",
            "  continuity:",
            '    entry: "A enters."',
            '    exit: "A reacts."',
            '  reaction_plan: "The reaction stays inside this fragment."',
            '  director_brief: "Cover the whole event chain."',
        ]
    )

    normalised = _normalise_story_planner_output(planner_output, "\n".join(script_events))
    sections = spi._extract_yaml_sections(normalised)

    assert len(sections) == 5
    assert all(2 <= len(spi._source_script_events(section)) <= 3 for section in sections)
    assert not spi._story_planner_coarse_fragment_issues(normalised)
    assert _validate_story_planner_output(normalised, "\n".join(script_events)) == []


def test_story_planner_normalises_overfragmented_episode_to_dynamic_units(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script_events = [f"Episode event {index}." for index in range(1, 25)]
    fragments: list[str] = []
    for index, event in enumerate(script_events, start=1):
        fragments.extend(
            [
                f"- fragment_id: F{index:02d}",
                f'  片段任务: "Tiny beat {index}"',
                '  目标时长: "3-5秒"',
                '  节奏类型: "快节奏"',
                '  事件密度判断: "单个小节拍。"',
                '  片段内节奏分配: "按当前小节拍执行。"',
                '  动作节奏指导: "正常承接。"',
                "  施工剧本原文事件:",
                f'    - "{event}"',
                '  出现人物: ["A", "B"]',
                '  入场状态: "上个小节拍结束。"',
                '  出场状态: "当前小节拍结束。"',
                '  承接要求: "留在片段内部。"',
                '  镜头导演交接: "覆盖当前小节拍。"',
            ]
        )

    normalised = _normalise_story_planner_output("\n".join(fragments), "\n".join(script_events))
    sections = spi._extract_yaml_sections(normalised)

    assert len(sections) == 4
    assert [spi._extract_fragment_id(section) for section in sections] == [f"F{index:02d}" for index in range(1, 5)]
    assert sum(len(spi._source_script_events(section)) for section in sections) == len(script_events)
    assert "有限切镜" in normalised
    assert _validate_story_planner_output(normalised, "\n".join(script_events), require_rhythm_fields=True) == []


def test_story_planner_attention_unit_estimator_handles_ten_episode_types():
    cases = [
        (
            "morning_child_photo_flashback",
            [
                "闹钟响，乔熙一边接电话一边抓起小豆丁的外套。",
                "小豆丁在沙发上乱蹬腿，不肯把手伸进袖子。",
                "乔熙夹着手机催她快点穿衣。",
                "小豆丁低声说：我不想上学。",
                "乔熙停住动作，蹲下哄她说妈妈陪你说清楚。",
                "乔熙拿起书包，照片从夹层里掉出来。",
                "乔熙捡起照片，看清照片背后的日期。",
                "回忆开始：四年前，乔熙站在银杏树下等人。",
                "少年把围巾递给她，两人第一次靠近。",
                "回到现实：乔熙握着照片，听见小豆丁叫她。",
            ],
            4,
        ),
        (
            "office_contract_recording",
            [
                "乔熙推门进入办公室，所有人看向她。",
                "商北琛让她解释昨晚的缺席。",
                "乔熙把合同递到桌上，要求重新核对签名。",
                "助理打开录音，昨晚的电话内容播放出来。",
                "商北琛听完后沉默，会议室安静下来。",
            ],
            3,
        ),
        (
            "hospital_diagnosis_phone",
            [
                "母亲催乔熙别再查下去。",
                "乔熙整理病历时，诊断书从文件夹里露出来。",
                "她看清诊断结果，手停在纸边。",
                "手机震动打断沉默，屏幕上跳出陌生号码。",
                "乔熙接起电话，听见对方说已经知道真相。",
            ],
            3,
        ),
        (
            "school_bullying_monitor",
            [
                "小豆丁站在教室门口，不敢往里走。",
                "同学把她的画本推到地上。",
                "乔熙蹲下捡画本，压住火气问老师。",
                "老师打开监控视频，走廊里的推搡画面出现。",
                "班主任赶到，所有人都安静下来。",
            ],
            3,
        ),
        (
            "wedding_interruption_video_ring",
            [
                "婚礼进行到交换戒指，宾客鼓掌。",
                "大门被推开，乔熙冲进来，所有人停住。",
                "她打开视频投到屏幕上，昨晚的真相出现。",
                "新郎的戒指掉在地上，女方父亲站起身。",
                "现场陷入沉默。",
            ],
            4,
        ),
        (
            "crime_chase_recording_police",
            [
                "雨夜里，女主抱着包穿过巷子。",
                "追车灯光逼近，她躲进便利店后门。",
                "录音笔从包里滑出，里面传出嫌疑人的声音。",
                "对方推门进来，女主把录音笔藏到货架后。",
                "警笛响起，店里所有人看向门口。",
            ],
            3,
        ),
        (
            "family_dinner_dna_emergency",
            [
                "家宴上，父亲让乔熙给妹妹道歉。",
                "乔熙没有动筷，只把亲子鉴定报告放到桌中央。",
                "众人看清报告，妹妹脸色变了。",
                "母亲突然倒下，救护车声音从窗外逼近，众人停住。",
                "乔熙扶住母亲，没人再说话。",
            ],
            3,
        ),
        (
            "elevator_necklace_memory",
            [
                "商北琛挡在电梯门口，不让乔熙离开。",
                "乔熙低头避开他的视线。",
                "项链从她衣领里露出，商北琛看清吊坠。",
                "回忆开始：他曾把同一条项链戴到她颈上。",
                "回到现实：商北琛伸手停在半空，乔熙后退半步。",
            ],
            4,
        ),
        (
            "restaurant_misunderstanding_messages",
            [
                "餐厅里，乔熙看到商北琛和陌生女人同桌。",
                "她忍着情绪转身要走。",
                "手机屏幕亮起，一张照片弹出来。",
                "乔熙放大照片，看见女人手里的医院缴费单。",
                "新的短信出现，解释对方只是医生。",
                "乔熙停在门口，回头看向商北琛。",
            ],
            3,
        ),
        (
            "fantasy_key_memory_return",
            [
                "女孩在旧书店里找到一扇锁住的门。",
                "门上的钥匙发光，书页自动翻开。",
                "回忆开始：她小时候曾在这里听见母亲的声音。",
                "母亲把钥匙放进她掌心。",
                "回到现实：门锁打开，楼梯尽头传来脚步声。",
            ],
            4,
        ),
    ]

    for name, lines, expected_count in cases:
        script = "\n".join(lines)
        units = _script_emotional_attention_units(script)
        assert len(units) == expected_count, name
        assert _target_episode_fragment_count(len(lines), script) == expected_count, name


def test_story_planner_handoff_does_not_assign_shot_design():
    instruction = _story_planner_fragment_count_instruction(
        "闹钟响，乔熙抓起外套。\n小豆丁说不想上学。\n乔熙蹲下哄她。"
    )
    system_prompt = spi._rhythm_story_planner_system_prompt()

    assert "情绪曲线" in instruction
    assert "可压缩弱拍" in instruction
    assert "禁止决定镜头数、景别、机位、运镜或切镜方案" in instruction
    assert "不得规定镜头数、景别、机位、运镜或切镜方案" in system_prompt
    assert "建议有效镜头数区间" not in instruction
    assert "建议2-3个有效镜头" not in system_prompt


def test_story_planner_merges_overfragmented_morning_scene_by_attention_problem(monkeypatch):
    monkeypatch.setattr(spi, "_llm_validate_source_events", lambda *args, **kwargs: [])
    script_events = [
        "闹钟响，乔熙一边接电话一边抓起小豆丁的外套。",
        "小豆丁在沙发上乱蹬腿，不肯把手伸进袖子。",
        "乔熙夹着手机催她快点穿衣。",
        "小豆丁低声说：我不想上学。",
        "乔熙停住动作，蹲下哄她说妈妈陪你说清楚。",
        "乔熙拿起书包，照片从夹层里掉出来。",
        "乔熙捡起照片，看清照片背后的日期。",
        "回忆开始：四年前，乔熙站在银杏树下等人。",
        "少年把围巾递给她，两人第一次靠近。",
        "回到现实：乔熙握着照片，听见小豆丁叫她。",
    ]
    fragments: list[str] = []
    for index, event in enumerate(script_events, start=1):
        fragments.extend(
            [
                f"- fragment_id: F{index:02d}",
                f'  片段任务: "tiny beat {index}"',
                '  目标时长: "3-5秒"',
                '  节奏类型: "正常承接"',
                '  事件密度判断: "单个动作或台词。"',
                '  片段内节奏分配: "按当前事件执行。"',
                '  动作节奏指导: "正常承接。"',
                "  施工剧本原文事件:",
                f'    - "{event}"',
                '  出现人物: ["乔熙", "小豆丁"]',
                '  入场状态: "承接上一事件。"',
                '  出场状态: "当前事件结束。"',
                '  承接要求: "留在片段内部。"',
                '  镜头导演交接: "覆盖当前事件。"',
            ]
        )

    normalised = _normalise_story_planner_output("\n".join(fragments), "\n".join(script_events))
    sections = spi._extract_yaml_sections(normalised)

    assert len(sections) == 4
    first_events = "\n".join(spi._source_script_events(sections[0]))
    assert "闹钟响" in first_events
    assert "不想上学" in first_events
    assert "蹲下哄她" in first_events
    assert "照片从夹层里掉出来" in "\n".join(spi._source_script_events(sections[1]))
    assert "回忆开始" in "\n".join(spi._source_script_events(sections[2]))
    assert "回到现实" in "\n".join(spi._source_script_events(sections[3]))


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
  片段任务: "乔熙在闹钟和电话催促下急忙处理小豆丁外套，并压住孩子抗拒。"
  目标时长: "8-12秒"
  节奏类型: "快节奏"
  事件密度判断: "多个短动作连续发生，并带有孩子抗拒的反应落点，属于同一观众注意力问题。"
  片段内节奏分配: "0-4秒：闹钟、电话和够外套动作链急促完成；4-8秒：小豆丁抗拒和乔熙压制落地。"
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
  镜头导演交接: "必须保留乔熙同时处理电话和孩子的忙乱感；可以压缩拿外套和拉拉链弱拍；结尾停在小豆丁扭向沙发靠背。"
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
                "text": "急促短动作应压缩到 2-5秒，带完整抗拒和应对的生活动作群可用 8-12秒完整片段。",
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
    assert "8-12秒" in prompt
    assert "片段内节奏分配" in prompt
    assert "动作节奏指导" in prompt
    assert "禁止输出任何镜头设计字段" in prompt
    assert "story_planner" in result["agent_outputs"]
    assert "rhythm_rewrite_director" in result["agent_outputs"]
    assert "给镜头导演" in result["atmosphere_strategy"]
    assert "0-4秒" in result["atmosphere_strategy"]
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
