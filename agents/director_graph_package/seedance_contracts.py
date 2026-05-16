"""Pure helpers for Seedance 2.0 cross-agent contract checks.

The functions in this module intentionally avoid graph/runtime imports so they
can be called from planner, director, compiler, and QC nodes without creating
new dependency cycles.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


ALLOWED_TEMPLATE_LEVELS = {"W1", "W2", "R1", "X", "candidate"}
REFERENCE_ROLES = {
    "identity_reference",
    "scene_reference",
    "prop_reference",
    "motion_reference",
    "camera_reference",
    "audio_reference",
    "keyframe_sequence",
    "video_reference",
    "video_reference_required",
}
BOUND_REFERENCE_MARKERS_RE = re.compile(
    r"(?i)(reference_bindings?|reference_assets?|reference_binding_id|reference_asset_id|"
    r"video_path|video_reference_path|keyframe_path|keyframe_sequence_path|motion_reference_path|"
    r"image_id|asset_id|source_path)"
)
TEXT_DEPENDENCY_RE = re.compile(
    r"(?i)("
    r"(?:依赖|靠|通过|用|以).{0,16}(?:字幕|屏幕文字|屏幕内文字|画面内文字|文件文字|手机文字|可读文字|文字浮层|文字证据|subtitles?|captions?|screen text|onscreen text|on-screen text)"
    r"|(?:字幕|屏幕文字|屏幕内文字|画面内文字|文件文字|手机文字|可读文字|文字浮层|文字证据|subtitles?|captions?|screen text|onscreen text|on-screen text).{0,16}(?:揭示|说明|传达|显示|写着|读出|作为关键|作为证据)"
    r")"
)
NO_TEXT_HARD_CONSTRAINT = (
    "禁止字幕、屏幕文字、英文字幕、文字浮层、水印、logo、可读标牌、"
    "手机屏幕文字、文件可读字"
)
NO_TEXT_REQUIRED_TERMS = (
    "字幕",
    "屏幕文字",
    "英文字幕",
    "文字浮层",
    "水印",
    "logo",
    "可读标牌",
    "手机屏幕文字",
    "文件可读字",
)
ABSTRACT_VIEWPOINT_RE = re.compile(
    r"沙发与地毯之间的关系视角|空间关系视角|关系视角|职责视角|承接视角|"
    r"客厅侧面略高视角|复杂坐标式机位|关系复位视角|覆盖职责视角"
)
CAMERA_LANGUAGE_RE = re.compile(
    r"机位|景别|过肩|反打|特写|推镜|拉镜|摇镜|移镜|环绕|俯拍|仰拍|"
    r"camera|shot_size|angle|movement",
    re.IGNORECASE,
)
FINAL_PROMPT_REQUIRED_TERMS = (
    "风格",
    "9:16",
    "连续性",
    "参考",
    "镜头",
    "尾帧",
    "约束",
)


def contains_camera_language(text: str) -> bool:
    return bool(CAMERA_LANGUAGE_RE.search(text or ""))


def _strip_forbidden_metadata(text: str) -> str:
    """Ignore explicit forbidden lists when scanning for accidental output content."""
    kept: list[str] = []
    in_forbidden = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^forbidden\s*:", stripped):
            in_forbidden = True
            continue
        if in_forbidden and (stripped.startswith("-") or not stripped):
            continue
        in_forbidden = False
        kept.append(line)
    return "\n".join(kept)


def abstract_viewpoint_terms(text: str) -> list[str]:
    return _dedupe(match.group(0) for match in ABSTRACT_VIEWPOINT_RE.finditer(text or ""))


def has_no_text_hard_constraint(text: str) -> bool:
    lowered = (text or "").lower()
    return all(term.lower() in lowered for term in NO_TEXT_REQUIRED_TERMS)


def prompt_contract_issues(prompt: str) -> list[str]:
    issues: list[str] = []
    prompt = prompt or ""
    for term in FINAL_PROMPT_REQUIRED_TERMS:
        if term not in prompt:
            issues.append(f"final_seedance_prompt_missing:{term}")
    if not has_no_text_hard_constraint(prompt):
        issues.append("final_seedance_prompt_missing:no_text_hard_constraint")
    for term in abstract_viewpoint_terms(prompt):
        issues.append(f"final_seedance_prompt_forbidden_abstract_viewpoint:{term}")
    return _dedupe(issues)


def rhythm_operation_sheet_issues(text: str) -> list[str]:
    required = (
        "rhythm_operation_sheet",
        "segment_id",
        "rhythm_mode",
        "target_duration",
        "pressure_curve",
        "beat_plan",
        "beat_budget",
        "pause_points",
        "reaction_ownership",
        "compression_policy",
        "tail_state_required",
        "shot_budget_hint",
    )
    issues = [f"rhythm_operation_sheet_missing:{field}" for field in required if field not in (text or "")]
    content_text = _strip_forbidden_metadata(text or "")
    if contains_camera_language(content_text):
        issues.append("rhythm_operation_sheet_forbidden:camera_language")
    if not has_no_text_hard_constraint(text or ""):
        issues.append("rhythm_operation_sheet_missing:no_text_hard_constraint")
    return _dedupe(issues)


def generation_unit_contract_issues(text: str) -> list[str]:
    required = (
        "generation_unit_id",
        "source_script_events",
        "event_atom",
        "duration_target",
        "model_complexity_score",
        "reference_needs",
        "tail_state_required",
        "rhythm_operation_sheet_ref",
        "shot_director_handoff",
    )
    issues = [f"generation_unit_missing:{field}" for field in required if field not in (text or "")]
    content_text = _strip_forbidden_metadata(text or "")
    if contains_camera_language(content_text):
        issues.append("generation_unit_forbidden:camera_language")
    return _dedupe(issues)


def _ensure_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text


def _ensure_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple, set, dict)) and not value:
            continue
        return value
    return None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "required", "high"}
    return bool(value)


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _normalise_template_level(level: Any) -> str | None:
    if not isinstance(level, str):
        return None
    cleaned = level.strip().strip("\"'`")
    upper = cleaned.upper()
    if upper in {"W1", "W2", "R1", "X"}:
        return upper
    if cleaned.lower() == "candidate":
        return "candidate"
    if upper in {"W2_R1", "R1_X"}:
        return "R1" if "R1" in upper else "X"
    return None


def _extract_scalar(text: str, names: tuple[str, ...]) -> str | None:
    joined = "|".join(re.escape(name) for name in names)
    pattern = re.compile(
        rf"(?im)^\s*(?:{joined})\s*[:=]\s*(?P<value>[^\n#]+?)\s*$"
    )
    match = pattern.search(text)
    if not match:
        return None
    return match.group("value").strip().strip("\"'`")


def _extract_template_level(text: str, template_id: str | None = None) -> str | None:
    explicit = _extract_scalar(text, ("template_level",))
    level = _normalise_template_level(explicit)
    if level:
        return level

    search_text = " ".join(part for part in (template_id, text) if part)
    for candidate in ("W1", "W2", "R1", "X"):
        if re.search(rf"(?<![A-Za-z0-9]){candidate}(?![A-Za-z0-9])", search_text):
            return candidate
    if re.search(r"(?i)(?<![A-Za-z0-9])candidate(?![A-Za-z0-9])", search_text):
        return "candidate"
    return None


def _extract_references(text: str) -> list[str]:
    roles: list[str] = []
    lowered = text.lower()
    for role in sorted(REFERENCE_ROLES):
        if role.lower() in lowered:
            roles.append(role)
    return roles


def _has_bound_motion_reference(text: str) -> bool:
    lowered = text.lower()
    has_motion_role = any(
        role in lowered
        for role in ("motion_reference", "camera_reference", "keyframe_sequence", "video_reference", "video_reference_required")
    )
    return has_motion_role and bool(BOUND_REFERENCE_MARKERS_RE.search(text))


def extract_seedance_contract_flags(text: str) -> dict[str, Any]:
    """Extract Seedance contract flags from planner/director/compiler text.

    Missing fields are returned as ``None`` or empty lists so callers can decide
    whether absence is a warning or a hard failure.
    """

    text = _ensure_text(text)
    template_id = _extract_scalar(
        text, ("template_id", "coverage_template_id", "shot_template_id")
    )
    reference_need = _extract_references(text)
    tail_state = _extract_scalar(
        text,
        (
            "tail_state",
            "tail_state_card",
            "scene_tail_state",
            "tail_frame_lock",
            "tail_state_required",
        ),
    )
    complexity_raw = _extract_scalar(text, ("model_complexity_score",))

    template_level = _extract_template_level(text, template_id=template_id)
    has_motion_reference = _has_bound_motion_reference(text)

    return {
        "template_id": template_id,
        "template_level": template_level,
        "reference_need": reference_need,
        "has_reference": bool(reference_need),
        "has_motion_reference": has_motion_reference,
        "tail_state": tail_state,
        "model_complexity_score": _coerce_int(complexity_raw),
        "text_dependency": _has_text_dependency(text),
    }


def seedance_complexity_score(
    *,
    duration_s: Any = None,
    primary_actor_count: Any = None,
    event_count: Any = None,
    action_contact: Any = False,
    fast_motion: Any = False,
    camera_changes: Any = False,
    emotion_turns: Any = None,
    lip_sync: Any = False,
    state_changes: Any = False,
    reference_count: Any = None,
) -> int:
    """Compute the conservative 0+ Seedance complexity score."""

    score = 0
    duration = _coerce_int(duration_s)
    actors = _coerce_int(primary_actor_count)
    events = _coerce_int(event_count)
    turns = _coerce_int(emotion_turns)
    refs = _coerce_int(reference_count)

    if actors is not None and actors > 2:
        score += 1
    if _coerce_bool(action_contact):
        score += 1
    if _coerce_bool(fast_motion):
        score += 1
    if _coerce_bool(camera_changes):
        score += 1
    if turns is not None and turns >= 2:
        score += 1
    if _coerce_bool(lip_sync):
        score += 1
    if _coerce_bool(state_changes):
        score += 1
    if duration is not None and duration > 8:
        score += 1
    if refs is not None and refs >= 4:
        score += 1
    if duration is not None and events is not None and duration > 8 and events >= 3:
        score += 1
    return score


def seedance_complexity_issues(
    *,
    duration_s: Any = None,
    primary_actor_count: Any = None,
    event_count: Any = None,
    action_contact: Any = False,
    fast_motion: Any = False,
    camera_changes: Any = False,
    emotion_turns: Any = None,
    lip_sync: Any = False,
    state_changes: Any = False,
    reference_count: Any = None,
    complexity_score: Any = None,
) -> list[str]:
    """Return standardized complexity issues without raising on missing fields."""

    score = _coerce_int(complexity_score)
    if score is None:
        score = seedance_complexity_score(
            duration_s=duration_s,
            primary_actor_count=primary_actor_count,
            event_count=event_count,
            action_contact=action_contact,
            fast_motion=fast_motion,
            camera_changes=camera_changes,
            emotion_turns=emotion_turns,
            lip_sync=lip_sync,
            state_changes=state_changes,
            reference_count=reference_count,
        )

    issues: list[str] = []
    if score >= 5:
        issues.append(
            f"seedance_complexity_score>=5: score={score}; split, use motion/video reference, or route to post/human review"
        )
    elif score >= 3:
        issues.append(
            f"seedance_complexity_score=3-4: score={score}; downgrade or split into smaller generation units"
        )

    actors = _coerce_int(primary_actor_count)
    events = _coerce_int(event_count)
    duration = _coerce_int(duration_s)
    if duration is not None and duration > 8 and events is not None and events >= 3:
        issues.append(
            "seedance_hard_limit: duration>8s with 3+ events is not a single controllable unit"
        )
    if actors is not None and actors >= 3:
        issues.append(
            "seedance_actor_limit: 3+ primary actors require static background roles or split"
        )
    return issues


def format_seedance_contract_block(
    *,
    template_id: Any = None,
    template_level: Any = None,
    reference_need: Any = None,
    tail_state: Any = None,
    complexity_score: Any = None,
    compiler_guard: Any = None,
) -> str:
    """Format a concise block suitable for insertion into a Seedance prompt."""

    refs = _normalise_reference_list(reference_need)
    guards = _normalise_reference_list(compiler_guard)
    lines = ["【Seedance 2.0合同约束】"]
    lines.append(f"- template_id: {_display(template_id)}")
    lines.append(f"- template_level: {_display(template_level)}")
    lines.append(f"- reference_need: {_display_list(refs)}")
    lines.append(f"- model_complexity_score: {_display(complexity_score)}")
    lines.append(f"- tail_state: {_display(tail_state)}")
    if guards:
        lines.append(f"- compiler_guard: {_display_list(guards)}")
    return "\n".join(lines)


def seedance_qc_issues(contract: str | Mapping[str, Any] | None = None, **overrides: Any) -> list[str]:
    """Return standardized Seedance QC issue strings.

    ``contract`` may be text from an upstream agent or a mapping of already
    extracted flags. Keyword overrides win over extracted values.
    """

    if contract is None:
        flags: dict[str, Any] = {}
    elif isinstance(contract, str):
        flags = extract_seedance_contract_flags(contract)
    else:
        flags = dict(_ensure_mapping(contract, "contract"))
    flags.update({key: value for key, value in overrides.items() if value is not None})

    template_id = _first_non_empty(flags.get("template_id"), flags.get("coverage_template_id"))
    template_level = _normalise_template_level(flags.get("template_level"))
    tail_state = _first_non_empty(
        flags.get("tail_state"),
        flags.get("tail_state_card"),
        flags.get("scene_tail_state"),
        flags.get("tail_state_required"),
    )
    refs = _normalise_reference_list(
        _first_non_empty(flags.get("reference_need"), flags.get("reference_needs"))
    )
    has_motion_reference = _coerce_bool(flags.get("has_motion_reference")) or _coerce_bool(
        flags.get("reference_asset_available")
    )

    issues: list[str] = []
    if not template_id:
        issues.append("seedance_template_id_missing: coverage template_id was not provided")
    if template_level == "X":
        issues.append("seedance_template_x_forbidden: X templates must be split, post-produced, or human-reviewed")
    elif template_level == "candidate":
        issues.append("seedance_template_candidate: candidate template is not production-whitelisted")
    elif template_level is None:
        issues.append("seedance_template_level_missing: template_level W1/W2/R1/X/candidate was not provided")

    if template_level == "R1" and not has_motion_reference:
        issues.append("seedance_r1_reference_missing: R1 requires motion_reference, keyframe_sequence, or video_reference")

    complexity = _coerce_int(flags.get("model_complexity_score"))
    if complexity is not None:
        issues.extend(seedance_complexity_issues(complexity_score=complexity))

    if not tail_state or re.search(r"待定|未知|不清|不明确|未说明|TBD|unclear", str(tail_state), re.IGNORECASE):
        issues.append("seedance_tail_state_missing: tail_state must be explicit and inheritable")

    text_dependency = _coerce_bool(flags.get("text_dependency"))
    raw_text = flags.get("text") if isinstance(flags.get("text"), str) else ""
    if text_dependency or _has_text_dependency(raw_text):
        issues.append("seedance_text_dependency: do not rely on subtitles, screen text, or document text for key plot information")

    return _dedupe(issues)


def _normalise_reference_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            stripped = stripped[1:-1]
        parts = re.split(r"[,，+;/\s]+", stripped)
        return [part.strip().strip("\"'`") for part in parts if part.strip().strip("\"'`")]
    if isinstance(value, Mapping):
        return [str(key) for key, val in value.items() if _coerce_bool(val)]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _has_text_dependency(text: str) -> bool:
    return bool(TEXT_DEPENDENCY_RE.search(text or ""))


def _display(value: Any) -> str:
    if value is None or value == "":
        return "未提供"
    return str(value)


def _display_list(values: list[str]) -> str:
    return ", ".join(values) if values else "未提供"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
