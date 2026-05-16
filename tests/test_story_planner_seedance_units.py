from __future__ import annotations

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from agents.director_graph_package import story_planner_impl as spi  # noqa: E402


BASE_PLANNER_YAML = """
- fragment_id: F01
  duration_target: "5-8s"
  dramatic_unit: "Alex notices the phone evidence"
  source_script_events:
    - "Alex picks up the phone."
    - "Alex freezes after seeing the photo."
  cast:
    - "Alex"
  continuity:
    entry: "Alex is beside the table."
    exit: "Alex holds the phone and looks toward the doorway."
  reaction_plan: "Keep Alex's reaction inside this unit, hand off to the person at the door."
  director_brief: "Protect the evidence reveal and the reaction landing."
"""


def test_story_planner_validation_reports_missing_seedance_unit_contract():
    issues = spi._validate_story_planner_output(
        BASE_PLANNER_YAML,
        require_generation_unit_fields=True,
    )

    assert any("missing Seedance generation_unit contract fields" in issue for issue in issues)
    assert any("generation_unit_id" in issue for issue in issues)
    assert any("tail_state_required" in issue for issue in issues)


def test_story_planner_normalise_adds_seedance_unit_contract_fields():
    normalised = spi._normalise_story_planner_output(BASE_PLANNER_YAML)

    for field in (
        "generation_unit_id",
        "signal_type",
        "event_atom",
        "emotion_delta",
        "reaction_handoff",
        "model_complexity_score",
        "split_required",
        "reference_needs",
        "tail_state_required",
        "rhythm_operation_sheet_ref",
        "shot_director_handoff",
    ):
        assert f"{field}:" in normalised

    assert spi._validate_story_planner_output(normalised, require_generation_unit_fields=True) == []


def test_story_planner_rejects_legacy_seedance_fields_without_canonical_contract():
    legacy_output = (
        BASE_PLANNER_YAML
        + '\n  generation_unit: "core_visible_event=Alex sees the phone; reaction_bridge=door handoff; emotion_landing=alerted"\n'
        + '  model_complexity_score: "1"\n'
        + '  required_reference_role: "identity_reference + scene_reference + prop_reference"\n'
    )

    issues = spi._validate_story_planner_output(legacy_output, require_generation_unit_fields=True)

    assert any("missing Seedance generation_unit fields" in issue for issue in issues)
    assert any("generation_unit_id" in issue for issue in issues)
    assert any("reference_needs" in issue for issue in issues)


def test_story_planner_seedance_contract_is_in_prompts():
    rhythm_system = spi._rhythm_story_planner_system_prompt()
    rhythm_user = spi._rhythm_story_planner_user_prompt(
        state={"script": "Alex picks up the phone.", "aspect_ratio": "9:16"},
        truncated_script="Alex picks up the phone.",
        slim_rules="",
    )
    repair_prompt = spi._story_planner_repair_prompt(
        original_script="Alex picks up the phone.",
        scene_output="",
        rhythm_guidance="",
        previous_output=BASE_PLANNER_YAML,
        validation_issues=["missing Seedance generation_unit contract fields"],
    )

    for prompt in (rhythm_system, rhythm_user, repair_prompt):
        assert "generation_unit_id" in prompt
        assert "signal_type" in prompt
        assert "event_atom" in prompt
        assert "reaction_handoff" in prompt
        assert "tail_state_required" in prompt
        assert "rhythm_operation_sheet_ref" in prompt
        assert "shot_director_handoff" in prompt
