from __future__ import annotations

from agents.director_graph_package import rhythm_rewrite_impl as rri
from agents.director_graph_package import shot_director_impl as sdi
from agents.director_graph_package import storyboard_designer_impl as sbi
from agents.director_graph_package.prompt_compiler_impl import _compiler_guard_report
from agents.director_graph_package.seedance_contracts import (
    NO_TEXT_HARD_CONSTRAINT,
    prompt_contract_issues,
    rhythm_operation_sheet_issues,
)


def _coverage_v3(shot: str) -> str:
    return f"""- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: morning pressure
    rhythm_intent: compressed action then reaction hold
    space_contract:
      location: apartment living room
    shot_budget:
      target_count: 1
      max_count: 3
    required_beats:
      - inherited_tail_state
  template_plan:
    shots:
{shot}
  guard_result:
    status: pass
    final_shots: [F01-S01]
    repairs: []
"""


def test_rhythm_operation_sheet_fallback_has_required_fields_and_no_camera_language() -> None:
    sheet = rri._fallback_rhythm_operation_sheet({}, ["missing"])

    assert rhythm_operation_sheet_issues(sheet) == []
    assert "beat_plan" in sheet
    assert "reaction_ownership" in sheet
    assert "tail_state_required" in sheet
    assert "shot_budget_hint" in sheet
    assert NO_TEXT_HARD_CONSTRAINT in sheet


def test_shot_director_rejects_abstract_viewpoints_and_accepts_w1_relation_reaction_prop() -> None:
    bad = _coverage_v3("""      - shot_id: F01-S01
        duration: 0-4秒
        coverage_role: relation
        task: hold relation
        subject: 乔熙和小豆丁
        shot: 沙发与地毯之间的关系视角
        action: 乔熙停住，小豆丁看向照片。
        dialogue: none
        must_carry: reaction and photo state
        cut_reason: reaction appears after photo lands
        cut_point: reaction appears
        continuity: both stay beside the sofa
        companion_visibility: both visible
        state_delta: photo noticed
        tailframe_role: carry both characters
        template_id: COV-SD20-W1-TWO-SHOT-PRESSURE
        template_level: W1
        model_complexity_score: 2
        reference_need: identity_reference scene_reference
        tail_state: 乔熙和小豆丁仍在沙发边，照片在地面。
""")

    assert any("forbidden abstract viewpoint" in issue for issue in sdi._validate_shot_director_output(bad, ["F01"]))

    good = _coverage_v3("""      - shot_id: F01-S01
        duration: 0-4秒
        coverage_role: relation
        task: hold relation
        subject: 乔熙和小豆丁
        shot: 双人半身关系镜，平视，固定视角
        action: 乔熙停住，小豆丁看向照片。
        dialogue: none
        must_carry: reaction and photo state
        cut_reason: reaction appears after photo lands
        cut_point: reaction appears
        continuity: both stay beside the sofa
        companion_visibility: both visible
        state_delta: photo noticed
        tailframe_role: carry both characters
        template_id: COV-SD20-W1-TWO-SHOT-PRESSURE
        template_level: W1
        model_complexity_score: 2
        reference_need: identity_reference scene_reference
        tail_state: 乔熙和小豆丁仍在沙发边，照片在地面。
""")

    assert sdi._validate_shot_director_output(good, ["F01"]) == []


def test_storyboard_frame_control_contract_does_not_add_shots() -> None:
    shots = [
        {
            "shot_id": "F01-S01",
            "action": "乔熙把手机放到沙发坐垫上。",
            "continuity": "手机在沙发坐垫上。",
            "tail_state": "乔熙和小豆丁仍在沙发边，手机在沙发坐垫上。",
        }
    ]

    contract = sbi._frame_control_contract(shots)

    assert "frame_control_contract" in contract
    assert "tailframe_state" in contract
    assert "add_new_shots" in contract
    assert contract.count("F01-S01") == 1


def test_final_prompt_guard_requires_no_text_tailframe_and_blocks_abstract_viewpoint() -> None:
    prompt = "风格：真人短剧。9:16竖屏。连续性：同一客厅。参考：只锁人物。镜头：沙发与地毯之间的关系视角。尾帧：乔熙停在沙发边。约束：禁止字幕。"
    issues = prompt_contract_issues(prompt)
    assert any("no_text_hard_constraint" in issue for issue in issues)
    assert any("forbidden_abstract_viewpoint" in issue for issue in issues)

    report = _compiler_guard_report(prompt, "", "generation_unit_id: U01\nsource_script_events:\n- a\nevent_atom: a\nduration_target: 4秒\nmodel_complexity_score: 1\nreference_needs: identity_reference\ntail_state_required: still\nrhythm_operation_sheet_ref: F01\nshot_director_handoff: handoff", "")
    assert "FINAL-SEEDANCE-PROMPT-CONTRACT" in report
    assert "SEEDANCE-ABSTRACT-VIEWPOINT-GATE" in report
