"""Quality inspector / QC router implementation extracted from legacy_impl.

Owns rule-based QC, optional LLM depth inspection, and graph routing
after quality control.
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
from .helpers import call_llm
from . import legacy_impl as _legacy
from . import prompt_compiler_impl as _prompt_compiler_impl
from .state_store import _persist_update


# ---------------------------------------------------------------------------
# Low-level report parsers / normalisers
# ---------------------------------------------------------------------------
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
    script: str,
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
    if not _legacy._agent_configured("quality_inspector_llm_a"):
        return "skip", [], ""

    reviewers = [
        ("quality_inspector_llm_a", "创意与叙事合理性审视", "检查镜头是否有戏剧张力、人物动机是否成立、节奏是否合理。"),
        ("quality_inspector_llm_b", "规则与逻辑漏洞审视", "检查 prompt 是否违反知识库规则、是否存在空间不连续、是否编造剧本外内容。"),
        ("quality_inspector_llm_c", "视觉与连续性审视", "检查画面描述是否可执行、镜头语言是否连贯、受击落点是否具体。"),
    ]

    review_reports: list[tuple[str, str]] = []
    for agent_key, role_brief, focus in reviewers:
        if not _legacy._agent_configured(agent_key):
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
            f"【原始剧本（节选）】\n{script[:1200]}\n\n"
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
    if _legacy._agent_configured("quality_inspector_merger") and review_reports:
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
    outputs = _legacy._agent_outputs(state)
    segment_index = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
    prompt = outputs.get(f"compiled_segment_{segment_index}", "")
    planner_segment = _legacy._segment_block(outputs.get("story_planner", ""), segment_index)
    director_segment = _legacy._segment_block(outputs.get("shot_director", ""), segment_index)
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

    if director_segment and not re.search(r"shots\s*:", director_segment):
        qc_issues.append("- shot_director 未给出当前片段的 shots。")
    if director_segment and not re.search(r"(fragment_task|reaction_coverage)\s*:", director_segment):
        qc_issues.append("- shot_director 未说明当前片段的 fragment_task/reaction_coverage。")
    if director_segment and re.search(r"(?m)^\s*shots\s*:", director_segment) and not re.search(r"(?m)^\s*cut_point\s*:", director_segment):
        qc_issues.append("- shot_director 的施工单缺少 cut_point，无法判断切镜触发点。")
    if director_segment and re.search(r"sub_shots\s*:", director_segment) and not re.search(r"parent_shot_id\s*:", director_segment):
        qc_issues.append("- shot_director 的 sub_shots 没有挂靠 parent_shot_id。")

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

    # === [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单段反打硬失败 — 检查编译后 prompt ===
    if _REVERSE_SHOT_INSIDE_SEGMENT_RE.search(prompt):
        qc_issues.append(
            '- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 编译后 prompt 出现"反打至"：'
            "Seedance 是单镜头连续生成模型，单次生成内无法完成跨轴反打，会让人物左右颠倒、背景翻面。"
            "需要反打的两镜必须拆成相邻两个 segment，并通过转身/越轴中性镜头/场景固定机位过渡。"
        )

    # === [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单时间段轴线锁 — 检查编译后 prompt ===
    compiled_timeline_blocks = _prompt_compiler_impl._timeline_blocks(prompt)
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
            script=state.get("script", ""),
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
                "revision_instruction": _legacy._agent_outputs(state).get("quality_inspector", ""),
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
