from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph_package.shot_director_impl import (  # noqa: E402
    _build_shot_director_signal_retrieval_profile,
    _build_shot_director_workflow_trace,
    _call_stage_split_by_fragment,
    _extract_rhythm_shot_director_notes,
    _planner_source_event_context,
    _reference_image_manifest_prompt,
    _reference_images,
    _scene_reference_items,
    _rhythm_shot_director_notes_prompt,
    _shot_library_signal_task_card,
    _shot_director_coverage_contract_prompt,
    _shot_director_downstream_context,
    _shot_director_workflow_contract,
    _validate_shot_director_output,
    _validate_shot_director_variety,
)
from agents.director_graph_package import shot_director_impl as sdi  # noqa: E402


def test_shot_director_explicit_workflow_contract_is_present():
    contract = _shot_director_workflow_contract()
    coverage_contract = _shot_director_coverage_contract_prompt()

    for stage_name in (
        "事实提取",
        "节奏意图读取",
        "剪辑策略判断",
        "戏剧任务判断",
        "镜头骨架",
        "镜头语言变化",
        "动作与子镜头",
        "切镜时机",
        "冲突裁决",
        "最小修复",
        "最终交付",
    ):
        assert stage_name in contract

    for field_name in (
        "覆盖职责",
        "切镜原因",
        "同场人物位置",
        "状态变化",
        "尾帧职责",
    ):
        assert field_name in contract
        assert field_name in coverage_contract


def test_shot_director_accepts_all_chinese_output_fields():
    director_output = """- 片段编号: F01
  片段任务: 电梯口压迫
  节奏: 前压后停
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头任务: 建立关系
      拍摄主体: 乔熙和商北琛
      镜头: 侧面视角双人中景
      画面动作: 乔熙停在电梯口，商北琛挡住去路
      台词: ~
      必须承载: 两人的空间距离和压迫关系
      切镜点: 电梯门停在半开状态时切出
      连续性: 乔熙在画面右侧，商北琛在画面左侧，电梯门仍半开
"""

    assert _validate_shot_director_output(director_output, ["F01"]) == []


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

    assert trace["mode"] == "three_stage_fused_pipeline"
    assert trace["stages"] == [
        "layout_task_space",
        "blocking_language_action",
        "guard_final_handoff",
    ]
    assert trace["stage_contracts"]["layout_task_space"].startswith("摆位导演")
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
    assert "出场人物: 乔熙" in context
    assert "出场连续性: 照片滑落到地面" in context


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
    assert "[Atmosphere Excerpt]" not in context
    assert "结构规划施工指令" not in context


def test_shot_director_builds_signal_based_shot_library_tasks():
    planner_output = """- 片段编号: F01
  施工剧本原文事件:
    - "乔熙冲进电梯，撞到商北琛。"
    - "商北琛命令她停下，乔熙不敢立刻回答。"
    - "照片从书包里滑落，乔熙看清照片内容。"
  出场状态: "电梯门继续合拢，乔熙盯着照片停住。"
"""
    atmosphere_strategy = "镜头导演节奏执行约束: 命令句后给听者反应；碰撞后先给乔熙受击反应，照片看清后再切，尾帧用照片承接。"

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="保护照片揭示，不要把碰撞拍成暧昧。",
        aspect_ratio="9:16",
    )

    assert "[镜头库调用任务单]" in card
    assert "impact_reaction" in card
    assert "long_dialogue_coverage" in card
    assert "reveal_insert_reaction" in card
    assert "door_threshold_continuity" in card
    assert "tailframe_handoff" in card
    assert "调用受击/碰撞镜头库" in card
    assert "调用对白覆盖镜头库" in card
    assert "不得一个固定机位吃完整长台词" in card
    assert "必须至少安排一次说话者外的画面承载台词后半句" in card
    assert "调用信息揭示镜头库" in card
    assert "必须检索的知识" in card
    assert "ACTION-COLLISION-001" in card
    assert "SHOT-DIALOGUE-COVERAGE-001" in card
    assert "22_多机位分镜与镜头多样性规则 反站桩正反打 过肩 反应特写" in card
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
    assert "editing_ellipsis" in profile["signals"]
    assert "shot_variety" in profile["signals"]
    assert "rhythm_alignment" in profile["signals"]
    assert "long_dialogue_coverage" in profile["reusable_pattern"]
    assert "SHOT-DIALOGUE-COVERAGE-001" in profile["reusable_pattern"]
    assert "22_多机位分镜与镜头多样性规则 反站桩正反打 过肩 反应特写" in profile["reusable_pattern"]
    assert "多机位模板" in profile["tags"]
    assert "镜头多样性" in profile["tags"]
    assert "机位切换减法" in profile["tags"]
    assert "剪辑省略" in profile["tags"]
    assert "节奏联动" in profile["tags"]
    assert "故事节奏控制" in profile["tags"]
    assert "上游导演约束" in profile["tags"]
    assert "CASE_拍摄剪辑_切出镜头_访谈对话与情感片段技巧" in profile["tags"]
    assert "必须把检索到的剪辑/镜头库规则转成镜头、切镜点、连续性、声音，不得只写原则" in profile["visual_constraints"]
    assert "必须优先使用本片段剧情信号匹配到的 CASE 案例和规则卡" in profile["visual_constraints"]
    assert profile["max_chunks_per_source"] == 2


def test_shot_director_variety_guard_flags_repeated_shot_language():
    output = """- 片段编号: F01
  片段任务: 长对白压迫
  节奏: 压迫递进
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头: 正面中景
      台词: "你解释。"
    - 镜头编号: F01-S02
      时长: 2-4秒
      镜头: 正面中景
      台词: ~
    - 镜头编号: F01-S03
      时长: 4-6秒
      镜头: 正面中景
      台词: ~
"""

    issues = _validate_shot_director_variety(output)

    assert issues
    assert "连续使用同一种镜头语言" in issues[0] or "连续三个镜头重复" in issues[0]


def test_shot_director_variety_guard_allows_explicit_rhythm_exception():
    output = """- 片段编号: F01
  片段任务: 压住沉默
  节奏: 节奏总控要求固定机位压住不切
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头: 正面中景
    - 镜头编号: F01-S02
      时长: 2-4秒
      镜头: 正面中景
    - 镜头编号: F01-S03
      时长: 4-6秒
      镜头: 正面中景
"""

    assert _validate_shot_director_variety(output) == []


def test_shot_library_signal_task_card_keeps_rhythm_as_constraints_without_overriding_boundaries():
    planner_output = """- 片段编号: F01
  施工剧本原文事件:
    - "乔熙冲进电梯，撞到商北琛。"
  出场状态: "乔熙站在电梯门内侧，商北琛挡住门口。"
- 片段编号: F02
  施工剧本原文事件:
    - "乔熙看清照片内容，愣在原地。"
  出场状态: "照片留在乔熙手里，视线承接到下一段。"
"""
    atmosphere_strategy = """节奏总合同: F01 碰撞后短暂停顿，F02 照片揭示降速。
镜头导演节奏执行约束: F01 只压住受击反应；F02 必须照片读清后再切，不能把照片提前塞回 F01。
拆片边界建议: 保持 F01/F02 边界，镜头只做节奏施工。
"""

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="严格按拆片边界执行，不新增剧本外动作。",
        aspect_ratio="9:16",
    )

    assert "节奏总控约束:" in card
    assert "先读上游导演资产" in card
    assert "不能扩写新剧情" in card
    assert "- 片段编号: F01" in card
    assert "- 片段编号: F02" in card
    assert "乔熙冲进电梯，撞到商北琛" in card
    assert "乔熙看清照片内容，愣在原地" in card
    assert card.index("- 片段编号: F01") < card.index("- 片段编号: F02")
    assert "F02 必须照片读清后再切" in card
    assert card.count("- 片段编号:") == 2


def test_shot_library_signal_task_card_asserts_long_dialogue_and_repeated_camera_rules():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "商北琛用一整段高压命令质问乔熙。"
    - "乔熙沉默回避，电梯门继续合拢。"
"""
    atmosphere_strategy = "镜头导演节奏执行约束: 长对白内部必须切给听者反应，避免同一正反打机位重复吃完整句。"

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="对白压迫感递进，但不要机械重复固定机位。",
        aspect_ratio="9:16",
    )

    assert "long_dialogue_coverage" in card
    assert "authority_pressure" in card
    assert "调用对白覆盖镜头库" in card
    assert "同侧听者反应/过肩" in card
    assert "不得一个固定机位吃完整长台词" in card
    assert "cut_point 写明台词断点或压迫落点" in card
    assert "调用权力压迫镜头库" in card
    assert "不得全程均速正反打" in card


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


def test_shot_director_does_not_upload_raw_reference_images_without_scene_manifest():
    state = {"reference_image_b64s": ["scene-a", "person-a"]}

    assert _reference_images(state) == []


def test_shot_director_uploads_only_scene_layout_references():
    state = {
        "reference_image_b64s": ["person-a", "layout-a", "grid-a", "annotated-a", "raw-scene-a"],
        "reference_image_manifest": [
            {"label": "@图片1", "role": "character", "purpose": "主角人物"},
            {"label": "@图片2", "role": "scene_layout", "purpose": "电梯口场景俯视布局图，含人物位置和移动轨迹"},
            {"label": "@图片3", "type": "scene_card", "purpose": "场景九宫格机位图"},
            {"label": "@图片4", "role": "annotated_scene_layout", "purpose": "用户标注后的俯视图"},
            {"label": "@图片5", "asset_type": "scene", "purpose": "原始场景参考图"},
        ],
        "scene_layout_annotations": [{"scene_number": "1", "summary": "人物标点: 乔熙(0.30,0.50)"}],
    }

    assert _reference_images(state) == ["layout-a", "grid-a", "annotated-a"]
    assert [item["label"] for _image, item in _scene_reference_items(state)] == ["@图片2", "@图片3", "@图片4"]

    prompt = _reference_image_manifest_prompt(state)
    assert "[Scene Layout Reference Images]" in prompt
    assert "@图片2" in prompt
    assert "移动轨迹" in prompt
    assert "@图片3" in prompt
    assert "@图片4" in prompt
    assert "乔熙(0.30,0.50)" in prompt
    assert "主角人物" not in prompt
    assert "原始场景参考图" not in prompt


def test_shot_director_merges_completed_background_scene_cards(monkeypatch):
    monkeypatch.setenv("AIDIRECTOR_SCENE_CARD_WAIT_SECONDS", "0")
    monkeypatch.setattr(
        sdi,
        "load_state",
        lambda: {
            "scene_card_status": "done",
            "reference_image_b64s": ["layout-a"],
            "reference_image_manifest": [
                {"role": "scene_layout", "purpose": "generated scene layout"},
            ],
            "agent_outputs": {"scene_card_status": "done"},
        },
    )

    merged = sdi._await_scene_card_generation(
        {
            "scene_card_status": "running",
            "reference_image_b64s": ["raw-scene"],
            "reference_image_manifest": [{"purpose": "raw scene reference"}],
            "agent_outputs": {"scene_card_status": "running"},
        }
    )

    assert _reference_images(merged) == ["layout-a"]
    assert merged["scene_card_status"] == "done"


def test_split_fragment_mode_passes_scene_reference_images(monkeypatch):
    captured_images: list[list[str] | None] = []

    def fake_call_llm(**kwargs):
        captured_images.append(kwargs.get("images_base64"))
        return "- 片段编号: F01\n  片段任务: 建立空间\n  镜头列表: []\n"

    monkeypatch.setattr(sdi, "call_llm", fake_call_llm)

    output, runtime = _call_stage_split_by_fragment(
        stage_key="shot_director",
        system_prompt="system",
        expected_segments=["F01"],
        planner_output="- fragment_id: F01\n  source_script_events:\n    - A enters.\n",
        aspect_ratio="9:16",
        contract_output="",
        prompt_builder=lambda _fid, context, _contract: context,
        images_base64=["layout-a"],
    )

    assert "片段编号: F01" in output
    assert runtime["mode"] == "split_by_fragment"
    assert captured_images == [["layout-a"]]


def test_shot_director_node_forwards_filtered_scene_references(monkeypatch):
    captured: dict[str, object] = {}

    def fake_three_stage(**kwargs):
        captured["images_base64"] = kwargs.get("images_base64")
        captured["scene_reference_context"] = kwargs.get("scene_reference_context")
        return (
            "- 片段编号: F01\n  片段任务: 建立空间\n  镜头列表: []\n",
            {"elapsed_seconds": 0.1},
            {"final": {"retrieval_mode": "stub"}},
            {"final": "- 片段编号: F01\n  片段任务: 建立空间\n  镜头列表: []\n"},
        )

    def fake_review_board(**kwargs):
        captured["review_images_base64"] = kwargs.get("images_base64")
        return kwargs["primary_output"], {"status": "accepted_primary"}, "accepted"

    monkeypatch.setattr(sdi, "_run_shot_director_three_stage", fake_three_stage)
    monkeypatch.setattr(sdi, "_run_shot_director_review_board", fake_review_board)
    monkeypatch.setattr(sdi, "_persist_update", lambda state, update: {**state, **update})
    monkeypatch.setattr(sdi, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(sdi, "_hard_shot_director_issues", lambda issues: [])

    result = sdi.shot_director_node(
        {
            "script": "乔熙走到电梯门口。",
            "aspect_ratio": "9:16",
            "agent_outputs": {"story_planner": "- fragment_id: F01\n  source_script_events:\n    - 乔熙走到电梯门口。\n"},
            "reference_image_b64s": ["person-a", "layout-a", "annotated-a", "prop-a"],
            "reference_image_manifest": [
                {"role": "character", "purpose": "主角人物"},
                {"role": "scene_layout", "purpose": "电梯口俯视布局图"},
                {"role": "annotated_scene_layout", "purpose": "用户标注后的俯视图"},
                {"role": "prop", "purpose": "道具"},
            ],
            "scene_layout_annotations": [{"scene_number": "1", "summary": "人物标点: 乔熙(0.30,0.50)"}],
            "knowledge_metadata": {},
            "segment_names": ["F01"],
            "total_segments": 1,
        }
    )

    assert captured["images_base64"] == ["layout-a", "annotated-a"]
    assert captured["review_images_base64"] == ["layout-a", "annotated-a"]
    assert "用户标注后的俯视图" in str(captured["scene_reference_context"])
    assert "乔熙(0.30,0.50)" in str(captured["scene_reference_context"])
    assert result["agent_outputs"]["shot_director"].startswith("- 片段编号: F01")
