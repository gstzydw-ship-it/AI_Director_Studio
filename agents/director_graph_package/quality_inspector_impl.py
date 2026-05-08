"""Quality inspector / QC router implementation extracted from legacy_impl.

Owns rule-based QC, optional LLM depth inspection, and graph routing
after quality control.
"""
from __future__ import annotations

import re
from typing import Any

from .llm import call_llm, load_config
from .types import (
    DirectorState,
    MAX_QC_RETRIES,
    _AXIS_LEFT_RE,
    _AXIS_RIGHT_RE,
    _REVERSE_SHOT_INSIDE_SEGMENT_RE,
)
from .state_store import _agent_outputs, _persist_update
from .helpers import _fragment_id_for_segment_index, _segment_block_by_fragment_id, _yaml_line_field


# ---------------------------------------------------------------------------
# Low-level report parsers / normalisers
# ---------------------------------------------------------------------------
def _agent_configured(agent_name: str) -> bool:
    agent_cfg = (load_config().get("agent_models") or {}).get(agent_name) or {}
    if not isinstance(agent_cfg, dict):
        return False
    return bool(agent_cfg.get("model") or agent_cfg.get("base_url"))


def _segment_block(text: str, segment_index: int, fragment_id: str | None = None) -> str:
    selected_fragment_id = fragment_id or _fragment_id_for_segment_index([], segment_index)
    return _segment_block_by_fragment_id(text, selected_fragment_id)


def _timeline_blocks(prompt: str) -> list[tuple[float, float, str]]:
    matches = list(re.finditer(r"(?m)^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)绉掞細", prompt or ""))
    blocks: list[tuple[float, float, str]] = []
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        blocks.append((float(match.group(1)), float(match.group(2)), prompt[body_start:body_end].strip()))
    if blocks:
        return blocks

    shot_matches = list(re.finditer(r"(?m)^闀滃ご\s*\d+\s*銆怽s*(\d+(?:\.\d+)?)\s*绉抃s*銆?", prompt or ""))
    current = 0.0
    for index, match in enumerate(shot_matches):
        duration = float(match.group(1))
        body_start = match.end()
        body_end = shot_matches[index + 1].start() if index + 1 < len(shot_matches) else len(prompt)
        blocks.append((current, current + duration, prompt[body_start:body_end].strip()))
        current += duration
    return blocks


def _quality_report_rating(report: str) -> str | None:
    match = re.search(
        r"(?:总体评级|overall\s*rating|rating)\s*[：:]\s*(pass|warn|fail)",
        report or "",
        re.IGNORECASE,
    )
    return match.group(1).lower() if match else None


def _quality_section_body(report: str, keyword: str) -> str:
    match = re.search(
        rf"【[^】]*{re.escape(keyword)}[^】]*】([\s\S]*?)(?=\n【|\Z)",
        report or "",
    )
    return match.group(1).strip() if match else ""


def _quality_bullets(section: str, *, warn: bool = False) -> list[str]:
    empty_values = {"无", "none", "None", "NONE", "（无）", "(无)"}
    issues: list[str] = []
    for line in (section or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        body = stripped.lstrip("-").strip()
        if not body or body in empty_values:
            continue
        if warn and not body.startswith("[warn]"):
            body = f"[warn] {body}"
        issues.append(f"- {body}")
    return issues


def _normalise_merged_quality_report(report: str) -> tuple[str, list[str]] | None:
    rating = _quality_report_rating(report)
    if not rating:
        return None

    severe_issues = _quality_bullets(_quality_section_body(report, "严重问题"), warn=False)
    optional_issues = _quality_bullets(_quality_section_body(report, "次要提示"), warn=True)
    if rating == "fail":
        return rating, severe_issues + optional_issues
    if rating == "warn":
        return rating, optional_issues or [f"- [warn] {issue.lstrip('-').strip()}" for issue in severe_issues]
    return rating, []


def _normalise_llm_quality_issues(status: str, issues: list[str]) -> list[str]:
    if status == "pass":
        return []
    if status != "warn":
        return issues
    normalised: list[str] = []
    for issue in issues:
        body = issue.lstrip("-").strip()
        if not body:
            continue
        if not body.startswith("[warn]"):
            body = f"[warn] {body}"
        normalised.append(f"- {body}")
    return normalised


# ---------------------------------------------------------------------------
# Optional LLM depth inspection
# ---------------------------------------------------------------------------
def _run_llm_quality_inspector(
    segment_source: str,
    prompt: str,
    planner_segment: str,
    director_segment: str,
    segment_index: int,
    rule_based_issues: list[str],
) -> tuple[str, list[str], str]:
    """可选的 LLM 深度质检层：仅在配置了 quality_inspector_llm_a 时启用。

    返回：(status, additional_issues, merged_report)
    - status: 'pass' / 'warn' / 'fail'
    - additional_issues: 新发现的问题（不含 rule_based_issues）
    - merged_report: 最终合并后的可读报告

    若未配置，返回 ('skip', [], '') 表示调用方继续用规则质检结果。
    """
    if not _agent_configured("quality_inspector_llm_a"):
        return "skip", [], ""

    reviewers = [
        ("quality_inspector_llm_a", "创意与叙事合理性审视", "检查镜头是否有戏剧张力、人物动机是否成立、节奏是否合理。"),
        ("quality_inspector_llm_b", "规则与逻辑漏洞审视", "检查 prompt 是否违反知识库规则、是否存在空间不连续、是否编造剧本外内容。"),
        ("quality_inspector_llm_c", "视觉与连续性审视", "检查画面描述是否可执行、镜头语言是否连贯、受击落点是否具体。"),
    ]

    review_reports: list[tuple[str, str]] = []
    for agent_key, role_brief, focus in reviewers:
        if not _agent_configured(agent_key):
            continue
        system_prompt = (
            f"你是一位专业的短剧质检导演（{role_brief}）。\n"
            f"{focus}\n"
            "输出严格遵循以下格式：\n"
            "总体评级：pass|warn|fail\n"
            "问题清单：\n"
            "- 每一条问题必须以\"- \"开头\n"
            "- 仅列出真实存在的问题，没问题就写\"- 无\"\n"
            "不要输出任何其他文字。"
        )
        user_prompt = (
            f"【当前片段原文事件】\n{segment_source[:1200]}\n\n"
            f"【第 {segment_index} 段故事规划】\n{planner_segment[:1200]}\n\n"
            f"【第 {segment_index} 段分镜方案】\n{director_segment[:1200]}\n\n"
            f"【第 {segment_index} 段最终 Prompt】\n{prompt}\n\n"
            f"【规则质检已发现的问题】\n"
            + ("\n".join(rule_based_issues) if rule_based_issues else "（无）")
            + "\n\n请基于你的审视角度补充发现，不要重复上述规则质检已有的问题。"
        )
        try:
            report = call_llm(system_prompt, user_prompt, agent_name=agent_key)
        except Exception as exc:
            print(f"  [quality_inspector] {agent_key} 调用失败：{exc}")
            continue
        if report and report.strip():
            review_reports.append((role_brief, report.strip()))

    if not review_reports:
        return "skip", [], ""

    # 解析每份报告的评级 + 问题条目
    aggregated_issues: list[str] = []
    any_fail = False
    any_warn = False
    for role_brief, report in review_reports:
        m = re.search(r"总体评级[：:]\s*(pass|warn|fail)", report, re.IGNORECASE)
        rating = (m.group(1) if m else "warn").lower()
        if rating == "fail":
            any_fail = True
        elif rating == "warn":
            any_warn = True
        for line in report.splitlines():
            line_stripped = line.strip()
            if not line_stripped.startswith("-"):
                continue
            body = line_stripped.lstrip("-").strip()
            if not body or body in {"无", "none", "None"}:
                continue
            aggregated_issues.append(f"- [{role_brief}] {body}")

    # 若配置了 merger，再用 merger 做最终去重汇总
    merged_report = ""
    if _agent_configured("quality_inspector_merger") and review_reports:
        try:
            merger_system = (
                "你是质检汇总导演。以下是三位独立质检师的审查报告。\n"
                "任务：去重、按严重度分级，输出一份清晰的最终清单。\n"
                "输出格式：\n"
                "总体评级：pass|warn|fail\n"
                "【严重问题（需返修）】\n- ...\n"
                "【次要提示（可选优化）】\n- ...\n"
                '没有的类目直接写"- 无"。不要输出其他解释。'
            )
            merger_user = (
                f"【规则质检已列】\n{(chr(10).join(rule_based_issues)) or '（无）'}\n\n"
                + "\n\n".join(f"【{role}】\n{rep}" for role, rep in review_reports)
            )
            merged_report = call_llm(merger_system, merger_user, agent_name="quality_inspector_merger").strip()
            normalised_merged = _normalise_merged_quality_report(merged_report)
            if normalised_merged:
                return normalised_merged[0], normalised_merged[1], merged_report
        except Exception as exc:
            print(f"  [quality_inspector] merger 调用失败，使用原始汇总：{exc}")

    if any_fail:
        final_status = "fail"
    elif any_warn or aggregated_issues:
        final_status = "warn"
    else:
        final_status = "pass"

    return final_status, _normalise_llm_quality_issues(final_status, aggregated_issues), merged_report


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

    qc_issues: list[str] = []
    if guard_report:
        qc_issues.extend([line for line in guard_report.splitlines() if line.strip()])

    if planner_segment and not re.search(r"reaction_plan\s*:", planner_segment):
        qc_issues.append("- story_planner 未说明当前片段的 reaction_plan。")
    if planner_segment and re.search(r"source_script_events\s*:", planner_segment):
        source_block = re.search(
            r"source_script_events\s*:([\s\S]*?)(?=\n[a-z_]+\s*:|\Z)",
            planner_segment,
        )
        source_items = re.findall(r"-\s*(.+)", source_block.group(1) if source_block else "")
        if len(source_items) == 1 and re.search(r"[，。！？；].+[，。！？；]", source_items[0]):
            qc_issues.append(
                "- story_planner 似乎把完整发言/动作单元压成单条笼统事件，需更清楚标出片段覆盖事件。"
            )

    # === shot_director v1 schema hard validation ===
    if director_segment:
        # v1 fragment 必填字段检查
        if not re.search(r"fragment_task\s*:", director_segment):
            qc_issues.append("- shot_director 缺少 fragment_task 字段（v1 片段任务描述）。")
        if not re.search(r"rhythm\s*:", director_segment):
            qc_issues.append("- shot_director 缺少 rhythm 字段（v1 节奏指令）。")
        if re.search(r"schema_version\s*:", director_segment):
            qc_issues.append("- shot_director 残留 v2 字段 schema_version，必须使用 v1 字段。")
        if re.search(r"fragment_intent\s*:", director_segment):
            qc_issues.append("- shot_director 残留 v2 字段 fragment_intent，必须使用 v1 字段。")
        if re.search(r"reaction_coverage\s*:", director_segment):
            qc_issues.append("- shot_director 残留 v2 字段 reaction_coverage，必须使用 v1 字段。")
        if re.search(r"continuity_anchor\s*:", director_segment):
            qc_issues.append("- shot_director 残留 v2 字段 continuity_anchor，必须使用 v1 字段。")
        if not re.search(r"shots\s*:", director_segment):
            qc_issues.append("- shot_director 未给出当前片段的 shots。")
        # v1 shot 必填字段检查
        if re.search(r"shots\s*:", director_segment):
            shot_blocks = re.findall(
                r"(?ms)^\s*-\s*shot_id\s*:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$([\s\S]*?)(?=^\s*-\s*shot_id\s*:|^\s*[a-z_]+\s*:|\Z)",
                director_segment,
            )
            for shot_id_raw, shot_body in shot_blocks:
                shot_id = shot_id_raw.strip()
                for field in (
                    "duration",
                    "task",
                    "subject",
                    "camera",
                    "size",
                    "action",
                    "dialogue",
                    "must_carry",
                    "cut_point",
                    "continuity",
                ):
                    if not re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:", shot_body):
                        qc_issues.append(f"- {shot_id} 缺少 v1 字段 {field}。")

                duration = _yaml_line_field(shot_body, "duration")
                if duration:
                    if not re.search(r"(?:\d+(?:\.\d+)?\s*(?:-|~|–|—)\s*)?\d+(?:\.\d+)?\s*秒", duration):
                        qc_issues.append(
                            f"- {shot_id} 的 duration 格式非法（{duration}）；"
                            "应为连续时间段格式，例如 0-2秒、2-5秒。"
                        )

                cut_point = _yaml_line_field(shot_body, "cut_point")
                if cut_point and len(cut_point) < 6:
                    qc_issues.append(
                        f"- {shot_id} 的 cut_point 过于简短；"
                        "必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。"
                    )
        # v2 字段残留检查
        for v2_field in ("coverage_role", "cut_reason", "companion_visibility", "tailframe_role",
                         "dialogue_coverage", "transition_type", "tail_state_card",
                         "shot_size", "camera_height", "angle", "movement", "lens", "depth"):
            if re.search(rf"(?m)^\s*-?\s*{re.escape(v2_field)}\s*:", director_segment):
                qc_issues.append(f"- shot_director 残留 v2 字段 {v2_field}，必须使用 v1 字段。")
        # main_shots 旧结构禁用
        if re.search(r"(?m)^\s*main_shots\s*:", director_segment):
            qc_issues.append("- shot_director 仍在使用已禁用的 main_shots 旧结构，必须改为 shots。")

    has_legacy_structure = re.search(
        r"【风格锚点】[\s\S]*【画幅锚点】[\s\S]*"
        r"(?:【空间与首帧总控】|【连续性状态契约】)[\s\S]*"
        r"【时间轴】[\s\S]*(?:【约束】|【全段硬约束】)",
        prompt,
    )
    has_shot_sequence_structure = re.search(
        r"【风格锚点】[\s\S]*【画幅锚点】[\s\S]*"
        r"(?:【空间与首帧总控】|【连续性状态契约】)[\s\S]*"
        r"【人物】[\s\S]*【镜头序列】[\s\S]*(?:【约束】|【全段硬约束】)",
        prompt,
    )
    if not (has_shot_sequence_structure or has_legacy_structure):
        qc_issues.append(
            "- prompt 缺少规定结构，应包含【风格锚点】【画幅锚点】【空间与首帧总控】【人物】【镜头序列】【约束】。"
        )
    if planner_segment and re.search(r"reaction_plan\s*:\s*.*片段内", planner_segment) and not re.search(
        r"受击|反应|表情|眼神|嘴唇|下颌|呼吸|停顿", prompt
    ):
        qc_issues.append("- 当前片段规划要求片段内承受到击/反应，但 prompt 未写出可见落点。")

    if "同一机位继续" in prompt:
        qc_issues.append(
            '- [PROMPT-NO-SAME-CAMERA-ABUSE-001] prompt 仍使用"同一机位继续"：应改成"镜头保持在A身上"、"固定机位保持在某空间锚点"、"镜头切至B"或"镜头切近至/拉开至A"。'
        )

    if re.search(r"压迫感|张力|炸点|钩子|气口|留白|情绪顶点|受压反应|空气收紧|前慢后碎|稳慢压", prompt):
        qc_issues.append(
            "- [PROMPT-VISIBLE-BODY-LANGUAGE-001] prompt 仍残留抽象导演词：必须翻译成停顿时长、视线方向、肩膀收紧、下颌收紧、嘴唇停住、身体距离或门/道具状态等可见画面。"
        )

    timeline_blocks = _timeline_blocks(prompt)
    for block_idx, (_blk_start, _blk_end, blk_body) in enumerate(timeline_blocks[1:], start=2):
        prefix = blk_body[:120]
        if not re.search(r"镜头保持在|固定机位保持|镜头切至|镜头切到|镜头切近至|镜头拉开至|切至|切到|切近至|拉开至", prefix):
            qc_issues.append(
                f"- [PROMPT-SHOT-TRANSITION-VERB-001] 时间轴第 {block_idx} 个时间段缺少精确衔接词：必须明确写同主体保持、固定机位保持、主体切镜或同主体景别变化。"
            )
            break

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
        if _AXIS_LEFT_RE.search(blk_body) and _AXIS_RIGHT_RE.search(blk_body):
            qc_issues.append(
                f"- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 编译后 prompt 的时间轴第 {block_idx} 个时间段"
                '同时出现"左前方"和"右前方"机位（跨 180° 轴线）。'
                "Seedance 单次生成无法跨轴反打，会让人物左右颠倒、背景翻面。"
                '单段 prompt 只能选一个轴线侧（全部"右前方"或全部"左前方"），拆轴必须拆 segment。'
            )
            break

    fail_issues = [i for i in qc_issues if not i.strip().startswith("- [warn]")]
    qc_status = "fail" if fail_issues else ("warn" if qc_issues else "pass")

    # 可选：LLM 深度质检（三票会审 + 合并）——配置了 quality_inspector_llm_a 才触发
    llm_status = "skip"
    llm_issues: list[str] = []
    llm_merged = ""
    try:
        llm_status, llm_issues, llm_merged = _run_llm_quality_inspector(
            segment_source=segment_source,
            prompt=prompt,
            planner_segment=planner_segment,
            director_segment=director_segment,
            segment_index=segment_index,
            rule_based_issues=qc_issues,
        )
    except Exception as exc:
        print(f"  [quality_inspector] LLM 深度质检整体异常，使用规则质检：{exc}")
        llm_status = "skip"

    if llm_status != "skip":
        # LLM 报告允许把 pass 升级为 warn，把 warn 升级为 fail（不允许降级）
        severity_rank = {"pass": 0, "warn": 1, "fail": 2}
        if severity_rank[llm_status] > severity_rank[qc_status]:
            qc_status = llm_status
        if llm_issues:
            qc_issues.extend(_normalise_llm_quality_issues(llm_status, llm_issues))
        fail_issues = [i for i in qc_issues if not i.strip().startswith("- [warn]")]
        qc_status = "fail" if fail_issues else ("warn" if qc_issues else "pass")

    report_sections = [
        f"总体评级：{qc_status}",
        "【知识驱动质检】",
        ("\n".join(qc_issues) if qc_issues else "无"),
    ]
    if llm_merged:
        report_sections.append("\n【LLM 深度质检汇总】\n" + llm_merged)
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
