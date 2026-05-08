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


def _rhythm_context_hint(state: DirectorState) -> str:
    return (
        "节奏总控 冲突诊断 戏剧冲突弱点 冲突增强分级 速度曲线 "
        "动作密度 声音压力 道具阻碍 人物调度 时间压力 隐藏信息 情绪伤口 "
        "下游施工指令 戏剧微粒 受击反应 停顿 卡断 尾帧承接 "
        "禁止改写剧本 禁止新增事件 禁止重排台词 "
        f"aspect_ratio {state.get('aspect_ratio', '16:9')}"
    )


def _rhythm_retrieval_profile(state: DirectorState) -> dict[str, Any]:
    return {
        "agent_scope": ["rhythm_rewrite_director"],
        "rule_type": [
            "rhythm_rewrite",
            "dramatic_signal_rhythm",
            "story_rhythm",
            "conflict_diagnosis",
            "speed_curve",
        ],
        "priority": ["P0", "P1", "hard"],
        "signals": [
            "dialogue_coverage",
            "action_coverage",
            "continuity_lock",
            "reaction_beat",
            "time_pressure",
            "prop_pressure",
            "sound_pressure",
            "action_density",
        ],
        "scene_types": ["dialogue", "action", "suspense", "confrontation", "daily_rush"],
        "events": [
            "reaction",
            "collision",
            "power_reversal",
            "suspense_reveal",
            "conflict_escalation",
            "speed_shift",
        ],
        "risks": [
            "script_invention_risk",
            "over_segmentation",
            "rewriting_script_facts",
            "weak_conflict",
        ],
        "dialogue_types": ["long_dialogue_compression", "reaction_beat", "power_confrontation"],
        "aspect_ratios": [str(state.get("aspect_ratio", "16:9"))],
        "registry_top_k": 3,
        "max_chunks_per_source": 1,
    }


def _rhythm_user_director_intent(state: DirectorState) -> str:
    candidate_keys = (
        "director_intent",
        "user_director_intent",
        "user_notes",
        "director_notes",
        "creative_brief",
        "requirements",
        "visual_requirements",
        "reference_images",
    )
    lines: list[str] = []
    for key in candidate_keys:
        value = state.get(key)
        if not value:
            continue
        if isinstance(value, str):
            text = value.strip()
        else:
            text = str(value).strip()
        if text:
            lines.append(f"{key}: {text}")
    return "\n".join(lines)


def _rhythm_supervisor_role_prompt() -> str:
    return (
        "你是一位短剧导演系统的节奏总控导演。你的任务不是改写剧本，"
        "而是先诊断戏剧冲突，再把剧本和用户导演意图转成可执行的节奏调度方案。\n\n"
        "核心职责：\n"
        "1. 对任何剧本先做冲突诊断：主角目标、阻力、失败代价、时间压力、隐藏信息、情绪伤口、冲突弱点。\n"
        "2. 如果冲突偏弱，必须给出冲突增强方案，但要分清权限边界。\n"
        "3. 必须输出速度曲线：哪里起速、靠什么动作加速、哪里刹车、为什么慢、哪里再启动、爆点和钩子落点在哪里。\n"
        "4. 必须把概括性动作翻译为可拍的动作密度，例如“手忙脚乱”“急匆匆”“气氛紧张”“列队等候”。\n"
        "5. 必须给 story_planner 和 shot_director 下游施工指令，说明哪些是段内节拍、哪些需要拆片或卡断。\n\n"
        "增强权限分级：\n"
        "- L1_动作层增强：允许增加动作密度、声音压力、道具阻碍、时间压力、人物可见反应；不改剧情事实和台词。\n"
        "- L2_调度层增强：允许调整人物进入方向、信息释放顺序、群体压迫、谁先看到谁；不改变事件结果。\n"
        "- L3_剧情层增强：涉及新增事件、改变因果、增加误会或反转时，必须标为“需用户确认”，不能作为最终执行指令。\n\n"
        "绝对禁止：\n"
        "1. 不得输出改写后剧本。\n"
        "2. 不得改写、补写、删除、调换任何台词、人物关系或剧情事实。\n"
        "3. 不得把 L3 剧情层增强伪装成已确定剧情。\n"
        "4. 不得把普通停顿、受击反应、信息揭示自动判定为独立片段。\n"
        "5. 不得只写“节奏快/节奏慢”，快节奏必须写动作密度，慢节奏必须写停顿位置。\n\n"
        "输出格式必须包含以下字段，字段名必须原样保留，便于下游读取：\n"
        "- conflict_diagnosis：冲突诊断，包含目标、阻力、失败代价、时间压力、隐藏信息/情绪伤口、冲突弱点。\n"
        "- conflict_enhancement_plan：冲突增强方案，按 L1/L2/L3 分级；L3 必须写“需用户确认”。\n"
        "- speed_curve：速度曲线，按场次或片段写起速、加速动作、刹车点、慢拍原因、再启动点、爆点、钩子落点。\n"
        "- rhythm_diagnosis：节奏诊断，说明哪里快、哪里慢、哪里停、哪里压缩、哪里卡断、哪里给反应。\n"
        "- construction_notes：给 story_planner 的拆片施工指令，说明合并、拆分、卡断、尾帧承接。\n"
        "- shot_director_notes：给 shot_director 的镜头施工指令，说明动作密度、反应归属、停顿位置、卡断落点和尾帧承接。\n\n"
        "锚点归属必须写清楚：原文明确事实、概括动作可展开、用户指定导演意图、建议补强锚点、需用户确认剧情增强。"
    )


def _rhythm_supervisor_user_prompt(state: DirectorState) -> str:
    user_intent = _rhythm_user_director_intent(state)
    user_intent_block = user_intent or "无单独补充；只根据原始剧本做冲突诊断和节奏增强。"
    return (
        "请只做冲突诊断、节奏增强方案和下游施工指令，不要改写剧本。\n\n"
        f"【原始剧本】\n{state['script']}\n\n"
        f"【用户导演意图/补充要求】\n{user_intent_block}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n\n"
        "【处理要求】\n"
        "1. 如果原剧本冲突弱，先指出弱点，再用 L1/L2 增强动作、声音、道具、调度和信息释放。\n"
        "2. 当原文只写概括词，如“忙乱、急匆匆、紧张、等待、愣住”，必须转成可拍节奏锚点。\n"
        "3. 如果某个增强来自用户明确要求，标为“用户指定导演意图”，并优先传给下游。\n"
        "4. 如果某个增强是你基于剧本推断，标为“建议补强锚点”，不能当作原文事实。\n"
        "5. 如果增强会改变剧情因果或新增关键事件，放入 L3_剧情层增强，并标注“需用户确认”。\n"
    )


def rhythm_rewrite_director_node(state: DirectorState) -> DirectorState:
    from .legacy_impl import (
        _agent_outputs,
        _persist_update,
        _record_knowledge_metadata,
        call_llm,
    )
    from .helpers import build_system_prompt

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

    rhythm_hint = _rhythm_context_hint(state)
    rhythm_profile = _rhythm_retrieval_profile(state)
    system_prompt, retrieval_meta = build_system_prompt(
        _rhythm_supervisor_role_prompt(),
        "rhythm_rewrite_director",
        context_hint=rhythm_hint,
        retrieval_profile=rhythm_profile,
        include_critical_knowledge=False,
        fallback_to_full_knowledge=False,
        retrieval_mode="profiled",
    )

    user_prompt = _rhythm_supervisor_user_prompt(state)
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
