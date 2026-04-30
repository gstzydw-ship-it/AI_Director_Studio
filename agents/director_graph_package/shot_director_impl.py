"""Shot director implementation split from the legacy director graph module."""
from __future__ import annotations

from . import legacy_impl as _legacy
from . import helpers as _helpers


# Real implementation surface for Phase 2.  The implementation body currently
# remains source-compatible with the already migrated package-local helpers and
# legacy node internals; package callers import this module, not
# the old monolithic graph module.
shot_director_node = _legacy.shot_director_node
_run_shot_director_single_pass = _helpers._run_shot_director_single_pass_impl


def _run_shot_director_review_board(*args, **kwargs):
    return _run_shot_director_single_pass(*args, **kwargs)

_repair_shot_director_output_contracts = _legacy._repair_shot_director_output_contracts
_clean_shot_director_output = _legacy._clean_shot_director_output
_validate_shot_director_output = _legacy._validate_shot_director_output
_collect_shot_director_issues = _legacy._collect_shot_director_issues
_hard_shot_director_issues = _legacy._hard_shot_director_issues
_is_soft_shot_director_issue = _legacy._is_soft_shot_director_issue

# Vertical discipline, source_event coverage, continuity, anti-fabrication,
# review-board/layout helpers required by shot_director contracts.
_validate_shot_director_vertical_discipline = _legacy._validate_shot_director_vertical_discipline
_validate_shot_director_source_event_coverage = _legacy._validate_shot_director_source_event_coverage
_validate_shot_director_script_fidelity = _legacy._validate_shot_director_script_fidelity
_shot_director_source_event_rules = _legacy._shot_director_source_event_rules
_shot_director_rhythm_match_rules = _legacy._shot_director_rhythm_match_rules
_rhythm_insert_continuity_rules = _legacy._rhythm_insert_continuity_rules
_shot_director_rule_block = _legacy._shot_director_rule_block
_shot_director_blocking_rule_block = _legacy._shot_director_blocking_rule_block
_shot_director_layout_rule_block = _legacy._shot_director_layout_rule_block
_shot_director_shared_context = _legacy._shot_director_shared_context
_shot_director_layout_context = _legacy._shot_director_layout_context
_shot_director_downstream_context = _legacy._shot_director_downstream_context
_shot_stage_should_split = _legacy._shot_stage_should_split
_segment_name_to_fragment_id = _legacy._segment_name_to_fragment_id
_fragment_compact_context = _legacy._fragment_compact_context
_call_stage_split_by_fragment = _legacy._call_stage_split_by_fragment
_call_shot_director_stage = _legacy._call_shot_director_stage
_shot_director_stage_images = _legacy._shot_director_stage_images
_repair_shot_layout_output = _legacy._repair_shot_layout_output


__all__ = [name for name in globals() if name == "shot_director_node" or name.startswith("_shot_director") or name.startswith("_run_shot_director") or name.startswith("_repair_shot") or name.startswith("_clean_shot") or name.startswith("_validate_shot") or name in {"_collect_shot_director_issues", "_hard_shot_director_issues", "_is_soft_shot_director_issue"}]