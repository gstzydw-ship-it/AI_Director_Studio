"""Package-local rhythm_rewrite_director implementation extracted from legacy_impl."""
from __future__ import annotations

import re
from typing import Any

DirectorState = dict[str, Any]

_RHYTHM_ABSTRACT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("死寂气口", "短暂停顿"),
    ("气口", "停顿"),
    ("心理空间落差", "前后反应差异"),
    ("仪式感", "信息揭示顺序"),
    ("压迫感", "站位与视线压制"),
    ("张力", "对峙强度"),
    ("秩序被翻面", "场上视线和站位转向"),
)


def _cleanup_rhythm_abstract_language(text: str, *, preserve_heading: bool = False) -> str:
    if not text:
        return ""

    heading = ""
    body = text
    if preserve_heading and "\n" in text:
        heading, body = text.split("\n", 1)
    elif preserve_heading:
        return text

    for old, new in _RHYTHM_ABSTRACT_REPLACEMENTS:
        body = body.replace(old, new)

    regex_replacements: tuple[tuple[str, str], ...] = (
        (r"空气[^。；\n]{0,24}(?:凝住|绷住|按住|冻结)[^。；\n]*", "没有人接话"),
        (r"气氛[^。；\n]{0,24}(?:凝住|绷住|压住|冻结)[^。；\n]*", "场上没有人接话"),
        (r"制造前后反应差异", "拉开前后反应变化"),
        (r"制造(?:可见)?对峙强度", "拉高对峙强度"),
        (r"强化场面状态", "强化在场角色的可见反应"),
        (r"铺陈场面状态", "铺陈在场角色的可见反应"),
        (r"营造场面状态", "通过可见反应建立场面状态"),
    )
    for pattern, replacement in regex_replacements:
        body = re.sub(pattern, replacement, body)

    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if heading:
        return f"{heading}\n{body}" if body else heading
    return body


def _clean_rhythm_rewritten_script(text: str) -> str:
    cleaned = _cleanup_rhythm_abstract_language(text)
    lines = cleaned.splitlines()
    heading_markers = {
        "【改写后剧本】",
        "# 【改写后剧本】",
        "## 【改写后剧本】",
        "改写后剧本：",
    }
    wrapper_markers = {"---", "#", "```"}

    while True:
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and lines[0].strip() in heading_markers | wrapper_markers:
            lines.pop(0)
            continue
        break

    while True:
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and lines[-1].strip() in wrapper_markers:
            lines.pop()
            continue
        break

    return "\n".join(lines).strip()


def _normalise_script_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _validate_rhythm_structure_lock(original_script: str, rewritten_script: str) -> tuple[bool, list[str]]:
    original_lines = _normalise_script_lines(original_script)
    rewritten_lines = _normalise_script_lines(rewritten_script)

    cursor = 0
    missing: list[str] = []
    for line in original_lines:
        found = False
        while cursor < len(rewritten_lines):
            if rewritten_lines[cursor] == line:
                cursor += 1
                found = True
                break
            cursor += 1
        if not found:
            missing.append(line)
            if len(missing) >= 5:
                break
            continue

    return not missing, missing


def _rhythm_insert_continuity_rules() -> str:
    return (
        "【节奏插入连续性规则】\n"
        "1. 画面逻辑优先于情绪细节：任何新增辅助行都必须先保证人物位置、道具归属和下一拍连续性成立。\n"
        "2. 新增辅助行不得制造道具归属或位置跳变；同一件道具不能在相邻动作中同时被两个人持有、背着、收起或取用。\n"
        "3. 如果原文刚写某人拿起、捡起、塞回、攥住、交给某道具，新增行必须顺着这个状态承接，不能暗示道具已经离开该人。\n"
        "4. 低歧义画面优先：优先写\"放到桌上、站到门口、停住动作、看向某处\"等稳定可见动作，避免\"攥进掌心、指尖摩挲、掌心收紧\"等模型容易误画的细微手部状态。\n"
        "5. 插入儿童或人群小动作时，优先写身体姿态、站位、视线或停顿；只有原文明确道具已在该人物身上时，才写道具状态。\n"
    )


def _validate_rhythm_insert_continuity(original_script: str, rewritten_script: str) -> list[str]:
    original_lines = _normalise_script_lines(original_script)
    rewritten_lines = _normalise_script_lines(rewritten_script)
    issues: list[str] = []

    cursor = 0
    last_original = ""
    for original_line in original_lines:
        while cursor < len(rewritten_lines) and rewritten_lines[cursor] != original_line:
            inserted_line = rewritten_lines[cursor]
            if (
                "书包" in last_original
                and "照片" in last_original
                and "塞回书包" in last_original
                and "书包" in inserted_line
                and "小豆丁" in inserted_line
                and re.search(r"(背着|背上|挎着|单肩背着).*书包|书包.*(背着|背上|挎着)", inserted_line)
            ):
                issues.append(
                    "新增辅助行制造道具归属跳变：上一原文刚写照片塞回书包，"
                    f"下一插入行又写小豆丁背着书包：{inserted_line}"
                )
                return issues
            cursor += 1
        if cursor < len(rewritten_lines):
            last_original = rewritten_lines[cursor]
            cursor += 1

    return issues


def rhythm_rewrite_director_node(state: DirectorState) -> DirectorState:
    from .legacy_impl import (
        _agent_outputs,
        _persist_update,
        _record_knowledge_metadata,
        build_system_prompt,
        call_llm,
    )

    outputs = _agent_outputs(state)

    if bool(state.get("speed_mode", False)):
        outputs["rhythm_rewrite_director"] = "[快速模式] 跳过节奏改写，剧本原文直接透传。"
        return _persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_1_analyze",
                "message": "快速模式：已跳过节奏改写，场景分析师正在分析...（2/6）",
                "agent_outputs": outputs,
                "atmosphere_strategy": "",
            },
        )

    rhythm_hint = (
        f"节奏总控 剧本改写 动作增补 氛围渲染 微表情 死寂气口 蓄力泄压 "
        f"受击反应 情绪曲线 竖屏压迫 {state['script'][:200]}"
    )
    system_prompt, retrieval_meta = build_system_prompt(
        "你是一位短剧导演系统的节奏总控。你的任务不是改写剧本，而是诊断节奏并给下游拆片和镜头导演施工指令。\n\n"
        "绝对禁止：\n"
        "1. 不得输出改写后剧本。\n"
        "2. 不得改写、补写、删除、调换任何台词、动作、道具、人物关系或剧情事实。\n"
        "3. 不得把普通停顿、受击反应、信息揭示自动判定为独立片段。\n\n"
        "你只输出以下内容：\n"
        "- rhythm_diagnosis：哪里快、哪里慢、哪里需要停、哪里压缩、哪里卡断、哪里给反应。\n"
        "- construction_notes：给 story_planner 的拆片施工指令，说明哪些内容应合并为 15 秒以内完整剧情任务，哪些明确需要卡断/钩子/尾帧承接。\n"
        "- shot_director_notes：给 shot_director 的镜头施工指令，说明反应归属、停顿位置、卡断落点和尾帧承接。\n\n"
        "判断规则：\n"
        "1. 普通停顿、受击反应、信息揭示默认留在当前片段内部，由镜头导演处理。\n"
        "2. 只有明确出现卡断、钩子、尾帧、下一段承接、重大反转落点时，才允许建议拆短片段。\n"
        "3. 单段拆片目标是适配 Seedance 2.0 的 15 秒以内完整剧情任务，推荐 4-8 条原文事件。\n"
        "4. 超过 8 条原文事件应建议拆开；少于 4 条通常建议合并，除非是明确钩子、卡断或重大反转落点。\n",
        "rhythm_rewrite_director",
        context_hint=rhythm_hint,
    )

    user_prompt = (
        "请只做节奏诊断和施工指令，不要改写剧本。\n\n"
        f"【原始剧本】\n{state['script']}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n"
    )
    output = call_llm(system_prompt, user_prompt, agent_name="rhythm_rewrite_director")
    output = _cleanup_rhythm_abstract_language(output)
    knowledge_metadata = _record_knowledge_metadata(state, "rhythm_rewrite_director", rhythm_hint, retrieval_meta)
    atmosphere_strategy = output.strip()
    outputs["rhythm_rewrite_director"] = atmosphere_strategy
    return _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_1_analyze",
            "message": "节奏总控诊断完成，场景分析师正在分析...（1/6）",
            "atmosphere_strategy": atmosphere_strategy,
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
        },
    )

    atmosphere_strategy = ""
    rewritten_script = ""
    strategy_markers = ["【氛围与调度指导", "atmosphere_strategy", "【调度指导】"]
    split_found = False
    for marker in strategy_markers:
        if marker in output:
            split_pos = output.index(marker)
            atmosphere_strategy = _cleanup_rhythm_abstract_language(output[split_pos:], preserve_heading=True)
            rewritten_script = _clean_rhythm_rewritten_script(output[:split_pos].strip())
            split_found = True
            break

    if split_found:
        rebuilt_output: list[str] = []
        if rewritten_script:
            rebuilt_output.append(f"【改写后剧本】\n{rewritten_script}")
        if atmosphere_strategy:
            rebuilt_output.append(atmosphere_strategy)
        outputs["rhythm_rewrite_director"] = "\n\n".join(rebuilt_output).strip() or output
    else:
        outputs["rhythm_rewrite_director"] = output

    if split_found and rewritten_script:
        structure_ok, missing_lines = _validate_rhythm_structure_lock(state["script"], rewritten_script)
        continuity_issues = _validate_rhythm_insert_continuity(state["script"], rewritten_script) if structure_ok else []
        if not structure_ok or continuity_issues:
            if not structure_ok:
                print(f"  [Rhythm] WARN: 结构锁校验失败，尝试插入式修复。缺失原文行示例: {missing_lines[:3]}")
            if continuity_issues:
                print(f"  [Rhythm] WARN: 插入连续性校验失败，尝试插入式修复。问题示例: {continuity_issues[:3]}")
            issue_examples = missing_lines[:5] if missing_lines else continuity_issues[:5]
            repair_prompt = (
                "你上一版改写越界了。请重新输出，必须采用\"原文保留 + 插入辅助反应\"的方式。\n\n"
                "硬规则：\n"
                "1. 原剧本所有非空原文必须逐字逐行保留，并按原顺序出现；不能补全括号、不能修正标点、不能润色原句。\n"
                "2. 不得改名、改场景、改地点、改道具、改OS、改字幕、改音效、改闪回标记、改动作路径。\n"
                "3. 允许的创造性只有一种：在原文行与行之间插入新的\"▲\"辅助反应行。\n"
                "4. 插入行必须是当前场景内可拍动作，不承担新剧情因果。\n"
                "5. 每个节奏点最多插入 1-2 行，不要堆特写，不要写抽象词。\n\n"
                + _rhythm_insert_continuity_rules()
                + "\n"
                "可插入的例子：\n"
                "- 在\"▲乔熙手忙脚乱地给小豆丁穿衣服，一边打电话。\"之后，可以插入\"小豆丁把袖子缩回去\"\"小豆丁蹬着一只没穿好的鞋往床边躲\"等调皮动作。\n"
                "- 在\"▲天御集团门口，秘书和主管们列队等候，气氛紧张。\"之后，可以插入\"几名秘书和主管从大楼里快步跑出，在门口匆忙站成两列\"等紧张调度。\n\n"
                "你上一版的问题示例：\n"
                + "\n".join(f"- {line}" for line in issue_examples)
                + "\n\n【必须保留的原始剧本】\n"
                + state["script"]
            )
            repaired_output = call_llm(system_prompt, repair_prompt, agent_name="rhythm_rewrite_director")
            repaired_output = _cleanup_rhythm_abstract_language(repaired_output)

            repaired_script = ""
            repaired_strategy = ""
            repaired_split = False
            for marker in strategy_markers:
                if marker in repaired_output:
                    split_pos = repaired_output.index(marker)
                    repaired_strategy = _cleanup_rhythm_abstract_language(repaired_output[split_pos:], preserve_heading=True)
                    repaired_script = _clean_rhythm_rewritten_script(repaired_output[:split_pos].strip())
                    repaired_split = True
                    break

            if repaired_split and repaired_script:
                repaired_ok, repaired_missing = _validate_rhythm_structure_lock(state["script"], repaired_script)
                repaired_continuity_issues = (
                    _validate_rhythm_insert_continuity(state["script"], repaired_script) if repaired_ok else []
                )
                if repaired_ok and not repaired_continuity_issues:
                    outputs["rhythm_rewrite_director"] = (
                        f"【改写后剧本】\n{repaired_script}\n\n{repaired_strategy}"
                    )
                    rewritten_script = repaired_script

    persist_payload: dict[str, Any] = {
        "status": "running_phase_1",
        "step": "step_1_analyze",
        "message": "节奏总控诊断完成，场景分析师正在分析...（1/6）",
        "atmosphere_strategy": atmosphere_strategy,
        "agent_outputs": outputs,
    }

    if split_found and rewritten_script:
        persist_payload["script"] = rewritten_script
    elif not split_found and output.strip():
        cleaned = _cleanup_rhythm_abstract_language(output.strip())
        for prefix in ["【改写后剧本】", "# 改写后剧本", "改写后剧本："]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        if cleaned and cleaned != state.get("script", ""):
            persist_payload["script"] = cleaned
        print("  [Rhythm] WARN: 未能识别改写/策略分隔标记，已把整段 LLM 输出作为改写剧本使用。")

    return _persist_update(state, persist_payload)
