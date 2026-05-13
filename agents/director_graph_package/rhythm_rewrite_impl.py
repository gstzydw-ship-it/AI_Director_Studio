"""Package-local rhythm_rewrite_director implementation extracted from legacy_impl."""
from __future__ import annotations

import re
from typing import Any

from .llm import call_llm

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


_RHYTHM_SUGGESTED_DURATION_RE = re.compile(
    r"(建议时长(?:[：:])?\s*(?:\n\s*)?)(\d+(?:\.\d+)?)\s*(?:[-—–~～至到]\s*(\d+(?:\.\d+)?))?\s*秒"
)


def _format_rhythm_seconds(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _clamp_rhythm_segment_duration_suggestions(text: str) -> str:
    if not text:
        return ""

    def _replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        start = float(match.group(2))
        end_text = match.group(3)
        if end_text is None:
            if start <= 15:
                return match.group(0)
            return f"{prefix}13-15秒（原建议超过15秒，需压缩或拆为相邻片段）"

        end = float(end_text)
        lower, upper = sorted((start, end))
        if upper <= 15:
            return match.group(0)
        if lower >= 15:
            return f"{prefix}13-15秒（原建议超过15秒，需压缩或拆为相邻片段）"
        return f"{prefix}{_format_rhythm_seconds(lower)}-15秒"

    return _RHYTHM_SUGGESTED_DURATION_RE.sub(_replace, text)


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
        "节奏总控 时间分配 段落位置 节奏合同 片段边界 "
        "反应归属 停顿 停在未完成状态 尾帧承接 时长建议 切镜预算 无效过渡压缩 "
        "下游施工指令 不新增动作 不改写剧本 禁止新增事件 禁止重排台词 "
        f"aspect_ratio {state.get('aspect_ratio', '16:9')}"
    )


def _rhythm_retrieval_profile(state: DirectorState) -> dict[str, Any]:
    return {
        "agent_scope": ["rhythm_rewrite_director"],
        "rule_type": [
            "rhythm_rewrite",
            "dramatic_signal_rhythm",
            "story_rhythm",
            "segment_boundary",
            "tailframe_handoff",
            "reaction_ownership",
        ],
        "priority": ["P0", "P1", "hard"],
        "signals": [
            "dialogue_coverage",
            "action_coverage",
            "continuity_lock",
            "reaction_beat",
            "timing_allocation",
            "pause_point",
            "cut_point",
            "tailframe_handoff",
            "cut_budget",
            "transition_trim",
        ],
        "scene_types": ["dialogue", "action", "suspense", "confrontation", "daily_rush"],
        "events": [
            "reaction",
            "collision",
            "power_reversal",
            "suspense_reveal",
            "segment_boundary",
            "speed_shift",
        ],
        "risks": [
            "script_invention_risk",
            "over_segmentation",
            "rewriting_script_facts",
            "duplicate_action_enhancement",
        ],
        "dialogue_types": ["long_dialogue_compression", "reaction_beat", "power_confrontation"],
        "aspect_ratios": [str(state.get("aspect_ratio", "16:9"))],
        "registry_top_k": 3,
        "max_chunks_per_source": 1,
    }


def _rhythm_user_director_intent(state: DirectorState) -> str:
    candidate_fields = (
        ("director_intent", "导演意图"),
        ("user_director_intent", "用户导演意图"),
        ("user_notes", "用户备注"),
        ("director_notes", "导演备注"),
        ("creative_brief", "创作简报"),
        ("requirements", "补充要求"),
    )
    lines: list[str] = []
    for key, label in candidate_fields:
        value = state.get(key)
        if not value:
            continue
        if isinstance(value, str):
            text = value.strip()
        else:
            text = str(value).strip()
        if text:
            lines.append(f"{label}: {text}")
    return "\n".join(lines)


def _rhythm_supervisor_role_prompt() -> str:
    return (
        "你是一位短剧导演系统的节奏总控导演。你的任务不是改写剧本、不是增强动作，"
        "而是把当前施工剧本和上游导演意图转成可执行的时间与段落合同。\n\n"
        "核心职责：\n"
        "1. 只基于当前施工剧本中已经存在的动作、台词、停顿、转场和剧情增强契约进行判断。\n"
        "2. 决定已有内容的时间分配：哪些过渡压缩到几秒、哪些信息或反应至少停留几秒、哪些内容不拆。\n"
        "3. 决定段落位置：哪些事件合并、哪些地方拆分、哪些普通反应留在段内、哪些地方停在未完成状态给下一段承接。\n"
        "4. 决定反应归属和尾帧承接：反应属于本段还是下一段开头，段尾必须停在哪个可见状态。\n"
        "5. 给结构规划师和镜头导演分别输出下游操作单；结构规划师只收到分段操作，镜头导演只收到拍摄节奏操作。\n\n"
        "快节奏判断：\n"
        "- 快节奏优先来自短时间内的有效事件密度和人物动作/表情紧张态，而不是单纯增加切镜数量。\n"
        "- 只有当原文事件密集、动作/反应紧张或无效过渡可压缩时，才建议快切或短段化；不能为了显得快而把普通动作切碎。\n"
        "- 镜头快切只是辅助表达，必须设置最多镜头数和每镜停留边界；镜头过密会损害观感、连续性和信息可读性。\n"
        "- 快段仍必须保留信息命中点、动作顶点、人物第一反应和可继承尾帧，不能把观众需要读懂的反应剪没。\n\n"
        "片段时长硬约束：\n"
        "- 单个结构片段的建议时长绝对不得超过15秒；禁止输出 16秒、18-22秒、14-17秒 这类超过15秒上限的建议。\n"
        "- 如果已有事件在15秒内无法清楚承载，必须改为压缩无效过渡、合并短停留或建议拆成相邻片段；不能用拉长单片段解决。\n"
        "- 快节奏戏剧任务优先使用 4-10秒短段或 11-15秒紧凑段；普通段也只能写 13-15秒，不得写 18-22秒。\n\n"
        "硬边界与完整性：\n"
        "- 当前施工剧本中的转场标识、字幕标识、闪回开始/闪回结束是硬边界；不得把闪回前的现实触发反应和闪回内容合并成同一个结构片段。\n"
        "- 照片滑出、人物识别、孩子关于照片人物的台词、现实人物第一反应属于照片触发段；后续闪回必须从闪回开始标识之后独立承接。\n"
        "- 每个原文锚点必须完整写完所有字段，不得输出半截字段名或半截句子；如果内容过长，优先减少条目数量而不是截断字段。\n\n"
        "工作量控制：\n"
        "- 只处理会影响拆片、停顿、段尾状态、尾帧或镜头节奏的关键锚点；普通顺畅动作不必逐条分析。\n"
        "- 每个列表优先控制在 3-5 条；没有必要约束的字段写 无。\n"
        "- 不做完整剧情复盘，不做镜头方案，不做动作增强，只给下游必须遵守的节奏合同。\n\n"
        "绝对禁止：\n"
        "1. 不得新增动作、道具阻碍、人物调度、声音事件、人物反应、台词或剧情事实。\n"
        "2. 不得输出改写后剧本，不得改写、补写、删除、调换任何台词、人物关系或剧情结果。\n"
        "3. 不得继续提出动作层/调度层/剧情层增强方案；这些属于剧情增强导演。\n"
        "4. 不得把节奏建议写成新的剧情事件；每条建议必须绑定当前施工剧本中的原文锚点。\n"
        "5. 不得把普通停顿、受击反应、信息揭示自动判定为独立片段。\n"
        "6. 不得只写“节奏快/节奏慢”，必须把快慢翻译成下游能执行的操作字段。\n"
        "7. 输出中禁止使用 快推、慢拍、刹车、卡断、尾钩、爆点、爽点、压迫感 等导演黑话作为最终指令；必须改写成“必须包含/不能省略/建议时长/最多镜头数/结尾必须停在”。\n\n"
        "输出格式必须包含以下中文字段，字段名必须原样保留，便于下游读取；不得输出英文字段名：\n"
        "- 节奏诊断：仅供 UI 和调试查看，不传给下游；最多 3 条，说明为什么需要压缩、保护反应、独立成段或正常承接。\n"
        "- 给结构规划师：只写拆片 agent 需要的操作单；每条必须包含 原文锚点、分段决定、必须包含的原文事件、不能包含的后续事件、建议时长、可以压缩、不能省略、结尾必须停在、承接提醒。\n"
        "- 给镜头导演：只写镜头 agent 需要的操作单；每条必须包含 原文锚点、本段必须拍完整、可以省略、不能省略、最少停留时间、最多镜头数、禁止新增、结尾画面必须是。\n"
        "- 风险提醒：只保留下游执行会踩坑的硬风险，例如误加动作、误拆、误改道具状态、把节奏建议当剧情事实；没有风险也必须写 无，不能省略该字段。\n\n"
        "给结构规划师.分段决定 只能使用这些明确值：独立成段 / 与前面合并 / 与后面合并 / 留在当前段内 / 正常承接。\n"
        "给结构规划师.建议时长 必须写 15秒以内的范围或单值；若内容密度过高，写 13-15秒 并在承接提醒中说明需要压缩或拆段，不能写超过15秒。\n"
        "给结构规划师 不能写镜头数量、景别、运镜、情绪解释、戏剧理论或镜头方案。\n\n"
        "给镜头导演.最多镜头数 必须使用具体数量，不得只写高/中/低：\n"
        "- 主镜头：最多主镜头数，例如 1、1-2、2、2-3。\n"
        "- 辅助插入镜头：最多辅助插入镜头数，例如 0、0-1、1。\n"
        "给镜头导演.最少停留时间 必须使用具体秒数；没有停留要求也要写 0秒 或 无。\n"
        "给镜头导演 不能写是否独立成段、分段推理、全局节奏分析或知识库解释。\n\n"
        "锚点归属必须写清楚：当前施工剧本明确事实、剧情增强导演意图、用户指定导演意图、节奏合同建议。"
    )


def _rhythm_supervisor_user_prompt(state: DirectorState) -> str:
    user_intent = _rhythm_user_director_intent(state)
    user_intent_block = user_intent or "无单独补充；只根据当前施工剧本做时间分配和段落位置判断。"
    script_label = "当前施工剧本（已由剧情增强导演处理）" if state.get("enhanced_script") else "当前施工剧本"
    director_contract = str(state.get("director_brief") or "").strip()
    scene_context = str(state.get("scene_context_brief") or "").strip()
    return (
        "请只做时间分配、段落位置、反应归属、段尾状态和尾帧承接，不要改写剧本，不要新增动作。\n\n"
        f"【{script_label}】\n{state['script']}\n\n"
        f"【剧情增强导演契约】\n{director_contract or '无；仅以当前施工剧本为准。'}\n\n"
        f"【场景预分析约束】\n{scene_context or '无；不得自行补充空间、站位或道具。'}\n\n"
        f"【用户导演意图/补充要求】\n{user_intent_block}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n\n"
        "【处理要求】\n"
        "1. 每条节奏建议都必须绑定当前施工剧本中的原文锚点；没有锚点就写入风险提醒，不得执行。\n"
        "2. 动作密度已经由剧情增强导演完成；你只判断已有动作的时长、停顿、不拆、拆分、段尾状态和承接。\n"
        "3. 用户意图只可影响时间分配和段落位置；不得把用户意图补写成当前施工剧本外的新动作。\n"
        "4. 给结构规划师的内容只服务结构规划师：影响目标时长、片段边界、反应计划、连续性；不要放镜头数量、景别或运镜。\n"
        "5. 给镜头导演的内容只服务镜头导演：影响必须拍完整/可以省略/不能省略/停留秒数/最多镜头数/结尾画面；不要放分段推理或全局节奏分析。\n"
        "6. 对走向电梯、按按钮、门打开、进门、走廊移动、上下车等机械过渡，只在不影响主线、人物位置、道具状态、台词和剧情因果时给无效过渡压缩建议。\n"
        "7. 需要快节奏时，先确认事件密度和人物紧张态，再用有限快切辅助；不得只靠密集切镜制造速度。\n"
        "8. 禁止输出 快推、慢拍、刹车、卡断、尾钩、爆点、爽点、压迫感 等导演黑话；用明确操作字段替代。\n"
        "9. 最多镜头数和最少停留时间必须给具体数量；不要只写高/中/低切镜密度。\n"
        "10. 给结构规划师的建议时长必须小于或等于15秒；任何 16秒以上或 18-22秒 之类范围都是硬错误，应改成 13-15秒并提示压缩或拆段。\n"
        "11. 闪回开始/闪回结束、字幕、现实回神是片段边界硬锚点；不要把闪回前的现实照片触发反应和闪回本体合并进同一条结构规划建议。\n"
        "12. 输出必须以完整的 风险提醒 字段结束；不得停在“不能包含的后”“建议时”等半截字段或半截句子。\n"
    )


def rhythm_rewrite_director_node(state: DirectorState) -> DirectorState:
    from .legacy_impl import (
        _agent_outputs,
        _persist_update,
        _record_knowledge_metadata,
    )
    from .helpers import build_system_prompt

    outputs = _agent_outputs(state)

    if bool(state.get("speed_mode", False)):
        outputs["rhythm_rewrite_director"] = "[快速模式] 跳过节奏改写，剧本原文直接透传。"
        return _persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_2_plan",
                "message": "快速模式：已跳过节奏总控，结构规划师正在拆片...（4/8）",
                "agent_outputs": outputs,
                "atmosphere_strategy": "",
            },
        )

    rhythm_hint = _rhythm_context_hint(state)
    rhythm_profile = _rhythm_retrieval_profile(state)
    _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_0_rhythm",
            "message": "节奏总控正在检索节奏规则和上下文...",
            "agent_outputs": outputs,
        },
    )
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
    _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_0_rhythm",
            "message": "节奏总控正在调用大模型生成节奏策略...",
            "agent_outputs": outputs,
        },
    )
    output = call_llm(system_prompt, user_prompt, agent_name="rhythm_rewrite_director")
    output = _cleanup_rhythm_abstract_language(output)
    output = _clamp_rhythm_segment_duration_suggestions(output)
    knowledge_metadata = _record_knowledge_metadata(state, "rhythm_rewrite_director", rhythm_hint, retrieval_meta)
    atmosphere_strategy = output.strip()
    outputs["rhythm_rewrite_director"] = atmosphere_strategy
    return _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_2_plan",
            "message": "节奏总控诊断完成，结构规划师正在拆片规划...（4/8）",
            "atmosphere_strategy": atmosphere_strategy,
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
        },
    )
