from __future__ import annotations

import pytest

from agents.director_graph_package.seedance_contracts import (
    extract_seedance_contract_flags,
    format_seedance_contract_block,
    seedance_complexity_issues,
    seedance_qc_issues,
)


def test_w1_contract_passes_qc() -> None:
    text = """
template_id: COV-SD20-W1-REACTION-HOLD
template_level: W1
reference_need: [identity_reference, scene_reference]
tail_state: 女主仍看向男主，身体未离开原位。
model_complexity_score: 2
"""

    flags = extract_seedance_contract_flags(text)

    assert flags["template_id"] == "COV-SD20-W1-REACTION-HOLD"
    assert flags["template_level"] == "W1"
    assert flags["model_complexity_score"] == 2
    assert seedance_qc_issues(text) == []


def test_r1_missing_reference_fails() -> None:
    issues = seedance_qc_issues(
        {
            "template_id": "COV-SD20-R1-FIGHT-BEAT",
            "template_level": "R1",
            "reference_need": ["identity_reference", "scene_reference"],
            "tail_state": "动作后状态明确，不能继续打斗。",
            "model_complexity_score": 4,
        }
    )

    assert "seedance_r1_reference_missing" in "\n".join(issues)


def test_r1_declared_motion_reference_without_bound_asset_fails() -> None:
    issues = seedance_qc_issues(
        {
            "template_id": "COV-SD20-R1-FAST-CHASE",
            "template_level": "R1",
            "reference_need": ["identity_reference", "scene_reference", "motion_reference"],
            "tail_state": "Runner stops at the door.",
            "model_complexity_score": 2,
        }
    )

    assert "seedance_r1_reference_missing" in "\n".join(issues)


def test_r1_bound_motion_reference_passes_reference_gate() -> None:
    issues = seedance_qc_issues(
        """template_id: COV-SD20-R1-FAST-CHASE
template_level: R1
reference_need: identity_reference scene_reference motion_reference
reference_binding_id: ref_motion_001
tail_state: Runner stops at the door.
model_complexity_score: 2
"""
    )

    assert "seedance_r1_reference_missing" not in "\n".join(issues)


def test_x_template_fails() -> None:
    issues = seedance_qc_issues(
        {
            "template_id": "COV-SD20-X-CROWD-CROSS-SPACE-ONE-SHOT",
            "template_level": "X",
            "reference_need": ["not_for_pure_seedance_prompt"],
            "tail_state": "必须拆为 W1/W2 小单元。",
            "model_complexity_score": 2,
        }
    )

    assert "seedance_template_x_forbidden" in "\n".join(issues)


def test_complexity_five_or_more_fails() -> None:
    issues = seedance_complexity_issues(complexity_score=5)

    assert issues == [
        "seedance_complexity_score>=5: score=5; split, use motion/video reference, or route to post/human review"
    ]
    assert "seedance_complexity_score>=5" in "\n".join(
        seedance_qc_issues(
            {
                "template_id": "COV-SD20-W2-SLOW-FOLLOW",
                "template_level": "W2",
                "reference_need": ["identity_reference", "scene_reference"],
                "tail_state": "人物停在明确门口锚点前。",
                "model_complexity_score": 5,
            }
        )
    )


def test_tail_state_missing_fails_without_exception() -> None:
    issues = seedance_qc_issues(
        {
            "template_id": "COV-SD20-W1-TWO-SHOT-PRESSURE",
            "template_level": "W1",
            "reference_need": ["identity_reference", "scene_reference"],
            "model_complexity_score": 1,
        }
    )

    assert "seedance_tail_state_missing" in "\n".join(issues)


def test_missing_template_id_and_text_dependency_are_reported() -> None:
    issues = seedance_qc_issues(
        """
template_level: W1
reference_need: [identity_reference, scene_reference]
tail_state: 道具仍在桌面上。
model_complexity_score: 1
依赖屏幕文字展示关键遗嘱内容。
"""
    )

    joined = "\n".join(issues)
    assert "seedance_template_id_missing" in joined
    assert "seedance_text_dependency" in joined


def test_format_contract_block_is_concise() -> None:
    block = format_seedance_contract_block(
        template_id="COV-SD20-W1-REACTION-HOLD",
        template_level="W1",
        reference_need=["identity_reference", "scene_reference"],
        tail_state="表情和视线锁住。",
        complexity_score=1,
    )

    assert "【Seedance 2.0合同约束】" in block
    assert "template_id: COV-SD20-W1-REACTION-HOLD" in block
    assert "model_complexity_score: 1" in block


def test_type_errors_only_for_wrong_top_level_input() -> None:
    with pytest.raises(TypeError):
        extract_seedance_contract_flags({"template_id": "bad"})  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        seedance_qc_issues(123)  # type: ignore[arg-type]
