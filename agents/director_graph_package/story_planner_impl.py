"""Story planner implementation extracted from legacy_impl.

Owns story planning, schema repair, validation, and planner segment parsing.
"""
from __future__ import annotations

import re
import time
from typing import Any

from .types import DirectorState
from . import legacy_impl as _legacy
from .helpers import _agent_runtime_trace, _fragment_line_pattern, _truncate_for_prompt
from .llm import call_llm
from .planning_context_impl import _script_fidelity_rules
from .state_store import _agent_outputs, _persist_update
from ..knowledge_base import query_rule_registry
from ..request_context import emit_runtime_event

STORY_PLANNER_MAX_SCHEMA_ATTEMPTS = _legacy.STORY_PLANNER_MAX_SCHEMA_ATTEMPTS

_agent_configured = _legacy._agent_configured
_record_knowledge_metadata = _legacy._record_knowledge_metadata

def _story_planner_slim_rule_digest(context_hint: str, *, n_results: int = 3) -> tuple[str, dict[str, Any]]:
    """Fetch a tiny rule-registry digest for segmentation without broad RAG context."""
    emit_runtime_event(
        "knowledge_retrieval_started",
        agent_name="story_planner",
        context_hint_preview=(context_hint or "")[:240],
        retrieval_mode="rule_registry_slim",
    )
    try:
        results = query_rule_registry(context_hint, agent_name="story_planner", n_results=n_results)
    except Exception as exc:
        emit_runtime_event(
            "knowledge_retrieval_failed",
            agent_name="story_planner",
            retrieval_mode="rule_registry_slim",
            error_type=type(exc).__name__,
        )
        return "", {
            "retrieval_mode": "rule_registry_slim",
            "matched_sources": [],
            "critical_sources": [],
            "result_count": 0,
            "registry_rule_ids": [],
            "error": str(exc)[:300],
        }

    lines: list[str] = []
    rule_ids: list[str] = []
    for item in results:
        rule_id = str(item.get("rule_id") or "").strip()
        title = str(item.get("title") or "").strip()
        text = str(item.get("text") or "")
        instruction = ""
        avoid = ""
        instruction_match = re.search(r"(?m)^执行指令:\s*(.+)$", text)
        avoid_match = re.search(r"(?m)^例外边界:\s*(.+)$", text)
        if instruction_match:
            instruction = instruction_match.group(1).strip()
        if avoid_match:
            avoid = avoid_match.group(1).strip()
        if not instruction:
            continue

        rule_ids.append(rule_id)
        label = f"{rule_id} {title}".strip()
        line = f"- {label}: {_truncate_for_prompt(instruction, 120)}"
        if avoid:
            line += f"；例外：{_truncate_for_prompt(avoid, 80)}"
        lines.append(line)

    metadata = {
        "retrieval_mode": "rule_registry_slim",
        "matched_sources": ["rule_registry.yaml"] if lines else [],
        "critical_sources": [],
        "result_count": len(lines),
        "registry_rule_ids": rule_ids,
    }
    emit_runtime_event(
        "knowledge_retrieval_completed",
        agent_name="story_planner",
        retrieval_mode=metadata["retrieval_mode"],
        matched_sources=metadata["matched_sources"],
        registry_rule_ids=metadata["registry_rule_ids"],
        result_count=metadata["result_count"],
    )
    return "\n".join(lines), metadata

def _story_planner_rhythm_boundary_rules() -> str:
    return (
        "【结构规划师权限边界】\n"
        "1. 结构规划师只负责把当前施工剧本拆成给镜头导演使用的片段清单。\n"
        "2. 节奏总控只提供拆片边界、目标时长、反应归属、段尾是否停在未完成状态和尾帧承接；不能被当成新剧情事件来源。\n"
        "3. 施工剧本原文事件必须逐条引用当前施工剧本中的原文子串，不得概括、改写、合并或补写。\n"
        "4. 承接要求只能写结构判断，例如\"反应留在本段\"\"下一段承接\"\"尾帧停在照片仍在手中\"；不得新增动作、道具、龙套反应或人物调度。\n"
        "5. 只定义\"这一段从哪到哪\"和\"交给下个 agent 时需要怎样承接\"；不定义镜头语言、不定义机位、不定义具体运镜。\n"
    )

def _story_planner_granularity_rules() -> str:
    return (
        "【结构规划师拆片指南（Seedance 2.0 15秒剧情任务版）】\n"
        "1. 核心目标：每个片段承载一个 15 秒以内可完成的剧情任务；不追求多拆，也不允许把多个任务粗暴塞进一段。\n"
        "2. 单段推荐 4-8 条施工剧本原文事件。超过 8 条必须拆开；少于 4 条通常合并到相邻片段。\n"
        "3. 少于 4 条仍可独立的例外：明确结尾悬念、段尾停在未完成状态、尾帧承接、重大反转落点或下一段必须从该状态接起。\n"
        "4. 普通停顿、受击反应、信息揭示默认留在当前片段内部，由镜头导演处理，不自动拆成新片段。\n"
        "5. 拆片必须服从节奏总控给结构规划师的操作单：时长范围、停顿、不拆、压缩、段尾状态、反应归属和尾帧承接。\n"
        "6. 反应归属只做高层判断：留在本段、下一段承接、无须独立反应；不要替镜头导演设计具体镜头。\n"
        "7. 一个片段只承担一个核心剧情任务；若同一段里同时包含入场、对白、群体反应、道具动作、空间变化、情绪重音，应优先拆开，而不是把所有任务压进一个片段。\n"
        "8. 大动作优先拆成连续小任务链，例如进入门缝→撞上→扶住→停住；不要把复杂动作整包塞成一句笼统事件后再期待下游补救。\n"
        "9. 急促动作、短位移、冲入、小跑聚拢、开门入场、上下车或电梯进出，若没有完整发言、信息揭示或明确反应落点，目标时长必须压到 2-5秒；不要写成 8-10秒。\n"
        "10. 文戏/情绪戏/对白戏优先保持可延长的连续段；武戏/高动作冲突戏优先拆成可拼接的短段。\n"
    )

def _extract_yaml_sections(yaml_text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if re.match(_fragment_line_pattern(), stripped, re.IGNORECASE):
            if current:
                sections.append("\n".join(current))
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        sections.append("\n".join(current))
    return sections

def _extract_fragment_id(section: str) -> str:
    match = re.search(r"(?m)^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?([^\"'\s#]+)[\"']?", section)
    return match.group(1).strip() if match else ""

def _normalise_fragment_section_id(section: str, index: int) -> str:
    """Force planner fragment ids into the runtime contract: F01, F02, ..."""
    old_id = _extract_fragment_id(section)
    new_id = f"F{index:02d}"
    updated = re.sub(
        r"(?m)^(\s*-?\s*(?:fragment_id|片段编号)\s*:\s*)[\"']?[^\"'\s#]+[\"']?",
        rf'\1"{new_id}"',
        section,
        count=1,
    )
    if old_id and old_id != new_id:
        updated = re.sub(rf"\b{re.escape(old_id)}(?=\b|[-_])", new_id, updated)
    return updated

def _is_missing_planner_field(section: str, field: str) -> bool:
    return not re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:", section)

def _has_planner_field_alias(section: str, fields: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:", section) for field in fields)

def _has_planner_field_any(section: str, fields: tuple[str, ...]) -> bool:
    return any(not _is_missing_planner_field(section, field) for field in fields)

def _field_value(section: str, field: str) -> str:
    fields = {
        "dramatic_unit": ("dramatic_unit", "片段任务", "戏剧单元"),
        "duration_target": ("duration_target", "目标时长"),
        "reaction_plan": ("reaction_plan", "承接要求"),
        "director_brief": ("director_brief", "导演交接", "镜头导演交接", "shot_director_handoff"),
        "intra_fragment_rhythm": ("片段内节奏分配", "段内节奏分配", "内部节拍预算", "intra_fragment_rhythm", "internal_beat_budget"),
    }.get(field, (field,))
    for candidate in fields:
        match = re.search(rf"(?m)^\s*-?\s*{re.escape(candidate)}\s*:\s*[\"']?(.+?)[\"']?\s*$", section)
        if match:
            return match.group(1).strip()
    return ""

def _infer_boundary_reason(section: str) -> str:
    dramatic_unit = _field_value(section, "dramatic_unit")
    events_block = re.search(r"source_script_events\s*:([\s\S]*?)(?=\n\s*[a-z_]+\s*:|\n\s*shots\s*:|\Z)", section)
    events = re.findall(r"(?m)^\s*-\s*[\"']?(.+?)[\"']?\s*$", events_block.group(1) if events_block else "")
    event_hint = "、".join(event.strip() for event in events[:2] if event.strip())
    core = dramatic_unit or event_hint or "当前动作单元"
    return f'本片段围绕"{core}"形成独立戏剧动作单元；在此处开收段可保持动作、台词与受击反应完整。'

def _infer_reaction_plan(section: str) -> str:
    dramatic_unit = _field_value(section, "dramatic_unit") or "当前片段"
    has_reaction_signal = re.search(
        r"受击|反应|震|惊|愣|停顿|目光|os|旁白|冲击|权力|压制|反转|追问|质问|台词|对白",
        section,
        re.IGNORECASE,
    )
    if has_reaction_signal:
        return (
            f"{dramatic_unit} 的信息冲击与人物反应留在本片段内部承接，"
            "下游镜头导演负责决定具体反应镜头与动作落点。"
        )
    return (
        f"{dramatic_unit} 不涉及独立受击反应，保持片段内动作/对白连续承接，"
        "无需升级为独立片段。"
    )

def _infer_fragment_task(section: str) -> str:
    events = _source_script_events(section)
    duration = _field_value(section, "duration_target")
    first_events = "；".join(event.strip() for event in events[:2] if event.strip())
    if first_events:
        suffix = f"，目标时长 {duration}" if duration else ""
        return f"覆盖本片段原文事件：{first_events}{suffix}"
    reaction_plan = _field_value(section, "reaction_plan")
    if reaction_plan:
        return f"围绕承接要求组织本片段：{reaction_plan}"
    return "覆盖本片段内的原文事件，不新增镜头导演职责外的剧情内容。"

def _infer_shot_director_handoff(section: str) -> str:
    duration = _field_value(section, "duration_target") or "按目标时长执行"
    reaction_plan = _field_value(section, "reaction_plan") or "按片段内动作和台词自然承接"
    exit_state = _field_value(section, "出场状态") or _field_value(section, "exit_state")
    exit_part = f"结尾画面按出场状态承接：{exit_state}" if exit_state else "结尾画面按本片段最后一个原文事件承接"
    return (
        f"镜头导演只覆盖本片段原文事件；目标时长：{duration}；承接要求：{reaction_plan}；"
        f"{exit_part}；不得新增剧本外人物、台词、道具、动作或空间。"
    )

def _infer_intra_fragment_rhythm(section: str) -> str:
    events = _source_script_events(section)
    duration = _field_value(section, "duration_target") or "片段目标时长"
    rhythm_type = _field_value(section, "节奏类型")
    action_rhythm = _field_value(section, "动作节奏指导")
    text = "\n".join([rhythm_type, action_rhythm, "\n".join(events)])
    has_fast_action = bool(re.search(r"急|忙|叠|短促|紧凑|快|闹钟|手机|穿衣|外套|扣衣|乱蹬|躲", text))
    has_dialogue_or_reaction = bool(re.search(r"：|:|拒绝|哄|安抚|反应|停住|犹豫|看清|照片|OS", text))
    if has_fast_action and has_dialogue_or_reaction:
        return (
            f"前段用 2-3秒完成急促动作链；后段在剩余{duration}内完成台词、反应或情绪落点。"
            "镜头导演在同一片段内部控制快慢，不拆成新片段。"
        )
    if has_fast_action:
        return f"全段按{duration}紧凑执行，短动作连续完成，不为单个动作另起片段。"
    return f"按整体目标时长{duration}执行；若内部出现停顿或反应，由镜头导演在片段内处理。"

def _planner_field_indent(lines: list[str]) -> str:
    indent = "  " if re.match(r"^\s*-\s*(?:fragment_id|片段编号)\s*:", lines[0] if lines else "") else ""
    for line in lines[1:]:
        field_match = re.match(r"^(\s+)(?:[a-z_]+|[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_/]*)\s*:", line)
        if field_match:
            return field_match.group(1)
    return indent

def _insert_planner_field_before(
    lines: list[str],
    *,
    field: str,
    value: str,
    before_fields: tuple[str, ...],
) -> None:
    indent = _planner_field_indent(lines)
    insert_at = len(lines)
    before_pattern = "|".join(re.escape(item) for item in before_fields)
    for idx, line in enumerate(lines):
        if re.match(rf"^\s*(?:{before_pattern})\s*:", line):
            insert_at = idx
            break
    safe_value = value.replace('"', "'")
    lines.insert(insert_at, f'{indent}{field}: "{safe_value}"')

def _script_event_lines(script: str) -> list[str]:
    return [line for line in (script or "").splitlines() if line.strip()]

def _split_merged_source_event(event: str, script_lines: list[str]) -> list[str]:
    event = (event or "").strip()
    if not event or not script_lines or event in script_lines:
        return [event] if event else []

    for start in range(len(script_lines)):
        merged = ""
        chunk: list[str] = []
        for current in script_lines[start:]:
            merged += current
            chunk.append(current)
            if merged == event and len(chunk) > 1:
                return chunk
            if len(merged) >= len(event):
                break
    return [event]

def _replace_source_script_events_block(section: str, events: list[str]) -> str:
    match = re.search(
        r"(?m)^(\s*)(source_script_events|施工剧本原文事件|当前剧本事件)\s*:\s*"
        r"([\s\S]*?)(?=\n\s*(?:[a-z_]+|[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_/]*)\s*:|\n\s*-?\s*(?:fragment_id|片段编号)\s*:|\Z)",
        section,
    )
    if not match:
        return section

    field_indent = match.group(1)
    item_indent = field_indent + "  "
    field_name = match.group(2)
    block_lines = [f"{field_indent}{field_name}:"]
    for event in events:
        safe_event = event.replace('"', "'")
        block_lines.append(f'{item_indent}- "{safe_event}"')
    replacement = "\n".join(block_lines)
    return section[: match.start()] + replacement + section[match.end() :]

def _repair_story_planner_source_events(section: str, script: str) -> str:
    script_lines = _script_event_lines(script)
    if not script_lines:
        return section

    events = _source_script_events(section)
    if not events:
        return section

    repaired_events: list[str] = []
    changed = False
    for event in events:
        expanded = _split_merged_source_event(event, script_lines)
        repaired_events.extend(expanded)
        if expanded != [event]:
            changed = True
    if not changed:
        return section
    return _replace_source_script_events_block(section, repaired_events)

def _normalise_story_planner_output(planner_output: str, source_script: str = "") -> str:
    """Autofill repairable story_planner schema omissions before validation."""
    sections = _extract_yaml_sections(planner_output or "")
    if not sections:
        return (planner_output or "").strip()

    normalised_sections: list[str] = []
    for section in sections:
        lines = section.splitlines()
        section_after_boundary = "\n".join(lines)
        if not _has_planner_field_alias(section_after_boundary, ("dramatic_unit", "片段任务", "戏剧单元")):
            _insert_planner_field_before(
                lines,
                field="片段任务",
                value=_infer_fragment_task(section_after_boundary),
                before_fields=("duration_target", "目标时长", "source_script_events", "施工剧本原文事件"),
            )
            section_after_boundary = "\n".join(lines)
        if not _has_planner_field_alias(section_after_boundary, ("reaction_plan", "承接要求")):
            _insert_planner_field_before(
                lines,
                field="承接要求",
                value=_infer_reaction_plan(section_after_boundary),
                before_fields=("director_brief", "beat_design", "shots"),
            )
            section_after_boundary = "\n".join(lines)
        if not _has_planner_field_alias(section_after_boundary, ("片段内节奏分配", "段内节奏分配", "内部节拍预算", "intra_fragment_rhythm", "internal_beat_budget")):
            _insert_planner_field_before(
                lines,
                field="片段内节奏分配",
                value=_infer_intra_fragment_rhythm(section_after_boundary),
                before_fields=("动作节奏指导", "施工剧本原文事件", "source_script_events", "director_brief", "beat_design", "shots"),
            )
            section_after_boundary = "\n".join(lines)
        if not _has_planner_field_alias(section_after_boundary, ("shot_director_handoff", "镜头导演交接", "导演交接")):
            _insert_planner_field_before(
                lines,
                field="镜头导演交接",
                value=_infer_shot_director_handoff(section_after_boundary),
                before_fields=("director_brief", "beat_design", "shots"),
            )
        section_text = "\n".join(lines).strip()
        if source_script:
            section_text = _repair_story_planner_source_events(section_text, source_script)
        normalised_sections.append(_normalise_fragment_section_id(section_text, len(normalised_sections) + 1))

    return "\n\n".join(normalised_sections).strip()

def _source_script_events(section: str) -> list[str]:
    block_match = re.search(
        r"(?m)^\s*(?:source_script_events|施工剧本原文事件|当前剧本事件)\s*:\s*"
        r"([\s\S]*?)(?=\n\s*(?:[a-z_]+|[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_/]*)\s*:|\n\s*-?\s*(?:fragment_id|片段编号)\s*:|\Z)",
        section,
    )
    block = block_match.group(1) if block_match else ""
    return [
        item.strip().strip("\"'")
        for item in re.findall(r"(?m)^\s*-\s*[\"']?(.+?)[\"']?\s*$", block)
        if item.strip()
    ]

_URGENT_SHORT_ACTION_RE = re.compile(
    r"急促|小跑|快步|冲|闯|赶|跑|扑|撞|追|抢|打断|推开|拉开|踉跄|摔|"
    r"开门|进门|出门|上车|下车|电梯|门口|聚拢|列队|整理仪表"
)

_DURATION_EXTENSION_REASON_RE = re.compile(
    r"长台词|长对白|质问|命令|信息揭示|发现|看清|照片|受击|反转|停住|愣"
)

_NO_REACTION_RE = re.compile(r"无需独立反应|无须独立反应|不涉及独立反应|无受击|无需反应|无须反应")

_DURATION_SECONDS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:[-—–~～至到]\s*(\d+(?:\.\d+)?))?\s*(?:秒|s)\b",
    re.IGNORECASE,
)

_DOMESTIC_SCRAMBLE_MARKERS = (
    ("闹钟", "alarm"),
    ("手机", "phone"),
    ("外套", "衣服", "穿衣", "扣衣", "套衣", "coat", "jacket"),
    ("小豆丁", "孩子", "kid", "child"),
)

_DIALOGUE_UNIT_SIGNAL_RE = re.compile(
    r"对话|台词|发言|问答|追问|反问|质问|解释|回应|回答|安抚|哄|"
    r"问道|问她|问他|问起|说道|说完|喊道|叫住|OS|：|:",
    re.IGNORECASE,
)

_DIALOGUE_UNIT_BOUNDARY_ALLOW_RE = re.compile(
    r"场景转换|转场|空间变化|状态变化|新话题|话题转向|信息揭示|受击落点|反应落点|"
    r"独立反应完成|情绪落地|进入新动作单元|进入下一动作单元|离开|出门|进门|第二天|下一场"
)

_DIALOGUE_CHARACTER_HINTS = (
    "乔熙",
    "小豆丁",
    "女主",
    "妈妈",
    "孩子",
    "商北琛",
    "严飞",
    "苏小可",
)

def _duration_upper_seconds(text: str) -> float | None:
    values: list[float] = []
    for match in _DURATION_SECONDS_RE.finditer(text or ""):
        values.append(float(match.group(1)))
        if match.group(2) is not None:
            values.append(float(match.group(2)))
    return max(values) if values else None

def _has_duration_extension_reason(text: str) -> bool:
    normalized = _NO_REACTION_RE.sub("", text or "")
    return bool(_DURATION_EXTENSION_REASON_RE.search(normalized))

_INTERNAL_FAST_BEAT_RE = re.compile(
    r"急|忙|叠|短促|紧凑|快|抢时间|闹钟|手机|通话|免提|穿衣|外套|扣衣|套衣|乱蹬|躲",
    re.IGNORECASE,
)

_INTERNAL_LATER_BEAT_RE = re.compile(
    r"后段|第二|第2|剩余|之后|随后|台词|拒绝|哄|安抚|反应|情绪|落点|停住|"
    r"信息|揭示|回忆|闪回|OS|承诺|回应|亲吻|照片|爸爸|受击",
    re.IGNORECASE,
)

def _has_short_fast_internal_beat(text: str) -> bool:
    if not text or not _INTERNAL_FAST_BEAT_RE.search(text):
        return False
    for match in _DURATION_SECONDS_RE.finditer(text):
        values = [float(match.group(1))]
        if match.group(2) is not None:
            values.append(float(match.group(2)))
        if max(values) > 6:
            continue
        context = text[max(0, match.start() - 28) : min(len(text), match.end() + 36)]
        if _INTERNAL_FAST_BEAT_RE.search(context) or re.search(r"前段|第一|第1|先|开头|起始", context):
            return True
    return False

def _has_later_internal_beat(text: str) -> bool:
    return bool(text and _INTERNAL_LATER_BEAT_RE.search(text))

def _story_planner_duration_contract_issues(planner_output: str) -> list[str]:
    sections = _extract_yaml_sections(planner_output)
    issues: list[str] = []
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        duration = _field_value(section, "duration_target")
        upper_seconds = _duration_upper_seconds(duration)
        if upper_seconds is None or upper_seconds <= 6:
            continue

        event_text = "\n".join(_source_script_events(section))
        combined_text = "\n".join(
            part
            for part in (
                event_text,
                _field_value(section, "dramatic_unit"),
                _field_value(section, "reaction_plan"),
                duration,
            )
            if part
        )
        if not _URGENT_SHORT_ACTION_RE.search(combined_text):
            continue
        if _has_duration_extension_reason(combined_text):
            continue

        issues.append(
            f"{fragment_id} 是急促短动作但目标时长为 {duration}；"
            "无长对白、信息揭示或明确反应落点时必须压到 2-5秒，多个短动作叠加也应控制在 5-6秒，不能写成慢动作段。"
        )
    return issues

def _rhythm_planning_contract_issues(planner_output: str) -> list[str]:
    sections = _extract_yaml_sections(planner_output)
    issues: list[str] = []
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        required_fields = (
            ("节奏类型", ("节奏类型",)),
            ("事件密度判断", ("事件密度判断",)),
            ("动作节奏指导", ("动作节奏指导",)),
            ("片段内节奏分配", ("片段内节奏分配", "段内节奏分配", "内部节拍预算", "intra_fragment_rhythm", "internal_beat_budget")),
        )
        for display_name, aliases in required_fields:
            if not _has_planner_field_alias(section, aliases):
                issues.append(f"{fragment_id} 缺少字段 {display_name}。")

        rhythm_type = _field_value(section, "节奏类型")
        action_rhythm = _field_value(section, "动作节奏指导")
        if rhythm_type and "快" in rhythm_type:
            duration = _field_value(section, "duration_target")
            upper_seconds = _duration_upper_seconds(duration)
            if upper_seconds is not None and upper_seconds > 6:
                intra_rhythm = _field_value(section, "intra_fragment_rhythm")
                if not (
                    _has_short_fast_internal_beat(intra_rhythm)
                    and _has_later_internal_beat(intra_rhythm)
                ):
                    issues.append(
                        f"{fragment_id} 标记为快节奏且目标时长为 {duration}；"
                        "合并戏剧单元可以超过 6秒，但必须在片段内节奏分配中把急促动作小节拍压到 5-6秒以内，"
                        "并说明后续台词、反应或情绪落点的时间预算。"
                    )
            if action_rhythm and not re.search(r"急|忙|叠|短促|紧凑|抢时间", action_rhythm):
                issues.append(f"{fragment_id} 的动作节奏指导没有明确急忙、叠压或短促执行。")
    return issues

def _story_planner_fast_cluster_merge_issues(planner_output: str) -> list[str]:
    sections = _extract_yaml_sections(planner_output)
    if len(sections) <= 1:
        return []

    for previous_section, next_section in zip(sections, sections[1:]):
        pair_text = "\n".join(
            "\n".join(
                part
                for part in (
                    _field_value(section, "dramatic_unit"),
                    _field_value(section, "duration_target"),
                    _field_value(section, "节奏类型"),
                    _field_value(section, "事件密度判断"),
                    _field_value(section, "动作节奏指导"),
                    _field_value(section, "intra_fragment_rhythm"),
                    _field_value(section, "reaction_plan"),
                    "\n".join(_source_script_events(section)),
                )
                if part
            )
            for section in (previous_section, next_section)
        )
        lowered_pair = pair_text.lower()
        pair_marker_hits = sum(any(marker.lower() in lowered_pair for marker in markers) for markers in _DOMESTIC_SCRAMBLE_MARKERS)
        if pair_marker_hits < 4:
            continue
        if re.search(r"照片|书包口滑落|Four Years Ago|One Hour Later|集团|劳斯莱斯|车道|闪回|回忆|看清", pair_text, re.IGNORECASE):
            continue
        first_id = _extract_fragment_id(previous_section) or "unknown"
        second_id = _extract_fragment_id(next_section) or "unknown"
        return [
            f"{first_id}-{second_id} 属于同一晨间穿衣/通话/孩子抗拒戏剧单元，但被拆成相邻片段；"
            "请合并为一个完整生活动作群片段，并用片段内节奏分配写清前段急促动作、后段孩子拒绝/乔熙应对的时间预算。"
        ]

    combined_text = "\n".join(
        "\n".join(
            part
            for part in (
                _field_value(section, "dramatic_unit"),
                _field_value(section, "duration_target"),
                _field_value(section, "节奏类型"),
                _field_value(section, "事件密度判断"),
                _field_value(section, "动作节奏指导"),
                "\n".join(_source_script_events(section)),
            )
            if part
        )
        for section in sections
    )
    lowered = combined_text.lower()
    marker_hits = sum(any(marker.lower() in lowered for marker in markers) for markers in _DOMESTIC_SCRAMBLE_MARKERS)
    if marker_hits < 4:
        return []
    if _has_duration_extension_reason(combined_text):
        return []

    fast_sections = [
        section
        for section in sections
        if "快" in _field_value(section, "节奏类型")
        and (_duration_upper_seconds(_field_value(section, "duration_target")) or 0) <= 6
    ]
    if len(fast_sections) < 2:
        return []

    first_id = _extract_fragment_id(fast_sections[0]) or "unknown"
    last_id = _extract_fragment_id(fast_sections[-1]) or "unknown"
    return [
        f"{first_id}-{last_id} 属于同一急促生活动作群（闹钟/手机/外套/孩子抗拒），但被拆成多个连续快节奏短段；"
        "这类短动作群应优先合并为一个 5-6秒 紧凑段，并在动作节奏指导中写明急急忙忙、动作叠压。"
    ]

def _dialogue_unit_section_text(section: str) -> str:
    return "\n".join(
        part
        for part in (
            _field_value(section, "dramatic_unit"),
            _field_value(section, "节奏类型"),
            _field_value(section, "事件密度判断"),
            _field_value(section, "动作节奏指导"),
            _field_value(section, "intra_fragment_rhythm"),
            _field_value(section, "reaction_plan"),
            _field_value(section, "director_brief"),
            "\n".join(_source_script_events(section)),
        )
        if part
    )

def _dialogue_speakers(events: list[str]) -> set[str]:
    speakers: set[str] = set()
    for event in events:
        match = re.match(r"\s*([^：:\s]{1,12})\s*[：:]", event or "")
        if match:
            speakers.add(match.group(1).strip())
    return speakers

def _dialogue_character_mentions(section: str) -> set[str]:
    events = _source_script_events(section)
    text = _dialogue_unit_section_text(section)
    mentions = _dialogue_speakers(events)
    for character in _DIALOGUE_CHARACTER_HINTS:
        if character in text:
            mentions.add(character)
    return mentions

def _source_event_span(section: str, script_lines: list[str]) -> tuple[int, int] | None:
    indices: list[int] = []
    for event in _source_script_events(section):
        for index, script_line in enumerate(script_lines):
            if event == script_line:
                indices.append(index)
                break
    if not indices:
        return None
    return min(indices), max(indices)

def _has_dialogue_unit_signal(section: str) -> bool:
    events = _source_script_events(section)
    if _dialogue_speakers(events):
        return True
    return bool(_DIALOGUE_UNIT_SIGNAL_RE.search(_dialogue_unit_section_text(section)))

def _dialogue_boundary_allows_split(previous_section: str, next_section: str) -> bool:
    boundary_text = "\n".join(
        part
        for part in (
            _field_value(previous_section, "dramatic_unit"),
            _field_value(previous_section, "reaction_plan"),
            _field_value(previous_section, "director_brief"),
            _field_value(previous_section, "出场状态"),
            _field_value(next_section, "dramatic_unit"),
            _field_value(next_section, "reaction_plan"),
            _field_value(next_section, "director_brief"),
            _field_value(next_section, "入场状态"),
        )
        if part
    )
    normalized = _NO_REACTION_RE.sub("", boundary_text)
    return bool(_DIALOGUE_UNIT_BOUNDARY_ALLOW_RE.search(normalized))

def _story_planner_dialogue_unit_split_issues(planner_output: str, script: str = "") -> list[str]:
    sections = _extract_yaml_sections(planner_output)
    if len(sections) <= 1:
        return []

    script_lines = _script_event_lines(script)
    issues: list[str] = []
    for previous_section, next_section in zip(sections, sections[1:]):
        if not (_has_dialogue_unit_signal(previous_section) and _has_dialogue_unit_signal(next_section)):
            continue

        if script_lines:
            previous_span = _source_event_span(previous_section, script_lines)
            next_span = _source_event_span(next_section, script_lines)
            if previous_span and next_span and next_span[0] > previous_span[1] + 1:
                continue

        previous_characters = _dialogue_character_mentions(previous_section)
        next_characters = _dialogue_character_mentions(next_section)
        shared_characters = previous_characters & next_characters
        combined_characters = previous_characters | next_characters
        if len(combined_characters) < 2:
            continue
        if not shared_characters and not (_dialogue_speakers(_source_script_events(previous_section)) and _dialogue_speakers(_source_script_events(next_section))):
            continue
        if _dialogue_boundary_allows_split(previous_section, next_section):
            continue

        first_id = _extract_fragment_id(previous_section) or "unknown"
        second_id = _extract_fragment_id(next_section) or "unknown"
        issues.append(
            f"{first_id}-{second_id} 属于同一对话戏剧单元，但被拆成连续片段；"
            "完整问答、回应与反应落点应优先留在同一片段内，再由镜头导演在片段内部处理子分镜或 5-8秒生成单元。"
        )
    return issues

def _llm_validate_source_events(
    sections: list[str], script: str
) -> list[str]:
    """Check source_script_events are verbatim substrings of the current script."""
    # Collect all events to review
    fragment_events: list[tuple[str, str]] = []  # (fragment_id, event)
    for section in sections:
        fid = _extract_fragment_id(section) or "unknown"
        for event in _source_script_events(section):
            if event:
                fragment_events.append((fid, event))
    if not fragment_events:
        return []

    issues: list[str] = []
    for fid, event in fragment_events:
        if event not in script:
            issues.append(
                f"{fid} source_script_events must quote original script verbatim: {event}"
            )
            break
    return issues

def _story_planner_soft_validation_issues(planner_output: str) -> list[str]:
    """Collect planning quality concerns that should not block by themselves."""
    sections = _extract_yaml_sections(planner_output)
    issues: list[str] = []
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        event_count = len(_source_script_events(section))
        if event_count > 10:
            issues.append(
                f"{fragment_id} 的 source_script_events 有 {event_count} 条，片段信息偏密；"
                "请由校验导演判断是否真的需要拆分。"
            )

        reaction_match = re.search(
            r"(?:reaction_plan|承接要求)\s*:([\s\S]*?)(?=\n\s*(?:[a-z_]+|[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_/]*)\s*:|\Z)",
            section,
        )
        reaction_text = reaction_match.group(1).strip() if reaction_match else ""
        if reaction_text and not re.search(
            r"片段内|内部|本片段|独立片段|独立主分镜|无需独立|不需要|无需|不涉及|N/?A|none|无受击|画外|背景|虚化|升级|下一段|下个片段|后续片段"
            r"|within|internal|same.?fragment|separate|independent|no.?reaction|covered|absorbed|next.?fragment",
            reaction_text, re.IGNORECASE
        ):
            issues.append(f"{fragment_id} 的承接要求不够直白。")

    return issues

def _story_planner_fragment_count_instruction(script: str) -> str:
    source_lines = len(_script_event_lines(script))
    if source_lines <= 0:
        return ""

    return (
        "【戏剧单元拆片硬约束】\n"
        f"当前施工剧本约 {source_lines} 条非空原文行；这些行只是 source_script_events 覆盖清单，"
        "不是片段数量公式，不得按行数或物理动作数推导片段数。\n"
        "必须先识别戏剧单元：人物目标、阻碍、策略变化、完整问答、反应落点、状态转折。"
        "一连串动作若服务于同一个目标或同一个生活任务，应合并为同一戏剧单元；"
        "节奏快慢只影响目标时长、片段内节奏分配、动作节奏指导和镜头导演交接，不把动作链拆成多个平级片段。\n"
        "如果一个完整戏剧任务内存在快慢变化，请保持为一个片段，并在片段内节奏分配中写清："
        "第1小节约几秒、完成什么戏剧功能；第2小节约几秒、完成什么戏剧功能。\n\n"
    )

def _story_planner_fragment_granularity_issues(planner_output: str) -> list[str]:
    sections = _extract_yaml_sections(planner_output)
    if not sections:
        return []

    total_events = sum(len(_source_script_events(section)) for section in sections)
    fragment_count = len(sections)
    if fragment_count > 1 and total_events > 0 and total_events / fragment_count <= 1.5:
        return [
            f"全局拆片疑似按动作行切分：{total_events} 条 source_script_events 被拆成 {fragment_count} 段，"
            "平均每段只覆盖 1-2 条原文。source_script_events 是覆盖清单，不是戏剧单元；"
            "请按人物目标、阻碍、策略变化、完整问答、反应落点和状态转折合并相邻动作。"
        ]
    return []


_HARD_BOUNDARY_SIGNAL_RE = re.compile(
    r"转场|换场|闪回|回忆|多年后|小时后|第二天|另一|切到|新场景|到达|离开|进入新空间|"
    r"scene change|new scene|flashback|later|meanwhile",
    re.IGNORECASE,
)
_CONTINUATION_SIGNAL_RE = re.compile(
    r"继续|承接|仍|还|正在|刚|同一|下一段承接|反应|回应|问答|追问|解释|安抚|"
    r"电话|手机|外套|孩子|闹钟|门口|电梯门|撞|扶|躲|拉|按|扯|扣|"
    r"continue|same|reaction|reply|respond|question|answer",
    re.IGNORECASE,
)


def _section_boundary_text(previous_section: str, next_section: str) -> str:
    return "\n".join(
        part
        for part in (
            _field_value(previous_section, "dramatic_unit"),
            _field_value(previous_section, "duration_target"),
            _field_value(previous_section, "节奏类型"),
            _field_value(previous_section, "事件密度判断"),
            _field_value(previous_section, "动作节奏指导"),
            _field_value(previous_section, "intra_fragment_rhythm"),
            _field_value(previous_section, "reaction_plan"),
            _field_value(previous_section, "director_brief"),
            _field_value(previous_section, "出场状态"),
            _field_value(next_section, "dramatic_unit"),
            _field_value(next_section, "duration_target"),
            _field_value(next_section, "节奏类型"),
            _field_value(next_section, "事件密度判断"),
            _field_value(next_section, "动作节奏指导"),
            _field_value(next_section, "intra_fragment_rhythm"),
            _field_value(next_section, "reaction_plan"),
            _field_value(next_section, "director_brief"),
            _field_value(next_section, "入场状态"),
            "\n".join(_source_script_events(previous_section)),
            "\n".join(_source_script_events(next_section)),
        )
        if part
    )


def _story_planner_thin_continuation_split_issues(planner_output: str, script: str = "") -> list[str]:
    """Reject adjacent tiny fragments that are just one continuous dramatic unit."""
    sections = _extract_yaml_sections(planner_output)
    if len(sections) <= 1:
        return []

    script_lines = _script_event_lines(script)
    issues: list[str] = []
    for previous_section, next_section in zip(sections, sections[1:]):
        previous_events = _source_script_events(previous_section)
        next_events = _source_script_events(next_section)
        if len(previous_events) > 2 or len(next_events) > 2:
            continue

        if script_lines:
            previous_span = _source_event_span(previous_section, script_lines)
            next_span = _source_event_span(next_section, script_lines)
            if previous_span and next_span and next_span[0] > previous_span[1] + 1:
                continue

        boundary_text = _section_boundary_text(previous_section, next_section)
        if _HARD_BOUNDARY_SIGNAL_RE.search(boundary_text):
            continue

        previous_characters = _dialogue_character_mentions(previous_section)
        next_characters = _dialogue_character_mentions(next_section)
        shared_characters = previous_characters & next_characters
        shared_character_continuity = bool(shared_characters) or (
            bool(previous_characters)
            and bool(next_characters)
            and not (_dialogue_speakers(previous_events) and _dialogue_speakers(next_events))
        )
        if not shared_character_continuity:
            continue

        if _dialogue_boundary_allows_split(previous_section, next_section):
            continue

        combined_duration = " ".join(
            part
            for part in (
                _field_value(previous_section, "duration_target"),
                _field_value(next_section, "duration_target"),
            )
            if part
        )
        short_pair = len(previous_events) + len(next_events) <= 4
        continuation = _CONTINUATION_SIGNAL_RE.search(boundary_text)
        if not (short_pair and continuation):
            continue

        first_id = _extract_fragment_id(previous_section) or "unknown"
        second_id = _extract_fragment_id(next_section) or "unknown"
        issues.append(
            f"{first_id}-{second_id} 疑似把同一连续动作/问答单元拆成过薄相邻片段；"
            f"两段合计仅 {len(previous_events) + len(next_events)} 条原文事件，时长标注为 {combined_duration or '未标注'}。"
            "请优先合并为一个 5-8秒或 8-12秒片段，并用片段内节奏分配写清快慢变化；"
            "只有出现转场、明确状态转折、独立尾帧悬点或必须分段生成的硬边界时才拆开。"
        )
        break
    return issues

def _parse_story_planner_agent_validation(report: str) -> tuple[str, list[str]]:
    text = (report or "").strip()
    if not text:
        return "skip", []

    status = "warn"
    match = re.search(r"总体评级\s*[:：]\s*(通过|提醒|失败|pass|warn|fail)", text, re.IGNORECASE)
    if match:
        raw = match.group(1).lower()
        if raw in {"通过", "pass"}:
            status = "pass"
        elif raw in {"失败", "fail"}:
            status = "fail"
        else:
            status = "warn"
    elif re.search(r"不通过|失败|不可用|无法交给后续", text):
        status = "fail"
    elif re.search(r"通过|可用|可以交给后续", text):
        status = "pass"

    issues: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        body = line.lstrip("-").strip()
        if body and body not in {"无", "没有", "none", "None"}:
            issues.append(body)
    return status, issues

def _run_story_planner_agent_validator(
    *,
    original_script: str,
    scene_output: str,
    planner_output: str,
    soft_issues: list[str],
) -> dict[str, Any]:
    if not soft_issues:
        return {"status": "skip", "issues": [], "reason": "no_soft_issues"}
    agent_name = "validator" if _agent_configured("validator") else ""
    if not agent_name and _agent_configured("script_event_validator"):
        agent_name = "script_event_validator"
    if not agent_name:
        return {"status": "skip", "issues": [], "reason": "validator_not_configured"}

    system_prompt = (
        "你是一位短剧拆片校验导演。你的任务不是机械执行数字规则，"
        "而是判断 story_planner 的拆片结果能不能交给后续镜头导演继续工作。\n\n"
        "只把真正会导致后续无法接住的问题判为失败，例如：片段边界完全混乱、"
        "明显漏掉核心剧情、把不同场景硬塞成一段、使用剧本外事件、人物连续性自相矛盾。\n"
        "下面这些默认只算提醒，不要直接判失败：单段施工剧本原文事件略多、"
        "片段略密、承接要求表述不够漂亮、某段可能还可以再拆。\n\n"
        "输出格式必须严格如下：\n"
        "总体评级：通过/提醒/失败\n"
        "问题清单：\n"
        "- 没有问题就写\"无\"\n"
        "不要输出其他文字。"
    )
    user_prompt = (
        f"【当前施工剧本】\n{_truncate_for_prompt(original_script, 4000)}\n\n"
        f"【story_planner 输出】\n{_truncate_for_prompt(planner_output, 9000)}\n\n"
        "【代码层发现的非阻断提醒】\n"
        + "\n".join(f"- {issue}" for issue in soft_issues)
        + "\n\n请判断这份拆片结果是否足够交给后续镜头导演。"
    )
    started = time.perf_counter()
    try:
        report = call_llm(system_prompt, user_prompt, agent_name=agent_name)
    except Exception as exc:
        return {
            "status": "skip",
            "issues": [],
            "reason": "validator_call_failed",
            "error": str(exc)[:500],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }

    status, issues = _parse_story_planner_agent_validation(report)
    return {
        "status": status,
        "agent_name": agent_name,
        "issues": issues,
        "report": report.strip()[:2000],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

def _validate_story_planner_output(
    planner_output: str,
    script: str = "",
    *,
    require_rhythm_fields: bool = False,
) -> list[str]:
    issues: list[str] = []
    sections = _extract_yaml_sections(planner_output)
    if not sections:
        return ["story_planner 未输出可解析的 fragment_id 分段。"]

    required_field_groups = [
        ("片段编号", ("片段编号", "fragment_id")),
        ("目标时长", ("目标时长", "duration_target")),
        ("施工剧本原文事件", ("施工剧本原文事件", "当前剧本事件", "source_script_events")),
        ("出现人物", ("出现人物", "cast", "active_cast")),
        ("入场状态", ("入场状态", "continuity", "state_contract")),
        ("出场状态", ("出场状态", "continuity", "state_contract")),
        ("承接要求", ("承接要求", "reaction_plan")),
    ]
    source_script = script or ""
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        if not re.fullmatch(r"F\d{2}", fragment_id):
            issues.append(f"{fragment_id} 片段编号不符合 F01/F02 顺序契约。")
        for display_name, aliases in required_field_groups:
            if not _has_planner_field_alias(section, aliases):
                issues.append(f"{fragment_id} 缺少字段 {display_name}。")

    issues.extend(_story_planner_fragment_granularity_issues(planner_output))
    issues.extend(_story_planner_duration_contract_issues(planner_output))
    if require_rhythm_fields:
        issues.extend(_rhythm_planning_contract_issues(planner_output))
        issues.extend(_story_planner_fast_cluster_merge_issues(planner_output))
        issues.extend(_story_planner_dialogue_unit_split_issues(planner_output, source_script))
        issues.extend(_story_planner_thin_continuation_split_issues(planner_output, source_script))

    # 剧本外事件语义审查（大模型批量审查，放在 per-section 循环之后）
    if source_script:
        event_issues = _llm_validate_source_events(sections, source_script)
        issues.extend(event_issues)

    return issues

def _story_planner_repair_prompt(
    *,
    original_script: str,
    scene_output: str,
    rhythm_guidance: str = "",
    previous_output: str,
    validation_issues: list[str],
) -> str:
    issue_text = "\n".join(f"- {issue}" for issue in validation_issues[:40])
    return (
        "上一轮 story_planner 输出没有通过运行时结构校验。请只做结构修复，重新输出一份完整 YAML 列表。\n\n"
        "【必须修复的问题】\n"
        f"{issue_text}\n\n"
        f"{_story_planner_fragment_count_instruction(original_script)}"
        "【修复硬约束】\n"
        "1. 只输出 YAML，不要解释、不要 Markdown 代码围栏、不要前后说明。\n"
        "2. 片段编号必须从 F01 开始顺序递增，不能跳号，不能使用场次号或复合编号。\n"
        "3. 每个片段只需要包含：片段编号、片段任务、目标时长、节奏类型、事件密度判断、片段内节奏分配、动作节奏指导、施工剧本原文事件、出现人物、入场状态、出场状态、承接要求、镜头导演交接。\n"
        "4. 禁止输出镜头、机位、景别、子分镜、剧情解释、场景预分析简表、剧情增强约束或风险长说明。\n"
        "5. 施工剧本原文事件必须逐条引用【当前施工剧本】中的原文，不能概括、改写或新增剧本外动作。\n"
        "6. 只做分段，不做分镜；不要写 shots、shot_id、sub_shots、camera、angle、beat_design。\n"
        "7. 按 15 秒估算：普通对白段约 6-8 条原文事件；动作密集段约 2-4 条原文事件；一句完整台词或一个未完成动作不要从中间拆。\n"
        "8. 每个片段必须补齐 节奏类型、事件密度判断、片段内节奏分配、动作节奏指导；动作节奏指导必须明确急忙/叠压/短促/慢处理等执行状态。\n"
        "9. 急促动作、短位移、冲入、小跑聚拢、开门入场、上下车或电梯进出，若没有长对白、信息揭示或明确反应落点，目标时长必须压到 2-5秒；多个短动作叠加也应控制在 5-6秒，禁止写成 8-10秒。\n"
        "10. 闹钟/手机/外套/孩子抗拒这类同一生活动作群若被拆成多个连续快节奏短段，应合并为一个 5-6秒 紧凑段，除非有长对白、信息揭示、场景转换或明确反应落点。\n"
        "11. 合并相邻片段时不要丢失节奏差异；把差异写进片段内节奏分配，例如“0-2秒：急促动作链；2-6秒：孩子拒绝台词与乔熙应对”。\n"
        "12. 如果上一轮输出太短、截断或不是 YAML，请忽略它，直接根据当前施工剧本重建完整 YAML。\n\n"
        f"【节奏总控施工指令】\n{_truncate_for_prompt(rhythm_guidance or 'none', 2400)}\n\n"
        f"【当前施工剧本】\n{original_script}\n\n"
        f"【上一轮无效输出】\n{_truncate_for_prompt(previous_output, 9000)}\n\n"
        "请输出修复后的完整 YAML。"
    )

def _story_planner_validation_error_message(
    issues: list[str],
    output: str,
    attempts: list[dict[str, Any]],
) -> str:
    repair_count = max(0, len(attempts) - 1)
    issue_text = "\n".join(f"- {issue}" for issue in issues[:40])
    preview = _truncate_for_prompt((output or "").strip(), 1200)
    prefix = (
        f"story_planner 输出未满足知识驱动结构要求（已自动修复 {repair_count} 次仍失败）："
        if repair_count
        else "story_planner 输出未满足知识驱动结构要求："
    )
    parts = [prefix, issue_text]
    if preview:
        parts.append("【最后一次输出预览】\n" + preview)
    return "\n".join(parts)

def _yaml_quote(value: str) -> str:
    return '"' + (value or "").replace("\\", "\\\\").replace('"', "'") + '"'

def _run_story_planner_with_schema_repair(
    *,
    system_prompt: str,
    user_prompt: str,
    original_script: str,
    scene_output: str,
    rhythm_guidance: str = "",
    require_rhythm_fields: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    """Run story_planner and give it one focused repair pass on schema failure."""
    attempts: list[dict[str, Any]] = []
    current_prompt = user_prompt
    output = ""
    planner_issues: list[str] = []

    for attempt_index in range(1, STORY_PLANNER_MAX_SCHEMA_ATTEMPTS + 1):
        started = time.perf_counter()
        try:
            raw_output = call_llm(system_prompt, current_prompt, agent_name="story_planner")
        except Exception as exc:
            attempts.append(
                _agent_runtime_trace(
                    "story_planner",
                    mode="direct",
                    started_at=started,
                    status="error",
                    error=exc,
                    attempt=attempt_index,
                    path="direct_llm_only",
                )
            )
            if attempt_index == 1:
                raise RuntimeError(f"节奏拆片导演大模型连接不成功，尚未得到可校验 YAML：{exc}") from exc
            raise RuntimeError(f"节奏拆片导演结构修复大模型连接不成功，仍未得到可校验 YAML：{exc}") from exc

        output = _normalise_story_planner_output(raw_output, original_script)
        planner_issues = _validate_story_planner_output(
            output,
            original_script,
            require_rhythm_fields=require_rhythm_fields,
        )
        soft_issues = _story_planner_soft_validation_issues(output) if not planner_issues else []
        agent_validation: dict[str, Any] = {"status": "skip", "issues": []}
        if soft_issues:
            agent_validation = _run_story_planner_agent_validator(
                original_script=original_script,
                scene_output=scene_output,
                planner_output=output,
                soft_issues=soft_issues,
            )
            if agent_validation.get("status") == "fail":
                agent_issues = agent_validation.get("issues") or ["校验导演判定拆片结果不可交给后续镜头导演。"]
                planner_issues = [f"校验导演：{issue}" for issue in agent_issues]

        status = "success" if not planner_issues else "invalid_schema"
        attempts.append(
            _agent_runtime_trace(
                "story_planner",
                mode="direct",
                started_at=started,
                status=status,
                output=output,
                attempt=attempt_index,
                validation_issues=planner_issues[:40],
                soft_validation_issues=soft_issues[:40],
                agent_validation=agent_validation,
                path="direct_llm_only",
            )
        )

        if not planner_issues:
            return output, attempts

        if attempt_index < STORY_PLANNER_MAX_SCHEMA_ATTEMPTS:
            current_prompt = _story_planner_repair_prompt(
                original_script=original_script,
                scene_output=scene_output,
                rhythm_guidance=rhythm_guidance,
                previous_output=output or raw_output,
                validation_issues=planner_issues,
            )

    raise RuntimeError(_story_planner_validation_error_message(planner_issues, output, attempts))

def _extract_segments(planner_output: str) -> tuple[int, list[str]]:
    sections = _extract_yaml_sections(planner_output or "")
    if not sections:
        return 1, ["片段01"]
    return len(sections), [f"片段{index:02d}" for index in range(1, len(sections) + 1)]

def _extract_labeled_rhythm_sections(
    text: str,
    labels: tuple[str, ...],
    stop_labels: tuple[str, ...],
) -> str:
    source = (text or "").strip()
    if not source:
        return ""

    label_re = "|".join(re.escape(label) for label in labels)
    stop_re = "|".join(re.escape(label) for label in stop_labels)
    start_pattern = re.compile(
        rf"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?(?:{label_re})\s*[：:]\s*(.*)$"
    )
    stop_pattern = re.compile(
        rf"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?(?:{stop_re})\s*[：:]"
    )

    sections: list[str] = []
    for match in start_pattern.finditer(source):
        lines: list[str] = []
        first_line = match.group(1).strip()
        if first_line:
            lines.append(first_line)
        for line in source[match.end() :].splitlines():
            if stop_pattern.match(line):
                break
            lines.append(line.rstrip())
        section = "\n".join(lines).strip()
        if section and section not in sections:
            sections.append(section)
    return "\n\n".join(sections).strip()

def _extract_rhythm_story_planner_notes(atmosphere_strategy: str) -> str:
    """Keep only the rhythm supervisor handoff that affects segmentation."""
    text = (atmosphere_strategy or "").strip()
    if not text:
        return ""

    preferred = _extract_labeled_rhythm_sections(
        text,
        ("给结构规划师", "结构规划师操作单", "story_planner_notes"),
        (
            "节奏诊断",
            "给结构规划师",
            "结构规划师操作单",
            "story_planner_notes",
            "给镜头导演",
            "镜头导演操作单",
            "镜头导演节奏执行约束",
            "风险提醒",
        ),
    )
    if preferred:
        return preferred

    legacy = _extract_labeled_rhythm_sections(
        text,
        ("结构规划施工指令", "拆片边界建议", "反应归属", "尾帧承接", "construction_notes"),
        (
            "节奏诊断",
            "节奏总合同",
            "拆片边界建议",
            "反应归属",
            "尾帧承接",
            "结构规划施工指令",
            "给结构规划师",
            "给镜头导演",
            "镜头导演节奏执行约束",
            "风险提醒",
        ),
    )
    return legacy or text

def _build_rhythm_handoff_from_planner_output(planner_output: str) -> str:
    sections = _extract_yaml_sections(planner_output or "")
    lines = [
        "节奏诊断:",
        "  - 节奏拆片导演已在同一次推理中完成节奏判断和片段拆分，避免二次翻译拉长动作节奏。",
        "给镜头导演:",
    ]
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        task = _field_value(section, "dramatic_unit") or "当前片段"
        duration = _field_value(section, "duration_target") or "按片段目标时长执行"
        rhythm_type = _field_value(section, "节奏类型") or "按片段任务判断"
        density = _field_value(section, "事件密度判断") or "按施工剧本原文事件密度执行"
        action_rhythm = _field_value(section, "动作节奏指导") or "按原文动作速度执行，不额外拖慢。"
        intra_rhythm = _field_value(section, "intra_fragment_rhythm") or "无；按片段整体目标时长执行。"
        handoff = _field_value(section, "director_brief") or _infer_shot_director_handoff(section)
        lines.extend(
            [
                f"  - 片段: {fragment_id}",
                f"    片段任务: {task}",
                f"    目标时长: {duration}",
                f"    节奏类型: {rhythm_type}",
                f"    事件密度判断: {density}",
                f"    片段内节奏分配: {intra_rhythm}",
                f"    动作节奏指导: {action_rhythm}",
                f"    镜头导演交接: {handoff}",
            ]
        )
    if not sections:
        lines.append("  - 无可解析片段；以 story_planner 输出为准。")
    lines.append("风险提醒: 节奏指导不是新增剧情来源；若与施工剧本原文事件冲突，必须以原文事件为准。")
    return "\n".join(lines)

def _rhythm_story_planner_system_prompt() -> str:
    return (
        "你是节奏拆片导演，合并承担原节奏总控导演和结构规划师的职责。\n"
        "你的工作是分析当前施工剧本，直接拆成给镜头导演使用的片段清单，并在每个片段内写清节奏预算、动作节奏和镜头导演交接。\n"
        "你不能和镜头导演混同：禁止设计具体镜头、机位、景别、焦段、运镜、子分镜或镜头方案。\n"
        "戏剧单元与节奏预算并列优先：完整问答、连续回应、同一对话目标和反应落点未完成前，不得为了卡秒数拆成平级片段。\n"
        "同一戏剧任务内可以有多个内部小节拍：第一部分可以短促，第二部分可以放长；这应写进片段内节奏分配，而不是拆成多个片段。\n"
        "快节奏的定义是短时间 + 密集有效事件 + 短动作连续发生；不是把很多短动作拉长到 8-10 秒慢慢演。\n"
        "急促动作、短位移、冲入、小跑聚拢、闹钟按掉、夹手机、够外套、扯拉链、按肩、开门入场、上下车或电梯进出，"
        "如果没有完整发言、信息揭示或明确反应落点，通常应压到 2-5秒；多短动作叠加但都很短时可用 5-6秒紧凑段。\n"
        "同一急促生活动作群（例如闹钟、手机、外套、孩子抗拒在同一小段时间里连续发生）优先合并成一个 5-6秒 紧凑段，"
        "不要拆成多个 5-6秒 快节奏段。\n"
        "人物动作节奏必须写清：急急忙忙、动作叠压、正常承接、停住观察、慢处理或犹豫拖延。"
    )

def _rhythm_story_planner_user_prompt(
    *,
    state: DirectorState,
    truncated_script: str,
    slim_rules: str,
) -> str:
    director_contract = str(state.get("director_brief") or "").strip()
    scene_context = str(state.get("scene_context_brief") or "").strip()
    user_intent = str(state.get("director_notes") or state.get("user_prompt") or state.get("prompt") or "").strip()
    fragment_count_instruction = _story_planner_fragment_count_instruction(str(state.get("script") or truncated_script))
    return (
        "请把以下【当前施工剧本】直接拆成若干片段。当前施工剧本可能已经由前序 agent 改写并经用户确认；"
        "施工剧本原文事件必须引用这个版本，不要退回原始剧本。\n\n"
        f"【当前施工剧本】\n{truncated_script}\n\n"
        f"【剧情增强导演契约】\n{director_contract or '无；仅以当前施工剧本为准。'}\n\n"
        f"【场景预分析约束】\n{scene_context or '无；不得自行补充空间、站位或道具。'}\n\n"
        f"【用户导演意图/补充要求】\n{user_intent or '无单独补充。'}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n\n"
        "【知识库极简规则】\n"
        f"{slim_rules or '无额外规则；按下方分段规则执行。'}\n\n"
        f"{fragment_count_instruction}"
        "【输出格式】\n"
        "只输出 YAML 列表。每个片段只允许中文字段；不要 Markdown 代码围栏。\n"
        "每个片段必须包含：\n"
        "- 片段编号：必须从 F01 开始顺序递增。\n"
        "- 片段任务：一句话说明本段要完成的剧情施工任务，只概括原文事件，不写镜头、机位、景别或运镜。\n"
        "- 目标时长：通常 15 秒以内；急促短动作按 2-5秒 或 5-6秒紧凑段处理。\n"
        "- 节奏类型：快节奏 / 慢节奏 / 正常承接 / 停顿反应。\n"
        "- 事件密度判断：说明是短时间密集事件、低密度过渡、完整发言单元或反应落点。\n"
        "- 片段内节奏分配：按内部小节拍写时间预算和戏剧功能，例如“0-2秒：闹钟/电话/穿衣动作链急促完成；2-6秒：孩子拒绝台词和乔熙应对落地”。\n"
        "- 动作节奏指导：明确人物动作应急急忙忙、动作叠压、正常承接、停住观察、慢处理或犹豫拖延；这是给动作调度导演和镜头导演的节奏约束。\n"
        "- 施工剧本原文事件：数组，逐条照抄当前施工剧本里的动作或台词原文。\n"
        "- 出现人物：只写本片段出现或被明确听见的人物。\n"
        "- 入场状态：本片段开始时，人物、道具、门、电梯、空间等必要状态。\n"
        "- 出场状态：本片段结束时，需要下游接住的必要状态。\n"
        "- 承接要求：只写分段承接提醒，例如反应留在本段、下一段承接某状态、无需独立反应。\n"
        "- 镜头导演交接：写清必须拍完整、可压缩/可省略、不能省略、最少停留、最多镜头数、结尾画面；不得写具体镜头方案。\n\n"
        "【分段与节奏规则】\n"
        "1. 只按剧情动作单元、完整发言单元、场景/状态变化来分段，不平均切秒数。\n"
        "1A. 戏剧单元与节奏并列：同一人物关系内的完整问答、连续回应、安抚/质问/解释和反应落点，应优先保持在同一个片段内；镜头变化或 5-8秒生成单元只能在片段内部处理。\n"
        "1B. 片段可以包含多个内部小节拍；用片段内节奏分配控制快慢，不用新增片段制造承接负担。\n"
        "2. 快节奏 = 短时间 + 密集有效事件 + 短动作连续发生；不要把短动作拆成慢悠悠的长段。\n"
        "3. 多个短动作叠加时，优先压缩成紧凑短段，例如 5-6秒，而不是写成 8-10秒。\n"
        "4. 急促动作、短位移、闹钟按掉、夹手机、够外套、扯拉链、按肩、冲入、小跑、开门入场、上下车或电梯进出，没有完整发言/信息揭示/明确反应落点时，目标时长必须是 2-5秒。\n"
        "5. 如果短时间内同时有电话台词、孩子抗拒、外套动作等多个短动作，可写 5-6秒紧凑段，并在动作节奏指导中写明急急忙忙、动作叠压。\n"
        "6. 闹钟/手机/外套/孩子抗拒这类同一生活动作群，如果没有长对白、信息揭示、场景转换或明确反应落点，不要按闹钟、电话、外套分别拆成多个 5-6秒段；应合并成一个 5-6秒 紧凑段。\n"
        "7. 节奏提示只能影响片段边界、片段任务、目标时长、入场状态、出场状态、承接要求、动作节奏指导和镜头导演交接，不得变成新的剧本事件。\n"
        "8. 不要在一句话中间、一个动作中间、同一个反应尚未落地、只是换表情或未来会换镜头的位置拆开。\n"
        "9. 禁止输出任何镜头设计字段，包括 shots、shot_id、sub_shots、camera、angle、size、beat_design、景别、机位、运镜。"
    )

def rhythm_story_planner_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    truncated_script = _truncate_for_prompt(state.get("script", ""), 12000)
    planner_hint = f"节奏拆片导演 短时间密集事件 急促动作 2-5秒 5-6秒 动作节奏指导 不做分镜 {truncated_script[:200]}"
    slim_rules, retrieval_meta = _story_planner_slim_rule_digest(planner_hint, n_results=5)
    retrieval_meta["context_hint"] = planner_hint
    retrieval_meta["reason"] = "merged rhythm_story_planner uses one slim rule-registry digest for rhythm and segmentation."
    system_prompt = _rhythm_story_planner_system_prompt()
    user_prompt = _rhythm_story_planner_user_prompt(
        state=state,
        truncated_script=truncated_script,
        slim_rules=slim_rules,
    )
    output, planner_attempts = _run_story_planner_with_schema_repair(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        original_script=state.get("script", ""),
        scene_output=str(state.get("scene_context_brief") or ""),
        rhythm_guidance="节奏与拆片已合并到同一次推理；修复时继续遵守急促短动作 2-5秒、紧凑短动作群 5-6秒。",
        require_rhythm_fields=True,
    )
    knowledge_metadata = _record_knowledge_metadata(state, "story_planner", planner_hint, retrieval_meta)
    knowledge_metadata.setdefault("story_planner", {})["runtime"] = planner_attempts[-1] if planner_attempts else {}
    knowledge_metadata["story_planner"]["attempts"] = planner_attempts
    knowledge_metadata["story_planner"]["merged_from_agents"] = ["rhythm_rewrite_director", "story_planner"]
    knowledge_metadata.setdefault("rhythm_rewrite_director", {})["merged_into"] = "story_planner"
    knowledge_metadata["rhythm_rewrite_director"]["runtime"] = planner_attempts[-1] if planner_attempts else {}
    planner_issues = _validate_story_planner_output(output, state.get("script", ""), require_rhythm_fields=True)
    total_segments, segment_names = _extract_segments(output)
    if planner_issues:
        raise RuntimeError("rhythm_story_planner 输出未满足知识驱动结构要求：\n" + "\n".join(f"- {issue}" for issue in planner_issues))
    atmosphere_strategy = _build_rhythm_handoff_from_planner_output(output)
    outputs["rhythm_rewrite_director"] = atmosphere_strategy
    outputs["story_planner"] = output
    return _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_3_direct",
            "message": "节奏拆片完成，等待生成当前片段镜头方案...（4/6）",
            "atmosphere_strategy": atmosphere_strategy,
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "director_review_report": state.get("director_review_report", ""),
            "total_segments": total_segments,
            "segment_names": segment_names,
            "current_segment_index": 1,
        },
    )

def story_planner_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    rhythm_guidance_full = state.get("atmosphere_strategy", "") or outputs.get("rhythm_rewrite_director", "")
    rhythm_guidance = _extract_rhythm_story_planner_notes(rhythm_guidance_full)
    truncated_script = _truncate_for_prompt(state.get("script", ""), 12000)
    planner_hint = f"story_planner 纯拆片 15秒 片段边界 原文事件 不做分镜 {truncated_script[:200]}"
    slim_rules, retrieval_meta = _story_planner_slim_rule_digest(planner_hint)
    retrieval_meta["context_hint"] = planner_hint
    retrieval_meta["reason"] = "story_planner uses only a tiny rule-registry digest, not broad knowledge context."
    system_prompt = (
        "你是纯拆片 agent。你的唯一工作是把当前施工剧本拆成片段清单。\n"
        "只做分段，不做分镜；只判断每段从哪里到哪里、约几秒、交给下游时要接住什么状态。\n"
        "不要设计镜头、机位、景别、运镜、子分镜；不要写剧情解释；不要新增动作、台词、人物、道具或场景。\n"
        "直接输出 YAML，不要寒暄，不要 Markdown 代码围栏。"
    )
    user_prompt = (
        "请把以下【当前施工剧本】拆成若干片段。当前施工剧本可能已经由前序 agent 改写并经用户确认；"
        "施工剧本原文事件必须引用这个版本，不要退回原始剧本。\n\n"
        f"【当前施工剧本】\n{truncated_script}\n\n"
        "【给结构规划师的节奏操作单】\n"
        f"{_truncate_for_prompt(rhythm_guidance or 'none', 1200)}\n\n"
        "【知识库极简规则】\n"
        f"{slim_rules or '无额外规则；按下方分段规则执行。'}\n\n"
        f"{_story_planner_fragment_count_instruction(str(state.get('script') or truncated_script))}"
        "【输出格式】\n"
        "只输出 YAML 列表。每个片段只允许这些中文字段：\n"
        "- 片段编号：必须从 F01 开始顺序递增。\n"
        "- 片段任务：一句话说明本段要完成的剧情施工任务，只概括原文事件，不写镜头、机位、景别或运镜。\n"
        "- 目标时长：通常 15 秒以内；内容很短可以更短。\n"
        "- 片段内节奏分配：当一个片段内含快慢变化时，写清内部小节拍的时间预算和戏剧功能；没有快慢变化可写“按整体目标时长执行”。\n"
        "- 施工剧本原文事件：数组，逐条照抄当前施工剧本里的动作或台词原文。\n"
        "- 出现人物：只写本片段出现或被明确听见的人物。\n"
        "- 入场状态：本片段开始时，人物、道具、门、电梯、空间等必要状态。\n"
        "- 出场状态：本片段结束时，需要下游接住的必要状态。\n"
        "- 承接要求：只写分段承接提醒，例如反应留在本段、下一段承接某状态、无需独立反应。\n"
        "- 镜头导演交接：把节奏总控里和本段相关的必须拍完整、可省略、不能省略、最少停留、最多镜头数、结尾画面压成一句施工交接；没有额外节奏要求时写按目标时长与承接要求执行。不得写具体镜头方案。\n\n"
        "【分段规则】\n"
        "1. 只按剧情动作单元、完整发言单元、场景/状态变化来分段，不平均切秒数。\n"
        "2. 不要为了凑满 15 秒补写剧本外内容；动作少就短一点，弱事件可合并。\n"
        "3. 一段太长或同时包含多个清楚任务时再拆开；普通停顿、短反应、信息揭示不用单独拆成一段。\n"
        "4. 节奏提示只能影响片段边界、片段任务、目标时长、片段内节奏分配、入场状态、出场状态、承接要求和镜头导演交接，不得变成新的剧本事件。\n"
        "5. 15 秒估算尺：普通对白段通常可容纳 6-8 条原文事件；动作密集段通常只容纳 2-4 条原文事件；长对白按完整意思单元拆。\n"
        "6. 急促动作、短位移、冲入、小跑聚拢、开门入场、上下车或电梯进出，没有完整发言/信息揭示/明确反应落点时，目标时长必须是 2-5秒；不要为了凑 10秒让人物慢慢走、慢慢停、慢慢看。\n"
        "7. 优先在进门完成、照片落地、人物发现、关系反转、场景切换、动作结果已经成立的位置拆开。\n"
        "8. 不要在一句话中间、一个动作中间、同一个反应尚未落地、只是换表情或未来会换镜头的位置拆开。\n"
        "9. 禁止输出任何镜头设计字段，包括 shots、shot_id、sub_shots、camera、angle、size、beat_design。"
    )
    output, planner_attempts = _run_story_planner_with_schema_repair(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        original_script=state.get("script", ""),
        scene_output="",
        rhythm_guidance=rhythm_guidance,
    )
    knowledge_metadata = _record_knowledge_metadata(state, "story_planner", planner_hint, retrieval_meta)
    knowledge_metadata.setdefault("story_planner", {})["runtime"] = planner_attempts[-1] if planner_attempts else {}
    knowledge_metadata["story_planner"]["attempts"] = planner_attempts
    planner_issues = _validate_story_planner_output(output, state.get("script", ""))
    total_segments, segment_names = _extract_segments(output)
    if planner_issues:
        raise RuntimeError("story_planner 输出未满足知识驱动结构要求：\n" + "\n".join(f"- {issue}" for issue in planner_issues))
    outputs["story_planner"] = output
    return _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_3_direct",
            "message": "镜头导演正在设计全局分镜骨架...（5/6）",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "director_review_report": state.get("director_review_report", ""),
            "total_segments": total_segments,
            "segment_names": segment_names,
            "current_segment_index": 1,
        },
    )
