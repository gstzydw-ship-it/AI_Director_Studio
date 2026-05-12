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
from .helpers import _fragment_id_for_segment_index, _segment_block_by_fragment_id, _yaml_line_field


# ---------------------------------------------------------------------------
# Low-level report parsers / normalisers
# ---------------------------------------------------------------------------
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
        if re.search(r"schema_version\s*:", director_segment) and not re.search(
            r"(?m)^\s*schema_version\s*:\s*shot_director_local_fallback_v1\s*$",
            director_segment,
        ):
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
                r"(?ms)^\s*-\s*shot_id\s*:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$([\s\S]*?)(?=^\s*-\s*shot_id\s*:|^\s{0,2}[a-z_]+\s*:|\Z)",
                director_segment,
            )
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
                    if not re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:", shot_body):
                        qc_issues.append(f"- {shot_id} 缺少 v1 字段 {field}。")
                has_merged_shot = re.search(r"(?m)^\s*-?\s*shot\s*:", shot_body)
                has_legacy_camera_size = re.search(r"(?m)^\s*-?\s*camera\s*:", shot_body) and re.search(
                    r"(?m)^\s*-?\s*size\s*:",
                    shot_body,
                )
                if not (has_merged_shot or has_legacy_camera_size):
                    qc_issues.append(f"- {shot_id} 缺少 v1 字段 shot（或旧版 camera+size）。")

                duration = _yaml_line_field(shot_body, "duration")
                if duration:
                    if not re.search(r"(?:\d+(?:\.\d+)?\s*(?:-|~|–|—)\s*)?\d+(?:\.\d+)?\s*(?:秒|s)\b", duration):
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
                         "transition_type", "tail_state_card",
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
