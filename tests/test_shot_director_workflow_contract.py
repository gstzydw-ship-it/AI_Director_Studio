from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph_package.shot_director_impl import (  # noqa: E402
    _build_shot_director_workflow_trace,
    _extract_rhythm_shot_director_notes,
    _reference_images,
    _rhythm_shot_director_notes_prompt,
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


def test_rhythm_shot_director_notes_are_extracted_for_handoff():
    atmosphere_strategy = """rhythm_diagnosis: reveal is too fast.
construction_notes: keep photo reveal inside the same fragment.
shot_director_notes: hold Qiao Xi's reaction before the flashback.
  - cut on photo-read completion, not on random movement.
  - tailframe must carry the photo into the flashback.
"""

    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    prompt = _rhythm_shot_director_notes_prompt(atmosphere_strategy)

    assert "hold Qiao Xi's reaction" in notes
    assert "cut on photo-read completion" in notes
    assert "Rhythm Supervisor Shot Notes" in prompt
    assert "tailframe" in prompt


def test_shot_director_downstream_context_includes_rhythm_shot_notes():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "Qiao Xi sees the photo."
"""
    atmosphere_strategy = """rhythm_diagnosis: reveal is too fast.
shot_director_notes: reaction belongs to Qiao Xi; cut after the photo is readable.
construction_notes: no split before the flashback.
"""

    context = _shot_director_downstream_context(planner_output, atmosphere_strategy, "9:16")

    assert "[Rhythm Supervisor Shot Notes]" in context
    assert "reaction belongs to Qiao Xi" in context
    assert "[Atmosphere Excerpt]" in context


def test_shot_director_does_not_upload_raw_reference_images():
    state = {"reference_image_b64s": ["scene-a", "person-a"]}

    assert _reference_images(state) == []
