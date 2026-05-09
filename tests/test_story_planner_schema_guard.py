from __future__ import annotations

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from agents.director_graph_package import story_planner_impl as spi  # noqa: E402
from agents.director_graph_package.story_planner_impl import (  # noqa: E402
    _extract_segments,
    _extract_yaml_sections,
    _normalise_story_planner_output,
    _parse_story_planner_agent_validation,
    _run_story_planner_with_schema_repair,
    _story_planner_fragment_granularity_issues,
    _story_planner_granularity_rules,
    _story_planner_soft_validation_issues,
    _story_planner_rhythm_boundary_rules,
    _story_planner_target_fragment_range,
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
        rhythm_guidance="卡断留在 F01 尾帧，普通受击反应留在片段内部。",
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


def test_story_planner_target_range_prefers_medium_granularity():
    assert _story_planner_target_fragment_range(12) == (2, 3)
    assert _story_planner_target_fragment_range(36) == (5, 9)
    assert _story_planner_target_fragment_range(71) == (9, 18)


def test_story_planner_rejects_overfragmented_medium_script():
    events = [f"Event {i}." for i in range(1, 76)]
    fragments: list[str] = []
    for index in range(25):
        fragment_events = events[index * 3 : (index + 1) * 3]
        fragments.extend(
            [
                f"- fragment_id: F{index + 1:02d}",
                '  duration_target: "8-10s"',
                f'  dramatic_unit: "Beat {index + 1}"',
                "  source_script_events:",
                *[f'    - "{event}"' for event in fragment_events],
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

    assert any("全局拆片过细" in issue for issue in hard_issues)
    assert granularity_issues


def test_story_planner_granularity_rules_state_merge_policy():
    rules = _story_planner_granularity_rules()

    assert "15 秒以内" in rules
    assert "4-8 条" in rules
    assert "普通停顿、受击反应、信息揭示默认留在当前片段内部" in rules
    assert "明确钩子、卡断、尾帧承接" in rules


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


def test_story_planner_prompt_uses_current_script_and_upstream_contracts(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        spi,
        "build_system_prompt",
        lambda prompt, agent_name, context_hint="": (prompt, {"retrieval_mode": "test"}),
    )
    monkeypatch.setattr(spi, "_record_knowledge_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr(spi, "_validate_story_planner_output", lambda *args, **kwargs: [])
    monkeypatch.setattr(spi, "_persist_update", lambda state, payload: {**state, **payload})

    def fake_run_story_planner(**kwargs):
        captured["user_prompt"] = kwargs["user_prompt"]
        captured["rhythm_guidance"] = kwargs["rhythm_guidance"]
        return LIGHTWEIGHT_YAML, [{"status": "success"}]

    monkeypatch.setattr(spi, "_run_story_planner_with_schema_repair", fake_run_story_planner)

    result = spi.story_planner_node(
        {
            "script": "增强后施工剧本：乔熙拿起书包，照片滑落。",
            "director_brief": "主线保护: 不改变人物关系\n节奏总控交接: 照片滑落后必须刹车。",
            "atmosphere_strategy": "拆片边界建议: 照片滑落后不拆；尾帧承接: 乔熙低头停住。",
            "agent_outputs": {"scene_analyst": "道具锚点: 书包在乔熙手边。"},
            "aspect_ratio": "9:16",
        }
    )

    prompt = str(captured["user_prompt"])
    assert "【当前施工剧本】" in prompt
    assert "增强后施工剧本" in prompt
    assert "节奏总控施工指令" in prompt
    assert "施工剧本原文事件" in prompt
    assert "剧情增强导演契约" not in prompt
    assert "场景空间记忆卡" not in prompt
    assert "按原始剧本" not in prompt
    assert captured["rhythm_guidance"] == result["atmosphere_strategy"]
