"""Story planner implementation extracted from legacy_impl.

Owns story planning, schema repair, validation, and planner segment parsing.
"""
from __future__ import annotations

import re
import time
from typing import Any

from .types import DirectorState
from . import legacy_impl as _legacy
from .helpers import call_llm, build_system_prompt

STORY_PLANNER_MAX_SCHEMA_ATTEMPTS = _legacy.STORY_PLANNER_MAX_SCHEMA_ATTEMPTS

_agent_runtime_trace = _legacy._agent_runtime_trace
_agent_configured = _legacy._agent_configured
_truncate_for_prompt = _legacy._truncate_for_prompt
_scene_memory_card = _legacy._scene_memory_card
_agent_outputs = _legacy._agent_outputs
_director_brief = _legacy._director_brief
_director_brief_prompt_block = _legacy._director_brief_prompt_block
_script_fidelity_rules = _legacy._script_fidelity_rules
_record_knowledge_metadata = _legacy._record_knowledge_metadata
_persist_update = _legacy._persist_update
_fragment_line_pattern = _legacy._fragment_line_pattern

def _story_planner_rhythm_boundary_rules() -> str:
    return (
        "【story_planner 节奏权限边界】\n"
        "1. story_planner 只负责识别戏剧微粒、Hook 权重、片段边界、受击承接层级和节拍轻重；不负责改写剧本，不负责插入新动作。\n"
        "2. 若检索到含\"改写、增补动作、氛围具象化\"的节奏规则，这些权限只属于 rhythm_rewrite_director；story_planner 不能执行。\n"
        "3. source_script_events 必须逐条引用当前输入剧本中的原文子串，不得概括、改写、合并或补写。\n"
        "4. director_brief / reaction_plan 只能写结构判断，例如\"片段内承接\"\"升级到下一片段\"\"预留停顿\"\"在台词后收束\"；不得新增具体动作、道具、龙套反应或人物调度。\n"
        "5. 如果某处节奏需要更紧或需要气口，但当前剧本没有对应动作，只能标注承接层级，不能把需要写成新的剧情内容。\n"
    )

def _story_planner_granularity_rules() -> str:
    return (
        "【story_planner 颗粒度拆片指南（Seedance 2.0 15秒剧情任务版）】\n"
        "1. 核心目标：每个片段承载一个 15 秒以内可完成的剧情任务；不追求多拆，也不允许把多个任务粗暴塞进一段。\n"
        "2. 单段推荐 4-8 条 source_script_events。超过 8 条必须拆开；少于 4 条通常合并到相邻片段。\n"
        "3. 少于 4 条仍可独立的例外：明确钩子、卡断、尾帧承接、重大反转落点或下一段必须从该状态接起。\n"
        "4. 普通停顿、受击反应、信息揭示默认留在当前片段内部，由 shot_director 处理，不自动拆成新 fragment。\n"
        "5. 拆片必须服从节奏总控施工指令：哪里快、哪里慢、哪里停、哪里压缩、哪里卡断、哪里给反应。\n"
        "6. 反应归属只做高层判断：留在本段、下一段承接、无须独立反应；不要替镜头导演设计具体镜头。\n"
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
    match = re.search(r"(?m)^\s*-?\s*fragment_id\s*:\s*[\"']?([^\"'\s#]+)[\"']?", section)
    return match.group(1).strip() if match else ""

def _normalise_fragment_section_id(section: str, index: int) -> str:
    """Force planner fragment ids into the runtime contract: F01, F02, ..."""
    old_id = _extract_fragment_id(section)
    new_id = f"F{index:02d}"
    updated = re.sub(
        r"(?m)^(\s*-?\s*fragment_id\s*:\s*)[\"']?[^\"'\s#]+[\"']?",
        rf'\1"{new_id}"',
        section,
        count=1,
    )
    if old_id and old_id != new_id:
        updated = re.sub(rf"\b{re.escape(old_id)}(?=\b|[-_])", new_id, updated)
    return updated

def _is_missing_planner_field(section: str, field: str) -> bool:
    return not re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:", section)

def _has_planner_field_any(section: str, fields: tuple[str, ...]) -> bool:
    return any(not _is_missing_planner_field(section, field) for field in fields)

def _field_value(section: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:\s*[\"']?(.+?)[\"']?\s*$", section)
    return match.group(1).strip() if match else ""

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
    indent = "  " if re.match(r"^\s*-\s*fragment_id\s*:", lines[0] if lines else "") else ""
    for line in lines[1:]:
        field_match = re.match(r"^(\s+)[a-z_]+\s*:", line)
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
        r"(?m)^(\s*)source_script_events\s*:\s*([\s\S]*?)(?=\n\s*[a-z_]+\s*:|\n\s*-?\s*fragment_id\s*:|\Z)",
        section,
    )
    if not match:
        return section

    field_indent = match.group(1)
    item_indent = field_indent + "  "
    block_lines = [f"{field_indent}source_script_events:"]
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
        if _is_missing_planner_field(section_after_boundary, "reaction_plan"):
            _insert_planner_field_before(
                lines,
                field="reaction_plan",
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
        r"(?m)^\s*source_script_events\s*:\s*([\s\S]*?)(?=\n\s*[a-z_]+\s*:|\n\s*-?\s*fragment_id\s*:|\Z)",
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

        reaction_match = re.search(r"reaction_plan\s*:([\s\S]*?)(?=\n\s*[a-z_]+\s*:|\Z)", section)
        reaction_text = reaction_match.group(1).strip() if reaction_match else ""
        if reaction_text and not re.search(
            r"片段内|内部|本片段|独立片段|独立主分镜|无需独立|不需要|无需|不涉及|N/?A|none|无受击|画外|背景|虚化|升级|下一段|下个片段|后续片段"
            r"|within|internal|same.?fragment|separate|independent|no.?reaction|covered|absorbed|next.?fragment",
            reaction_text, re.IGNORECASE
        ):
            issues.append(f"{fragment_id} 的 reaction_plan 承接层级不够直白。")

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
        "下面这些默认只算提醒，不要直接判失败：单段 source_script_events 略多、"
        "片段略密、reaction_plan 表述不够漂亮、某段可能还可以再拆。\n\n"
        "输出格式必须严格如下：\n"
        "总体评级：通过/提醒/失败\n"
        "问题清单：\n"
        "- 没有问题就写\"无\"\n"
        "不要输出其他文字。"
    )
    user_prompt = (
        f"【原始剧本】\n{_truncate_for_prompt(original_script, 4000)}\n\n"
        f"【场景空间记忆卡】\n{_scene_memory_card(scene_output, 1600)}\n\n"
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

    required_fields = [
        "fragment_id",
        "duration_target",
        "dramatic_unit",
        "source_script_events",
        "reaction_plan",
        "director_brief",
    ]
    source_script = script or ""
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        if not re.fullmatch(r"F\d{2}", fragment_id):
            issues.append(f"{fragment_id} 片段编号不符合 F01/F02 顺序契约。")
        for field in required_fields:
            if not re.search(rf"{field}\s*:", section):
                issues.append(f"{fragment_id} 缺少字段 {field}。")
        if not _has_planner_field_any(section, ("cast", "active_cast")):
            issues.append(f"{fragment_id} 缺少字段 cast（或兼容字段 active_cast）。")
        if not _has_planner_field_any(section, ("continuity", "state_contract")):
            issues.append(f"{fragment_id} 缺少字段 continuity（或兼容字段 state_contract）。")

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
        "2. fragment_id 必须从 F01 开始顺序递增，不能跳号，不能使用场次号或复合编号。\n"
        "3. 每个片段只需要包含：fragment_id、duration_target、dramatic_unit、source_script_events、cast、continuity、reaction_plan、director_brief。\n"
        "4. cast 使用 active / must_not_show；continuity 使用 entry / exit。只写对后续连续性有用的信息。\n"
        "5. 禁止输出 shots、shot_id、camera_setup_type、primary_subject、action_unit、line_unit、sub_shots、sub_shot_strategy；这些属于后续镜头导演。\n"
        "6. source_script_events 必须逐条引用【原始剧本】中的原文，不能概括、改写或新增剧本外动作。\n"
        "7. 如果上一轮输出太短、截断或不是 YAML，请忽略它，直接根据原始剧本和场景分析重建完整 YAML。\n"
        f"8. {_story_planner_granularity_rules()}\n\n"
        f"【节奏总控施工指令】\n{_truncate_for_prompt(rhythm_guidance or 'none', 2400)}\n\n"
        f"【原始剧本】\n{original_script}\n\n"
        f"【场景空间记忆卡】\n{_scene_memory_card(scene_output)}\n\n"
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

def story_planner_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    director_brief_block = _director_brief_prompt_block(_director_brief(state))
    scene_output = outputs.get("scene_analyst", "")
    scene_memory = _scene_memory_card(scene_output, 1800)
    rhythm_guidance = state.get("atmosphere_strategy", "") or outputs.get("rhythm_rewrite_director", "")
    planner_hint = f"剧本拆分 15秒片段规划 多机位分镜 节奏控制 镜头切换 {state['script'][:200]}"
    system_prompt, retrieval_meta = build_system_prompt(
        "你是一位短剧结构规划师。你的核心任务是把剧本拆成可拍的视频片段施工单："
        "只决定每段从哪到哪、谁在场、连续性如何交接、反应归属哪里。"
        "不要设计机位、景别、shot_id、子分镜或具体镜头动作，这些交给后续镜头导演。",
        "story_planner",
        context_hint=planner_hint,
    )
    user_prompt = (
        f"{director_brief_block}\n"
        f"基于以下【原始剧本】与【场景空间记忆卡】，制定严格拆片方案。\n\n"
        f"【原始剧本】\n{state['script']}\n\n"
        f"【场景空间记忆卡】\n{scene_memory}\n\n"
        "【输出结构硬约束】\n"
        "你必须输出 YAML 列表；每个片段只保留轻量施工单字段：\n"
        "- fragment_id（必须从 F01 开始按顺序递增：F01、F02、F03；严禁输出 F2-1A、F2-2B、片段2A、scene-1 等复合编号）\n"
        "- duration_target\n"
        "- dramatic_unit\n"
        "- source_script_events（数组，逐条引用原剧本动作/台词）\n"
        "- cast（active / must_not_show，只写本段允许出现和明确不能出现的人）\n"
        "- continuity（entry / exit，只写本段开始和结束的关键连续性状态）\n"
        "- reaction_plan（只判断反应留在本片段内部，还是升级到下一片段；不要设计具体镜头）\n"
        "- director_brief（一句话告诉后续镜头导演本段要抓住的戏剧重点）\n\n"
        "【严禁输出的字段】\n"
        "不要输出 shots、shot_id、primary_subject、camera_setup_type、action_unit、line_unit、sub_shots、sub_shot_strategy、beat_design。\n"
        "这些属于后续 shot_director 的职责。\n\n"
        "【核心拆片原则】\n"
        "0. 片段编号是运行时硬契约，只能使用 F01/F02/F03 顺序编号；不得把集数、场次或动作层级写入 fragment_id。\n"
        "1. 每个片段 = 一个清楚的戏剧动作单元或一次完整交锋，不是机械切 15 秒。\n"
        "2. 完整发言单元优先保持完整，不得把完整意思单元机械拆碎。\n"
        "3. 禁止为了凑时长补写剧本外动作。若动作不足，用更短片段或合并相邻弱事件。\n"
        "4. 反应归属只做高层判断：留在本段、下一段承接、无需独立反应。具体怎么拍由后续镜头导演处理。\n"
        "5. continuity 只写会影响下一段首帧/角色位置/道具状态/门电梯状态的关键信息。\n\n"
        f"{_story_planner_granularity_rules()}\n"
        f"{_script_fidelity_rules()}"
        f"{_story_planner_rhythm_boundary_rules()}"
        "11. source_script_events 必须逐条引用原剧本原文，不得改写、概括或补写剧本外动作。\n"
        "12. 直接输出 YAML 拆片结果，不要解释。"
    )
    user_prompt += (
        "\n\n【节奏总控施工指令】\n"
        f"{_truncate_for_prompt(rhythm_guidance or 'none', 2400)}\n\n"
        "【当前最高优先级拆片规则】\n"
        "1. 拆片目标是适配 Seedance 2.0 的 15 秒以内完整剧情任务，不追求多拆，也不允许太粗。\n"
        "2. 单段推荐承载 4-8 条原文事件；超过 8 条必须拆开，少于 4 条通常合并。\n"
        "3. 明确钩子、卡断、尾帧承接或重大反转落点，可以保留短片段。\n"
        "4. 普通停顿、受击反应、信息揭示默认留在片段内部，由 shot_director 处理，不单独拆段。\n"
        "5. 拆片必须服从节奏总控给出的快慢、停顿、卡断、反应归属和尾帧承接指令。\n"
    )
    output, planner_attempts = _run_story_planner_with_schema_repair(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        original_script=state.get("script", ""),
        scene_output=scene_memory,
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
            "message": "镜头导演正在设计全局分镜骨架...（4/6）",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "director_review_report": state.get("director_review_report", ""),
            "total_segments": total_segments,
            "segment_names": segment_names,
            "current_segment_index": 1,
        },
    )
