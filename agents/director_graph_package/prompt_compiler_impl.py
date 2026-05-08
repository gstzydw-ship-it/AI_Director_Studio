"""Prompt compiler implementation extracted from legacy_impl.

Owns prompt compilation guard helpers and the package runtime prompt_compiler node.
"""
from __future__ import annotations

import re
from typing import Any

from .types import DirectorState
from . import legacy_impl as _legacy

# V1 schema contract: shot_director outputs fragment_task/rhythm/shots
# with shot fields: duration, task, subject, shot, action, dialogue, must_carry, cut_point, continuity
# Legacy camera+size assets are still accepted at the compiler gate.
# Optional: type, audio
from .helpers import (
    _truncate_for_prompt,
    _runtime_context_contract_card,
    _shot_composition_task_selection_rules,
    _dialogue_coverage_contract_rules,
    _camera_execution_rules,
    _camera_task_selection_rules,
    _script_fidelity_rules,
    _subject_framing_rules,
    _yaml_line_field,
    _dialogue_payload_is_long,
    _MAIN_SHOT_BLOCK_RE,
    _DIALOGUE_COVERAGE_TERMS_RE,
    _fragment_id_for_segment_index,
    _segment_block_by_fragment_id,
)
from .llm import call_llm
from .prompting import build_system_prompt
from .state_store import _agent_outputs, _persist_update
from ..mcp_llm import call_llm_with_mcp

_record_knowledge_metadata = _legacy._record_knowledge_metadata
_scene_memory_card = _legacy._scene_memory_card
_current_segment_event_card = _legacy._current_segment_event_card
_reference_context = _legacy._reference_context
_validate_spatial_geometry_contract = _legacy._validate_spatial_geometry_contract
_cleanup_timeline_constraints = _legacy._cleanup_timeline_constraints
_normalise_prompt_character_aliases = _legacy._normalise_prompt_character_aliases
_INTERNAL_FIELD_LEAK_RE = _legacy._INTERNAL_FIELD_LEAK_RE
_SPATIAL_GEOMETRY_FIELDS = _legacy._SPATIAL_GEOMETRY_FIELDS
_AMBIGUOUS_PROMPT_CAMERA_TERMS = _legacy._AMBIGUOUS_PROMPT_CAMERA_TERMS
_ABSTRACT_PROMPT_TERMS = _legacy._ABSTRACT_PROMPT_TERMS
_SPATIAL_OVEREXPLAIN_TERMS_RE = _legacy._SPATIAL_OVEREXPLAIN_TERMS_RE
_SPACE_SECTION_ACTION_RE = _legacy._SPACE_SECTION_ACTION_RE
_ELEVATOR_OFFICE_DRIFT_RE = _legacy._ELEVATOR_OFFICE_DRIFT_RE
_ELEVATOR_ENTRY_RE = _legacy._ELEVATOR_ENTRY_RE
_ELEVATOR_CABIN_LOCK_RE = _legacy._ELEVATOR_CABIN_LOCK_RE
_ELEVATOR_NEGATIVE_SPACE_LOCK_RE = _legacy._ELEVATOR_NEGATIVE_SPACE_LOCK_RE
_PSEUDO_PRECISE_CAMERA_RE = _legacy._PSEUDO_PRECISE_CAMERA_RE
_EMPLOYEE_FACE_LOCK_RE = _legacy._EMPLOYEE_FACE_LOCK_RE
_UNSAFE_ACTION_TERMS = _legacy._UNSAFE_ACTION_TERMS
_REACTION_BEAT_TERMS = _legacy._REACTION_BEAT_TERMS
_DIALOGUE_VISUAL_CUT_RE = _legacy._DIALOGUE_VISUAL_CUT_RE
_PERFORMANCE_BEAT_RE = _legacy._PERFORMANCE_BEAT_RE
_TIMELINE_BRIDGE_RE = _legacy._TIMELINE_BRIDGE_RE
_TIMELINE_END_STATE_RE = _legacy._TIMELINE_END_STATE_RE
_SPATIAL_ANCHOR_RE = _legacy._SPATIAL_ANCHOR_RE
_CAMERA_RETREAT_INTO_DOOR_RE = _legacy._CAMERA_RETREAT_INTO_DOOR_RE
_PROXIMITY_CONTRADICTION_RE = _legacy._PROXIMITY_CONTRADICTION_RE
_SPATIAL_DIRECTION_TERMS_RE = _legacy._SPATIAL_DIRECTION_TERMS_RE
_EXPLICIT_CUT_RE = _legacy._EXPLICIT_CUT_RE
_REVERSE_SHOT_INSIDE_SEGMENT_RE = _legacy._REVERSE_SHOT_INSIDE_SEGMENT_RE
_PIXEL_ANCHOR_TERMS_RE = _legacy._PIXEL_ANCHOR_TERMS_RE
_AXIS_LEFT_RE = _legacy._AXIS_LEFT_RE
_AXIS_RIGHT_RE = _legacy._AXIS_RIGHT_RE
_SILENT_CUT_TRIGGER_RE = _legacy._SILENT_CUT_TRIGGER_RE
_NEW_SUBJECT_FRAMING_RE = _legacy._NEW_SUBJECT_FRAMING_RE


def _segment_block(text: str, segment_index: int, fragment_id: str | None = None) -> str:
    """Extract the YAML block for one Fxx fragment."""
    selected_fragment_id = fragment_id or _fragment_id_for_segment_index([], segment_index)
    return _segment_block_by_fragment_id(text, selected_fragment_id)

_INTERNAL_DIALOGUE_CUT_RE = re.compile(r"(镜头切至|镜头切到|切至|切到|切回|反打至|反打镜头|过肩|画外音|OS|L-cut|J-cut)")
_LISTENER_COVERAGE_RE = re.compile(r"(听者|对手|对方|受击|反应|反打|过肩|视线|下颌|呼吸|停顿|画外音|OS|L-cut|J-cut)")
_DIRECTOR_JARGON_RE = re.compile(
    r"("
    r"稳定器在同一运动里带到|同一运动里带到|顺势带到|带到.{0,12}(?:受压|受击|情绪)?反应|"
    r"受压反应|受击反应|情绪受击|被压住|压迫感|权力压住|气场压住|空气收紧|沉默就是回应|"
    r"压入|压住空间|卡断|卡在.{0,8}落点|尾帧悬停|悬停收尾|黄金停顿|留足回味|留白|气口|泄压|"
    r"炸点|钩子|情绪顶点|情绪任务|戏剧任务|节奏快狠|前慢后碎|稳慢压|凝滞|粘滞|暧昧感|氛围感|张力"
    r")"
)
_COMPLEX_CAMERA_PHRASE_RE = re.compile(
    r"("
    r"纵深中全景到[^，。；\n]{0,20}(?:半身中景|中景|近景)|"
    r"(?:中景|半身中景|关系景)转.{0,16}(?:中景|关系景|固定机位)|"
    r"同轴线偏右|同轴线偏左|大堂中轴偏右|大堂中轴偏左|右侧同轴|左侧同轴|"
    r"前后景关系|前后景分布|肩线/侧身分布|"
    r"稳定器在人物前方同速后退|稳定器在人物背后同速前进|稳定器在.{0,8}前方.{0,8}同速后退|"
    r"truck\s*(?:left|right)|横移\s*truck|"
    r"同一镜头内横移|横移.{0,12}回到|带过.{0,12}反应|"
    r"眼平高度"
    r")",
    re.IGNORECASE,
)


def _reaction_cut_and_action_path_rules() -> str:
    return (
        "【反应切镜与动作路径安全硬规则】\n"
        "1. 时间轴内可以也必须写清镜头切换。凡出现受击、回神、视线相撞、表情一僵、听完反应、松手等反应落点，必须明确写\"镜头切至/切回\"谁；单段内禁止写反打。\n"
        "2. 反应镜头必须写成：镜头切至乔熙胸部以上中近景，摄影机位于乔熙正前方0度或商北琛右肩后方，眼平高度，画面前景保留商北琛右肩/西装领口虚化，乔熙抬头看向他。\n"
        "3. 如果同一时间段内有\"商北琛说话 -> 乔熙受击反应 -> 商北琛继续说话 -> 乔熙回神动作\"，必须拆成至少两个同侧镜头句：说话镜头、乔熙听者反应/过肩镜头；不要全塞在同一个双人中景里。\n"
        "4. 所有关键动作必须写清\"起点 -> 路径 -> 接触/避让对象 -> 终点 -> 结束状态\"。禁止只写结果词，例如冲入、撞上、退开、弹开、转身、靠近、拉开、扶住、松开、走进。\n"
        "5. 身体位移动作必须写清移动方向和停止位置：从门外中轴向电梯门缝冲入，右肩先穿过门缝，脚步在商北琛胸前半步处刹停失败，身体前倾撞到他胸前，最后停在电梯内近门侧。\n"
        "6. 接触动作必须写清接触部位和力度状态：商北琛右手从身侧抬到乔熙右腰侧，手掌平贴腰侧布料扶住，不上滑、不环抱，乔熙重心停止前扑。\n"
        "7. 离开接触点的动作必须写清离开路径和结束位置：手指松开西装前襟 -> 手掌向自己胸前后撤10-15厘米 -> 自然落回身体两侧或移向发梢。\n"
        "8. 禁止写\"手弹开\"\"从西装前襟弹开\"\"飞开\"\"甩开\"\"弹向空中\"\"猛地弹开\"\"身体弹开\"\"突然闪开\"。这些词会让视频模型生成肢体乱甩或空间跳变。\n"
        "9. 正确示例：乔熙双手松开商北琛西装前襟，手指张开，双手先向自己胸前收回约一掌距离，再自然下落到身体两侧；手掌不向上甩、不出画、不再碰到商北琛。\n"
        "10. 所有反应镜头都要交代画面内可见物：谁在前景虚化、谁占画面中心、被抓住的西装前襟是否仍可见、电梯门或门框在画面哪一侧。\n"
        "11. 明确切镜不等于频繁碎切。13秒以内片段通常控制在4-5个有效镜头；只有上游明确给出关键 sub_shot 时才允许更多。\n"
        "12. 单个2秒以内时间段禁止同时承载\"局部插入镜头 + 切回人物中近景 + 一整句长台词\"。长台词至少给3秒左右，手部/道具插入镜头应放在台词前后，或并入双人中景完成。\n"
        "13. 反应切镜要服务信息增量：说话者镜头、同侧听者反应、动作路径复位可以各自成镜；不要为了每个微动作单独切镜。\n"
    )


def _timeline_continuity_contract_rules() -> str:
    return (
        "【时间轴段内连续性交接硬规则】\n"
        "1. 时间轴不是独立小段落拼接。每个时间段都必须包含：承接上一段的入口状态、当前动作推进、结束状态。\n"
        "2. 除第一个时间段外，每个时间段开头必须明确写\"同一机位继续\"\"延续上一镜\"\"镜头切至/切回\"之一；不能直接重新开一个新主体新机位，单段内禁止反打。\n"
        "3. 如果同一机位继续，必须继承上一时间段尾部的人物位置、朝向、景别、空间锚点；只能让动作在这个状态上继续推进。\n"
        "4. 如果镜头切至新机位，必须写清切镜类型和原因：同侧反应、动作承接、插入细节、空间复位、尾帧复位；禁止无理由硬切。\n"
        "5. 每次切镜必须保留至少一个空间锚点：电梯门框、走廊中轴、大堂两侧员工列、商北琛身体方向、严飞所在侧边位置等。没有锚点的切镜会被模型当成换场。\n"
        "6. 每个时间段最后一句必须写清结束状态：谁停在什么位置、身体朝向哪里、谁仍在画内/画外、门/道具/手部/距离状态是什么。\n"
        "7. 下一个时间段的第一句必须继承上一个时间段最后一句的结束状态；如果不继承，必须明确说明这是\"镜头切至同一空间的另一机位\"，并说明保留的空间锚点。\n"
        "8. 人物相对机位和场景固定机位不能混用。人物要转身、进入电梯、穿过门框时，必须切换为场景固定机位，例如\"摄影机固定在电梯门外大堂中轴，朝向电梯内部\"。\n"
        "9. 禁止写成\"3-6秒：员工群体中景...\"这种像新 prompt 的开头；应写成\"延续上一镜/镜头切至员工列反应中景，保留商北琛背影在右前景...\"并说明承接关系。\n"
        "10. 尾段尤其要拆清楚：命令落点、让路、进入电梯、门合拢不能塞进一个固定人物正面镜头；必须用场景固定机位或明确切镜桥接。\n"
        "11. 空间锚点的前景/后景必须符合摄影机位置与人物朝向。若人物面朝电梯且镜头拍人物正面，摄影机就在电梯方向，电梯门框不能写成后景；只能写成前景边缘、侧边门框，或改用人物背面/侧背机位让电梯门框位于前方。\n"
    )




def _director_jargon_translation_rules() -> str:
    return (
        "【导演调度翻译成 Seedance 可见语言硬规则】\n"
        "1. prompt_compiler 的职责不是照抄 shot_director 的导演口语，而是把它翻译成 Seedance 能直接生成的画面自然句。它负责翻译，不负责再导演。\n"
        "2. 禁止原样输出\"稳定器在同一运动里带到\"、\"同一机位继续\"这类导演现场口令；必须改成镜头切至、固定机位保持、或具体可见动作。\n"
        "3. 如果画面主体从 A 变成 B，必须写成\"镜头切至 B\"，不能写\"同一机位继续拍 B\"。\n"
        "4. 只有同一人物在当前空间内切换景别，才允许写\"镜头切近至\"、\"镜头拉开至\"等承接词。\n"
        "5. \"受压反应/被压住\"必须改成可见表演：低头、屏住呼吸、肩膀收紧、眼神回避、嘴唇停住、身体僵住、让开通道、没人说话。\n"
        "6. \"压入/卡断/炸点/钩子/尾帧悬停\"必须改成动作或台词触发：台词说完后停0.8秒、手刚要抬起时切镜、门尚未完全闭合时冲入、画面停在两人身体接触瞬间。\n"
        "7. \"凝滞/粘滞/暧昧感/张力\"必须改成身体距离、视线时长、动作速度和表情落点：两人相距半步、对视1秒、手停在腰侧不移动、乔熙嘴唇停住。\n"
        "8. \"气口/留白/回味/泄压\"必须改成时间和画面状态：停0.5-1秒、无人说话、人物停在原位、镜头保持固定、呼吸放慢。\n"
        "9. 正确示例：\"镜头切至严飞和几名主管胸部以上中近景；严飞微微低头，主管们肩膀收紧、屏住呼吸、避开商北琛视线。\"\n"
        "10. 错误示例：\"稳定器在同一运动里带到严飞和主管胸部以上受压反应。\" 这类句子像导演现场口令，不能作为最终 Seedance prompt。\n"
        "11. 上游若写\"纵深中全景到半身中景\"\"中景转关系景\"\"同轴线偏右\"\"眼平高度\"\"truck right/left\"，最终必须降级为一个简单镜头基底：\"大堂全景\"、\"商北琛半身中景\"、\"电梯口固定中景\"、\"正面平稳跟拍\"。\n"
    )


def _has_negation_near(text: str, start: int, end: int, window: int = 30) -> bool:
    """Return whether a matched phrase is locally negated in the same sentence."""
    boundaries = "。！？；;\n\r"
    left_boundary = max([text.rfind(mark, 0, start) for mark in boundaries] or [-1]) + 1
    right_candidates = [idx for mark in boundaries if (idx := text.find(mark, end)) != -1]
    right_boundary = min(right_candidates) if right_candidates else len(text)
    left = max(left_boundary, start - window)
    right = min(right_boundary, end + window)
    local = text[left:right]
    return bool(re.search(r"禁止|严禁|不得|不能|不许|不要|避免|不可|无|没有|不再|不在|不出现|已退出", local))


def _prompt_guard_report(prompt: str, script: str, planner_segment: str = "", director_segment: str = "") -> str:
    issues: list[str] = []
    scene_terms = [
        "大堂",
        "电梯厅",
        "电梯",
        "入口",
        "前台",
        "走廊",
        "办公室",
        "公寓",
        "卧室",
        "玄关",
        "集团门口",
        "通道",
        "空间",
        "场景",
    ]
    shot_terms = "半身中景|中景|近景|特写|中近景|远景|全景|局部特写"
    for term in scene_terms:
        pattern = rf"{re.escape(term)}(?:[\u4e00-\u9fff]{{0,8}})?(?:{shot_terms})"
        if re.search(pattern, prompt):
            issues.append(f'非人物主体误带景别：发现类似"{term}+景别"的写法。')
            break

    quote_pattern = r"[\"\u201c\u201d]([^\"\u201c\u201d]{2,120})[\"\u201c\u201d]"
    dialogue_markers = (
        "说|道|喊|问|答|念|心声|画外|旁白|低声|开口|台词|对白|声音|确认|回应|"
        "说出|喊出|嘀咕|耳语|补充|打出"
    )
    for match in re.finditer(quote_pattern, prompt):
        text = match.group(1)
        normalized = text.strip()
        if not normalized:
            continue
        if normalized in script:
            continue
        context_start = max(0, match.start() - 18)
        context_end = min(len(prompt), match.end() + 18)
        context = prompt[context_start:context_end]
        if not re.search(dialogue_markers, context):
            continue
        if normalized.startswith("@") or normalized.lower() in {"pass", "warn", "fail"}:
            continue
        if re.search(r"[\u4e00-\u9fffA-Za-z]", normalized):
            issues.append(f"疑似新增剧本外引号内容：{normalized}")
            break

    fabrication_patterns = [
        (r"员工[们]?(?:低声|小声|窃窃私语|议论|确认|低语|嘀咕)", "员工低语/议论"),
        (r"(?:有人|旁人|路人|围观者)(?:低声|小声|窃窃私语|议论|确认)", "旁人低语/议论"),
        (r"(?:众人|大家|所有人)(?:整齐|齐声|同声|异口同声)(?:回应|回答|应答)", "群体整齐回应"),
    ]
    for pattern, label in fabrication_patterns:
        for match in re.finditer(pattern, prompt):
            if _has_negation_near(prompt, match.start(), match.end()):
                continue
            if re.search(pattern, script or "") or re.search(pattern, (planner_segment or "") + (director_segment or "")):
                continue
            issues.append(f'疑似编造剧本外行为：发现[{label}]但原剧本与上游资产中均无此情节。')
            break
        if issues and "疑似编造剧本外行为" in issues[-1]:
            break

    return "\n".join(f"- {issue}" for issue in issues)


def _prompt_section(prompt: str, title: str) -> str:
    match = re.search(rf"【{re.escape(title)}】([\s\S]*?)(?=\n【|$)", prompt or "")
    return match.group(1).strip() if match else ""


def _prompt_execution_text(prompt: str) -> str:
    sections = [
        _prompt_section(prompt, "镜头序列"),
        _prompt_section(prompt, "时间轴"),
    ]
    text = "\n".join(section for section in sections if section)
    return text or (prompt or "")


def _meaningful_sentence_count(text: str) -> int:
    pieces = re.split(r"[。！？\n]+", text or "")
    return len([piece for piece in pieces if piece.strip()])


def _quoted_dialogues(text: str) -> list[str]:
    return [item.strip() for item in re.findall(r"[\"\u201c\u201d]([^\"\u201c\u201d]+)[\"\u201c\u201d]", text or "") if item.strip()]


def _has_internal_dialogue_visual_coverage(body: str) -> bool:
    quote_matches = list(re.finditer(r"[\"\u201c\u201d]([^\"\u201c\u201d]+)[\"\u201c\u201d]", body or ""))
    dialogues = [match.group(1).strip() for match in quote_matches if match.group(1).strip()]
    if not _dialogue_payload_is_long(dialogues):
        return True

    first_quote_end = quote_matches[0].end() if quote_matches else 0
    after_first_line_starts = (body or "")[first_quote_end:]
    if _INTERNAL_DIALOGUE_CUT_RE.search(after_first_line_starts) and _LISTENER_COVERAGE_RE.search(after_first_line_starts):
        return True

    before_first_line = (body or "")[: quote_matches[0].start()] if quote_matches else body or ""
    if re.search(r"(听者|对手|对方|受击|反应|过肩|反打)", before_first_line) and re.search(r"(画外音|OS|L-cut|J-cut)", before_first_line):
        return True

    return False

_SOURCE_DIALOGUE_LINE_RE = re.compile(
    r"(?m)^\s*[\u4e00-\u9fffA-Za-z0-9_\u00b7\uff08\uff09()]+"
    r"(?:\s*(?:OS|O\.S\.|VO|V\.O\.))?\s*[:\uff1a].+"
)
_SOURCE_SOUND_LINE_RE = re.compile(
    r"(?m)^\s*\u3010\s*(?:\u97f3\u6548|\u65c1\u767d|\u753b\u5916\u97f3|OS|O\.S\.|VO|V\.O\.)\s*[:\uff1a].+?\u3011"
)
_SOURCE_ACTION_BEAT_RE = re.compile(
    r"(?m)^\s*\u25b2.+(?:\u53cd\u5e94|\u56de\u5e94|\u505c\u987f|\u6c89\u9ed8|\u8fdf\u7591|\u6123\u4f4f|\u50f5\u4f4f|\u773c\u795e|\u770b\u7740|\u770b\u5411|\u773c\u7736|\u6469\u6332).+"
)

def _normalise_compiled_prompt(prompt: str, segment_index: int | None = None, script: str = "") -> str:
    """Clean common streaming pollution while preserving the actual compiled prompt."""
    text = (prompt or "").strip()
    if not text:
        return ""

    # Keep the first matching segment heading when old stream chunks leaked earlier text.
    if segment_index:
        pattern = rf"(?=片段\s*{segment_index}\s*[｜|])"
        parts = re.split(pattern, text, maxsplit=1)
        if len(parts) == 2:
            text = parts[1].strip()

    # Remove repeated blank lines caused by stream concatenation.
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _cleanup_timeline_constraints(text)
    text = text.replace("'", "'").replace("'", "'")
    text = _normalise_prompt_character_aliases(text, script)
    text = re.sub(r"(?<!乔)熙先", "乔熙先", text)
    return text


def _compress_director_for_compiler(fragment_text: str) -> str:
    """Keep current-fragment shot assets compact before prompt compilation."""
    if not fragment_text:
        return fragment_text

    def compress_geometry(match: re.Match[str]) -> str:
        block = match.group(0)
        fields = {field: _yaml_line_field(block, field) for field in _SPATIAL_GEOMETRY_FIELDS}
        if not all(fields.values()):
            return block
        indent_match = re.search(r"(?m)^(\s*)camera_basis\s*:", block)
        indent = indent_match.group(1) if indent_match else "      "
        geom_line = (
            f"{indent}geom: 机位:{fields['camera_basis']} {fields['camera_scene_position']} "
            f"→{fields['camera_looks_toward']} | 主体:{fields['subject_position']} "
            f"朝{fields['subject_facing']} | 锚点:{fields['visible_landmarks']}"
        )
        compact = block
        for field in _SPATIAL_GEOMETRY_FIELDS:
            compact = re.sub(rf"(?m)^\s*{field}\s*:\s*.*(?:\n|$)", "", compact)
        return compact.rstrip() + "\n" + geom_line + "\n"

    text = _MAIN_SHOT_BLOCK_RE.sub(compress_geometry, fragment_text)
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        if not line.strip() and result and not result[-1].strip():
            continue
        result.append(line)
    return "\n".join(result)


def _timeline_blocks(prompt: str) -> list[tuple[float, float, str]]:
    matches = list(re.finditer(r"(?m)^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒：", prompt or ""))
    blocks: list[tuple[float, float, str]] = []
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        blocks.append((float(match.group(1)), float(match.group(2)), prompt[body_start:body_end].strip()))
    if blocks:
        return blocks

    shot_matches = list(re.finditer(r"(?m)^镜头\s*\d+\s*【\s*(\d+(?:\.\d+)?)\s*秒\s*】", prompt or ""))
    current = 0.0
    for index, match in enumerate(shot_matches):
        duration = float(match.group(1))
        body_start = match.end()
        body_end = shot_matches[index + 1].start() if index + 1 < len(shot_matches) else len(prompt)
        blocks.append((current, current + duration, prompt[body_start:body_end].strip()))
        current += duration
    return blocks


def _compiler_guard_report(prompt: str, script: str, planner_segment: str, director_segment: str) -> str:
    issues: list[str] = []
    execution_text = _prompt_execution_text(prompt)
    base_report = _prompt_guard_report(prompt, script, planner_segment, director_segment)
    if base_report:
        issues.extend(line for line in base_report.splitlines() if line.strip())

    if _INTERNAL_FIELD_LEAK_RE.search(prompt or ""):
        issues.append("- Prompt 泄漏了上游内部字段名：必须把 fragment_task、must_carry、cut_point 等翻译成自然中文镜头语言。")

    uses_construction_sheet = bool(re.search(r"(?m)^\s*(?:duration|must_carry|cut_point|continuity)\s*:", director_segment or ""))
    director_geometry_issues = [] if uses_construction_sheet else _validate_spatial_geometry_contract(director_segment or "")
    if any("缺少空间几何字段" in issue for issue in director_geometry_issues):
        issues.append(
            "- 镜头资产缺少空间几何合同：shots 必须包含 camera_basis、camera_scene_position、"
            "camera_looks_toward、subject_position、subject_facing、visible_landmarks，compiler 不应凭空补前后景。"
        )
    for issue in director_geometry_issues:
        if "缺少空间几何字段" not in issue:
            issues.append(f"- 镜头资产空间几何合同错误：{issue}")

    if not re.search(r"(商北琛|乔熙|严飞|苏小可|众主管|众员工|他|她|两人|众人).{0,20}(半身中景|中景|近景|特写|中近景|全景|远景|胸部以上)", prompt):
        issues.append("- Prompt 缺少明确的主体+景别表达。")

    ambiguous_camera_terms = [term for term in _AMBIGUOUS_PROMPT_CAMERA_TERMS if term in prompt]
    if ambiguous_camera_terms:
        issues.append(
            "- 机位/运镜存在模糊描述："
            + "、".join(ambiguous_camera_terms[:6])
            + "。请改成摄影机位于人物正前方/左前方/右前方/背后+角度+镜头高度+固定/轨道/稳定器跟拍。"
        )

    abstract_terms = [term for term in _ABSTRACT_PROMPT_TERMS if term in prompt]
    if abstract_terms:
        issues.append(
            "- Prompt 包含不可生成的抽象情绪判断："
            + "、".join(abstract_terms[:6])
            + "。请改写为停顿时长、视线方向、身体距离、站位变化、让路动作、电梯门状态等可见画面。"
        )
    director_jargon_terms = sorted(set(match.group(0) for match in _DIRECTOR_JARGON_RE.finditer(execution_text)))
    if director_jargon_terms:
        issues.append(
            "- Prompt 残留导演调度口语："
            + "、".join(director_jargon_terms[:5])
            + "。请翻译成 Seedance 可见语言：明确镜头从谁到谁、景别、运动方向，以及低头/屏息/肩膀收紧/眼神回避等可见反应。"
        )
    complex_camera_terms = sorted(set(match.group(0) for match in _COMPLEX_CAMERA_PHRASE_RE.finditer(execution_text)))
    if complex_camera_terms:
        issues.append(
            "- Prompt 残留复杂摄影字段："
            + "、".join(complex_camera_terms[:5])
            + "。请降级为 Seedance 稳定短句：一个主体焦点、一个景别、一个机位、最多一种运动；反应落点改为同侧切镜。"
        )

    space_section = _prompt_section(prompt, "空间与首帧总控")
    if space_section:
        spatial_terms = _SPATIAL_OVEREXPLAIN_TERMS_RE.findall(space_section)
        if len(space_section) > 220 or _meaningful_sentence_count(space_section) > 3 or len(spatial_terms) > 7:
            issues.append(
                "- 空间与首帧总控过载：只保留2-3句不可变硬锚点（场景类型、1-3个空间关键节点、人物首帧站位与光线），"
                "不要反复解释前景/中景/后景/左右/远端/近侧/尽头；把镜头调度、动作和表情放回时间轴。"
            )
        if _SPACE_SECTION_ACTION_RE.search(space_section):
            issues.append("- 空间与首帧总控混入动作：该段只写首帧静态关系，走、让、散开、进入、门合拢等动作必须放在时间轴。")

    if _ELEVATOR_OFFICE_DRIFT_RE.search(prompt):
        issues.append(
            "- 电梯空间漂移：电梯门打开/门内/轿厢后方不得写成办公区、会议室、走廊、窗户或另一片空间；"
            "入电梯只能锁为封闭金属轿厢。"
        )
    if _ELEVATOR_ENTRY_RE.search(prompt):
        if not _ELEVATOR_CABIN_LOCK_RE.search(prompt):
            issues.append("- 入电梯片段缺少轿厢物理锁：必须明确封闭金属轿厢、侧壁/后壁/控制面板等少量可见硬锚点。")
        if not _ELEVATOR_NEGATIVE_SPACE_LOCK_RE.search(prompt):
            issues.append("- 入电梯片段缺少负向空间锁：约束中必须禁止电梯门后生成办公区、会议区、走廊、窗户或另一片大堂。")
    if _PSEUDO_PRECISE_CAMERA_RE.search(prompt):
        issues.append(
            '- 伪精确空间机位：禁止写"电梯门外背后/电梯口180度/大堂中轴背后"等场景相对背后机位；'
            '背后、侧后方、180度必须绑定人物，例如"商北琛背后中景"或"商北琛侧后方中景"。'
        )
    if re.search(r"(员工|众员工|人群|群演)", prompt) and re.search(r"(商北琛|严飞|乔熙|苏小可)", prompt):
        if not _EMPLOYEE_FACE_LOCK_RE.search(prompt):
            issues.append("- 群演身份锁缺失：众员工/群演不得与命名人物相似、重复或同脸，应写成匿名差异化面孔/侧脸/背影/轻虚。")

    if not re.search(
        r"(?:摄影机|机位|镜头).{0,32}(?:正面|正前方|左前方|右前方|左侧|右侧|侧面|背后|左后方|右后方|场景固定|固定机位)",
        prompt,
    ):
        issues.append('- Prompt 缺少可执行摄影机位置：至少一个时间段应明确"正面/左前方/右前方/侧面/背后/场景固定机位"等简洁机位。')

    unsafe_action_terms = [term for term in _UNSAFE_ACTION_TERMS if term in prompt]
    if unsafe_action_terms:
        issues.append(
            "- 动作路径存在失控词："
            + "、".join(unsafe_action_terms[:6])
            + '。请改成"起点 -> 路径 -> 接触/避让对象 -> 终点 -> 结束状态"，例如手指松开西装前襟后向自己胸前收回，再落回身体两侧。'
        )

    has_reaction_beat = any(term in prompt for term in _REACTION_BEAT_TERMS)
    has_explicit_reaction_cut = re.search(r"(?:镜头)?(?:切至|切到|切回)|反打至|反打镜头", prompt)
    if has_reaction_beat and not has_explicit_reaction_cut:
        issues.append('- 受击/反应落点缺少明确切镜：请写清"镜头切至谁、什么景别、什么机位、画面里保留谁/什么空间锚点"。')

    all_dialogues = _quoted_dialogues(prompt)
    if _dialogue_payload_is_long(all_dialogues) and not _DIALOGUE_VISUAL_CUT_RE.search(prompt):
        issues.append(
                "- 长台词/高压对白被单镜头吃完：完整发言单元要保持语义连续，但必须加入同侧听者反应、过肩、画外音或景别变化。"
        )

    contact_action_terms = ("抓住", "扶住", "松开", "撞上", "冲向", "冲入", "转身", "退开", "移到", "进入电梯")
    has_contact_action = any(term in prompt for term in contact_action_terms)
    has_path_language = re.search(r"(?:从|由).{0,18}(?:向|到|沿|穿过|离开).{0,40}(?:停|落回|收回|站定|垂回|保持|不再)", prompt)
    if has_contact_action and not has_path_language:
        issues.append("- 关键动作缺少起点/路径/终点/结束状态，请把冲入、撞上、扶住、松开、转身、退开等动作写成可执行动作链。")

    timeline_blocks = _timeline_blocks(prompt)
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        block_dialogues = _quoted_dialogues(body)
        if _dialogue_payload_is_long(block_dialogues) and not _has_internal_dialogue_visual_coverage(body):
            issues.append(
                f"- 时间轴第 {index} 个时间段让长台词/高压对白停留在单一画面：人物说话时严禁一个镜头、一个景别或一个机位说完整句；"
                '请在对白内部加入“说话者起句，切至同侧听者反应或过肩；镜头停留在听者脸部或过肩画面，说话者后半句在画外继续；若后续还有新动作或新信息点，必须另起新镜头承接”的覆盖变化。'
            )
            break

    if director_segment and re.search(r"dialogue_coverage\s*:", director_segment):
        dialogue_coverage = re.findall(r"dialogue_coverage\s*:\s*(.+)", director_segment)
        coverage_text = "\n".join(dialogue_coverage)
        if len(coverage_text) >= 42 and not _DIALOGUE_COVERAGE_TERMS_RE.search(director_segment):
            issues.append(
                "- 上游镜头资产的 dialogue_coverage 缺少对白覆盖设计：长句/高压句必须在 shot_director layout/blocking/guard 阶段标出"
                "同侧听者反应、过肩、画外音/L-cut 或景别变化；prompt_compiler 只能翻译，不应临场发明切镜。"
            )

    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        if not _PERFORMANCE_BEAT_RE.search(body):
            issues.append(
                f"- 时间轴第 {index} 个时间段缺少人物动作/表情落点：不要只写空间和机位，"
                "至少写清一个可见动作、视线或表情反应。"
            )
            break

    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        spatial_count = len(_SPATIAL_OVEREXPLAIN_TERMS_RE.findall(body))
        performance_count = len(_PERFORMANCE_BEAT_RE.findall(body))
        if spatial_count > 6 and performance_count < 4:
            issues.append(
                f"- 时间轴第 {index} 个时间段空间描写过载：每段只保留当前镜头必要的0-1个空间锚点，"
                "不要解释前景/中景/后景/左右边缘；把文字预算让给动作、视线和表情。"
            )
            break

    for index, (_start, _end, body) in enumerate(timeline_blocks[1:], start=2):
        prefix = body[:120]
        if not _TIMELINE_BRIDGE_RE.search(prefix):
            issues.append(f'- 时间轴第 {index} 个时间段缺少段内交接词：请以"同一机位继续/延续上一镜/镜头切至/切回"承接上一时间段，单段内禁止反打。')
            break

    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        if not _TIMELINE_END_STATE_RE.search(body[-120:]):
            issues.append(f"- 时间轴第 {index} 个时间段缺少结束状态：请写清谁停在什么位置、朝向、画内/画外、门/道具/距离状态。")
            break

    for _start, _end, body in timeline_blocks:
        if _TIMELINE_BRIDGE_RE.search(body) and not _SPATIAL_ANCHOR_RE.search(body):
            issues.append("- 时间轴切镜缺少空间锚点：每次切镜至少保留电梯门框/中轴/员工列/前后景人物/轿厢等同一空间信号。")
            break

    for _start, _end, body in timeline_blocks:
        if (
            re.search(r"摄影机位于商北琛正前方0度", body)
            and re.search(r"转入电梯|进入电梯", body)
            and not re.search(r"电梯门外|大堂中轴|场景固定机位|摄影机固定在电梯", body)
        ):
            issues.append("- 人物相对机位与入电梯动作冲突：商北琛转身/进入电梯时必须切至电梯门外大堂中轴的场景固定机位。")
            break

    for _start, _end, body in timeline_blocks:
        if (
            re.search(r"商北琛[^。\n]{0,40}(?:面朝|朝向)[^。\n]{0,12}电梯", body)
            and re.search(r"(?:商北琛)?(?:正面|正前方0度)", body)
            and re.search(r"后景[^。\n]{0,20}电梯(?:门框|门|口)", body)
        ):
            issues.append("- 空间前后景矛盾：商北琛面朝电梯且镜头拍其正面时，电梯门框不能在后景；请改成电梯门框在前景/侧边，或改用背面/侧背机位。")
            break

    for _start, _end, body in timeline_blocks:
        if (
            re.search(r"(?:面朝|朝向)[^。\n]{0,16}(?:电梯|门口|房门|车门|门框)", body)
            and re.search(r"(?:正面|正前方0度)", body)
            and re.search(r"后景[^。\n]{0,24}(?:电梯|门口|房门|车门|门框)", body)
        ):
            issues.append("- 通用门框前后景矛盾：人物面朝门/电梯/车门且镜头拍正面时，该门框不能同时位于人物后景。请改成前景/侧边，或改用背面/侧背/场景固定机位。")
            break


    # --- 新增空间几何矛盾检测（v2） ---

    # 检测1: 摄影机后退方向物理可行性——面朝电梯/门口 + 正前方机位 + 同速后退 → 摄影机会退进电梯/墙壁
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        if _CAMERA_RETREAT_INTO_DOOR_RE.search(body):
            issues.append(
                f"- 时间轴第 {index} 个时间段摄影机后退路径不可行：人物面朝电梯/门口、摄影机在正前方0度同速后退，"
                "摄影机会退进电梯或退出场景边界。请改用场景固定机位（scene_fixed）从侧面或背后拍摄，"
                "或让摄影机从大堂中轴侧面跟拍。"
            )
            break

    # 检测2: 近侧/远端与机位方向的逻辑矛盾
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        if _PROXIMITY_CONTRADICTION_RE.search(body):
            issues.append(
                f"- 时间轴第 {index} 个时间段空间方位矛盾：'近侧侧边'与人物面朝方向和电梯/门框的实际几何位置不一致。"
                "请根据摄影机位置重新判断锚点应该在前景/侧边/后景的哪一侧。"
            )
            break

    # 检测3: 单个时间段空间方位词过载
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        spatial_direction_count = len(_SPATIAL_DIRECTION_TERMS_RE.findall(body))
        if spatial_direction_count > 4:
            issues.append(
                f"- 时间轴第 {index} 个时间段空间方位词过载（{spatial_direction_count}个）：单个时间段最多保留"
                "当前镜头必要的0-1个空间锚点短语；不要堆叠前景/中景/后景/远端/近侧/边缘/侧边/左右。"
                "把文字预算让给人物动作和表情。"
            )
            break

    # 检测4: 相邻时间段之间视角剧烈翻转——从正面突变为纯背面或反之
    _frontal_cam_re = re.compile(r"正前方0度|正面")
    _rear_cam_re = re.compile(r"背后|背对摄影机|180度|背面")
    prev_frontal = False
    prev_rear = False
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        is_frontal = bool(_frontal_cam_re.search(body))
        is_rear = bool(_rear_cam_re.search(body))
        if index > 1:
            if prev_frontal and is_rear and not re.search(r"转身|回身|转过身", body):
                issues.append(
                    f"- 时间轴第 {index - 1} → {index} 段视角剧烈翻转：从正面突变为背面/背对，"
                    "但文本未铺垫转身动作。视频模型无法在连续流中实现180度视角翻转，"
                    "需要通过人物转身动作或中间过渡机位（侧面）来衔接。"
                )
                break
            if prev_rear and is_frontal and not re.search(r"转身|回身|转过身", body):
                issues.append(
                    f"- 时间轴第 {index - 1} → {index} 段视角剧烈翻转：从背面突变为正面，"
                    "但文本未铺垫转身动作。需要通过人物转身或中间过渡机位来衔接。"
                )
                break
        prev_frontal = is_frontal
        prev_rear = is_rear

    title_duration_match = re.search(r"~\s*(\d+(?:\.\d+)?)\s*秒", prompt)
    prompt_duration = float(title_duration_match.group(1)) if title_duration_match else 0.0
    explicit_cut_count = len(_EXPLICIT_CUT_RE.findall(prompt))

    # === [PROMPT-CUT-BUDGET-001] 切镜预算（按 segment 时长档位）===
    # 比旧的 "≤13.5s 允许 5 cuts" 严格得多。Seedance 单镜头模型实际只能稳渲 1-2 个有效切。
    if prompt_duration:
        if prompt_duration <= 3.0:
            cut_budget = 0
        elif prompt_duration <= 8.0:
            cut_budget = 1
        elif prompt_duration <= 13.0:
            cut_budget = 2
        else:
            cut_budget = 3
        if explicit_cut_count > cut_budget:
            issues.append(
                f"- [PROMPT-CUT-BUDGET-001] 切镜超预算：{prompt_duration:.0f}秒片段最多允许 {cut_budget} 个显式切镜，"
                f"当前 {explicit_cut_count} 个。Seedance 是单镜头连续生成模型，超预算会导致空间瞬移/乱切。"
                "请把超出的镜头并入前后段，或要求 story_planner 重新拆段。"
            )

    # === [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单段反打硬失败 ===
    if _REVERSE_SHOT_INSIDE_SEGMENT_RE.search(prompt):
        issues.append(
            '- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单段 prompt 内出现"反打"：Seedance 无法在一次生成里完成跨轴反打，'
            "会让人物左右颠倒、背景翻面。需要反打的两镜必须拆成相邻两个 segment，并通过转身/越轴中性镜头/场景固定机位过渡。"
        )

    # === [PROMPT-FIRST-FRAME-PIXEL-LOCK-001] 首帧像素锚点缺失 ===
    space_anchor_section = _prompt_section(prompt, "空间与首帧总控")
    if space_anchor_section:
        pixel_hits = len(set(_PIXEL_ANCHOR_TERMS_RE.findall(space_anchor_section)))
        if pixel_hits < 2:
            issues.append(
                "- [PROMPT-FIRST-FRAME-PIXEL-LOCK-001] 空间与首帧总控缺少像素锚点："
                f"当前命中 {pixel_hits} 个像素锚词，至少需要 2 个。"
                '请加入"画面中央 / 占画面高度 X / 对齐画面纵向 X 处 / 三分线"等像素描述，'
                "否则模型每次生成首帧位置都不稳定，段间必跳。"
            )

    # === [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 单时间段轴线锁 ===
    # 同一 timeline 段 body 内同时出现 "左前方" + "右前方" 即为跨轴
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        if _AXIS_LEFT_RE.search(body) and _AXIS_RIGHT_RE.search(body):
            issues.append(
                f"- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 时间轴第 {index} 个时间段跨 180° 轴线："
                '同段同时出现"左前方"和"右前方"机位。Seedance 单次生成无法跨轴反打，'
                "会让人物左右颠倒、背景翻面。请把这两个机位拆到不同 segment，并通过转身或场景固定机位过渡。"
            )
            break

    # === [PROMPT-CUT-BUDGET-001] 隐性切镜识别 ===
    # "同一机位继续 / 镜头保持" 后 60 字内若引入 "新主体名 + 新景别"，视为隐性切镜
    silent_cut_blocks: list[int] = []
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        for trig_match in _SILENT_CUT_TRIGGER_RE.finditer(body):
            window = body[trig_match.end(): trig_match.end() + 60]
            if _NEW_SUBJECT_FRAMING_RE.search(window):
                silent_cut_blocks.append(index)
                break
    if silent_cut_blocks:
        seg_list = "、".join(str(i) for i in silent_cut_blocks[:3])
        issues.append(
            f'- [PROMPT-NO-SAME-CAMERA-ABUSE-001] [PROMPT-CUT-BUDGET-001] 隐性切镜：时间段 {seg_list} 写了"同一机位继续"但紧接着引入新主体+新景别，'
            "实际等于一次硬切，模型会按切镜处理。请要么把后续描述改成同主体的延续动作/表情，"
            '要么显式拆成新时间段并写明"镜头切至 ..."。'
        )

    for match in re.finditer(r"(?m)^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒：(.+)$", prompt):
        start = float(match.group(1))
        end = float(match.group(2))
        body = match.group(3)
        body_cut_count = len(re.findall(r"(?:镜头)?切(?:至|到|回)|反打至|反打镜头", body))
        quoted_dialogue_len = sum(len(item) for item in _quoted_dialogues(body))
        if end - start <= 2.5 and body_cut_count >= 2 and quoted_dialogue_len >= 20:
            issues.append("- 单个短时间段同时包含多次切镜和长台词，时间预算不足；请把长台词给足约3秒，或把插入镜头并入前后镜头。")
            break

    if director_segment and not re.search(r"shots\s*:", director_segment):
        issues.append("- 当前片段镜头资产缺少 shots 骨架。")

    reaction_text = ""
    if planner_segment and re.search(r"reaction_plan\s*:", planner_segment):
        reaction_line = re.search(r"reaction_plan\s*:\s*(.+)", planner_segment)
        reaction_text = reaction_line.group(1).strip() if reaction_line else ""
    if not reaction_text and director_segment and re.search(r"reaction_coverage\s*:", director_segment):
        reaction_line = re.search(r"reaction_coverage\s*:\s*(.+)", director_segment)
        reaction_text = reaction_line.group(1).strip() if reaction_line else ""

    if reaction_text and re.search(r"受击|反应|炸点", reaction_text) and not re.search(r"受击|反应|表情|眼神|嘴唇|呼吸|停顿|肩线|下颌", prompt):
        issues.append("- 上游要求当前片段承接受击/反应落点，但 prompt 未体现可见反应。")

    source_events_block = re.search(r"source_script_events\s*:([\s\S]*?)(?=\n[a-z_]+\s*:|\Z)", planner_segment)
    source_events = re.findall(r"-\s*(.+)", source_events_block.group(1) if source_events_block else "")
    if source_events:
        matched_events = 0
        for event in source_events[:6]:
            event = event.strip()
            if not event or len(event) < 2:
                continue
            tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", event)[:4]
            if any(token in prompt for token in tokens):
                matched_events += 1
        if matched_events == 0:
            issues.append("- Prompt 似乎没有覆盖当前片段的 source_script_events。")

    if "镜头切到" in prompt and not re.search(r"主导主体|主分镜|子分镜", planner_segment + director_segment):
        issues.append("- Prompt 出现硬切表达，但上游未提供可支撑的主分镜/子分镜骨架。")

    return "\n".join(issues)


def prompt_compiler_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    segment_index = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
    total_segments = int(state.get("total_segments") or 1)
    aspect_ratio = state.get("aspect_ratio", "16:9")
    current_fragment_id = _fragment_id_for_segment_index(state.get("segment_names") or [], segment_index)
    aspect_label = "9:16竖屏" if "9:16" in aspect_ratio else "16:9横屏"

    compiler_hint = (
        f"Seedance提示词编译 输出词典 模型适配 动作描述精细化 故事节奏 "
        f"情绪锚点 尾帧收束 切镜 受击者 炸点 对白 信息冲击 "
        f"动作接续 人物关系 场面总控 子分镜 道具接续 视线轴线 当前片段压缩上下文"
    )
    system_prompt, retrieval_meta = build_system_prompt(
        "你是一位 Seedance 视觉模型提示词编译大师。\n\n"
        "你的唯一职责：读取当前片段压缩上下文（场景空间记忆卡、当前拆片资产、当前镜头资产），"
        "针对指定片段编译出一份可直接放入 Seedance 模型的最终中文导演 Prompt。\n\n"
        "【输出格式硬约束——必须严格遵守】\n"
        "你的输出必须严格按以下结构，不得增删段落、不得使用 YAML、不得使用教学标签：\n\n"
        "```\n"
        "片段N｜场景名｜情绪/动作关键词(用+连接)｜~秒数秒\n\n"
        "【风格锚点】\n"
        "一句话风格定义。\n\n"
        "【画幅锚点】\n"
        "画幅比例+方向（如 9:16竖屏）。\n\n"
        "【空间与首帧总控】\n"
        "**最多 1-2 句，越短越好**。只允许写：场景名 + 1-2 个不可变硬锚点（如电梯方向、桌位、门口）+ 光线基底。\n"
        "禁止：堆砌前景/中景/后景/左右/远近的层级链条；推理门后空间；把场景图复述成建筑说明书；写动作动词（走进、迈入、冲来、转身等）。\n"
        "**镜头语言和人物动作才是这个 prompt 的主菜**——空间总控只是开场两句话，把舞台立住就够了，不要喧宾夺主。\n"
        "Seedance会顺序读取prompt，如果空间总控里写了动作或过量空间解释，时间轴会被稀释，模型容易重复执行或重建错误场景。\n\n"
        "【人物】\n"
        "- 人物名：年龄/身份/服装/当前情绪状态。只写本片段会出现的人物。\n\n"
        "【镜头序列】\n"
        "镜头1【X秒】【主体】景别，机位/视角，动作从起点到落点；对白直接嵌入动作句中（具体切镜触发→镜头2）。\n\n"
        "镜头2【X秒】【主体】景别，机位/视角，承接上一镜动作/道具/轴线；必要时用 OS/J-cut/L-cut 把台词压到听者反应上（具体切镜触发→镜头3）。\n\n"
        "每一行都必须来自上游 shot 的 duration、subject、shot、action、dialogue、must_carry、cut_point、continuity；不得泄漏这些字段名。\n\n"
        "【约束】\n"
        "主体锁定、空间锁定、道具连续性、禁止项。简洁列出。\n\n"
        "片段N prompt 已输出。\n"
        "请生成视频后，上传：\n\n"
        "片段N的尾帧截图\n"
        "当前人物位置关系（若有变化）\n\n"
        "我将基于实际尾帧继续输出片段N+1。\n"
        "```\n\n"
        "【语言风格硬约束】\n"
        "1. 用简洁的导演调度语言，不用文学化描写。\n"
        "2. 表情只写关键状态，不堆砌微表情。\n"
        "3. 运镜必须使用可执行机位术语，并绑定摄影机位置与运动方向；不要写模糊口语。\n"
        "4. 一句一个动作，句子简短有力，不在一句中塞多个并列描写。\n"
        "5. 台词直接嵌入动作描述中，不单独列出。\n\n"
        f"{_shot_composition_task_selection_rules()}\n"
        f"{_dialogue_coverage_contract_rules()}\n"
        f"{_camera_execution_rules()}\n"
        f"{_camera_task_selection_rules()}\n"
        # NOTE: _spatial_geometry_contract_rules() 不注入 compiler，已由【空间几何字段翻译规则】替代。
        f"{_reaction_cut_and_action_path_rules()}\n"
        f"{_timeline_continuity_contract_rules()}\n"
        f"{_director_jargon_translation_rules()}\n"
        "【片段连续性规则——替代旧的单主体僵化规则】\n"
        "1. 单个片段必须有清晰的主导主体与稳定空间轴线，但不等于全程只能看一个人。\n"
        "2. 如果上游资产明确给出 shots / sub_shots / reaction_plan，你可以在同一片段内自然承接炸点命中、受击落点、双人关系变化；但必须写出连续过渡，不能伪造剪辑软件式瞬切。\n"
        "3. 不得无动机跳轴、跳空间、跳主体。主体重心变化必须来自上游主分镜骨架，并在时间轴中写出动作或视线过渡。\n"
        "4. 若上游明确要求受击落点留在片段内，不能为了省事把受击者降成背景虚化。\n"
        "5. 若上游明确要求下一独立片段再承接受击，则当前片段也不得提前偷跑完整反应。\n\n"
        "【视频模型物理限制——必须服从但不能误解】\n"
        "1. 整个片段仍是连续视频流，所以每个时间段的画面必须从上一个时间段自然演变。\n"
        "2. 禁止180度视角翻转，展示背影必须靠人物自然转身。\n"
        "3. 景别变化必须通过动作、视线、调度或运镜自然过渡。\n"
        "4. 如果时间轴出现第二人物的反应，必须保证它来自当前空间关系与上游主分镜/子分镜骨架，而不是凭空切去另一个场景。\n"
        "5. 近景里不要描述超出当前画面可见范围的大量背景动作。\n"
        "6. 原则：把每个时间段想象成同一段导演编排在连续视频里自然展开。\n\n"
        "【Seedance 2.0 空间极简策略——最重要规则】\n"
        "1. **严禁空间过载**：时间轴的重点是\"动作、情绪、机位\"。绝不允许堆叠\"前景、中景、后景、远端、近侧、边缘、画面左、画面右\"等冗余方位词。\n"
        "2. 每个时间段最多保留 1 个必需的空间锚点（如\"电梯门旁\"），超过 1 个即为违规。\n"
        "3. 遇到上游提供的复杂 `geom:` 字段，**必须大幅裁剪**。只提取能说明机位和人物朝向的最少词汇，其余一律丢弃，绝不能逐字翻译。\n"
        "4. 【空间与首帧总控】最多 2 句，极简点明场景和光线，禁止写出详细的建筑结构或人物的精确坐标。\n"
        "5. 空间简写不等于剪辑省略；除第一个时间段外，每段开头必须保留\"同一机位继续/延续上一镜/镜头切至/切回\"等交接话术；单段内禁止写\"反打至/反打镜头\"。\n"
        "6. compiler 不重新设计教学视频里的拍摄技巧，只忠实保留上游镜头资产已有的动作匹配、视线引导、同侧过肩、听者反应、景别递进、出画入画等设计；若上游写了反打，必须改写成同侧听者反应或提示拆段。\n"
        "7. 每个时间段必须至少有一个人物动作或表情/视线落点；如果空间锚点和表演落点冲突，优先保留表演落点。\n"
        "8. 背后、侧后方、180度必须绑定人物，不绑定场景。正确写法是\"商北琛背后中景/商北琛侧后方中景\"；禁止写\"电梯门外背后180度\"\"电梯口背后\"\"大堂中轴背后\"。\n"
        "9. 表现人物与电梯关系时，从人物背后或侧后方看他走向/进入电梯，不要让文字暗示从电梯里面向外拍。\n"
        "10. 电梯场景硬锁：电梯门打开后只能是封闭金属轿厢、侧壁/后壁/控制面板；禁止生成办公室、会议区、走廊、窗户、另一片大堂或会客区。\n"
        "11. 群演硬锁：只有命名人物使用清晰身份参考；员工/路人必须是匿名差异化面孔、侧脸、背影或轻虚，不得与主角或助理同脸。\n\n"
        "【成功案例镜头链条】\n"
        "遇到职场权威入场、冷处理问候、平静下令、群体退让这类片段时，优先学习这种结构：\n"
        "1. 用一个局部动作或人物半身建立节奏，例如皮鞋落地、手部动作、人物稳定步速；不要先写大段空间说明。\n"
        "2. 问候/对峙用过肩或双人关系景，前景肩线只一句带过，重点写谁说话、谁不回应、视线如何移开。\n"
        "3. 命令句用半身景承载，必要时插入一次眼神/表情局部特写，再切回半身收完整句。\n"
        "4. 命令生效用群体关系景收束，写主管/员工如何停步、让路、四散、退回边线；不要补复杂南北东西或远近层级。\n"
        "5. 最终时间轴应读起来像\"镜头机位切换 + 人物动作表情 + 台词落点\"，而不是空间坐标说明书。\n\n"
        "【节奏与事件覆盖】\n"
        "1. 片段必须完整覆盖拆片方案中 source_script_events 的所有事件，不得遗漏。\n"
        "2. 建立段可以快过，炸点/受击段适当留时间，收束段干净利落。\n"
        "3. 剧情推进优先于表情堆砌。\n"
        "4. 末尾必须给出清晰尾帧状态，作为下一片段的衔接起点。\n\n"
        "【绝对禁止】\n"
        "1. 禁止使用 YAML 格式。\n"
        "2. 禁止使用教学标签（如'主分镜1：''子分镜2.1：'）。\n"
        "3. 禁止堆砌微表情。\n"
        "4. 禁止编造剧本中不存在的台词、对白、旁白、员工低语或新情节。\n"
        "5. 禁止把场景名当主体写景别。\n"
        "6. 禁止输出分析说明、思考过程或教学话术。\n"
        "7. 禁止无依据的空间跳转、人物瞬移或主体硬切。\n\n"
        "请优先服从 07 号输出词典、当前片段上游资产和 prompt_compiler 规则卡；不要模仿离线范例扩写剧情。",
        "prompt_compiler",
        context_hint=compiler_hint,
    )
    revision_instruction = state.get("revision_instruction", "")
    previous_prompt = outputs.get(f"compiled_segment_{segment_index}", "")
    revision_block = ""
    if revision_instruction and previous_prompt:
        revision_block = (
            "\n【质检返修要求】\n"
            f"{revision_instruction}\n\n"
            "【上一版Prompt】\n"
            f"{previous_prompt}\n\n"
            "请只输出修订后的当前片段 Prompt，不要解释修改过程。\n"
        )

    current_planner_segment = _segment_block(outputs.get("story_planner", ""), segment_index, current_fragment_id)
    current_director_segment_raw = _segment_block(outputs.get("shot_director", ""), segment_index, current_fragment_id)
    current_director_segment = _compress_director_for_compiler(current_director_segment_raw)
    scene_memory = _scene_memory_card(outputs.get("scene_analyst", ""), 1400)
    current_source_events = _current_segment_event_card(current_planner_segment, 1600)
    current_script_context = "\n\n".join(
        part for part in (current_source_events, current_planner_segment) if part
    )
    tail_frame_memory = _truncate_for_prompt(state.get("tail_frame_analysis", ""), 1800)
    if tail_frame_memory:
        tail_frame_memory = (
            f"{tail_frame_memory}\n\n"
            "【视频桥接决策执行规则】\n"
            "1. 如果视频分析里的 next_segment_start_mode.mode 是 image_start，空间与首帧总控必须继承 selected_candidate 对应的可见人物位置、朝向、道具和空间状态。\n"
            "2. 如果 next_segment_start_mode.mode 是 direct_cut，禁止强行沿用上一段尾帧；应按当前片段规划资产重新开镜、闪回、换场或做空间复位。\n"
            "3. 如果 bridge_frame.usable_as_start_image=false，不能把该帧当作下一段首帧，只能继承明确可见的道具/空间状态。\n"
            "4. 如果 continuity_constraints.must_reset_space=true，当前片段开头必须用关系景、中景或明确空间状态重建，不要从局部特写硬接。\n"
            "5. 本桥接决策高于下面旧的尾帧继承规则；direct_cut 时，“必须以视频最终位置为准”只适用于明确可继承的道具/空间状态，不适用于人物首帧站位。"
        )
    reference_context = _reference_context(state)
    reference_usage_instruction = (
        "第一段也必须调用人物参考图与场景参考图：人物图只锁定身份/五官/服装，场景图只锁定空间/光线/轴线。\n\n"
        if reference_context.strip()
        else "本次未提供参考图；最终 Prompt 中严禁编造 @图片1、@图片2、@图片3 或任何参考图占位。\n\n"
    )
    # --- v1 schema validation ---
    v1_issues: list[str] = []
    if current_director_segment_raw:
        for field in ("fragment_task", "rhythm", "shots"):
            if not re.search(rf"(?m)^\s*{re.escape(field)}\s*:", current_director_segment_raw):
                v1_issues.append(f"shot_director 缺少 fragment 字段 {field}。")
        for v2_field in ("schema_version", "fragment_intent", "reaction_coverage", "continuity_anchor"):
            if re.search(rf"(?m)^\s*{re.escape(v2_field)}\s*:", current_director_segment_raw):
                v1_issues.append(f"shot_director 残留 v2 字段 {v2_field}，必须用 v1 字段。")
        shot_blocks = _MAIN_SHOT_BLOCK_RE.findall(current_director_segment_raw)
        if not shot_blocks:
            v1_issues.append("shot_director 当前片段没有任何合法 shot_id，无法编译。")
        for shot_id_raw, shot_body in shot_blocks:
            shot_id = shot_id_raw.strip()
            for field in ("duration", "task", "subject", "action", "dialogue", "must_carry", "cut_point", "continuity"):
                if not re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:", shot_body):
                    v1_issues.append(f"{shot_id} 缺少必要字段 {field}。")
            has_merged_shot = re.search(r"(?m)^\s*-?\s*shot\s*:", shot_body)
            has_legacy_camera_size = re.search(r"(?m)^\s*-?\s*camera\s*:", shot_body) and re.search(
                r"(?m)^\s*-?\s*size\s*:", shot_body
            )
            if not (has_merged_shot or has_legacy_camera_size):
                v1_issues.append(f"{shot_id} 缺少必要字段 shot（或旧版 camera+size）。")
    else:
        v1_issues.append("当前片段缺少镜头资产，无法编译。")

    if v1_issues:
        raise RuntimeError(
            "[PROMPT-COMPILER-V1-GATE] prompt_compiler 发现 shot_director 输出不符合 v1 schema。\n"
            + "\n".join(f"  - {issue}" for issue in v1_issues)
            + "\n请确保 shot_director 输出 v1 合同镜头资产（fragment_task/rhythm/duration/task/subject/shot/action/dialogue/must_carry/cut_point/continuity）。"
        )

    user_prompt = (
        f"=== 当前片段压缩上下文 ===\n\n"
        f"{_runtime_context_contract_card()}\n\n"
        f"【场景空间记忆卡】\n{scene_memory}\n\n"
        f"【当前片段原文事件】\n{current_source_events}\n\n"
        f"【当前片段规划资产】\n{current_planner_segment}\n\n"
        f"【当前片段镜头资产】\n{current_director_segment}\n\n"
        f"【上一段人物最终姿势/视频分析（最高优先级空间参考）】\n{tail_frame_memory}\n\n"
        f"⚠️ 【空间与首帧总控的核心规则】\n"
        f"如果上方存在【上一段人物最终姿势/视频分析】内容，则该分析描述的是上一段视频的**实际生成结果**。\n"
        f"你在编写【空间与首帧总控】时，**必须以该视频分析中描述的人物最终位置、朝向、姿态和空间布局为准**，\n"
        f"而非照搬任何全局镜头预案。预先规划是理想状态，实际视频可能有偏差。\n"
        f"具体要求：\n"
        f"1. 首帧中人物的站位、朝向必须与视频分析中描述的【最终状态】完全一致。\n"
        f"2. 空间锚点（门、走廊、电梯等）的相对位置必须与视频分析中描述的【空间轴线】一致。\n"
        f"3. 如果视频分析提到了续接约束，必须严格执行。\n"
        f"4. 不要在空间总控中扩写复杂场景说明；只保留1-3个关键节点和首帧人物关系，其他信息交给时间轴中的机位与动作承接。\n"
        f"5. 如果场景关系不确定，禁止补写门后、走廊尽头、办公室延伸等推理空间。\n\n"
        f"【参考图清单】\n{reference_context or '无'}\n\n"
        f"{revision_block}\n"
        f"【当前任务】\n"
        f"请专门为【片段 {segment_index}】编译最终 Seedance Prompt。\n\n"
        "你必须严格服从【当前片段规划资产】与【当前片段镜头资产】：\n"
        "1. 当前片段的 shots 决定戏剧骨架，不得随意删掉其中的动作单元。\n"
        "2. 当前片段的 sub_shots / reaction_plan 决定炸点、受击、表情重音落在哪里；不得把这些落点随意抹平成背景附带。\n"
        "3. 若上游要求受击在片段内承接，时间轴必须真正写出该受击/反应的可见落点。\n"
        "4. 若上游要求完整发言单元保持连续，意思是语义和声音连续，不是单镜头吃完整段台词；必须保留上游给出的听者反应、同侧过肩、画外音或景别变化；若上游写了反打，单段内改写为同侧听者反应，真反打必须拆段。\n"
        "5. source_script_events 必须全部覆盖，不得遗漏。\n\n"
        "【镜头覆盖字段翻译规则】\n"
        "如果镜头资产包含新施工单字段 duration / task / must_carry / cut_point / continuity，必须按下面方式编译成【镜头序列】：\n"
        "1. duration 只进入镜头编号后的秒数，例如 镜头1【4秒】；不要在最终 prompt 里写 duration 字段名。\n"
        "2. task 决定镜头功能，但最终只写成自然镜头动作，不要输出 task 字段名。\n"
        "3. subject + shot 必须合成镜头行开头，例如【乔熙】过肩视角半身以上中景。若上游仍是旧版 size + camera，则先合并成同样的【视角+景别】短语。\n"
        "4. action + dialogue 是镜头行主体；台词直接嵌入动作句中，OS/J-cut/L-cut 写成画外音或声音桥。\n"
        "5. must_carry 必须转译成画面里看得见的信息或反应，不能只放到约束里。\n"
        "6. cut_point 必须放进括号，写成（动作顶点前切至镜头2）、（台词断点时切至乔熙反应镜头）、（文件内容看清后切至镜头3）这类自然中文触发句；禁止使用箭头式表达。\n"
        "7. continuity 必须落实到镜头行或【约束】里，保证人物左右关系、道具状态、动作路径和尾帧不跳变。\n"
        "8. 最终 prompt 禁止出现 fragment_task、must_carry、cut_point、continuity、shot_id、fragment_id 等内部字段名。\n\n"
        "【Seedance 2.0 场景简写与表演优先规则】\n"
        "1. 最终 Prompt 不要把场景空间写成说明书；空间只服务连续性，不承担戏剧表达。\n"
        "2. 【空间与首帧总控】最多2-3句，只写不可变硬锚点：场景类型、入口/门/电梯/桌边等关键节点、人物首帧站位、光线。\n"
        "3. 每个时间段优先写：机位在哪里、谁做什么、动作从哪里到哪里、视线看向谁、表情怎样变化、结束时停在哪里。\n"
        "4. 每个时间段的空间锚点最多0-1个短语，且必须是当前镜头确实需要看见的节点；不要反复堆叠前景/中景/后景/左右/远近/边缘。\n"
        "5. 空间锚点可以少，但剪辑交接词不能省；除第一个时间段外，每段开头必须写\"同一机位继续/延续上一镜/镜头切至/切回\"，禁止单段内写\"反打至\"。\n"
        "6. compiler 只翻译上游导演输出，不新增拍摄技巧；但如果上游写了动作匹配、视线引导、同侧过肩、听者反应、出画入画、景别递进等设计，必须保留成可执行时间轴语言。\n"
        "7. 背后、侧后方、180度是人物相对机位，不是场景相对机位；只写\"商北琛背后中景/商北琛侧后方中景\"，不要写\"电梯门外背后180度\"。\n"
        "8. 电梯开门/入电梯时只需写\"封闭金属轿厢\"，必要时加\"控制面板\"；并在约束中禁止\"办公区、会议区、走廊、窗户、另一片大堂\"。\n"
        "9. 有众员工/群演时，必须在约束中写明：员工不得与命名人物相似、重复或同脸，优先用匿名差异化面孔、侧脸、背影、轻虚。\n\n"
        "【空间几何字段翻译规则——严禁透传】\n"
        "镜头资产中的 camera_basis / camera_scene_position / camera_looks_toward / subject_position / subject_facing / visible_landmarks 是上游内部结构化字段。\n"
        "你必须将它们翻译成自然中文导演语言，绝对禁止在最终 Prompt 中出现 key=value 格式（如 camera_basis=scene_fixed、visible_landmarks=lobby_entrance=background_center）。\n"
        "1. camera_basis=scene_fixed 时，时间轴写成\"场景固定机位/电梯口固定机位/桌侧固定机位\"等短词，不要展开成长空间说明，也不要改成人物正前方机位。\n"
        "2. camera_basis=subject_relative 时，只能用于人物朝向和位置稳定的说话/反应镜头；人物穿过门框、进入电梯、进入车门时必须改用 scene_fixed。\n"
        "3. visible_landmarks 只允许挑选当前镜头最必要的1-2个可见锚点翻译，不得把全部锚点硬塞进前景/中景/后景说明。\n"
        "4. subject_facing 和 angle 冲突时，优先修正 angle 或 visible_landmarks；不要保留互相打架的\"正面+朝门+后景门框\"。\n"
        "5. camera_scene_position → 只在必须保持空间连续时翻译成短句；如果会造成歧义，改成人物相对机位，如\"商北琛侧后方中景\"。\n"
        "6. visible_landmarks → 只挑一个当前镜头必要锚点写成短语，如\"电梯门旁\"；不要翻译成长串前景/中景/后景说明。\n"
        "7. subject_position/subject_facing → 只在必要时翻译成人物站位和朝向，如\"商北琛站在通道中，面朝电梯\"；不要写南侧/远端/近侧/外侧/内侧等多重方位链。\\n"
        "8. 摄影机后退可行性：如果人物面朝电梯/门口且机位在正前方0度，同速后退会让摄影机退进电梯/撞墙；"
        "必须改用侧面跟拍或场景固定机位，或改用左前方45度/右前方45度。\n"
        "9. 视角翻转铺垫：相邻时间段不得从正面突变为背面（或反之），除非文本中明确写出人物转身动作；"
        "如需视角大幅变化，必须插入侧面过渡机位或在时间轴中写明转身动作。\n\n"
        "错误示例（绝对禁止出现在最终输出中）：camera_basis=scene_fixed，camera_scene_position=lobby_axis_between_entrance_and_elevator，visible_landmarks=lobby_entrance=background_center。\n"
        "正确示例：场景固定机位看向大堂入口，员工分列通道两侧。\n\n"
        f"画幅为 {aspect_label}。\n"
        "严禁包含多段；只输出当前片段。\n\n"
        f"{reference_usage_instruction}"
        f"{_script_fidelity_rules()}\n"
        f"{_subject_framing_rules()}\n"
        f"{_shot_composition_task_selection_rules()}\n"
        f"{_dialogue_coverage_contract_rules()}\n"
        # NOTE: _spatial_geometry_contract_rules() 不注入 compiler，已由【空间几何字段翻译规则】替代。
        f"{_camera_execution_rules()}\n"
        f"{_camera_task_selection_rules()}\n"
        f"{_reaction_cut_and_action_path_rules()}\n"
        f"{_timeline_continuity_contract_rules()}\n"
        f"{_director_jargon_translation_rules()}\n"
        "【输出前强制自检】\n"
        "1. 标题行是否为 '片段N｜场景名｜关键词｜~秒数秒' 格式？\n"
        "2. 是否包含【风格锚点】【画幅锚点】【空间与首帧总控】【人物】【镜头序列】【约束】六个段落？\n"
        "3. 每个镜头行是否为 镜头N【X秒】【主体】景别+简洁机位+动作/对白+括号切镜触发？\n"
        "4. 每个镜头行是否有至少1个可见动作、信息或情绪落点？\n"
        "5. 每个镜头行是否自然简短，不靠堆空间词凑字？\n"
        "6. 是否存在场景名+景别的违规写法？\n"
        "7. 是否存在剧本外编造的台词或情节？\n"
        f"8. 末尾是否包含尾帧上传提示（片段{segment_index} prompt 已输出...）？\n"
        "9. 拆片方案中当前片段的 source_script_events 是否全部被覆盖？有无遗漏事件（尤其是片段末尾的悬点/收束动作）？\n"
        "10. 节奏是否合理——建立段是否简洁、炸点/受击段是否留足空间？是否存在表情堆砌导致剧情推进过慢的问题？\n"
        "11. 【空间连续性】每个时间段的画面是否从上一时间段自然演变？是否存在空间跳变或视角翻转？\n"
        "12. 【主体递进而非硬切】主体重心变化是否严格来自上游 shots/sub_shots/reaction_plan，且通过动作/视线/调度自然过渡？\n"
        "13. 【空间总控无动作】空间与首帧总控中是否包含了动作动词（走进、迈入、冲来、转身等）？\n"
        "    如果有，必须改为纯静态描述（站在、位于、面朝），动作只能出现在时间轴中。\n"
        "14. 是否还存在三分之四角度、侧前方、轻微前推跟随、沉默就是回应、权力关系锁住、空气收紧等模糊或抽象描述？如有必须改成明确左右机位、角度、运镜和可见动作。\n"
        "15. 受击反应是否写清\"镜头切至谁/什么景别/什么机位/画面中保留谁\"？关键动作是否写清起点、路径、接触对象、终点和结束状态？是否还存在弹开、飞开、甩开、突然闪开等失控动作词？\n"
        "16. 每个镜头是否继承上一镜头结束状态？除第一个镜头外，是否用动作、视线、道具或轴线明确交接？是否误写了单段反打？每次切镜是否保留必要空间锚点？\n"
        "17. 【禁止透传内部字段】最终输出中是否存在 camera_basis=、camera_scene_position=、camera_looks_toward=、subject_position=、subject_facing=、visible_landmarks= 等 key=value 格式？如有必须全部改写为自然中文句子。\n"
        "18. 【空间简写】空间与首帧总控是否超过3句或反复解释前景/中景/后景/左右/远近？如果是，删到只剩1-3个硬锚点。\n"
        "19. 【表演优先】每个时间段是否至少有一个人物动作、视线或表情落点？如果没有，不要继续补空间，改补人物调度。\n"
        "20. 【电梯硬锁】电梯门后是否被写成办公区/会议区/走廊/窗户/另一片大堂？如果是，改为封闭金属轿厢，并加入禁止项。\n"
        "21. 【群演同脸】有众员工/群演时，是否明确禁止与命名人物同脸、相似或重复？如果没有，必须加入约束。\n"
        "22. 【对白覆盖】长台词、高压命令、质问或揭晓句是否被一个固定机位从头吃到尾？如果是，必须保留/恢复同侧听者反应、过肩、画外音或景别变化；真反打必须拆到相邻片段。\n"
        "23. 【摄影机后退可行性】如果某个时间段写了'正前方0度+同速后退'且人物面朝电梯/门口，检查摄影机后退方向是否会退进电梯/撞墙？如果会，改用侧面跟拍或场景固定机位。\n"
        "24. 【近侧/远端一致性】'近侧侧边''远端''前景''后景'是否与当前摄影机位置和人物朝向的实际几何关系一致？人物面朝电梯+摄影机拍正面时，电梯门框只能在前景/侧边，不能在后景/远端。\n"
        "25. 【空间方位词密度】每个时间段的空间方位词（前景/中景/后景/远端/近侧/边缘/侧边/画面左/画面右/前方/后方/左侧/右侧）是否超过3个？如果超过，只保留最必要的0-1个锚点。\n"
        "26. 【视角翻转铺垫】相邻两个时间段之间是否存在从正面突变为背面（或反之）的视角翻转？如果有，必须在文本中铺垫人物转身动作，或插入侧面过渡机位。\n"
        "27. 【内部字段泄漏】是否出现 fragment_task、must_carry、cut_point、continuity、shot_id、fragment_id 等字段名？如有必须改写成自然中文镜头语言。\n"
        "28. 【导演口语翻译】镜头序列里是否还残留\"稳定器在同一运动里带到\"\"顺势带到\"\"受压反应\"\"权力压住\"\"压入\"\"卡断\"\"炸点\"\"钩子\"\"凝滞\"\"留白\"等导演调度口语？如有必须改成镜头从谁到谁、景别、运动方向、触发动作和低头/屏息/肩膀收紧/眼神回避等可见表演。\n"
        "全部通过后再输出。"
    )
    output = call_llm_with_mcp(system_prompt, user_prompt, server_type="filesystem", images_base64=None, agent_name="prompt_compiler")
    output = _normalise_compiled_prompt(output, segment_index, current_script_context)
    knowledge_metadata = _record_knowledge_metadata(state, "prompt_compiler", compiler_hint, retrieval_meta)
    try:
        compiler_guard_report = _compiler_guard_report(
            output,
            current_script_context,
            current_planner_segment,
            current_director_segment_raw,
        )
    except Exception as exc:
        compiler_guard_report = f"- prompt_compiler guard check failed: {type(exc).__name__}: {exc}"
    guard_report = "\n".join(part for part in [compiler_guard_report] if part).strip()
    outputs[f"compiled_segment_{segment_index}"] = output
    outputs["prompt_compiler"] = output
    return _persist_update(
        state,
        {
            "status": "running_phase_2",
            "step": "step_5_inspect",
            "message": f"质检导演正在审查第 {segment_index} 段...（6/6）",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "system_guard_report": guard_report,
        },
    )


__all__ = [
    "_normalise_compiled_prompt",
    "_compress_director_for_compiler",
    "_timeline_blocks",
    "_compiler_guard_report",
    "prompt_compiler_node",
]
