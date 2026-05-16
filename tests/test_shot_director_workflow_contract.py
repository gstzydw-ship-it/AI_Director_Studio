from pathlib import Path
import sys

import pytest


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
    _shot_director_blocking_rule_block,
    _shot_director_coverage_contract_prompt,
    _shot_director_downstream_context,
    _shot_director_guard_stage_rule_block,
    _shot_director_rule_block,
    _shot_director_workflow_contract,
    _repair_shot_director_output_contracts,
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
  空间连续性总控: 本片段是一段电梯口压迫；乔熙和商北琛始终在同一电梯口空间内；单人镜只改变拍摄主体，不代表另一人离开；每一镜继承上一镜尾帧的人物位置、道具状态、视线方向和同侧轴线。
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


def test_shot_director_accepts_coverage_v3_template_plan():
    director_output = """- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: elevator two-person pressure
    rhythm_intent: hold reaction after pressure line
    space_contract:
      location: elevator
      characters_present: [Sunny, Nash]
      axis: face-to-face axis
    shot_budget:
      target_count: 2
      max_count: 3
    required_beats:
      - beat_id: B01
        purpose: establish_relation
  template_plan:
    shots:
      - shot_id: F01-S01
        duration: 0-3s
        task: establish close two-person pressure
        subject: Sunny and Nash
        shot: two-person medium relation shot, eye-level fixed view
        action: Sunny looks at Nash after standing steady; Nash holds his position.
        dialogue: ~
        must_carry: distance, facing direction, closed elevator door
        cut_point: cut after the distance relation is readable
        continuity: both remain inside the same closed elevator
        coverage_role: establish_relation
        cut_reason: distance relation becomes readable before reaction
        companion_visibility: both visible in same frame
        state_delta: Sunny is steady
        tailframe_role: hand off to reaction
        template_id: COV-SD20-W1-TWO-SHOT-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: Sunny and Nash remain close, facing each other, elevator door closed.
      - shot_id: F01-S02
        duration: 3-6s
        task: carry Sunny impact reaction
        subject: Sunny
        shot: Sunny chest-up medium close shot, eye-level, from Nash shoulder toward Sunny
        action: Sunny looks up at Nash and briefly freezes.
        dialogue: ~
        must_carry: Sunny reaction after being pressured
        cut_point: cut after reaction appears
        continuity: Nash shoulder remains in foreground; distance unchanged
        coverage_role: impact_reaction
        cut_reason: reaction appears before returning to relation
        companion_visibility: Nash shoulder in foreground
        state_delta: Sunny changes from unsettled to frozen
        tailframe_role: hold post-reaction state
        template_id: COV-SD20-W1-REACTION-HOLD
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: Sunny remains facing Nash; Nash is still close in the same elevator.
  guard_result:
    status: pass
    repairs: []
    final_shots: [F01-S01, F01-S02]
"""

    assert _validate_shot_director_output(director_output, ["F01"]) == []

def test_shot_director_coverage_v3_requires_coverage_fields():
    director_output = """- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: 建立关系
    rhythm_intent: 正常承接
    space_contract:
      location: 电梯内
    shot_budget:
      target_count: 1
    required_beats:
      - establish_relation
  template_plan:
    shots:
      - shot_id: F01-S01
        duration: 0-3秒
        task: 建立关系
        subject: 乔熙和商北琛
        shot: 双人半身关系景，平视，固定视角
        action: 两人面对面站定。
        dialogue: ~
        must_carry: 两人位置关系
        cut_point: 位置关系看清后切出
        continuity: 两人仍在同一电梯内
  guard_result:
    status: pass
    final_shots: [F01-S01]
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("coverage v3 missing field coverage_role" in issue for issue in issues)
    assert any("coverage v3 missing field tailframe_role" in issue for issue in issues)
    assert any("missing Seedance coverage template field template_id" in issue for issue in issues)
    assert any("seedance_template_id_missing" in issue for issue in issues)


def test_shot_director_rejects_overfragmented_life_pressure_segment():
    shot_lines = []
    durations = ["0-2.2秒", "2.2-2.9秒", "2.9-4.9秒", "4.9-6.7秒", "6.7-9.3秒", "9.3-10.1秒", "10.1-12.1秒"]
    for index, duration in enumerate(durations, start=1):
        shot_lines.append(
            f"""    - 镜头编号: F01-S{index:02d}
      时长: {duration}
      镜头任务: 承载清晨赶时间穿衣动作
      拍摄主体: 乔熙、小豆丁
      镜头: 双人半身关系景，茶几侧面固定机位
      画面动作: 乔熙在沙发前帮小豆丁穿衣，小豆丁短暂抗拒后停住。
      台词: ~
      必须承载: 乔熙赶时间，小豆丁抗拒穿衣。
      切镜点: 小豆丁抗拒动作停住后切出
      连续性: 乔熙和小豆丁仍在沙发与茶几之间，手机仍在茶几上。
"""
        )
    director_output = """- 片段编号: F01
  片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
  节奏: 紧凑生活动作压力
  空间连续性总控: 本片段是一段公寓生活压力戏；乔熙和小豆丁始终在沙发与茶几之间。
  镜头列表:
""" + "".join(shot_lines)

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("镜头切分过碎" in issue for issue in issues)
    assert any("1秒以下碎镜" in issue for issue in issues)


def test_shot_director_rules_lock_subject_ownership_and_task_combos():
    combined_rules = "\n".join(
        [
            _shot_director_workflow_contract(),
            _shot_director_rule_block("9:16"),
            sdi._shot_director_layout_rule_block("9:16"),
            _shot_director_blocking_rule_block("9:16"),
            _shot_director_guard_stage_rule_block("9:16"),
        ]
    )

    assert "拍摄主体不是人物/道具清单" in combined_rules
    assert "戏剧任务镜头组合" in combined_rules
    assert "承接上一镜尾帧" in combined_rules


def test_shot_director_rejects_overloaded_random_subject_list():
    director_output = """- 片段编号: F01
  片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
  节奏: 紧凑生活压力
  空间连续性总控: 乔熙和小豆丁始终在公寓客厅沙发边，手机仍在乔熙耳边。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-4秒
      镜头任务: 建立赶时间生活压力
      拍摄主体: 乔熙、小豆丁、闹钟、手机、外套、草莓蛋糕、书包
      镜头: 双人半身关系景，沙发侧面固定机位
      画面动作: 乔熙坐在沙发边给小豆丁套衣服，小豆丁缩脚抗拒，镜尾两人仍在沙发边。
      台词: "Kiki, cover for me. I'll be right there!"
      必须承载: 乔熙赶时间，小豆丁抗拒穿衣。
      切镜点: 小豆丁缩脚动作停住后切出
      连续性: 手机仍在乔熙耳边，小豆丁仍在沙发边。
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("拍摄主体过载" in issue for issue in issues)
    assert any("随机道具集合" in issue or "道具混进主拍摄主体" in issue for issue in issues)


def test_shot_director_rejects_teleport_without_tailframe_carry():
    director_output = """- 片段编号: F01
  片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
  节奏: 紧凑生活压力
  空间连续性总控: 乔熙和小豆丁始终在公寓客厅沙发边，手机仍在乔熙耳边。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-4秒
      镜头任务: 建立母女穿衣阻力
      拍摄主体: 乔熙和小豆丁
      镜头: 双人半身关系景，沙发侧面固定机位
      画面动作: 乔熙坐在沙发边给小豆丁套衣服，小豆丁缩脚抗拒，镜尾两人仍坐在沙发边。
      台词: "Kiki, cover for me. I'll be right there!"
      必须承载: 乔熙赶时间，小豆丁抗拒穿衣。
      切镜点: 小豆丁缩脚动作停住后切出
      连续性: 乔熙和小豆丁仍坐在沙发边，手机仍在乔熙耳边。
    - 镜头编号: F01-S02
      时长: 4-8秒
      镜头任务: 承载穿衣完成和拿书包
      拍摄主体: 乔熙和小豆丁
      镜头: 双人中景，茶几侧面固定机位
      画面动作: 小豆丁突然站在茶几旁，衣服已经穿好。乔熙拿起书包。
      台词: ~
      必须承载: 小豆丁已经配合穿衣，乔熙准备出门。
      切镜点: 乔熙拿起书包后切出
      连续性: 手机在茶几上。
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("缺少承接上一镜尾帧" in issue for issue in issues)


def test_shot_director_repair_adds_fragment_continuity_context():
    director_output = """- 片段编号: F01
  片段任务: 车内命令戴项链
  节奏: 命令压迫后给乔熙反应
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-3秒
      镜头任务: 建立车内双人关系
      拍摄主体: 乔熙、商北琛
      镜头: 竖屏双人中景
      画面动作: 商北琛拿着项链看向乔熙，乔熙坐在旁边承接压力
      台词: ~
      必须承载: 两人同处车内和项链压迫关系
      切镜点: 项链被拿起后切出
      连续性: 乔熙和商北琛仍在同一车内空间，项链仍在商北琛手中
"""
    script = """9-1 夜/内/劳斯莱斯车内
人物：乔熙、商北琛
商北琛：Put the necklace on. And don't embarrass me.
"""

    repaired = _repair_shot_director_output_contracts(director_output, script)

    assert "空间连续性总控:" in repaired
    assert "乔熙、商北琛在9-1 夜/内/劳斯莱斯车内的同一空间内" in repaired
    assert "单人镜只改变拍摄主体" in repaired
    assert _validate_shot_director_output(repaired, ["F01"]) == []


def test_shot_director_rules_keep_camera_and_performance_fields_separate():
    rule_block = _shot_director_rule_block("9:16")
    blocking_rules = _shot_director_blocking_rule_block("9:16")
    guard_rules = _shot_director_guard_stage_rule_block("9:16")

    for text in (rule_block, blocking_rules, guard_rules):
        assert "镜头字段只写" in text
        assert "视角/观看位置" in text
        assert "画面动作" in text

    assert "人物动作表情链" in rule_block
    assert "起始状态 -> 动作变化 -> 表情/身体反应 -> 结束状态" in rule_block
    assert "道具接触戏必须锁定道具归属和动作阶段" in rule_block
    assert "不要在此字段写人物动作" in rule_block
    assert "动作表情必须写进画面动作" in blocking_rules
    assert "不要写戏剧判断、人物动作、台词或表情" in guard_rules
    assert "不要输出“固定机位/侧面机位/摄影机位于”" in guard_rules


def test_shot_director_rejects_untranslated_camera_jargon_in_final_shot_field():
    director_output = """- 片段编号: F01
  片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
  节奏: 紧凑生活压力
  空间连续性总控: 乔熙和小豆丁始终在公寓客厅沙发边，手机仍在乔熙耳边。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-4秒
      镜头任务: 建立赶时间生活压力
      拍摄主体: 乔熙和小豆丁
      镜头: 双人半身关系景，沙发侧面固定机位
      画面动作: 乔熙坐在沙发边给小豆丁套衣服，视线看向门口；小豆丁缩脚抗拒，镜尾两人仍在沙发边。
      台词: "Kiki, cover for me. I'll be right there!"
      必须承载: 乔熙赶时间，小豆丁抗拒穿衣。
      切镜点: 台词落下后小豆丁抗拒反应出现时切出
      连续性: 手机仍在乔熙耳边，小豆丁仍在沙发边。
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("未翻译机位术语" in issue for issue in issues)
    assert any("侧面视角" in issue and "固定视角" in issue for issue in issues)


def test_shot_logic_reviewer_local_issues_flag_camera_action_leak():
    director_output = """- 片段编号: F01
  片段任务: 车内命令戴项链
  节奏: 项链识别反应必须停住
  空间连续性总控: 本片段是一段车内项链压迫；乔熙和商北琛始终在同一车后排空间内；单人镜只改变拍摄主体，不代表另一人离开。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头任务: 承载乔熙识别项链
      拍摄主体: 乔熙
      镜头: 乔熙中近景，她低头看清项链
      画面动作: 乔熙看项链
      台词: ~
      必须承载: 乔熙认出项链
      切镜点: 乔熙看清后切出
      连续性: 项链在画面里
"""
    script = """9-1 夜/内/劳斯莱斯车内
人物：乔熙、商北琛
"""

    issues = sdi._shot_logic_local_issues(director_output, script)

    assert any("镜头字段混入人物动作" in issue for issue in issues)
    assert any("画面动作缺少动作表情链" in issue for issue in issues)
    assert any("单人镜缺少同场人物保留" in issue for issue in issues)


def test_shot_logic_reviewer_local_issues_flag_action_overload_for_prompt_compiler():
    director_output = """- 片段编号: F01
  片段任务: 沙发边安抚孩子
  节奏: 先压迫再安抚
  空间连续性总控: 乔熙和小豆丁始终在沙发边，手机仍在乔熙耳边。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-4秒
      镜头任务: 承载乔熙靠近并试图控制局面
      拍摄主体: 乔熙与小豆丁
      镜头: 中近景，沙发边同侧机位
      画面动作: 乔熙仍用右手拿着手机贴在耳边说话，同时顺着沙发边伸手牵住小豆丁，身体压近沙发边想把外套套到孩子身上；小豆丁先缩脚躲开，又配合穿衣完成。
      台词: ~
      必须承载: 手机仍在乔熙手里，小豆丁还在抗拒。
      切镜点: 小豆丁缩脚后切出
      连续性: 两人仍在沙发边，衣服尚未穿好。
"""

    issues = sdi._shot_logic_local_issues(director_output, "乔熙：Kiki, cover for me.\n小豆丁：不要。")

    assert any("画面动作过载或肢体占用不清" in issue for issue in issues)
    assert any("人物从抗拒到配合缺少过渡" in issue for issue in issues)
    assert any("1-2 句自然短动作" in issue for issue in issues)


def test_shot_logic_reviewer_accepts_safe_repair(monkeypatch):
    primary_output = """- 片段编号: F01
  片段任务: 车内命令戴项链
  节奏: 项链靠近后乔熙识别
  空间连续性总控: 本片段是一段车内项链压迫；乔熙和商北琛始终在同一车后排空间内；单人镜只改变拍摄主体，不代表另一人离开。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头任务: 承载乔熙识别项链
      拍摄主体: 乔熙
      镜头: 乔熙中近景，她低头看清项链
      画面动作: 乔熙看项链
      台词: ~
      必须承载: 乔熙认出项链
      切镜点: 乔熙看清后切出
      连续性: 项链在画面里
"""
    repaired_output = """- 片段编号: F01
  片段任务: 车内命令戴项链
  节奏: 项链靠近后乔熙识别
  空间连续性总控: 本片段是一段车内项链压迫；乔熙和商北琛始终在同一车后排空间内；单人镜只改变拍摄主体，不代表另一人离开。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头任务: 承载乔熙识别项链
      拍摄主体: 乔熙
      镜头: 乔熙中近景，车内同侧微侧视角
      画面动作: 乔熙原本身体后收，视线先落到商北琛手中的项链，随后低头看清吊坠，眼神短暂停住，肩颈保持绷紧。
      台词: ~
      必须承载: 乔熙认出项链，商北琛仍在近侧形成压力，项链仍未戴上。
      切镜点: 乔熙看清项链后眼神停住时切出
      连续性: 商北琛仍在乔熙近侧，项链仍在商北琛手中，乔熙坐在原位没有离开。
"""

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        assert "镜头逻辑裁判" in system_prompt
        assert "单片段内部逻辑" in user_prompt
        assert kwargs["agent_name"] == "shot_director_logic_reviewer"
        return f"""审查结论: 需要返修
裁判摘要: 镜头字段混入人物动作，已做最小修复。
单片段审查:
  - 片段编号: F01
    通过: false
    问题:
      - 镜头字段混入动作。
硬错误: []
修复后镜头方案:
{repaired_output}
"""

    monkeypatch.setattr(sdi, "call_llm", fake_call_llm)

    output, runtime, report = sdi._run_shot_director_review_board(
        script="9-1 夜/内/劳斯莱斯车内\n人物：乔熙、商北琛",
        planner_output="",
        director_brief="",
        primary_output=primary_output,
    )

    assert runtime["agent_name"] == "shot_director_logic_reviewer"
    assert runtime["status"] == "repaired_by_logic_reviewer"
    assert "乔熙中近景，车内同侧微侧视角" in output
    assert "她低头看清项链" not in sdi._yaml_line_field(output, "shot")
    assert "裁判修复采纳: 是" in report


def test_shot_logic_reviewer_reports_connection_failure(monkeypatch):
    primary_output = """- 片段编号: F01
  片段任务: 车内命令戴项链
  节奏: 项链靠近后乔熙识别
  空间连续性总控: 本片段是一段车内项链压迫；乔熙和商北琛始终在同一车后排空间内；单人镜只改变拍摄主体，不代表另一人离开。
  镜头列表:
    - 镜头编号: F01-S01
      时长: 0-2秒
      镜头任务: 承载乔熙识别项链
      拍摄主体: 乔熙
      镜头: 乔熙中近景，她低头看清项链
      画面动作: 乔熙看项链
      台词: ~
      必须承载: 乔熙认出项链
      切镜点: 乔熙看清后切出
      连续性: 项链在画面里
"""

    def fake_call_llm(*args, **kwargs):
        raise RuntimeError("离线")

    monkeypatch.setattr(sdi, "call_llm", fake_call_llm)

    with pytest.raises(RuntimeError, match="镜头逻辑审查大模型连接不成功"):
        sdi._run_shot_director_review_board(
            script="9-1 夜/内/劳斯莱斯车内\n人物：乔熙、商北琛",
            planner_output="",
            director_brief="",
            primary_output=primary_output,
        )


def test_shot_director_workflow_trace_summarises_planner_fragments():
    planner_output = """- fragment_id: F01
  duration_target: "8s"
  dramatic_unit: "Photo reveal"
  source_script_events:
    - "Qiao Xi picks up the photo."
    - "Xiaodouding says she wants him to be daddy."
  reaction_plan: "Hold Qiao Xi reaction before flashback."
  shot_director_handoff: "Reveal the photo fully before the flashback handoff."
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
    assert trace["fragments"][0]["fragment_task"] == "Photo reveal"
    assert trace["fragments"][0]["duration_target"] == "8s"
    assert "flashback handoff" in trace["fragments"][0]["shot_director_handoff"]
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
  片段内节奏分配: "0-3秒：照片滑落；3-8秒：乔熙看清照片并完成反应。"
  镜头导演交接: "照片滑落必须拍完整，反应留在本段尾部，结尾停在乔熙看到照片。"
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
    assert trace["fragments"][0]["duration_target"] == "8-10秒"
    assert "反应留在本段尾部" in trace["fragments"][0]["reaction_plan"]
    assert "照片滑落" in trace["fragments"][0]["intra_fragment_rhythm"]
    assert "照片滑落必须拍完整" in trace["fragments"][0]["shot_director_handoff"]
    assert trace["fragments"][0]["source_event_count"] == 2
    assert "目标时长: 8-10秒" in context
    assert "片段内节奏分配: 0-3秒" in context
    assert "承接要求: 反应留在本段尾部" in context
    assert "镜头导演交接: 照片滑落必须拍完整" in context
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


def test_split_fragment_mode_can_pass_scene_reference_images_when_explicit(monkeypatch):
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


def test_shot_director_stages_do_not_upload_scene_reference_images():
    assert sdi._shot_director_stage_images("shot_director_layout", ["layout-a"]) is None
    assert sdi._shot_director_stage_images("shot_director_blocking", ["layout-a"]) is None
    assert sdi._shot_director_stage_images("shot_director_guard", ["layout-a"]) is None


def test_segment_shot_director_uses_text_scene_references_without_uploading_images(monkeypatch):
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

    monkeypatch.setattr(sdi, "_run_shot_director_three_stage", fake_three_stage)
    monkeypatch.setattr(sdi, "_persist_update", lambda state, update: {**state, **update})
    monkeypatch.setattr(sdi, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(sdi, "_hard_shot_director_issues", lambda issues: [])
    monkeypatch.setattr(
        sdi,
        "_run_shot_director_review_board",
        lambda **kwargs: (
            kwargs["primary_output"],
            {"agent_name": "shot_director_logic_reviewer", "status": "accepted_primary"},
            "review-ok",
        ),
    )

    result = sdi.run_shot_director_for_segment(
        {
            "script": "乔熙走到电梯门口。",
            "aspect_ratio": "9:16",
            "scene_context_brief": "空间约束：电梯门在画面右侧，走廊不能新增前台。",
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
        },
        1,
        force=True,
    )

    assert "shot_director_review_fragment_F01" in result["agent_outputs"]
    assert "shot_director_guard_fragment_F01" in result["agent_outputs"]
    assert captured["images_base64"] is None
    assert "场景分析师给镜头导演的空间约束" in str(captured["scene_reference_context"])
    assert "走廊不能新增前台" in str(captured["scene_reference_context"])
    assert "用户标注后的俯视图" in str(captured["scene_reference_context"])
    assert "乔熙(0.30,0.50)" in str(captured["scene_reference_context"])
    assert result["agent_outputs"]["shot_director"].startswith("- 片段编号: F01")