from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph_package.shot_director_impl import (  # noqa: E402
    _build_shot_director_signal_retrieval_profile,
    _build_shot_director_workflow_trace,
    _extract_rhythm_shot_director_notes,
    _planner_source_event_context,
    _reference_images,
    _rhythm_shot_director_notes_prompt,
    _shot_library_signal_task_card,
    _shot_director_coverage_contract_prompt,
    _shot_director_downstream_context,
    _shot_director_workflow_contract,
)


def test_shot_director_explicit_workflow_contract_is_present():
    contract = _shot_director_workflow_contract()
    coverage_contract = _shot_director_coverage_contract_prompt()

    for stage_name in (
        "fact_extraction",
        "dramatic_task_mapping",
        "layout_blueprint",
        "blocking_and_subshots",
        "cut_timing",
        "guard_minimal_repair",
        "final_yaml_handoff",
    ):
        assert stage_name in contract

    for field_name in (
        "coverage_role",
        "cut_reason",
        "companion_visibility",
        "state_delta",
        "tailframe_role",
    ):
        assert field_name in contract
        assert field_name in coverage_contract


def test_shot_director_workflow_trace_summarises_planner_fragments():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "Qiao Xi picks up the photo."
    - "Xiaodouding says she wants him to be daddy."
  reaction_plan: "Hold Qiao Xi reaction before flashback."
  director_brief: "Protect the photo reveal and emotional recoil."
- fragment_id: F02
  source_script_events:
    - "Flashback begins under the ginkgo tree."
"""

    trace = _build_shot_director_workflow_trace(
        planner_output=planner_output,
        expected_segments=["F01", "F02"],
        atmosphere_strategy="slow down before the reveal",
        director_brief="use the photo as the handoff anchor",
        aspect_ratio="9:16",
    )

    assert trace["mode"] == "explicit_internal_pipeline"
    assert trace["stages"][0] == "fact_extraction"
    assert trace["coverage_contract_fields"] == [
        "coverage_role",
        "cut_reason",
        "companion_visibility",
        "state_delta",
        "tailframe_role",
    ]
    assert trace["fragments"][0]["fragment_id"] == "F01"
    assert trace["fragments"][0]["source_event_count"] == 2
    assert "photo" in trace["fragments"][0]["source_event_preview"][0]


def test_shot_director_reads_chinese_story_planner_handoff():
    planner_output = """- 片段编号: F01
  目标时长: "8-10秒"
  施工剧本原文事件:
    - "乔熙拿起书包。"
    - "照片从书包里滑落。"
  出现人物:
    - "乔熙"
  入场状态: "乔熙手边有书包，照片仍在书包内。"
  出场状态: "照片滑落到地面，乔熙看到照片。"
  承接要求: "反应留在本段尾部。"
"""

    trace = _build_shot_director_workflow_trace(
        planner_output=planner_output,
        expected_segments=["片段01"],
        atmosphere_strategy="",
        director_brief="",
        aspect_ratio="9:16",
    )
    context = _shot_director_downstream_context(planner_output, "", "9:16")

    assert trace["fragments"][0]["fragment_id"] == "F01"
    assert trace["fragments"][0]["source_event_count"] == 2
    assert "乔熙拿起书包" in context
    assert "active_cast: 乔熙" in context
    assert "continuity_exit: 照片滑落到地面" in context


def test_rhythm_shot_director_notes_are_extracted_for_handoff():
    atmosphere_strategy = """节奏总合同: 照片揭示要降速。
结构规划施工指令: 照片揭示留在同一片段内。
镜头导演节奏执行约束: 乔熙进入闪回前必须先完成受击反应。
  - 切点落在照片内容被读清之后，不落在随机动作上。
  - 尾帧必须用照片承接到闪回。
风险提醒: 不要新增解释台词。
"""

    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    prompt = _rhythm_shot_director_notes_prompt(atmosphere_strategy)

    assert "乔熙进入闪回前必须先完成受击反应" in notes
    assert "切点落在照片内容被读清之后" in notes
    assert "节奏总控给镜头导演的执行约束" in prompt
    assert "尾帧" in prompt


def test_shot_director_downstream_context_includes_rhythm_shot_notes():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "Qiao Xi sees the photo."
"""
    atmosphere_strategy = """节奏总合同: 照片揭示要降速。
镜头导演节奏执行约束: 反应归乔熙；照片读清后再切。
结构规划施工指令: 闪回前不拆。
"""

    context = _shot_director_downstream_context(planner_output, atmosphere_strategy, "9:16")

    assert "[节奏总控给镜头导演的执行约束]" in context
    assert "反应归乔熙" in context
    assert "[Atmosphere Excerpt]" in context


def test_shot_director_builds_signal_based_shot_library_tasks():
    planner_output = """- 片段编号: F01
  施工剧本原文事件:
    - "乔熙冲进电梯，撞到商北琛。"
    - "照片从书包里滑落，乔熙看清照片内容。"
  出场状态: "电梯门继续合拢，乔熙盯着照片停住。"
"""
    atmosphere_strategy = "镜头导演节奏执行约束: 碰撞后先给乔熙受击反应，照片看清后再切，尾帧用照片承接。"

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="保护照片揭示，不要把碰撞拍成暧昧。",
        aspect_ratio="9:16",
    )

    assert "[镜头库调用任务单]" in card
    assert "impact_reaction" in card
    assert "reveal_insert_reaction" in card
    assert "door_threshold_continuity" in card
    assert "tailframe_handoff" in card
    assert "调用受击/碰撞镜头库" in card
    assert "调用信息揭示镜头库" in card
    assert "must_retrieve_knowledge" in card
    assert "ACTION-COLLISION-001" in card
    assert "CASE_拍摄剪辑_用反拍剪辑叙事的镜头拆解" in card
    assert "强制落地" in card


def test_shot_director_signal_profile_routes_knowledge_retrieval():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "乔熙冲进电梯，撞到商北琛。"
    - "商北琛命令她停下，乔熙看清照片。"
"""

    profile = _build_shot_director_signal_retrieval_profile(
        planner_output=planner_output,
        atmosphere_strategy="镜头导演节奏执行约束: 长对白需要听者反应，尾帧停在照片。",
        director_brief="压住碰撞浪漫化风险，保持电梯空间连续。",
        aspect_ratio="9:16",
    )

    assert "elevator" in profile["scene_types"]
    assert "collision" in profile["events"]
    assert "dialogue" in profile["events"]
    assert "romanticize_collision" in profile["risks"]
    assert "dialogue_integrity" in profile["risks"]
    assert "shot_library_routing" in profile["signals"]
    assert "long_dialogue_coverage" in profile["reusable_pattern"]
    assert "SHOT-DIALOGUE-COVERAGE-001" in profile["reusable_pattern"]
    assert "CASE_拍摄剪辑_切出镜头_访谈对话与情感片段技巧" in profile["tags"]
    assert "必须优先使用本片段剧情信号匹配到的 CASE 案例和规则卡" in profile["visual_constraints"]
    assert profile["max_chunks_per_source"] == 2


def test_legacy_rhythm_shot_director_notes_are_still_extracted():
    atmosphere_strategy = """rhythm_diagnosis: reveal is too fast.
shot_director_notes: reaction belongs to Qiao Xi; cut after the photo is readable.
construction_notes: no split before the flashback.
"""

    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)

    assert "reaction belongs to Qiao Xi" in notes


def test_planner_source_event_context_keeps_only_selected_fragments():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "Qiao Xi reads the photo."
  director_brief: "Protect the photo reveal."
- fragment_id: F02
  source_script_events:
    - "Flashback begins under the ginkgo tree."
"""

    context = _planner_source_event_context(planner_output, ["F02"])

    assert "F02 source_script_events" in context
    assert "Flashback begins" in context
    assert "Qiao Xi reads the photo" not in context


def test_shot_director_does_not_upload_raw_reference_images():
    state = {"reference_image_b64s": ["scene-a", "person-a"]}

    assert _reference_images(state) == []
