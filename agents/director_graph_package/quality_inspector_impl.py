"""Quality inspector / QC router implementation extracted from legacy_impl.

Owns rule-based QC and graph routing after quality control.
"""
from __future__ import annotations

import re
from typing import Any

from .types import (
    DirectorState,
    MAX_QC_RETRIES,
    _AXIS_LEFT_RE,
    _AXIS_RIGHT_RE,
    _REVERSE_SHOT_INSIDE_SEGMENT_RE,
)
from .state_store import _agent_outputs, _persist_update
from .helpers import (
    _MAIN_SHOT_BLOCK_RE,
    _fragment_id_for_segment_index,
    _has_yaml_field,
    _segment_block_by_fragment_id,
    _yaml_line_field,
)
from .seedance_contracts import seedance_qc_issues


# ---------------------------------------------------------------------------
# Low-level report parsers / normalisers
# ---------------------------------------------------------------------------
def _segment_block(text: str, segment_index: int, fragment_id: str | None = None) -> str:
    selected_fragment_id = fragment_id or _fragment_id_for_segment_index([], segment_index)
    return _segment_block_by_fragment_id(text, selected_fragment_id)


def _timeline_blocks(prompt: str) -> list[tuple[float, float, str]]:
    matches = list(re.finditer(r"(?m)^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒[:：]", prompt or ""))
    blocks: list[tuple[float, float, str]] = []
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        blocks.append((float(match.group(1)), float(match.group(2)), prompt[body_start:body_end].strip()))
    if blocks:
        return blocks

    shot_matches = list(
        re.finditer(
            r"(?m)^镜头\s*\d+\s*【\s*(?:(\d+(?:\.\d+)?)\s*[-~—]\s*)?(\d+(?:\.\d+)?)\s*秒\s*】",
            prompt or "",
        )
    )
    current = 0.0
    for index, match in enumerate(shot_matches):
        if match.group(1) is not None:
            start = float(match.group(1))
            end = float(match.group(2))
        else:
            duration = float(match.group(2))
            start = current
            end = current + duration
        body_start = match.end()
        body_end = shot_matches[index + 1].start() if index + 1 < len(shot_matches) else len(prompt)
        blocks.append((start, end, prompt[body_start:body_end].strip()))
        current = end
    return blocks


def _prompt_uses_shot_sequence(prompt: str) -> bool:
    return bool(
        re.search(r"【画面基底】[\s\S]*【镜头序列】[\s\S]*【约束】", prompt or "")
        and re.search(r"(?m)^镜头\s*\d+\s*【", prompt or "")
    )


def _planner_has_reaction_handoff(planner_segment: str) -> bool:
    return bool(
        _has_yaml_field(planner_segment, "reaction_plan")
        or re.search(r"(?m)^\s*(?:承接要求|镜头导演交接)\s*[:：]", planner_segment or "")
    )


def _seedance_contract_is_explicit(text: str) -> bool:
    return bool(
        re.search(
            r"(?im)^\s*(?:template_id|coverage_template_id|template_level)\s*[:=]|Seedance\s*2\.0|全能参考模式",
            text or "",
        )
    )


def _seedance_issue_to_qc_message(issue: str) -> str:
    if "seedance_template_id_missing" in issue or "seedance_template_level_missing" in issue:
        return "- [SEEDANCE-CONTRACT-GATE-001] COVERAGE_TEMPLATE_REQUIRED target=shot_director：Seedance 2.0 片段缺少 coverage template_id/template_level。"
    if "seedance_template_x_forbidden" in issue:
        return "- [SEEDANCE-COVERAGE-TEMPLATE-GATE-001] X_TEMPLATE_BLOCKED target=shot_director：命中 X 禁用 coverage 模板，不得进入生成。"
    if "seedance_template_candidate" in issue:
        return "- [SEEDANCE-COVERAGE-TEMPLATE-GATE-001] CANDIDATE_TEMPLATE_BLOCKED target=shot_director：coverage 模板仍是 candidate/untested，必须先测试或降级为 W1/W2。"
    if "seedance_r1_reference_missing" in issue:
        return "- [SEEDANCE-COVERAGE-TEMPLATE-GATE-001] R1_REFERENCE_REQUIRED target=shot_director：R1 模板缺少视频参考/关键帧/动作参考绑定，需要 video_reference/motion_reference/keyframe_sequence。"
    if "seedance_complexity_score" in issue:
        return "- [SEEDANCE-COMPLEXITY-GATE-001] SD20_COMPLEXITY_BUDGET target=story_planner：model_complexity_score 超过当前单段生产边界，必须拆分、降级或改用视频参考。"
    if "seedance_actor_limit" in issue:
        return "- [SEEDANCE-COMPLEXITY-GATE-001] SD20_MULTI_ACTOR_ACTION_BUDGET target=story_planner：三名以上主要角色动作必须静态化或拆分。"
    if "seedance_tail_state_missing" in issue:
        return "- [SEEDANCE-TAIL-STATE-GATE-001] TAILFRAME_STATE_REQUIRED target=shot_director：tail_state 必须明确且可继承。"
    if "seedance_text_dependency" in issue:
        return "- [SEEDANCE-NO-TEXT-DEPENDENCY-001] NO_SUBTITLE_SCREEN_TEXT target=prompt_compiler：不得依赖字幕/屏幕文字/文件文字传达剧情。"
    return f"- [SEEDANCE-CONTRACT-GATE-001] {issue}"


def _coverage_state_contract_text(state: DirectorState, fragment_id: str | None) -> str:
    contracts = state.get("coverage_contracts_by_segment") or {}
    if not isinstance(contracts, dict):
        return ""
    keys = [fragment_id, str(state.get("active_segment_index") or ""), str(state.get("current_segment_index") or "")]
    contract = next((contracts.get(key) for key in keys if key in contracts), None)
    if not isinstance(contract, dict):
        return ""
    return "\n".join(f"{key}: {value}" for key, value in contract.items())


def _seedance_contract_qc_issues(
    prompt: str,
    planner_segment: str,
    director_segment: str,
    state: DirectorState | None = None,
    fragment_id: str | None = None,
) -> list[str]:
    state_contract = _coverage_state_contract_text(state or {}, fragment_id)
    combined = "\n".join([prompt or "", planner_segment or "", director_segment or "", state_contract])
    if not _seedance_contract_is_explicit(combined):
        return []
    issues = [_seedance_issue_to_qc_message(issue) for issue in seedance_qc_issues(combined)]
    if re.search(r"action_budget_used\s*:[\s\S]{0,80}over_budget\s*:\s*true", combined, re.IGNORECASE):
        issues.append("- [SEEDANCE-COMPLEXITY-GATE-001] SD20_MULTI_ACTOR_ACTION_BUDGET target=shot_director：action_budget_used.over_budget=true，必须拆分或降级。")
    if re.search(r"main_character_count\s*:\s*[3-9]", combined) and re.search(r"同时|各自|争抢|冲向|伸手", combined):
        issues.append("- [SEEDANCE-COMPLEXITY-GATE-001] SD20_MULTI_ACTOR_ACTION_BUDGET target=story_planner：三名以上主要角色同时动作，必须静态化或拆分。")
    if re.search(r"尾帧[:：].{0,40}(压迫感|张力|氛围|情绪|黑场|留白)|tail_state\s*:\s*(?:不清|未知|待定|压迫感|black)", combined, re.IGNORECASE):
        issues.append("- [SEEDANCE-TAIL-STATE-GATE-001] TAILFRAME_STATE_REQUIRED target=shot_director：尾帧不能只写抽象情绪，必须写人物位置、视线、道具和门/空间状态。")
    if re.search(r"尾帧[:：].{0,40}(压迫感|张力|氛围|情绪)", combined):
        issues.append("- [PROMPT-VISIBLE-BODY-LANGUAGE-001] VISIBLE_EMOTION_ANCHOR_REQUIRED target=prompt_compiler：抽象情绪必须翻译为视线、肩背、下颌、手部、距离或道具状态。")
    return issues


_SHOT_DENSITY_LIFE_PRESSURE_RE = re.compile(
    r"生活|赶时间|穿衣|上学|孩子|小豆丁|闹钟|电话|手机|草莓|安抚|哄|抗拒|乱蹬|缩手|踢开|书包|紧凑生活",
    re.IGNORECASE,
)
_SHOT_DENSITY_HIGH_CUT_RE = re.compile(
    r"追逐|打斗|抢夺|闯入|冲进|救援|爆炸|车祸|急救|信息揭示|照片|文件|真相|证据|屏幕|监控|"
    r"亲子鉴定|高压对白|长对白|权力压迫|外部打断|宴会|群体|反转",
    re.IGNORECASE,
)


def _shot_density_limit(context: str, total_seconds: float | None) -> int:
    life_pressure = bool(_SHOT_DENSITY_LIFE_PRESSURE_RE.search(context or ""))
    high_cut_need = bool(_SHOT_DENSITY_HIGH_CUT_RE.search(context or ""))
    if total_seconds is None:
        return 4 if life_pressure and not high_cut_need else 5
    if total_seconds <= 6:
        return 3
    if total_seconds <= 12.5:
        return 4 if life_pressure and not high_cut_need else 5
    if total_seconds <= 15.5:
        return 5
    return 6


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "未知时长"
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded)}秒"
    return f"{rounded:.1f}秒"


def _prompt_shot_density_issues(
    prompt: str,
    planner_segment: str,
    director_segment: str,
    timeline_blocks: list[tuple[float, float, str]],
) -> list[str]:
    if not _prompt_uses_shot_sequence(prompt) or not timeline_blocks:
        return []
    total_seconds = max((end for _start, end, _body in timeline_blocks), default=0.0)
    total_seconds = total_seconds if total_seconds > 0 else None
    context = "\n".join([prompt or "", planner_segment or "", director_segment or ""])
    limit = _shot_density_limit(context, total_seconds)
    shot_count = len(timeline_blocks)
    issues: list[str] = []
    if shot_count > limit:
        issues.append(
            f"- 镜头切分过碎：{_format_seconds(total_seconds)}安排{shot_count}个镜头，"
            f"当前片段建议不超过{limit}个有效镜头；快节奏应靠人物动作紧张、停顿缩短和情绪压力，不靠碎切。"
        )
    short_blocks = [
        (index, end - start)
        for index, (start, end, _body) in enumerate(timeline_blocks, start=1)
        if 0 < end - start < 1.0
    ]
    life_pressure = bool(_SHOT_DENSITY_LIFE_PRESSURE_RE.search(context))
    high_cut_need = bool(_SHOT_DENSITY_HIGH_CUT_RE.search(context))
    if short_blocks and (len(short_blocks) >= 2 or (life_pressure and not high_cut_need)):
        short_text = "、".join(f"镜头{index}={seconds:.1f}秒" for index, seconds in short_blocks[:4])
        issues.append(
            f"- 1秒以下碎镜过多：{short_text}。生活动作/正常动作段不得把手、手机、脚、衣服等局部动作拆成碎插入；"
            "请合并进关系镜头，或只保留真正的信息揭示/危险命中短镜。"
        )
    return issues


_SEEDANCE_STRICT_CONTEXT_RE = re.compile(
    r"Seedance|seedance|全能参考|白名单|coverage_contract|coverage template|template_level|template_id|"
    r"coverage_template_id|COV-SD20|model_complexity_score|compiled_prompt_metadata"
)
_SEEDANCE_TEXT_DEPENDENCY_RE = re.compile(
    r"依赖(?:字幕|屏幕文字|文件文字|手机文字|可读文字)|"
    r"(?:字幕|屏幕文字|英文字幕|文字浮层|文件文字|手机屏幕文字|可读标牌|可读文字).{0,18}"
    r"(?:传递|说明|显示|展示|写着|读出|看清|揭示|证明|关键|证据)"
)
_SEEDANCE_VISIBLE_EMOTION_RE = re.compile(
    r"压迫感|张力|炸点|钩子|气口|留白|情绪顶点|情绪拉满|崩溃|震惊|高级感|电影感|爽感"
)
_SEEDANCE_VISIBLE_ACTION_ANCHOR_RE = re.compile(
    r"下颌|眼神|视线|呼吸|肩|手指|嘴唇|停顿|后退|前半步|转身|低头|抬眼|攥|松开|僵住|看向"
)
_SEEDANCE_COMPLEX_MULTI_ACTION_RE = re.compile(
    r"(?:三人|3人|四人|4人|多人|人群).{0,24}(?:同时|一起|各自|分别|集体).{0,24}"
    r"(?:动作|移动|冲|跑|抢|推|拉|打|摔|争抢|闯入|散开|围上|伸手)"
)
_SEEDANCE_R1_REFERENCE_RE = re.compile(
    r"motion_reference|video_reference|keyframe(?:_sequence)?|关键帧|视频参考|动作参考|首尾帧|尾帧参考",
    re.IGNORECASE,
)
_SEEDANCE_TAIL_FIELD_RE = re.compile(r"tail_state|tailframe|tail_frame|尾帧|尾帧状态|tail_state_card")
_SEEDANCE_WEAK_TAIL_RE = re.compile(r"尾帧[：:][^\n]*(?:眼神|手部|黑场|空镜|情绪|氛围)[^\n]*(?:停住|收束|结束)?")


def _state_lookup_by_segment(mapping: Any, segment_index: int, fragment_id: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    keys = (
        fragment_id,
        str(fragment_id),
        f"F{segment_index:02d}",
        f"F{segment_index}",
        str(segment_index),
        segment_index,
    )
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_flatten_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_flatten_text(item) for item in value)
    return str(value)


def _seedance_context_is_strict(state: DirectorState, prompt: str, planner_segment: str, director_segment: str) -> bool:
    context = "\n".join(
        [
            prompt or "",
            planner_segment or "",
            director_segment or "",
            _flatten_text(state.get("seedance_profile")),
            _flatten_text(state.get("coverage_contracts_by_segment")),
            _flatten_text(state.get("coverage_template_id_by_segment")),
            _flatten_text(state.get("model_complexity_score_by_segment")),
            _flatten_text(state.get("reference_bindings")),
        ]
    )
    return bool(_SEEDANCE_STRICT_CONTEXT_RE.search(context))


def _first_int_field(context: str, field_names: tuple[str, ...]) -> int | None:
    for field_name in field_names:
        match = re.search(rf"(?im)^\s*{re.escape(field_name)}\s*:\s*['\"]?(\d+)", context or "")
        if match:
            return int(match.group(1))
    return None


def _seedance_gate_issues(
    state: DirectorState,
    prompt: str,
    planner_segment: str,
    director_segment: str,
    segment_index: int,
    fragment_id: str,
) -> list[str]:
    strict_context = _seedance_context_is_strict(state, prompt, planner_segment, director_segment)
    coverage_contract = _state_lookup_by_segment(state.get("coverage_contracts_by_segment"), segment_index, fragment_id)
    generation_unit = None
    for unit in state.get("generation_units") or []:
        if isinstance(unit, dict) and unit.get("fragment_id") in {fragment_id, f"F{segment_index:02d}", f"F{segment_index}", str(segment_index)}:
            generation_unit = unit
            break

    coverage_text = _flatten_text(coverage_contract)
    generation_text = _flatten_text(generation_unit)
    reference_text = _flatten_text(state.get("reference_bindings")) + "\n" + _flatten_text(state.get("asset_selection"))
    context = "\n".join([prompt or "", planner_segment or "", director_segment or "", coverage_text, generation_text])

    template_id = _state_lookup_by_segment(state.get("coverage_template_id_by_segment"), segment_index, fragment_id)
    if not template_id and isinstance(coverage_contract, dict):
        template_id = coverage_contract.get("template_id") or coverage_contract.get("coverage_template_id")
    if not template_id:
        template_match = re.search(r"(?im)^\s*(?:template_id|coverage_template_id|compiled_from_template_id)\s*:\s*['\"]?([A-Za-z0-9_-]+)", context)
        template_id = template_match.group(1) if template_match else ""
    template_id_text = str(template_id or "")

    level = ""
    if isinstance(coverage_contract, dict):
        level = str(
            coverage_contract.get("template_level") or coverage_contract.get("template_status") or ""
        )
    if not level:
        level_match = re.search(r"(?im)^\s*(?:template_level|template_status)\s*:\s*['\"]?([A-Za-z0-9_-]+)", context)
        level = level_match.group(1) if level_match else ""
    level = level.upper()

    complexity = _state_lookup_by_segment(state.get("model_complexity_score_by_segment"), segment_index, fragment_id)
    if complexity is None and isinstance(generation_unit, dict):
        complexity = generation_unit.get("model_complexity_score")
    if complexity is None:
        complexity = _first_int_field(context, ("model_complexity_score",))
    try:
        complexity_score = int(complexity) if complexity is not None and str(complexity) != "" else None
    except (TypeError, ValueError):
        complexity_score = None

    issues: list[str] = []
    prefix = "- [SEEDANCE-QC]"

    if template_id_text.upper().startswith("COV-SD20-X") or level == "X":
        issues.append(
            f"{prefix} target=shot_director rule=X_TEMPLATE_BLOCKED issue=命中 Seedance 2.0 禁用 coverage 模板。"
            " repair_route=shot_director：将 X 手法拆成 W1/W2 小单元；每个单元保留一个核心可见事件、一个主动作和清楚尾帧，不得交给 prompt_compiler 直接生成。"
        )

    if not template_id_text and strict_context:
        issues.append(
            f"{prefix} target=shot_director rule=COVERAGE_TEMPLATE_REQUIRED issue=缺少可生产白名单 template_id。"
            " repair_route=shot_director：从 COV-SD20-W1/W2/R1 白名单选择 template_id，并补齐 duration_s、main_subject、action_budget、reference_need、tail_state、compiler_guard。"
        )
    elif re.search(r"candidate|untested|自由文本", template_id_text, re.IGNORECASE) or level in {"CANDIDATE", "UNTESTED"}:
        issues.append(
            f"{prefix} target=shot_director rule=COVERAGE_TEMPLATE_REQUIRED issue=template_id 仍是 candidate/untested，不能作为生产模板。"
            " repair_route=shot_director：降级到已测试 W1/W2，或补测后再交给 prompt_compiler。"
        )

    if (level == "R1" or template_id_text.upper().startswith("COV-SD20-R1")) and not _SEEDANCE_R1_REFERENCE_RE.search(
        context + "\n" + reference_text
    ):
        issues.append(
            f"{prefix} target=shot_director rule=R1_REFERENCE_REQUIRED issue=R1 参考驱动模板缺少 video_reference/motion_reference/keyframe_sequence。"
            " repair_route=shot_director：补充动作/视频/关键帧参考并绑定 target_id 与 scope，或降级为 W1/W2 小单元。"
        )

    if complexity_score is not None and complexity_score >= 5:
        issues.append(
            f"{prefix} target=story_planner/shot_director rule=SD20_COMPLEXITY_BUDGET issue=model_complexity_score={complexity_score} 超出单段生成边界。"
            " repair_route=story_planner/shot_director：拆成 2 个以上生成单元；每个单元只保留 1 个核心可见事件、1 个主动作链和 1 个尾帧状态。"
        )

    character_count = _first_int_field(context, ("main_character_count", "primary_actor_count", "visible_character_count"))
    if (character_count is not None and character_count >= 3 and re.search(r"over_budget\s*:\s*true|各自|同时|一起", context, re.IGNORECASE)) or _SEEDANCE_COMPLEX_MULTI_ACTION_RE.search(context):
        issues.append(
            f"{prefix} target=story_planner/shot_director rule=SD20_MULTI_ACTOR_ACTION_BUDGET issue=3人以上同动或多人复杂动作超出可控预算。"
            " repair_route=story_planner/shot_director：拆分为单一行动主体的小单元；其余角色只保留静态反应/画外反应，复杂动作改 R1 并补动作参考。"
        )

    if strict_context and not _SEEDANCE_TAIL_FIELD_RE.search(context):
        issues.append(
            f"{prefix} target=prompt_compiler rule=TAILFRAME_STATE_REQUIRED issue=缺少可继承 tail_state/tailframe。"
            " repair_route=prompt_compiler：在最后 0.5-1.0 秒写清人物位置、朝向/视线、道具/门/车门状态和下一段承接点，不新增动作或新事件。"
        )
    elif _SEEDANCE_WEAK_TAIL_RE.search(context):
        issues.append(
            f"{prefix} target=prompt_compiler rule=TAILFRAME_STATE_REQUIRED issue=尾帧停在眼神/手部/黑场/抽象空镜，下一段不可继承。"
            " repair_route=prompt_compiler：改为关系景或主体半身景尾帧，写清人物位置、视线、道具与门/车门状态。"
        )

    if _SEEDANCE_TEXT_DEPENDENCY_RE.search(context):
        issues.append(
            f"{prefix} target=prompt_compiler rule=NO_SUBTITLE_SCREEN_TEXT issue=prompt 依赖或诱发字幕/屏幕/文件可读文字传递剧情。"
            " repair_route=prompt_compiler：集中写明禁止字幕、屏幕文字、英文字幕、文字浮层；把证据改为道具来源、递出动作、识别反应和停顿落点。"
        )

    for line in re.split(r"[\n。；;]", prompt or ""):
        if _SEEDANCE_VISIBLE_EMOTION_RE.search(line) and not _SEEDANCE_VISIBLE_ACTION_ANCHOR_RE.search(line):
            issues.append(
                f"{prefix} target=prompt_compiler rule=VISIBLE_EMOTION_ANCHOR_REQUIRED issue=抽象情绪/精品感词未落到可见动作：{line.strip()[:80]}。"
                " repair_route=prompt_compiler：保留戏剧含义，改为 1 个可见身体/表情锚点，如下颌收紧、眼神停住、手指松开、呼吸停顿或肩背僵住。"
            )
            break

    return issues


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------
def quality_inspector_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    segment_index = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
    prompt = outputs.get(f"compiled_segment_{segment_index}", "")
    current_fragment_id = _fragment_id_for_segment_index(state.get("segment_names") or [], segment_index)
    planner_segment = _segment_block(outputs.get("story_planner", ""), segment_index, current_fragment_id)
    director_segment = _segment_block(outputs.get("shot_director", ""), segment_index, current_fragment_id)
    source_block = re.search(
        r"source_script_events\s*:([\s\S]*?)(?=\n[a-z_]+\s*:|\Z)",
        planner_segment,
    )
    segment_source = (source_block.group(1).strip() if source_block else planner_segment).strip()
    guard_report = state.get("system_guard_report") or ""
    uses_shot_sequence = _prompt_uses_shot_sequence(prompt)

    qc_issues: list[str] = []
    if guard_report:
        qc_issues.extend([line for line in guard_report.splitlines() if line.strip()])

    if planner_segment and not _planner_has_reaction_handoff(planner_segment):
        qc_issues.append("- story_planner 未说明当前片段的承接/反应计划。")
    if planner_segment and re.search(r"(?:source_script_events|施工剧本原文事件)\s*[:：]", planner_segment):
        source_block = re.search(
            r"(?:source_script_events|施工剧本原文事件)\s*[:：]([\s\S]*?)(?=\n\s*(?:[a-z_]+|出现人物|入场状态|出场状态|承接要求|镜头导演交接)\s*[:：]|\Z)",
            planner_segment,
        )
        source_items = re.findall(r"-\s*(.+)", source_block.group(1) if source_block else "")
        if len(source_items) == 1 and re.search(r"[，。！？；].+[，。！？；]", source_items[0]):
            qc_issues.append(
                "- story_planner 似乎把完整发言/动作单元压成单条笼统事件，需更清楚标出片段覆盖事件。"
            )

    # === shot_director schema validation ===
    if director_segment:
        # English v1 fields and the current Chinese contract are both valid.
        if not _has_yaml_field(director_segment, "fragment_task"):
            qc_issues.append("- shot_director 缺少片段任务字段。")
        if not _has_yaml_field(director_segment, "rhythm"):
            qc_issues.append("- shot_director 缺少节奏字段。")
        if re.search(r"(?m)^\s*schema_version\s*:\s*shot_director_local_fallback_v1\s*$", director_segment):
            qc_issues.append("- shot_director 输出来自旧本地兜底，必须重跑镜头导演并确保大模型连接成功。")
        if not _has_yaml_field(director_segment, "shots"):
            qc_issues.append("- shot_director 未给出当前片段的镜头列表。")
        if _has_yaml_field(director_segment, "shots"):
            shot_blocks = _MAIN_SHOT_BLOCK_RE.findall(director_segment)
            if not shot_blocks:
                qc_issues.append("- shot_director 镜头列表中没有合法镜头编号。")
            for shot_id_raw, shot_body in shot_blocks:
                shot_id = shot_id_raw.strip()
                for field in (
                    "duration",
                    "task",
                    "subject",
                    "action",
                    "dialogue",
                    "must_carry",
                    "cut_point",
                    "continuity",
                ):
                    if not _has_yaml_field(shot_body, field):
                        qc_issues.append(f"- {shot_id} 缺少字段 {field}。")
                if not _has_yaml_field(shot_body, "shot"):
                    qc_issues.append(f"- {shot_id} 缺少镜头字段。")

                duration = _yaml_line_field(shot_body, "duration")
                if duration:
                    if not re.search(r"(?:\d+(?:\.\d+)?\s*(?:-|~|–|—)\s*)?\d+(?:\.\d+)?\s*(?:秒|s)", duration):
                        qc_issues.append(
                            f"- {shot_id} 的 duration 格式非法（{duration}）；"
                            "应为时长或连续时间段格式，例如 2秒、0-2秒、2-5秒。"
                        )

                cut_point = _yaml_line_field(shot_body, "cut_point")
                if cut_point and len(cut_point) < 6:
                    qc_issues.append(
                        f"- {shot_id} 的 cut_point 过于简短；"
                        "必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。"
                    )

    has_shot_sequence_structure = re.search(
        r"【风格锚点】[\s\S]*【画幅锚点】[\s\S]*"
        r"(?:【空间与首帧总控】|【连续性状态契约】)[\s\S]*"
        r"【人物】[\s\S]*【镜头序列】[\s\S]*(?:【约束】|【全段硬约束】)",
        prompt,
    )
    has_compact_seedance_structure = re.search(
        r"【画面基底】[\s\S]*【镜头序列】[\s\S]*【约束】",
        prompt,
    )
    if not (has_compact_seedance_structure or has_shot_sequence_structure):
        qc_issues.append(
            "- prompt 缺少规定结构，应包含【画面基底】【镜头序列】【约束】，或【风格锚点】【画幅锚点】【人物】【镜头序列】【约束】。"
        )
    if planner_segment and re.search(r"reaction_plan\s*:\s*.*片段内", planner_segment) and not re.search(
        r"受击|反应|表情|眼神|嘴唇|下颌|呼吸|停顿", prompt
    ):
        qc_issues.append("- 当前片段规划要求片段内承受到击/反应，但 prompt 未写出可见落点。")

    qc_issues.extend(_seedance_contract_qc_issues(prompt, planner_segment, director_segment, state, current_fragment_id))

    if "同一机位继续" in prompt:
        qc_issues.append(
            '- [PROMPT-NO-SAME-CAMERA-ABUSE-001] prompt 仍使用"同一机位继续"：应改成"镜头保持在A身上"、"固定机位保持在某空间锚点"、"镜头切至B"或"镜头切近至/拉开至A"。'
        )

    if re.search(r"压迫感|张力|炸点|钩子|气口|留白|情绪顶点|受压反应|空气收紧|前慢后碎|稳慢压", prompt):
        qc_issues.append(
            "- [PROMPT-VISIBLE-BODY-LANGUAGE-001] prompt 仍残留抽象导演词：必须翻译成停顿时长、视线方向、肩膀收紧、下颌收紧、嘴唇停住、身体距离或门/道具状态等可见画面。"
        )
    if re.search(r"站在(?:门框|窗框|框架)里|(?:门框|窗框).{0,8}(?:形成|构成).{0,8}(?:前景|压线|框景)|前景压线|框住人物|被(?:门框|窗框|框架)框住|框景压迫", prompt):
        qc_issues.append(
            "- [PROMPT-SHOT-EXPRESSION-CORE-001] prompt 仍残留不稳定构图表达：门、窗、桌等只能作为空间边界或阻隔物，"
            "不要写成框住人物的构图术语；改成同侧过肩机位、门口/门边站位和具体人物动作。"
        )

    timeline_blocks = _timeline_blocks(prompt)
    qc_issues.extend(_prompt_shot_density_issues(prompt, planner_segment, director_segment, timeline_blocks))
    qc_issues.extend(
        _seedance_gate_issues(state, prompt, planner_segment, director_segment, segment_index, current_fragment_id)
    )
    if not uses_shot_sequence:
        for block_idx, (_blk_start, _blk_end, blk_body) in enumerate(timeline_blocks[1:], start=2):
            prefix = blk_body[:120]
            if not re.search(r"镜头保持在|固定机位保持|镜头切至|镜头切到|镜头切近至|镜头拉开至|切至|切到|切近至|拉开至", prefix):
                qc_issues.append(
                    f"- [PROMPT-SHOT-TRANSITION-VERB-001] 时间轴第 {block_idx} 个时间段缺少精确衔接词：必须明确写同主体保持、固定机位保持、主体切镜或同主体景别变化。"
                )
                break
    elif "切镜时机" not in prompt:
        qc_issues.append("- 镜头序列缺少切镜时机：非末尾镜头应写明动作顶点、台词断点、信息看清或反应出现后的切镜触发。")

    # === [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单段反打硬失败 — 检查编译后 prompt ===
    if _REVERSE_SHOT_INSIDE_SEGMENT_RE.search(prompt):
        qc_issues.append(
            '- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 编译后 prompt 出现"反打至"：'
            "Seedance 是单镜头连续生成模型，单次生成内无法完成跨轴反打，会让人物左右颠倒、背景翻面。"
            "需要反打的两镜必须拆成相邻两个 segment，并通过转身/越轴中性镜头/场景固定机位过渡。"
        )

    # === [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单时间段轴线锁 — 检查编译后 prompt ===
    compiled_timeline_blocks = _timeline_blocks(prompt)
    for block_idx, (_blk_start, _blk_end, blk_body) in enumerate(compiled_timeline_blocks, start=1):
        if re.search(
            r"(?:摄影机|机位|镜头)?(?:位于|在)?"
            r"(?:商北琛|乔熙|严飞|苏小可|小豆丁|人物|主体|他|她|两人).{0,8}"
            r"(?:左前方|右前方|左后方|右后方)",
            blk_body,
        ):
            qc_issues.append(
                f"- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 编译后 prompt 的时间轴第 {block_idx} 个时间段"
                "使用了人物相对左右机位。人物正面、背面或转身后左/右会反，模型无法稳定理解；"
                "必须改成同侧轴线内的简洁机位。"
            )
            break
        if _AXIS_LEFT_RE.search(blk_body) and _AXIS_RIGHT_RE.search(blk_body):
            qc_issues.append(
                f"- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 编译后 prompt 的时间轴第 {block_idx} 个时间段"
                '同时出现"左前方"和"右前方"机位（跨 180° 轴线）。'
                "Seedance 单次生成无法跨轴反打，会让人物左右颠倒、背景翻面。"
                "单段 prompt 必须保持同侧轴线，拆轴必须拆 segment。"
            )
            break

    fail_issues = [i for i in qc_issues if not i.strip().startswith("- [warn]")]
    qc_status = "fail" if fail_issues else ("warn" if qc_issues else "pass")

    report_sections = [
        f"总体评级：{qc_status}",
        "【知识驱动质检】",
        ("\n".join(qc_issues) if qc_issues else "无"),
    ]
    output = "\n".join(report_sections)

    outputs[f"quality_inspector_segment_{segment_index}"] = output
    outputs["quality_inspector"] = output
    return _persist_update(
        state,
        {
            "status": "running_phase_2",
            "step": "step_3_inspect",
            "message": f"第 {segment_index} 段知识驱动质检完成：{qc_status}（3/3）",
            "agent_outputs": outputs,
            "last_qc_status": qc_status,
        },
    )


def qc_router_node(state: DirectorState) -> DirectorState:
    qc_status = state.get("last_qc_status", "warn")
    retry_count = int(state.get("qc_retry_count") or 0)
    if qc_status == "fail" and retry_count < MAX_QC_RETRIES:
        return _persist_update(
            state,
            {
                "qc_retry_count": retry_count + 1,
                "revision_instruction": _agent_outputs(state).get("quality_inspector", ""),
                "step": "step_2_compile",
                "message": "机械质检发现问题，正在自动返修当前片段 Prompt。",
            },
        )
    return _persist_update(
        state,
        {
            "revision_instruction": "",
        },
    )


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------
def route_after_qc(state: DirectorState) -> str:
    if state.get("revision_instruction"):
        return "prompt_compiler"
    return "segment_complete"
