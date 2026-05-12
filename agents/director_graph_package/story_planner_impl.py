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
        "9. 文戏/情绪戏/对白戏优先保持可延长的连续段；武戏/高动作冲突戏优先拆成可拼接的短段。\n"
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
        "dramatic_unit": ("dramatic_unit", "片段任务"),
        "duration_target": ("duration_target", "目标时长"),
        "reaction_plan": ("reaction_plan", "承接要求"),
        "director_brief": ("director_brief",),
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
        if not _has_planner_field_alias(section_after_boundary, ("reaction_plan", "承接要求")):
            _insert_planner_field_before(
                lines,
                field="承接要求",
                value=_infer_reaction_plan(section_after_boundary),
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

    import math
    total_events = sum(len(_source_script_events(s)) for s in sections)
    min_fragments = math.ceil(total_events / 8) if total_events > 0 else 1
    if sections and len(sections) < min_fragments:
        issues.append(
            f"全局片段密度偏高：{total_events} 条剧本事件拆为 {len(sections)} 个片段，"
            f"按当前规则建议至少 {min_fragments} 个。"
        )
    return issues

def _story_planner_target_fragment_range(total_events: int) -> tuple[int, int]:
    if total_events <= 0:
        return 1, 1
    import math

    min_fragments = max(1, math.ceil(total_events / 8))
    max_fragments = max(min_fragments, math.ceil(total_events / 4))
    return min_fragments, max_fragments

def _story_planner_fragment_granularity_issues(planner_output: str) -> list[str]:
    sections = _extract_yaml_sections(planner_output)
    if not sections:
        return []

    total_events = sum(len(_source_script_events(section)) for section in sections)
    min_fragments, max_fragments = _story_planner_target_fragment_range(total_events)
    fragment_count = len(sections)
    if fragment_count > max_fragments:
        return [
            f"全局拆片过细：{total_events} 条 source_script_events 被拆成 {fragment_count} 段；"
            f"本轮应控制在 {min_fragments}-{max_fragments} 段左右。请合并相邻弱反应、OS 受击、"
            "同一空间内的连续问答和同一动作链，不要把一个反应/一句追问单独成段。"
        ]
    if total_events >= 24 and fragment_count < min_fragments:
        return [
            f"全局拆片过粗：{total_events} 条 source_script_events 只拆成 {fragment_count} 段；"
            f"本轮建议至少 {min_fragments} 段，避免一个片段覆盖多个完整戏剧任务。"
        ]
    return []

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

def _validate_story_planner_output(planner_output: str, script: str = "") -> list[str]:
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
        "【修复硬约束】\n"
        "1. 只输出 YAML，不要解释、不要 Markdown 代码围栏、不要前后说明。\n"
        "2. 片段编号必须从 F01 开始顺序递增，不能跳号，不能使用场次号或复合编号。\n"
        "3. 每个片段只需要包含：片段编号、目标时长、施工剧本原文事件、出现人物、入场状态、出场状态、承接要求。\n"
        "4. 禁止输出镜头、机位、景别、子分镜、剧情解释、场景预分析简表、剧情增强约束或风险长说明。\n"
        "5. 施工剧本原文事件必须逐条引用【当前施工剧本】中的原文，不能概括、改写或新增剧本外动作。\n"
        "6. 只做分段，不做分镜；不要写 shots、shot_id、sub_shots、camera、angle、beat_design。\n"
        "7. 按 15 秒估算：普通对白段约 6-8 条原文事件；动作密集段约 2-4 条原文事件；一句完整台词或一个未完成动作不要从中间拆。\n"
        "8. 如果上一轮输出太短、截断或不是 YAML，请忽略它，直接根据当前施工剧本重建完整 YAML。\n\n"
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

def _build_local_story_planner_fallback(original_script: str) -> str:
    """Build a conservative planner handoff from verbatim script lines."""
    script_lines = _script_event_lines(original_script)
    if not script_lines:
        script_lines = ["No script text was provided."]

    sections: list[str] = []
    for section_index, start in enumerate(range(0, len(script_lines), 8), start=1):
        events = script_lines[start : start + 8]
        first_event = events[0]
        last_event = events[-1]
        lines = [
            f"- fragment_id: F{section_index:02d}",
            '  duration_target: "8-15s"',
            f"  dramatic_unit: {_yaml_quote('Verbatim script handoff: ' + first_event[:80])}",
            "  source_script_events:",
        ]
        lines.extend(f"    - {_yaml_quote(event)}" for event in events)
        lines.extend(
            [
                "  cast:",
                '    active: ["script_defined_characters"]',
                "    must_not_show: []",
                "  continuity:",
                f"    entry: {_yaml_quote('Begin at script event: ' + first_event[:120])}",
                f"    exit: {_yaml_quote('End after script event: ' + last_event[:120])}",
                '  reaction_plan: "Keep reactions internal to this fragment unless the next fragment explicitly continues the same unfinished beat."',
                '  director_brief: "Local fallback generated after story_planner upstream failure; preserve only the listed verbatim script events."',
            ]
        )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)

def _story_planner_local_fallback_after_error(
    *,
    original_script: str,
    attempts: list[dict[str, Any]],
    started: float,
    attempt_index: int,
    error: Exception,
) -> tuple[str, list[dict[str, Any]]] | None:
    output = _normalise_story_planner_output(
        _build_local_story_planner_fallback(original_script),
        original_script,
    )
    planner_issues = _validate_story_planner_output(output, original_script)
    attempts.append(
        _agent_runtime_trace(
            "story_planner",
            mode="local_fallback",
            started_at=started,
            status="success" if not planner_issues else "invalid_schema",
            output=output,
            attempt=attempt_index,
            validation_issues=planner_issues[:40],
            upstream_error=str(error)[:800],
            path="local_verbatim_script_fallback",
            mcp_enabled=False,
        )
    )
    if planner_issues:
        return None
    return output, attempts

def _run_story_planner_with_schema_repair(
    *,
    system_prompt: str,
    user_prompt: str,
    original_script: str,
    scene_output: str,
    rhythm_guidance: str = "",
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
                    mcp_enabled=False,
                )
            )
            fallback_result = _story_planner_local_fallback_after_error(
                original_script=original_script,
                attempts=attempts,
                started=started,
                attempt_index=attempt_index,
                error=exc,
            )
            if fallback_result is not None:
                return fallback_result
            if attempt_index == 1:
                raise RuntimeError(f"story_planner 上游调用失败，尚未得到可校验 YAML：{exc}") from exc
            raise RuntimeError(f"story_planner 结构修复调用失败，仍未得到可校验 YAML：{exc}") from exc

        output = _normalise_story_planner_output(raw_output, original_script)
        planner_issues = _validate_story_planner_output(output, original_script)
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
                mcp_enabled=False,
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
        "【输出格式】\n"
        "只输出 YAML 列表。每个片段只允许这些中文字段：\n"
        "- 片段编号：必须从 F01 开始顺序递增。\n"
        "- 目标时长：通常 15 秒以内；内容很短可以更短。\n"
        "- 施工剧本原文事件：数组，逐条照抄当前施工剧本里的动作或台词原文。\n"
        "- 出现人物：只写本片段出现或被明确听见的人物。\n"
        "- 入场状态：本片段开始时，人物、道具、门、电梯、空间等必要状态。\n"
        "- 出场状态：本片段结束时，需要下游接住的必要状态。\n"
        "- 承接要求：只写分段承接提醒，例如反应留在本段、下一段承接某状态、无需独立反应。\n\n"
        "【分段规则】\n"
        "1. 只按剧情动作单元、完整发言单元、场景/状态变化来分段，不平均切秒数。\n"
        "2. 不要为了凑满 15 秒补写剧本外内容；动作少就短一点，弱事件可合并。\n"
        "3. 一段太长或同时包含多个清楚任务时再拆开；普通停顿、短反应、信息揭示不用单独拆成一段。\n"
        "4. 节奏提示只能影响片段边界、目标时长、入场状态、出场状态和承接要求，不得变成新的剧本事件。\n"
        "5. 15 秒估算尺：普通对白段通常可容纳 6-8 条原文事件；动作密集段通常只容纳 2-4 条原文事件；长对白按完整意思单元拆。\n"
        "6. 优先在进门完成、照片落地、人物发现、关系反转、场景切换、动作结果已经成立的位置拆开。\n"
        "7. 不要在一句话中间、一个动作中间、同一个反应尚未落地、只是换表情或未来会换镜头的位置拆开。\n"
        "8. 禁止输出任何镜头设计字段，包括 shots、shot_id、sub_shots、camera、angle、size、beat_design。"
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
