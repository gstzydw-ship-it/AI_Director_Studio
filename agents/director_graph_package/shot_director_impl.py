"""Shot director implementation split from the legacy director graph module."""
from __future__ import annotations  
  
import re  
import os
import time  
from typing import Any, Callable  
  
from ..knowledge_base import get_agent_knowledge_files  
from .helpers import _primary_script_character_names  
from .state_store import _persist_update, load_state  
from .story_planner_impl import _extract_segments  
from .types import DirectorState  


def _get_llm_settings(*args: Any, **kwargs: Any) -> Any:
    import agents.director_graph as dg

    return dg._get_llm_settings(*args, **kwargs)


def call_llm(*args: Any, **kwargs: Any) -> Any:
    import agents.director_graph as dg

    return dg.call_llm(*args, **kwargs)


def build_system_prompt(*args: Any, **kwargs: Any) -> Any:
    import agents.director_graph as dg

    return dg.build_system_prompt(*args, **kwargs)


_BODY_MECHANICS_ACTION_RE = re.compile(
    r"进入|走进|冲入|冲向|穿过|越过|进电梯|进门|出门|碰撞|撞上|扶住|松开|擦身而过|过阈值|转身|离开|"
    r"拿起|放下|递给|交给|推开|拉开|关上|打开|下车|上车|起身|坐下|后退|让出|站到|移动|行走|奔跑"
)
_ACTION_PATH_TASK_RE = re.compile(
    r"进入|走进|冲入|冲向|穿过|越过|进电梯|进门|出门|碰撞|撞上|扶住|松开|擦身而过|过阈值|转身|离开|"
    r"下车|上车|走向|冲向|退到|站到|让出|移动路径|动作路径|body path|movement path|action path",
    re.IGNORECASE,
)
_SELECTION_REASON_ANCHOR_RE = re.compile(
    r"viewer|audience|attention|information|reveal|delay|hide|miss|space|body|action|path|cut|continuity|"
    r"视线|注意|信息|揭示|隐藏|延迟|空间|身体|动作|路径|连续|切点|受击|反应|轴线|尾帧",
    re.IGNORECASE,
)
_GENERIC_SELECTION_REASON_RE = re.compile(
    r"cinematic|looks good|more emotional|follow(?:s|ing)? rules|rule match|好看|高级|有电影感|符合规则|更有情绪",
    re.IGNORECASE,
)
_GENERIC_CUT_REASON_RE = re.compile(
    r"更有电影感|更好看|想看表情|丰富画面|有张力|有压迫感|cinematic|looks good|more emotional",
    re.IGNORECASE,
)
_DIALOGUE_COVERAGE_TERMS_RE = re.compile(
    r"(反应|受击|听者|对手|对方|过肩|肩线|反打|视线|切回|切至|切到|切出|台词断点|画外音|OS|L-cut|J-cut|景别递进)"
)
# =============================================================================
# shot_director v1 schema contract — 镜头导演字段
# =============================================================================
_SHOT_CONSTRUCTION_FRAGMENT_FIELDS: tuple[str, ...] = ("fragment_task", "rhythm", "continuity_context", "shots")
_SHOT_CONSTRUCTION_REQUIRED_FIELDS: tuple[str, ...] = (
    "shot_id",
    "duration",
    "task",
    "subject",
    "shot",
    "action",
    "dialogue",
    "must_carry",
    "cut_point",
    "continuity",
)
_SHOT_YAML_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "fragment_id": ("fragment_id", "片段编号"),
    "fragment_task": ("fragment_task", "片段任务"),
    "rhythm": ("rhythm", "节奏"),
    "continuity_context": ("continuity_context", "空间连续性总控", "片段连续性总控"),
    "shots": ("shots", "镜头列表"),
    "shot_id": ("shot_id", "镜头编号"),
    "duration": ("duration", "时长"),
    "task": ("task", "镜头任务"),
    "subject": ("subject", "拍摄主体"),
    "shot": ("shot", "镜头"),
    "camera": ("camera", "机位"),
    "size": ("size", "景别"),
    "action": ("action", "画面动作"),
    "dialogue": ("dialogue", "台词"),
    "must_carry": ("must_carry", "必须承载"),
    "cut_point": ("cut_point", "切镜点"),
    "continuity": ("continuity", "连续性"),
    "type": ("type", "类型"),
    "audio": ("audio", "声音"),
}
_SHOT_COVERAGE_CONTRACT_FIELDS: tuple[str, ...] = (
    "coverage_role",
    "cut_reason",
    "companion_visibility",
    "state_delta",
    "tailframe_role",
)
_SHOT_DIRECTOR_WORKFLOW_STAGES: tuple[str, ...] = (
    "layout_task_space",
    "blocking_language_action",
    "guard_final_handoff",
)
_SHOT_DURATION_RE = re.compile(r"^\s*[\"']?(?:\d+(?:\.\d+)?\s*(?:-|~|–|—)\s*)?\d+(?:\.\d+)?\s*秒[\"']?\s*$")
_SHOT_CUT_TRIGGER_RE = re.compile(
    r"(动作顶点|台词(?:断点|落下|结束)?|反应(?:出现|落点)?|信息(?:看清|揭示)|看清|停住|完成|命中|落桌|撞上|尾帧|切出|切至|切到|状态(?:稳定|完成)|片段结束|→)"
)
_SHOT_DENSITY_LIFE_PRESSURE_RE = re.compile(
    r"生活|赶时间|穿衣|上学|孩子|小豆丁|闹钟|电话|手机|草莓|安抚|哄|抗拒|乱蹬|缩手|踢开|书包|紧凑生活",
    re.IGNORECASE,
)
_SHOT_DENSITY_HIGH_CUT_RE = re.compile(
    r"追逐|打斗|抢夺|闯入|冲进|救援|爆炸|车祸|急救|信息揭示|照片|文件|真相|证据|屏幕|监控|"
    r"亲子鉴定|高压对白|长对白|权力压迫|外部打断|宴会|群体|反转",
    re.IGNORECASE,
)
_SHOT_SUBJECT_SPLIT_RE = re.compile(r"[、,，/＋+]|和|与|及")
_SHOT_PROP_SUBJECT_RE = re.compile(
    r"闹钟|手机|电话|外套|衣服|裤|鞋|书包|照片|项链|文件|咖啡|杯|车门|房门|门|按钮|"
    r"桌|沙发|茶几|草莓|蛋糕|手链|戒指|礼盒|道具|花|车|钥匙"
)
_SHOT_GROUP_SUBJECT_RE = re.compile(r"双人|两人|二人|多人|众人|群体|员工|宾客|同框|关系|母女|母子|父女")
_SHOT_PROP_AS_SUBJECT_ALLOWED_RE = re.compile(
    r"唯一主体|信息揭示|关键物|关键道具|线索|证据|照片|文件内容|屏幕|文字|可读|看清|特写|insert|局部|揭示"
)
_SHOT_SPATIAL_STATE_JUMP_RE = re.compile(
    r"突然.{0,16}(站在|坐在|来到|出现在|跑到|移到|换到|穿好|戴好|完成)|"
    r"已经.{0,16}(站在|坐在|来到|出现在|跑到|移到|换到|穿好|戴好|完成)|"
    r"(站在|坐在|来到|出现在|跑到|移到|换到|穿好|戴好|完成)"
)
_SHOT_CONTINUITY_INHERIT_RE = re.compile(
    r"承接上一镜|继承上一镜|上一镜|仍|还|继续|保持|同一|没有离开|未离开|接上|镜尾|尾帧|动作中段"
)
_SHOT_VISIBLE_TRANSITION_RE = re.compile(
    r"起身|站起|坐下|走到|移到|退到|转身|跟随|抱起|放下|拿起|捡起|塞回|滑落|伸出|穿好|停止|停住"
)
_SHOT_FINAL_CAMERA_JARGON_RE = re.compile(r"机位|摄影机位于|camera|shot_size|angle|movement|scene_fixed", re.IGNORECASE)
_SHOT_VIEWPOINT_TRANSLATION_HINT = (
    "最终镜头字段必须把内部机位翻译成视角/观看位置，例如“侧面视角”“固定视角”"
    "“从乔熙肩后看向小豆丁”“小豆丁视线里的乔熙”；不要输出“固定机位/侧面机位/摄影机位于”。"
)

def _shot_director_workflow_contract() -> str:
    return (
        "【shot_director 三段式融合工作流】\n"
        "最终 YAML 只能来自第三阶段；前两阶段是导演施工资产，不能直接交给 prompt_compiler。\n"
        "阶段一｜摆位导演 + 镜头任务与空间安全：先读当前片段事实、节奏操作单和镜头库任务，判断戏剧任务、剪辑省略点、空间轴线和主镜头覆盖链；只搭主分镜骨架，不抢子分镜和反应细节。\n"
        "阶段二｜动作调度导演 + 镜头语言选择：在一号骨架上补动作路径、对白落点、反应落点、状态链和必要子分镜；必须按戏剧微粒、场景类型、风险约束和案例技法主动选择镜头语言，避免同侧固定机位和中近景成为默认答案。\n"
        "阶段三｜规则守门导演 + 最终自然表达：只做最小修复，检查剧本外内容、漏事件、道具跳变、越轴、特写过密、切点无信息变化、镜头语言重复，并把方案整理成自然中文镜头施工单。\n"
        "内部检查项仍必须覆盖：事实提取、节奏意图读取、剪辑策略判断、戏剧任务判断、镜头骨架、镜头语言变化、动作与子镜头、切镜时机、冲突裁决、最小修复、最终交付。\n"
        "冲突裁决：原剧本事实 > 拆片边界 > 连续性/空间安全 > 节奏总控建议 > 镜头美学。\n"
        "节奏裁决：快节奏优先来自人物动作密度、情绪压力和停顿缩短，不等于把生活动作切成碎镜；8-12秒生活动作段默认控制在2-4个有效镜头。\n"
        "拍摄主体裁决：拍摄主体不是人物/道具清单，而是本镜观众注意力的主焦点；道具只有承担信息揭示、线索命中或动作结果时才能成为主体。\n"
        "镜头组合裁决：先选戏剧任务镜头组合，再决定下一镜；生活压力、信息揭示、对白攻防、权力压迫、动作位移分别有不同覆盖链，禁止随机拼景别。\n"
        "连续性裁决：每一镜必须承接上一镜尾帧；人物坐站、位置、道具归属或穿戴状态变化，要么在本镜看见过程，要么用动作中段/尾帧复位切过去。\n"
        "每个镜头除基础字段外，可以补齐 覆盖职责、切镜原因、同场人物位置、状态变化、尾帧职责，"
        "让下游无需猜测镜头职责、切镜原因、同场人物位置和尾帧状态。\n"
    )


def _shot_director_coverage_contract_prompt() -> str:
    return (
        "【每个 shot 需要补齐的镜头职责字段】\n"
        "- 覆盖职责：这镜负责什么覆盖任务，例如建立关系、承载对白、听者反应、道具信息、尾帧承接。\n"
        "- 切镜原因：为什么必须在这里切，必须绑定动作顶点前、台词断点、信息看清、反应出现或尾帧完成。\n"
        "- 同场人物位置：同场人物是否在画面里、在前景/背景/画外/过肩位置，避免人物位置突然消失。\n"
        "- 状态变化：这一镜比上一镜多交代了什么信息、情绪或空间状态。\n"
        "- 尾帧职责：这一镜尾帧怎样交给下一镜或下一片段。\n"
        "这些字段是给提示词编译师的施工依据，不能写成空泛形容词；最终输出不要使用英文字段名。\n"
    )


def _build_shot_director_workflow_trace(
    *,
    planner_output: str,
    expected_segments: list[str],
    atmosphere_strategy: str,
    director_brief: str,
    aspect_ratio: str,
) -> dict[str, Any]:
    """Create a compact runtime trace for the explicit shot-director workflow."""
    sections = _extract_yaml_sections(planner_output)
    fragments: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        fragment_id = _extract_fragment_id(section) or f"F{index:02d}"
        source_events = _source_script_events(section)
        fragments.append(
            {
                "fragment_id": fragment_id,
                "fragment_task": _truncate_for_prompt(
                    _field_value_any(section, "片段任务", "dramatic_unit", "戏剧单元"),
                    240,
                ),
                "duration_target": _truncate_for_prompt(
                    _field_value_any(section, "目标时长", "duration_target"),
                    120,
                ),
                "source_event_count": len(source_events),
                "source_event_preview": [_truncate_for_prompt(event, 180) for event in source_events[:3]],
                "reaction_plan": _truncate_for_prompt(
                    _field_value_any(section, "承接要求", "reaction_plan"),
                    240,
                ),
                "intra_fragment_rhythm": _truncate_for_prompt(
                    _field_value_any(section, "片段内节奏分配", "段内节奏分配", "内部节拍预算", "intra_fragment_rhythm", "internal_beat_budget"),
                    300,
                ),
                "shot_director_handoff": _truncate_for_prompt(
                    _field_value_any(section, "镜头导演交接", "shot_director_handoff", "导演交接"),
                    300,
                ),
                "director_brief": _truncate_for_prompt(_field_value_any(section, "director_brief", "导演交接"), 240),
            }
        )

    if not fragments:
        fragments = [
            {
                "fragment_id": fragment_id,
                "fragment_task": "",
                "duration_target": "",
                "source_event_count": 0,
                "source_event_preview": [],
                "reaction_plan": "",
                "intra_fragment_rhythm": "",
                "shot_director_handoff": "",
                "director_brief": "",
            }
            for fragment_id in expected_segments
        ]

    rhythm_shot_notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    return {
        "mode": "three_stage_fused_pipeline",
        "stages": list(_SHOT_DIRECTOR_WORKFLOW_STAGES),
        "stage_contracts": {
            "layout_task_space": "摆位导演负责戏剧任务、空间安全和主镜头覆盖链。",
            "blocking_language_action": "动作调度导演负责镜头语言选择、动作路径、反应落点和子分镜。",
            "guard_final_handoff": "规则守门导演负责最小修复和自然中文最终交付。",
        },
        "required_shot_fields": list(_SHOT_CONSTRUCTION_REQUIRED_FIELDS),
        "coverage_contract_fields": list(_SHOT_COVERAGE_CONTRACT_FIELDS),
        "aspect_ratio": aspect_ratio,
        "rhythm_guidance_present": bool(rhythm_shot_notes),
        "rhythm_shot_director_notes_present": bool(rhythm_shot_notes),
        "rhythm_shot_director_notes_preview": _truncate_for_prompt(rhythm_shot_notes, 360),
        "director_brief_present": bool((director_brief or "").strip()),
        "fragments": fragments,
    }


def _knowledge_metadata(state: DirectorState) -> dict[str, Any]:  
    return dict(state.get("knowledge_metadata") or {})  
  
  
def _record_knowledge_metadata(  
    state: DirectorState,  
    agent_name: str,  
    context_hint: str,  
    retrieval_meta: dict[str, Any] | None,  
) -> dict[str, Any]:  
    metadata = _knowledge_metadata(state)  
    metadata[agent_name] = {  
        "context_hint": context_hint,  
        "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),  
        "all_sources": get_agent_knowledge_files(agent_name),  
        **(retrieval_meta or {}),  
    }  
    return metadata  
  
  
def _agent_outputs(state: DirectorState) -> dict[str, str]:  
    return dict(state.get("agent_outputs") or {})  
  
  
_SHOT_DIRECTOR_REFERENCE_TERMS = (
    "scene_layout",
    "scene_card",
    "scene_map",
    "annotated_scene_layout",
    "annotated_scene_map",
    "场景俯视",
    "俯视布局",
    "场景母版图",
    "九宫格机位",
    "人物位置",
    "移动轨迹",
    "用户标注",
)


def _scene_reference_items(state: DirectorState | dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return scene-layout references that are useful to shot construction."""
    images = list(state.get("reference_image_b64s") or [])
    manifest = [item if isinstance(item, dict) else {} for item in list(state.get("reference_image_manifest") or [])]
    while len(manifest) < len(images):
        manifest.append({})

    selected: list[tuple[str, dict[str, Any]]] = []
    for index, image in enumerate(images):
        if not image:
            continue
        item = manifest[index] if index < len(manifest) else {}
        role_text = " ".join(
            str(item.get(key) or "")
            for key in ("role", "type", "purpose", "name", "filename", "label", "annotations_summary")
        ).lower()
        if any(term.lower() in role_text for term in _SHOT_DIRECTOR_REFERENCE_TERMS):
            selected.append((str(image), item))
    return selected[:4]


def _reference_images(state: DirectorState) -> list[str]:
    """Send only scene-layout/card references to shot_director."""
    return [image for image, _item in _scene_reference_items(state)]


def _scene_card_status(state: DirectorState | dict[str, Any]) -> str:
    outputs = state.get("agent_outputs") if isinstance(state.get("agent_outputs"), dict) else {}
    return str(state.get("scene_card_status") or outputs.get("scene_card_status") or "").lower()


def _await_scene_card_generation(state: DirectorState) -> DirectorState:
    """Merge background scene-card results before shot planning, with a bounded wait."""
    if _reference_images(state) and _scene_card_status(state) not in {"queued", "running"}:
        return state
    if _scene_card_status(state) not in {"queued", "running"}:
        return state

    try:
        timeout_seconds = float(os.environ.get("AIDIRECTOR_SCENE_CARD_WAIT_SECONDS", "60"))
    except ValueError:
        timeout_seconds = 60.0
    timeout_seconds = max(0.0, min(timeout_seconds, 180.0))
    deadline = time.monotonic() + timeout_seconds
    latest: dict[str, Any] = dict(state)

    while True:
        disk_state = load_state() or {}
        if disk_state:
            latest = dict(state)
            latest.update(disk_state)
        status = _scene_card_status(latest)
        if status not in {"queued", "running"}:
            return latest
        if _reference_images(latest):
            return latest
        if time.monotonic() >= deadline:
            return latest
        time.sleep(1.0)


def _reference_image_manifest_prompt(state: DirectorState | dict[str, Any]) -> str:
    scene_refs = _scene_reference_items(state)
    layout_annotations = list(state.get("scene_layout_annotations") or [])
    if not scene_refs and not layout_annotations:
        return ""

    lines = [
        "[Scene Layout Reference Images]",
        "The attached images below are scene-layout references for blocking and continuity.",
        "If an overhead layout contains user markers or movement routes, treat them as staging constraints: character positions, movement direction, spatial boundaries, doors and fixed objects.",
        "Use these images only to choose camera orientation, blocking continuity and cut handoffs; do not add script-external props, actions, dialogue or people.",
    ]
    for index, (_image, item) in enumerate(scene_refs, start=1):
        label = str(item.get("label") or f"@图片{index}")
        role = str(item.get("role") or item.get("type") or "scene_reference")
        purpose = str(
            item.get("purpose")
            or item.get("annotations_summary")
            or item.get("name")
            or item.get("filename")
            or ""
        )
        lines.append(f"- {label}: {role}; {purpose}".rstrip("; "))
    for annotation in layout_annotations[:4]:
        if not isinstance(annotation, dict):
            continue
        summary = str(annotation.get("summary") or annotation.get("annotations_summary") or "").strip()
        if not summary:
            continue
        scene_number = str(annotation.get("scene_number") or "?")
        lines.append(f"- scene {scene_number} user annotations: {summary}")
    return "\n".join(lines)
  
  
def _director_brief(state: DirectorState | dict[str, Any]) -> str:  
    return str(state.get("director_brief") or "").strip()  


def _scene_context_brief(state: DirectorState | dict[str, Any]) -> str:
    outputs = state.get("agent_outputs") if isinstance(state.get("agent_outputs"), dict) else {}
    return str(state.get("scene_context_brief") or outputs.get("scene_analyst") or "").strip()


def _scene_context_prompt_block(scene_context: str) -> str:
    scene_context = (scene_context or "").strip()
    if not scene_context:
        return ""
    return (
        "[场景分析师给镜头导演的空间约束]\n"
        "只把它当作空间、固定物、入口、人物限制和可拍性参考；不得据此新增剧本外人物、台词、道具或动作。"
        "如果它与拆片原文事件、尾帧承接或节奏总控冲突，以拆片原文事件和连续性为准。\n"
        f"{_truncate_for_prompt(scene_context, 1200)}\n"
    )


def _director_brief_prompt_block(director_brief: str) -> str:
    director_brief = (director_brief or "").strip()
    if not director_brief:
        return ""
    return (
        "[Director Showrunner Brief]\n"
        "This brief is the top-level creative contract. Preserve script facts, "
        "but use it to choose emphasis, shot priority, rhythm, and acceptable tradeoffs.\n"
        f"{director_brief}\n"
    )
  
  
def _derive_segments_from_planner_output(planner_output: str) -> tuple[int, list[str]]:  
    sections = _extract_yaml_sections(planner_output or "")  
    if not sections:  
        return _extract_segments(planner_output)  
    fragment_ids = [_extract_fragment_id(section) for section in sections]  
    fragment_ids = [fragment_id for fragment_id in fragment_ids if fragment_id]  
    if not fragment_ids:  
        return _extract_segments(planner_output)  
    expected_ids = [f"F{index:02d}" for index in range(1, len(fragment_ids) + 1)]  
    if fragment_ids == expected_ids:  
        return len(fragment_ids), [f"片段{index:02d}" for index in range(1, len(fragment_ids) + 1)]  
    return len(fragment_ids), fragment_ids  
def _script_fidelity_rules() -> str:
    return (
        "【剧本忠实度硬规则】\n"
        "1. 只能使用原剧本已经出现的人物、场景、动作、台词和信息点，禁止补写剧本外新事件。\n"
        "2. 禁止新增剧本中没有的台词、旁白、员工低语、心理活动或解释性信息；凡带引号的台词必须能在原剧本中找到。\n"
        "3. 若原剧本没有写员工说话，就不能写员工低声确认、新CEO到了、议论等补戏。\n"
        "4. 片段不足15秒时允许短于15秒，禁止为了凑时长添加新情节。\n"
    )

def _rhythm_insert_continuity_rules() -> str:
    return (
        "【节奏插入连续性规则】\n"
        "1. 画面逻辑优先于情绪细节：任何新增辅助行都必须先保证人物位置、道具归属和下一拍连续性成立。\n"
        "2. 新增辅助行不得制造道具归属或位置跳变；同一件道具不能在相邻动作中同时被两个人持有、背着、收起或取用。\n"
        "3. 如果原文刚写某人拿起、捡起、塞回、攥住、交给某道具，新增行必须顺着这个状态承接，不能暗示道具已经离开该人。\n"
        "4. 低歧义画面优先：优先写\"放到桌上、站到门口、停住动作、看向某处\"等稳定可见动作，避免\"攥进掌心、指尖摩挲、掌心收紧\"等模型容易误画的细微手部状态。\n"
        "5. 插入儿童或人群小动作时，优先写身体姿态、站位、视线或停顿；只有原文明确道具已在该人物身上时，才写道具状态。\n"
    )

def _subject_framing_rules() -> str:
    return (
        "【主体+景别硬规则】\n"
        "1. 景别只能修饰人物、明确人物组合、可见身体局部或关键道具，不能修饰场景名。\n"
        "2. 禁止写\"大堂半身中景\"\"电梯厅近景\"\"空间中景\"\"通道特写\"等场景+景别组合。\n"
        "3. 正确写法示例：人物甲半身中景、人物乙胸部以上中近景、两人双人中景、剧本已有关键道具局部特写。\n"
        "4. 空间只能写作环境关系，例如\"大堂纵深关系清楚\"，不能写成\"大堂中景\"。\n"
    )

def _spatial_geometry_contract_rules() -> str:
    return (
        "【空间几何合同硬规则】\n"
        "1. 当前轻量施工单不再输出 camera_basis 等内部字段；空间几何必须翻译进 shot 与 continuity。内部校验仍使用 camera_basis、scene_fixed、visible_landmarks 等合同词判断前景/中景/后景是否闭环。\n"
        "2. shot/镜头字段只写最终可生成的镜头表达句，格式为【主体景别 + 视角/观看位置 + 必要运动】；不要在此字段写人物动作、台词、心理、戏剧效果或情绪判断。\n"
        "3. 内部可以判断机位锚点，但最终必须翻译成视角：写“侧面视角”“固定视角”“从谁肩后看向谁”，不要写“侧面机位/固定机位/摄影机位于”，也不要写坐标式空间说明。\n"
        "4. continuity 必须写清具名人物站位、朝向、道具位置和可继承尾帧；不能只写\"保持连续\"，也不能只写\"画面左侧/右侧\"而不说明谁看向谁。\n"
        "5. 人物转身、穿门、进电梯/车门/房门等阈值动作，最终写成侧面视角、背后跟随视角或固定视角；不要用人物正前方视角硬拍动作路径。\n"
        "6. 如果人物面朝电梯/门口且镜头拍正面，门框只能是前景或侧边锚点，不能写成后景。\n"
        "7. 几何闭环优先于好听文案：shot、action、continuity 三者必须互相兼容。\n"
    )

def _performance_logic_contract_rules() -> str:
    return (
        "【人物动作表情链与逻辑闭环硬规则】\n"
        "1. 镜头字段不承载表演；人物动作、表情、视线、呼吸、肩颈、手部和道具接触必须写进画面动作。\n"
        "2. 画面动作必须按可见顺序写清：起始状态 -> 动作变化 -> 表情/身体反应 -> 结束状态；不要只写\"抗拒\"\"压迫\"\"暧昧\"\"被影响\"这类抽象判断。\n"
        "3. 必须承载只写这一镜必须看见的信息、状态变化或反应结果，例如道具仍在谁手里、是否已经戴上、谁看清了什么、谁的身体距离发生变化。\n"
        "4. 道具接触戏必须锁定道具归属和动作阶段：靠近、贴近、绕到、扣上、松开不能跳步；相邻镜头不能让同一道具同时在两个人手里或突然完成佩戴。\n"
        "5. 身体接触戏要写低歧义边界：手靠近颈侧、项链贴近脖颈、指尖短暂掠过皮肤、肩颈轻颤；禁止写会诱发穿模或错位的复杂手部缠绕。\n"
        "6. 表情必须有可画出来的细节：视线停住、眉心收紧、嘴唇停住、肩颈绷紧、呼吸短暂停住、抬眼看向对方；不要只写\"明显拒绝\"或\"情绪复杂\"。\n"
        "7. 单人镜里也要在连续性说明同场人物和关键道具仍在何处，防止模型把画外人物或道具删除。\n"
    )

def _camera_execution_rules() -> str:
    return (
        "【内部机位规划与最终视角表达硬规则】\n"
        "1. 内部镜头设计必须保留完整镜头语法：主体+主体景别、焦段、景深、机位高度、拍摄角度、唯一运镜、动作/表演、光源；不得因为最终要给 Seedance 就提前丢掉焦段/景深/高度/角度判断。\n"
        "2. 每个 shot 只能有一个主体焦点、一个景别基底、一个主导运镜；景别可以在子分镜内递进，但不能写成\"纵深中全景到半身中景\"这种单字段混合景别。\n"
        "3. 内部可以判断平视、略低、略高、俯视等高度；最终要写成“自然平视角”“略低视角”“略高视角看动作”，避免机械写“眼平高度/低机位”。\n"
        "4. 内部拍摄角度从正面、侧面、侧背、背后、过肩、固定观察、荷兰角、POV 中选择；最终输出必须写“正面视角/侧面视角/背后跟随视角/从谁肩后看向谁/谁的主观视角”。\n"
        "5. 运镜从推近、拉开、横移、摇摄、升降、变焦、跟随、手持、固定观察中选唯一主导运动；禁止在一个 shot 内同时推近、横移、摇摄、再回主位。\n"
        "6. 运镜必须服务镜头目的：推近/切近/转特写只能服务信息逼近、情绪暴露、压迫上升、受击反应变重要、道具或局部动作成为焦点；禁止把慢推近当通用情绪模板。\n"
        "7. 反应落点优先按层级处理：主分镜负责主体关系和空间重心，子分镜负责受击、表情重音、局部动作；不要把\"同一运动里带到反应再回主位\"写成一个复杂主镜头。\n"
        "8. 禁止复合景别/复合机位：不要写\"纵深中全景到半身中景\"\"中景转电梯口关系景\"\"右后方中景转固定机位\"\"同轴线偏右侧\"\"前后景关系\"。最终改成自然句：主体 + 景别 + 视角 + 运动。\n"
        "9. 禁止使用模糊视角词：三分之四角度、斜侧、斜前方、轻微前推、轻微前推跟随、缓慢靠近、背影轻压。\n"
        "10. 禁止抽象判断句。不要写\"沉默就是回应\"\"权力关系锁住\"\"空气收紧\"\"命令落地即见效\"\"形成清晰钩子\"。必须改写成可见动作：停顿几秒、谁看向谁、谁后退半步、谁让出通道、电梯门停在什么开合状态。\n"
        "11. 内部可以技术化，最终编译必须感知化：85mm浅景深可译为\"背景虚化、主体突出\"，深景深可译为\"前后景都清楚\"，不得把\"电影感/高级感\"写成空壳标签。\n"
        f"12. {_SHOT_VIEWPOINT_TRANSLATION_HINT}\n"
    )

def _camera_task_selection_rules() -> str:
    return (
        "【镜头任务到机位选择硬规则】\n"
        "1. 先判断当前 main_shot 的 coverage_role 与 shot_intent，再决定 shot_size、camera_height、angle、movement、lens、depth；不要先挑一个好看的机位再硬套剧情。\n"
        "2. 主分镜只在主体关系变化、场面权力关系变化、叙事重心变化、空间观察点变化、当前主镜头无法承载下一动作单元时新开；不要用主分镜机械对应每句台词。\n"
        "3. 完整发言单元优先保持在同一主分镜内；长挑衅/揭晓/质问台词超过2秒时，用子分镜/L-cut 切受击者，让后半句以画外音落在反应上。\n"
        "4. 听者受击、视线撞上、回神、表情冻结：优先挂到现有主镜头或新增 sub_shot；受击者机位必须落在同侧轴线内，并写 companion_visibility，不要靠横移摆尾带到反应。\n"
        "5. 动作路径、身体位移、擦身而过、碰撞、扶住、松手：优先场景固定机位、门框侧机位、桌边侧机位、走廊侧机位、背面跟拍或过肩前景遮挡；目标是看清起点、路径、接触点和终点。整段保持同一场景锚点侧。\n"
        "6. 目标方向、走向门口、冲向门缝、进入电梯、穿过门框、离开画面：优先背面跟拍、侧面跟拍、门框侧固定机位或 scene_fixed；目标是看清人物前方目标与阈值关系，不使用人物左后方/右后方。\n"
        "7. 9:16 主力景别为半身景/中景/MS，MCU 只用于压迫段或信息逼近中间层，CU 只用于信息炸点/受击反应/情绪顶点；禁止长期只在 MCU 与 CU 之间摆动。\n"
        "8. 群体调度必须保留空间容量：群体四散、主管退让、员工让路不能用面部特写承接，优先中景关系、半身关系或 scene_fixed。\n"
        "9. 每个 main_shot 必须有 cut_reason，回答为什么从上一主镜头切到这里；有效理由包括台词落点后切听者反应、动作中间态切接续、需要回关系景确认距离/门状态、tailframe_reset。\n"
        "10. sub_shot 必须有 parent_shot_id、trigger、shot_size、cut_point、companion_visibility、state_delta、beat_purpose、emotion_anchor、duration_hint、action_phase；每个片段最多2个子分镜。\n"
        "11. 如果一个 fragment 里有多个 main_shots，禁止所有 shot 都重复同一套 shot_size + angle + movement；但变化必须有叙事动机，禁止假丰富感。"
    )

def _space_rules_contract_rules() -> str:
    return (
        "【场面调度地图合同】\n"
        "1. 每个片段必须先写空间规则，再写镜头列表；这是摆位、调度、守门和编译共用的平面图合同。\n"
        "2. 空间锚点必须列出稳定布景、门槛和地标，并说明相对方向，例如门在北侧、桌在中央、窗在东侧。\n"
        "3. 人物位置必须说明每个出场人物的起点、已知终点，以及身体朝向与空间锚点的关系。\n"
        "4. 动作轴线必须说明主要视线/动作轴，以及安全机位应落在哪一侧。\n"
        "5. 安全机位区必须列出物理可拍、能保轴且能保留必要人物/地标可见的机位区域。\n"
        "6. 禁用机位区必须列出越轴、遮挡、门口物理不可能或隐藏动作路径的危险位置。\n"
        "7. 主镜头的机位位置和可见地标必须与空间规则兼容；如果使用固定场景机位，必须来自安全机位区，或在选择理由里说明例外。\n"
    )

def _best_shot_selection_rules() -> str:
    return (
        "【最佳镜头选择合同】\n"
        "1. 不要因为某个镜头命中了规则分类就直接选择；先判断观众此刻应该看什么。\n"
        "2. 每个主镜头必须写注意目标：观众此刻必须看谁或看什么。\n"
        "3. 每个主镜头必须写信息策略：这一镜揭示、延迟、隐藏或故意让观众错过什么。\n"
        "4. 每个主镜头必须写选择理由：为什么此刻这个景别、角度和机位最强。\n"
        "5. 每个主镜头必须写放弃方案：至少一个看似可用但更弱的选择，以及放弃原因。\n"
        "6. 选择理由不能写成“有电影感、好看、符合规则、更有情绪”等空泛词，必须绑定注意力、信息、空间、身体动作或切镜连续性。\n"
        "7. 如果是反应镜头，说明为什么现在观众需要看承受者而不是说话者；如果是动作路径镜头，说明为什么身体路径必须清楚；如果是关系复位镜头，说明它修复了什么空间混乱。\n"
    )

def _has_body_mechanics_action(block: str) -> bool:
    """Return True if the shot block describes a body-contact or movement-path action."""
    return bool(_BODY_MECHANICS_ACTION_RE.search(block or ""))

def _shot_composition_task_selection_rules() -> str:
    return (
        "【镜头任务到景别/镜头类型选择硬规则】\n"
        "1. 先判断 shot 的叙事任务，再决定 shot_size 与 main_shot/sub_shot 归属；不要先随手选 CU/MCU/MS，再把任务硬塞进去。\n"
        "2. 建立空间、人物关系、尾帧交接：优先 全景/中景/半身中景/双人关系景；这些必须是 main_shot，不能用脸部特写或手部局部承担。\n"
        "3. 发言承载、正面施压、冷处理对峙：鼓励使用极端景别！情绪爆发、挑衅、冷笑或压抑点，大胆使用特写（CU）或极特写（ECU）；展现权势碾压或孤独感时，大胆使用大远景（Wide Shot）。拒绝平庸的电视感中景。\n"
        "4. 听者受击、回神、视线撞上、表情冻结：优先 中近景或胸部以上近景；只允许在真正情绪极点使用一次特写，且必须保留前景肩线、门框、桌边或人物边缘作为空间锚点。\n"
        "5. 身体位移、擦身而过、碰撞、扶住、松手、转身、穿门、进电梯/车门/房门：优先 中景、半身关系景、双人中景或全身关系景；禁止用 CU/ECU/手部局部主镜头承担动作路径。\n"
        "6. 手部、道具、门缝、照片、手机、衣角等细节只能作为短 sub_shot 或 action_insert_slot；必须挂 parent_shot_id，不能升级成 main_shot，除非该物件本身就是当前剧本事件的唯一主体。\n"
        "7. sub_shot 只负责重音，不负责重新建场；duration_hint 要短，action_phase 必须说明 pre_action、mid_action、impact、reaction 或 reset。\n"
        "8. 一个 fragment 的有效镜头应有景别层次：关系景/中景负责空间和动作，中近景负责对白和反应，特写只负责一次重点；禁止连续用特写推进整段。\n"
        "9. 最后一个 main_shot 若承担 tailframe_reset，必须回到可继承的关系景、中景或明确空间状态；不能停在脸部特写、眼神、手部或道具局部。\n"
        "10. 9:16 竖屏审美纪律：减少废话一样的多人宽幅全景（竖屏塞不下），多使用切边构图、前景遮挡构图和极特写来构建电影级的视觉压迫感。\n"
    )

def _dialogue_coverage_contract_rules() -> str:
    return (
        "【对白覆盖与反应切镜硬规则】\n"
        "1. 完整发言单元必须保持语义连续，但不能理解为单镜头吃完整段台词；画面可以且应该在同一发言单元内部切到对手反应、过肩、反打或不同景别。\n"
        "2. 任何长台词、命令、质问、揭晓、挑衅或高压对白，至少需要\"说话者起句 -> 对手/听者反应或反打 -> 必要时切回说话者/关系景\"的覆盖方案。\n"
        "3. 高级剪辑思维（告别乒乓球剪辑）：高冲击台词必须强制使用画外音（OS / J-cut / L-cut）。例如 A 放狠话时，镜头不要拍 A，而是直接切给 B 微妙颤抖的下颌线或紧握的拳头，A 的声音作为画外音处理。\n"
        "4. 视线引导（Eyeline Match）：layout 和 blocking 阶段在切镜前，必须写清上一个镜头角色的视线看向哪里，下一个镜头的机位必须从该视线方向自然承接，严禁无视线的盲切。\n"
        "5. compiler 只忠实翻译上游 dialogue_coverage、reaction_coverage、sub_shots 和 cut_point，不得把它们压扁成一个固定机位里的人物连续说完。\n"
        "6. 对白切镜服务信息增量，不是机械按秒切；如果台词短且没有受击/信息落点，可以同一机位继续，但长句和高压句必须有视觉变化。\n"
        "7. 人物说长压迫对白时，严禁一个镜头、一个景别、一个机位说完整句或完整问答；必须在对白内部写出明确切镜点，例如\"他说出前半句 -> 镜头切至同侧听者中近景/过肩 -> 后半句以画外音/L-cut 落在听者反应上 -> 必要时切回说话者\"。\n"
        "8. 如果一个时间段包含两句以上往返对白，不能写成同一双人中景连续说完；必须拆出说话者起句、同侧听者反应、关系景复位，至少一次改变主体、景别或机位。\n"
    )

def _shot_director_source_event_rules() -> str:
    return (
        "【shot_director 剧本继承硬规则】\n"
        "1. shot_director 只能把 story_planner 的 source_script_events 翻译成镜头、景别和受击落点；不得重新解释剧本、不得新增睡醒、床边、伴侣、保镖、记者、闪光灯、鞠躬等剧本外前提。\n"
        "2. 场次标题、人物行、source_script_events 的可见事实优先级高于英文台词里的词义联想；例如 OS 里的英文短语只按当前人物台词/画外音处理，不能联想成剧本外的新动作或新人物。\n"
        "3. 场景空间必须继承场次标题和 source_script_events；公寓不能改成车内，门口不能改成大堂，集团门口不能改成办公室。\n"
        "4. subject 只能来自当前片段的人物行、source_script_events 中的可见人物/群体/道具/车辆；不能把 OS 里的昵称或英文名当成画面主体替换角色名。\n"
        "5. 必须继承上游的道具状态和空间状态：已有道具在桌上就保持在桌上，已有随身物在人物身上就保持在人物身上，不得为了情绪镜头改写道具归属或位置。\n"
        "6. 低歧义画面优先：优先使用站位、视线、停顿、桌面、门口、车辆到达、下车等稳定可见动作；避免把简单动作改成掌心、指尖、指节、发丝等微观细节。\n"
        "7. 先判断当前片段的节奏任务，再匹配镜头语言；必须先回答这是权力反转、冲突升级、悬念揭示、误解错位、情绪极点还是钩子结尾，再决定要不要切镜、切几镜，不能先拿模板再套剧情。\n"
        "8. 9:16 竖屏默认以半身、中景、双人关系景别承担叙事；特写只给炸点、受击、情绪峰值或关键信息插入。一个片段的面部特写最多一次，不得把特写当默认景别。\n"
        "9. 没必要每个细节动作都给镜头：如果主镜头已经能看清动作和关系，就不要再为手指、掌心、鞋尖、袖口、嘴唇、眼角等微细节单独开镜头；只有线索揭示、动作前摇或受击落点无法看清时才允许插入。\n"
        "10. 悬念揭示优先采用\"停顿/发现前逼近 -> 关键物或文字 -> 人物反应\"；冲突升级优先采用\"施压 -> 受击 -> 短暂停顿\"；误解错位优先提升听者反应镜头，而不是让说话者一直占满画面。\n"
        "11. shot_director 不得重新判断整体节奏，必须服从 atmosphere_strategy / rhythm supervisor 给镜头导演的精简操作单；"
        "把快慢、停顿、卡断、反应归属、尾帧承接翻译成具体镜头设计。\n"
        "12. 若节奏建议与剧本事实、台词原文、动作道具连续性、人物位置、空间轴线安全冲突，后者优先。\n"
    )

_SHOT_RHYTHM_FAST_ACTION_RE = re.compile(
    r"闹钟|赶|急|忙|乱蹬|追车|追逐|逼近|跟着|身后|加快|穿过|撞开|躲|冲向|冲进|"
    r"小跑|跑|闯|警笛|救护车|不见了|走失|掉在|滑出|抓起|藏到|扶住|倒下|坍塌|抢|拉扯",
    re.IGNORECASE,
)
_SHOT_RHYTHM_DIALOGUE_RE = re.compile(
    r"说(?!不出话)|问|喊|解释|质问|回应|承认|否认|道歉|要求|命令|继续说|低声说|"
    r"电话(?:里|中|那头|问|说)|短信|：|:",
    re.IGNORECASE,
)
_SHOT_RHYTHM_REACTION_RE = re.compile(
    r"停住|愣|沉默|安静|脸色变|看向|回头|后退|哭|害怕|不敢|压住火气|受击|反应|"
    r"没有立刻回答|抬头|握紧|眼眶红|僵住|没有接|点头|低头|收回手",
    re.IGNORECASE,
)
_SHOT_RHYTHM_REVEAL_RE = re.compile(
    r"("
    r"(?:照片|文件|录音|短信|视频|监控|报告|合同|戒指|项链|亲子鉴定|诊断书|钥匙|书包|屏幕|通知|证据).{0,18}"
    r"(?:掉|滑|散落|露|翻|拿出|捡|看清|发现|打开|递出|递到|递来|送到|送来|推过|放到|放在|摆到|亮出|取出|掏出|落出|掉出|弹出|刷出|出现|播放|投到|显示|写着)|"
    r"(?:掉|滑|散落|露|翻|拿出|捡|看清|发现|打开|递出|递到|递来|送到|送来|推过|放到|放在|摆到|亮出|取出|掏出|落出|掉出|弹出|刷出|出现|播放|投到|显示|写着).{0,18}"
    r"(?:照片|文件|录音|短信|视频|监控|报告|合同|戒指|项链|亲子鉴定|诊断书|钥匙|书包|屏幕|通知|证据)|"
    r"真相出现|签名时间|遗嘱被改|过敏照片|缴费单|病危通知|新证据|真正签名"
    r")",
    re.IGNORECASE,
)
_SHOT_RHYTHM_MEMORY_RE = re.compile(r"回忆|闪回|回到现实|四年前|三年前|多年后|往事|从前", re.IGNORECASE)
_SHOT_RHYTHM_INTRUSION_RE = re.compile(
    r"门被推开|门突然开|突然开了|门打开|敲门|闯进|闯入|冲进|赶到|警笛|救护车|手机震动|电话响起|电话响|打断|挡在门口",
    re.IGNORECASE,
)

def _estimate_shot_director_coverage_plan(
    events: list[str],
    *,
    planner_handoff: str = "",
    duration_target: str = "",
) -> dict[str, str]:
    """Estimate shot-director coverage ownership from planner events for tests and diagnostics."""
    clean_handoff = "" if planner_handoff == "开场情绪注意力问题" else planner_handoff
    text = "\n".join([*(events or []), clean_handoff, duration_target])
    event_count = len(events or [])
    has_memory = bool(_SHOT_RHYTHM_MEMORY_RE.search(text))
    has_reveal = bool(_SHOT_RHYTHM_REVEAL_RE.search(text))
    has_intrusion = bool(_SHOT_RHYTHM_INTRUSION_RE.search(text))
    fast_action_hits = len(_SHOT_RHYTHM_FAST_ACTION_RE.findall(text))
    has_fast_action = fast_action_hits >= 2 or bool(
        re.search(r"追逐|追车|冲向|撞开|警笛|救护车|不见了|走失|乱蹬", text, re.IGNORECASE)
    )
    has_dialogue = bool(_SHOT_RHYTHM_DIALOGUE_RE.search(text))
    has_reaction = bool(_SHOT_RHYTHM_REACTION_RE.search(text))

    if has_memory:
        if re.search(r"回到现实|现实", text) and event_count <= 1:
            return {
                "rhythm_task": "时空切层/现实回收",
                "effective_shots": "1-2",
                "layout": "现实关系中近景或关系景接回尾帧，避免为了回神细节新增碎镜。",
                "cut_timing": "切点落在观众辨认现实层之后，尾帧停可继承状态。",
                "duration_logic": "短镜接回，情绪停顿可比动作更长。",
                "action_direction": "动作只保留回神、握住道具、看向对方等低歧义结果态。",
            }
        return {
            "rhythm_task": "回忆/时空切层",
            "effective_shots": "2-3",
            "layout": "先用切层识别镜头建立时空，再用关系/中景承载回忆内动作。",
            "cut_timing": "切点落在时空层明确、情绪动作完成或尾帧可回接处。",
            "duration_logic": "第一镜短促辨认，后续镜头给情绪动作留读秒。",
            "action_direction": "动作调度只保留记忆层的核心接触、递交、回望或离开。",
        }

    reveal_is_major = bool(
        re.search(
            r"看清|发现|播放|投到|显示|真相|结果|日期|照片|诊断|亲子鉴定|录音|视频|监控|短信|屏幕|"
            r"报告|病危通知|遗嘱|过敏照片|缴费单|签名时间|新证据",
            text,
            re.IGNORECASE,
        )
    )
    reveal_is_weak_prop = bool(
        re.search(
            r"(?:钥匙|书包).{0,8}(?:拿|取出|掏出|放|递|捡)|(?:拿|取出|掏出|放|递|捡).{0,8}(?:钥匙|书包)",
            text,
            re.IGNORECASE,
        )
    ) and not reveal_is_major
    if has_intrusion and not (has_reveal and reveal_is_major):
        return {
            "rhythm_task": "外部打断/压力转向",
            "effective_shots": "2-3",
            "layout": "当前关系镜头 -> 打断来源/入口方向 -> 被打断者或群体反应复位。",
            "cut_timing": "切点落在声音/入口/人群反应触发处，不盲切群体碎反应。",
            "duration_logic": "前后镜较短，中间打断来源要清楚。",
            "action_direction": "动作调度强调停住、看向、让开或护住道具等结果。",
        }

    if has_reveal and not reveal_is_weak_prop and not (has_dialogue and event_count >= 4 and not reveal_is_major):
        if event_count <= 1 and not has_reaction and not re.search(r"看清|发现|播放|投到|真相|结果|日期|发光|录音|视频|监控|短信", text):
            return {
                "rhythm_task": "关键物件承接",
                "effective_shots": "1-2",
                "layout": "用主关系镜头接住道具进入叙事，必要时给短插入。",
                "cut_timing": "切点落在道具状态成立后，不为递放过程单独碎切。",
                "duration_logic": "道具进入画面不拖长，结果状态清楚即可。",
                "action_direction": "递出、放下、拿起等过程并入主镜头，强调道具归属。",
            }
        return {
            "rhythm_task": "信息揭示/关键物件",
            "effective_shots": "2-3",
            "layout": "关系镜头或发现前状态 -> 信息可读近景/插入 -> 人物反应或关系复位。",
            "cut_timing": "切点不得早于文字/物件被看清，反应镜头落在信息读清之后。",
            "duration_logic": "信息镜头至少留出可读停顿，反应镜头不抢在揭示前。",
            "action_direction": "动作调度压缩寻找过程，保留发现、看清、停住或转向。",
        }

    if has_intrusion:
        return {
            "rhythm_task": "外部打断/压力转向",
            "effective_shots": "2-3",
            "layout": "当前关系镜头 -> 打断来源/入口方向 -> 被打断者或群体反应复位。",
            "cut_timing": "切点落在声音/入口/人群反应触发处，不盲切群体碎反应。",
            "duration_logic": "前后镜较短，中间打断来源要清楚。",
            "action_direction": "动作调度强调停住、看向、让开或护住道具等结果。",
        }

    if has_fast_action:
        return {
            "rhythm_task": "急促动作/压力上升",
            "effective_shots": "2-4" if event_count >= 3 else "2-3",
            "layout": "关系/跟随镜头承载动作链，必要时在动作顶点或结果落点切近。",
            "cut_timing": "只在动作顶点、主体切换、信息落点或结果状态完成时切。",
            "duration_logic": "短镜密度来自动作压力，不能把每个小动作拆成独立镜头。",
            "action_direction": "动作调度做叠压和省略，跳过走路/翻找/调整衣物等无增量过程。",
        }

    if has_dialogue and has_reaction:
        return {
            "rhythm_task": "高压对白/情绪反应",
            "effective_shots": "2-4",
            "layout": "说话者起句、同侧听者反应/过肩、必要时关系复位或反应近景。",
            "cut_timing": "切点落在台词压力词、听者受击、短暂停顿或回应前。",
            "duration_logic": "长句后半可用 OS/J-cut/L-cut 落在听者反应上。",
            "action_direction": "动作调度保留视线、停顿、后退、放下道具等情绪结果，不堆微表情。",
        }

    if has_dialogue or has_reaction:
        return {
            "rhythm_task": "对白/情绪铺垫",
            "effective_shots": "1-2" if event_count <= 2 else "2-3",
            "layout": "半身关系景或过肩承载交流，需要时切听者反应。",
            "cut_timing": "切点落在情绪落点、回应前或关系变化处。",
            "duration_logic": "语义连续优先，不为短句机械正反打。",
            "action_direction": "动作调度让人物动作自然承接台词，不新增解释性表演。",
        }

    return {
        "rhythm_task": "正常承接/情绪铺垫",
        "effective_shots": "1-2",
        "layout": "稳定关系镜头或中景承载，不为普通过渡动作单独开镜。",
        "cut_timing": "只有主体、空间或状态真的变化时切。",
        "duration_logic": "镜头时长随动作自然完成，不制造假停顿。",
        "action_direction": "弱动作并入主镜头或用结果状态呈现。",
    }

def _shot_director_rhythm_match_rules() -> str:
    return (
        "【节奏与镜头匹配规则（参考《AI 导演系统工程文档规范》）】\n"
        "0. shot_director 只执行 story_planner 给出的片段边界、情绪曲线、节奏意图、必须保留落点、可压缩弱拍和尾帧承接；不得重新判断整体节奏、不得重新拆片或新增剧情。\n"
        "0A. 镜头数、镜头时长、景别、机位、运镜、反应覆盖和切镜点由 shot_director 决定；若上游旧字段出现“最多镜头数/建议镜头数”，只当软提示，不得替代本阶段的镜头规划判断。\n"
        "1. 先识别戏剧微粒，再决定镜头：权力反转看压制与失势，冲突升级看施压与受击，悬念揭示看发现与停顿，误解错位看听者反应，情绪极点看停住后的内压，钩子结尾看最后的悬住点。\n"
        "2. 镜头数量由节奏任务决定，不由镜头库模板决定；能用 1 个主镜头讲清的动作，不要硬拆成 3 个细碎镜头。\n"
        "3. 快节奏不是多切镜，而是人物动作更紧、停顿更短、信息落点更密；快切只用于动作前摇、揭示落点、受击反应、关系变化、关键道具或文字出现。\n"
        "4. 正常节奏使用正常人物动作和正常镜头切分：保持半身/中景/双人关系镜头的连续性，不为了显得有节奏而切手、切眼、切衣角。\n"
        "5. 需要切镜时，只切信息增量最大的节点。走近、弯腰、拿起、站定、回头等中间过渡默认并入主镜头，不单独成镜。\n"
        "6. 权力反转优先用站位高低、画面占比、稳定推进和反应落点表达，不靠堆叠特写表达压迫。\n"
        "7. 冲突升级可以用 2-3 秒短镜，但每个短镜必须有明确戏剧功能；切掉无信息量动作过程。\n"
        "8. 悬念揭示里的关键物、文件、屏幕、照片要稳拍可读；不要为了好看加花哨运动，文字类信息优先静态或极轻微推进。\n"
        "9. 情绪极点允许更稳、更长一点，但仍应以简单背景、少动作、少机位运动为前提；9:16 下优先稳住半身或中景，再考虑是否真的需要更近景别。\n"
        "10. 9:16 竖屏下，半身/中景/双人关系镜头是主力，特写是强调而不是默认。若一个片段出现多次面部特写，必须有明确的炸点、受击或揭示理由，否则视为过度设计。\n"
        "11. 微细节镜头只用于关键信息，不用于堆砌存在感。手、嘴唇、眼角、袖口、鞋尖、发丝等局部如果不承载线索、动作前摇或受击结果，就不要单独给镜头。\n"
        "12. 一号 layout 阶段先决定主镜头覆盖骨架和粗景别：关系/中景负责空间和动作，中近景负责对白和反应，信息插入只给关键物件或文字，远景只在建立空间、权力关系或孤立感时使用。\n"
        "13. 二号 blocking 阶段再决定是否需要子镜头、反应镜头、OS/J-cut/L-cut、动作顶点前切和时长分配；长对白必须根据情绪压力切听者反应、过肩或景别变化，不能同一机位吃完整段。\n"
        "14. 镜头数施工尺：情绪铺垫/正常承接 1-2 个有效镜头；急促动作群/外部打断 2-4 个；信息揭示/关键物件 2-3 个；高压对白/冲突升级 2-4 个；情绪极点/停顿反应 1-2 个；短回忆/现实切层 1-3 个。\n"
        "15. 5-6秒片段一般不超过3个有效镜头，只有追逐、闯入、爆点连发可到4个；8-12秒片段一般2-4个；12-15秒若需要超过5个，应回报上游疑似粗拆，而不是硬塞更多镜头。\n"
        "16. 生活动作快节奏硬规则：赶时间、穿衣、接电话、孩子抗拒、哄劝等生活压力段，8-12秒优先3-4镜；不得拆出0.7秒/0.8秒的手、手机、脚、衣服碎插入。观众要看见同一动作关系连续变紧，而不是看剪辑碎片。\n"
        "17. 1秒以下镜头只允许用于关键信息揭示、突发危险、动作命中或必须读清的关键道具；同一片段出现两个以上1秒以下镜头，默认判为过碎，必须合并到主关系镜头或改成切镜时机。\n"
    )

def _shortdrama_master_rules() -> str:
    """6条短剧样片核心规则，来自94集短剧深度分析报告（RULE-SHORTDRAMA-* 系列）。"""
    return (
        "【RULE-SHORTDRAMA-MS-FIRST · 主骨架优先规则】\n"
        "适用：9:16 竖屏短剧、对白场景、双人冲突、群体对峙、权力压迫。\n"
        "执行：每个 fragment 的第一个镜头必须优先建立人物距离和空间方向，"
        "默认使用 MS/半身/关系镜头作为主骨架，确认空间关系后再切近景。\n"
        "禁止：禁止一上来就用整脸特写（ECU/CU）替代空间关系建立。\n"
        "禁止：禁止连续 CU 承载完整对白，禁止让对手和空间在特写后消失。\n\n"

        "【RULE-CU-MUST-BE-RELATION-WRAPPED · 特写包裹规则】\n"
        "适用：信息炸点、受击反应、情绪顶点、短促震动。\n"
        "执行：CU/ECU 前后至少有一个关系镜头（MS/中景/双人关系景）作为缓冲，"
        "或在 CU 内明确 companion_visibility（前景肩线、门框、桌边、人物边缘）。\n"
        "禁止：禁止连续 CU 承载完整对白，禁止让对手和空间在特写后消失。\n"
        "禁止：禁止在一个 fragment 内出现超过 1 次无包裹的纯特写。\n\n"

        "【RULE-CUT-REASON-INFORMATIONAL · 切镜信息理由规则】\n"
        "适用：所有 main_shot 与 sub_shot 的 transition_type 切换。\n"
        "执行：cut_reason 必须回答「为什么必须在这里切」，"
        "有效理由包括：主体变化、动作顶点前、台词断点、信息看清、视线锚点、"
        "空间复位、受击反应、尾帧交接。\n"
        "禁止：禁止写「更有电影感」「更好看」「想看表情」「丰富画面」「有张力」「有压迫感」。\n"
        "禁止：cut_reason 写成空泛形容词或情绪标签，必须是具体信息状态变化。\n\n"

        "【RULE-ACTION-INSERT-BELONGS-TO-26 · 局部动作归属规则】\n"
        "适用：手部、道具、按钮、门缝、衣角、法术、文件、手机、车门、电梯门。\n"
        "执行：局部动作默认由 sub_shot 承担，必须绑定 parent_shot_id；"
        "action_insert_slot 属于 sub_shot 范畴，不能独立于父镜头存在。\n"
        "禁止：禁止把局部动作（手/门缝/按钮/文件）随意升级为平级 main_shot 的主体，"
        "除非该道具本身就是当前剧本事件的唯一主体（如：展示文件的特写镜头）。\n"
        "禁止：sub_shot 不能重新建场（不能写 space_rules 或 continuity_anchor）。\n\n"

        "【RULE-THRESHOLD-STATE-CHAIN · 阈值状态单向链规则】\n"
        "适用：电梯、门、车门、走廊、入口、上车下车、进入房间、离开通道。\n"
        "执行：阈值动作必须建立单向状态链，状态只能单向推进，例如：\n"
        "  「可进入 → 人进入 → 门开始合拢 → 门缝未闭合 → 门完全关闭」\n"
        "每个状态变化必须在前一状态基础上推进，禁止跳跃。\n"
        "禁止：禁止门关上又重新打开、人物切镜后跳位、前一镜头已完成动作后一镜头从头做。\n"
        "禁止：电梯门状态不能写「门已关上」后又在下一镜头出现「门缝」。\n\n"

        "【RULE-GROUP-BEAT-RELATION-RESET · 群体节拍关系复位规则】\n"
        "适用：员工让路、主管散开、保镖包围、众人围观、多人施压。\n"
        "执行：群体动作必须用关系镜头（MS/中景/双人关系景/场景固定机位）承接；"
        "单人反应之后必须回到关系景确认站位变化和空间结果。\n"
        "禁止：禁止用单人大头（ECU/CU）承接群体散开或空间变化。\n"
        "禁止：群体让路后如果空间关系改变（如通道打开），必须有一个镜头展示整体关系，"
        "不能停在单个人物特写上。\n"
    )


def _clean_shot_director_output(text: str) -> str:
    """Strip thinking/prose wrappers and keep the YAML payload."""
    if not text:
        return ""
    cleaned = re.sub(r"(?is)<thinking>.*?</thinking>", "", text).strip()
    fence_match = re.search(r"(?is)```(?:yaml|yml)?\s*(.*?)```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    lines = cleaned.splitlines()
    while lines and not re.match(_fragment_line_pattern(), lines[0].strip(), re.IGNORECASE):
        lines.pop(0)
    return "\n".join(lines).strip()

def _is_closeup_shot_size(value: str) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return False

    # Do not classify medium-close vocabulary as close-up just because it
    # contains the substring "cu" (for example, "MCU").
    medium_close_tokens = [
        "mcu",
        "medium close",
        "medium-close",
        "medium_close",
        "medium close-up",
        "medium-close-up",
        "medium_close_up",
        "中近景",
        "胸部以上",
    ]
    if any(token in normalized for token in medium_close_tokens):
        return False

    if re.search(r"\b(?:ecu|cu)\b", normalized):
        return True
    if re.search(r"\b(?:extreme[-_ ]?)?close[-_ ]?up\b", normalized):
        return True
    return bool(re.search(r"极特写|大特写|脸部特写|手部特写|眼部特写|特写镜头|^特写$", normalized))

def _script_character_names(script: str) -> set[str]:
    names: set[str] = set()
    for line in (script or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("人物"):
            continue
        _, _, value = stripped.partition("：")
        if not value:
            _, _, value = stripped.partition(":")
        for item in re.split(r"[、,，/]", value):
            name = item.strip()
            if name:
                names.add(name)
    return names

def _has_medium_or_relation_shot(value: str) -> bool:
    normalized = (value or "").strip().lower()
    keeper_tokens = [
        "medium",
        "medium shot",
        "ms",
        "mcu",
        "medium close",
        "medium-close",
        "medium_close",
        "waist",
        "half",
        "two shot",
        "two-shot",
        "two_shot",
        "full",
        "wide",
        "半身",
        "中景",
        "中近景",
        "双人",
        "全景",
        "远景",
    ]
    return any(token in normalized for token in keeper_tokens)

def _is_micro_detail_subject(value: str) -> bool:
    return bool(
        re.search(
            r"掌心|指尖|指节|手背|手腕|袖口|鞋尖|嘴唇|唇角|眼角|睫毛|发丝|下颌|喉结|衣角",
            value or "",
        )
    )

def _validate_shot_director_script_fidelity(director_output: str, script: str) -> list[str]:
    issues: list[str] = []
    if not director_output or not script:
        return issues

    risky_inventions = [
        "伴侣",
        "丈夫",
        "男友",
        "床",
        "床尾",
        "睡颜",
        "睡眠",
        "睁眼",
        "仰卧",
        "枕头",
        "被褥",
        "车内",
        "车窗",
        "座位",
        "保镖",
        "记者",
        "闪光灯",
        "鞠躬",
    ]
    for term in risky_inventions:
        if term in director_output and term not in script:
            issues.append(f"shot_director 疑似新增剧本外前提或元素：{term}")
            break

    if "把照片放到桌上" in script and re.search(r"塞回书包|攥进掌心|掌心|指尖|指节", director_output):
        issues.append("shot_director 改写了照片/书包连续性或使用了高歧义手部细节。")

    character_names = _script_character_names(script)
    if character_names:
        subject_values = re.findall(r"(?m)^\s*subject\s*:\s*[\"']?(.+?)[\"']?\s*$", director_output)
        for subject in subject_values:
            if "Sunny" in subject and "Sunny" not in character_names:
                issues.append("shot_director 把 OS/台词里的 Sunny 当成画面主体，未继承人物行中的角色名。")
                break

    return issues

def _validate_shot_director_vertical_discipline(director_output: str, aspect_ratio: str) -> list[str]:
    if "9:16" not in (aspect_ratio or ""):
        return []

    issues: list[str] = []
    for section in _extract_yaml_sections(director_output):
        fragment_id = _extract_fragment_id(section) or "unknown"
        shot_sizes = re.findall(
            r'(?mi)^\s*(?:shot|shot_size|size)\s*:\s*["\']?([^"\n#]+?)["\']?\s*$',
            section,
        )
        subjects = re.findall(
            r'(?mi)^\s*subject\s*:\s*["\']?([^"\n#]+?)["\']?\s*$',
            section,
        )
        if not shot_sizes:
            continue

        closeup_count = sum(1 for item in shot_sizes if _is_closeup_shot_size(item))
        medium_or_relation_count = sum(1 for item in shot_sizes if _has_medium_or_relation_shot(item))
        micro_subject_count = sum(1 for item in subjects if _is_micro_detail_subject(item))

        if len(shot_sizes) >= 2 and closeup_count == len(shot_sizes):
            issues.append(f"{fragment_id} 在 9:16 里全部使用特写类景别，缺少半身/中景/关系镜头缓冲。")

        if closeup_count > 1:
            issues.append(f"{fragment_id} 在 9:16 里出现多次面部特写，特写使用过密。")

        if len(shot_sizes) >= 2 and medium_or_relation_count == 0:
            issues.append(f"{fragment_id} 在 9:16 里缺少半身/中景/双人关系景别作为主力镜头。")

        if micro_subject_count > 1:
            issues.append(f"{fragment_id} 给多个微细节局部单独开镜头，超出 9:16 竖屏所需的信息密度。")

    return issues

def _validate_shot_director_source_event_coverage(director_output: str, planner_output: str) -> list[str]:
    issues: list[str] = []
    if not director_output or not planner_output:
        return issues

    planner_sections = _extract_yaml_sections(planner_output)
    for planner_section in planner_sections:
        fragment_id = _extract_fragment_id(planner_section)
        if not fragment_id:
            continue
        director_block = _segment_block(director_output, int(fragment_id[1:]) if fragment_id[1:].isdigit() else 0)
        if not director_block:
            continue
        source_events = [
            event
            for event in _source_script_events(planner_section)
            if event and not event.startswith("人物") and not re.match(r"^\d+-\d+", event)
        ]
        active_cast = _extract_nested_list_items(planner_section, "cast", "active")
        if not active_cast:
            active_cast = _extract_top_level_list_items(planner_section, "出现人物")
        required_terms: list[str] = []
        for term in active_cast:
            cleaned = term.strip().strip("\"'")
            if cleaned and len(cleaned) <= 12 and cleaned not in required_terms:
                required_terms.append(cleaned)
        object_terms: set[str] = set()
        object_pattern = re.compile(
            r"门口|车门|电梯门|房门|门边|桌上|桌边|桌|背包|书包|包|照片|文件|合同|手机|钥匙|杯子|咖啡杯|车|车辆|座椅|沙发|床|窗边|窗"
        )
        for event in source_events:
            object_terms.update(object_pattern.findall(event))
        for term in sorted(object_terms, key=len, reverse=True):
            if term not in required_terms:
                required_terms.append(term)
        missing_terms: list[str] = []
        for event in source_events:
            for term in required_terms:
                if term in event and term not in director_block and term not in missing_terms:
                    missing_terms.append(term)
        if missing_terms:
            issues.append(f"{fragment_id} 未覆盖 source_script_events 中的关键人物/道具：{', '.join(missing_terms[:5])}")
    return issues

def _segment_block(text: str, segment_index: int) -> str:
    fragment_id = f"F{segment_index:02d}"
    match = re.search(
        rf"(?m)(^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F\d+|\Z)",
        text,
    )
    return match.group(1).strip() if match else ""

_MAIN_SHOT_BLOCK_RE = re.compile(
    r"(?ms)^\s*-\s*(?:shot_id|镜头编号)\s*:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$"
    r"([\s\S]*?)(?=^\s*-\s*(?:shot_id|镜头编号)\s*:|^\s*(?:sub_shots|子镜头|子镜头列表)\s*:|^\s*-\s*(?:fragment_id|片段编号)\s*:|\Z)"
)

def _main_shot_blocks(output: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for match in _MAIN_SHOT_BLOCK_RE.finditer(output or ""):
        blocks.append((match.group(1).strip(), match.group(0)))
    return blocks

def _fragment_line_pattern() -> str:
    return r"^-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F[\w-]+[\"']?"

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


def _shot_yaml_field_names(field: str) -> tuple[str, ...]:
    return _SHOT_YAML_FIELD_ALIASES.get(field, (field,))


def _shot_yaml_field_pattern(field: str) -> str:
    return "|".join(re.escape(name) for name in _shot_yaml_field_names(field))


def _has_shot_yaml_field(block: str, field: str) -> bool:
    return bool(re.search(rf"(?m)^\s*-?\s*(?:{_shot_yaml_field_pattern(field)})\s*:", block or ""))


def _fragment_ids_from_validation_issues(issues: list[str], expected_segments: list[str]) -> list[str]:
    """Return only fragment ids implicated by validation issues.

    This keeps shot_director repair scoped to the failed/missing fragments instead
    of rewriting already valid split-by-fragment output.
    """
    ordered_expected: list[str] = []
    for segment_name in expected_segments:
        segment_num = re.sub(r"\D", "", segment_name or "")
        fragment_id = f"F{int(segment_num):02d}" if segment_num else (segment_name or "").strip()
        if fragment_id and fragment_id not in ordered_expected:
            ordered_expected.append(fragment_id)

    failed: list[str] = []
    for issue in issues:
        for fragment_id in re.findall(r"\bF\d{2,}\b", issue or ""):
            if fragment_id not in failed:
                failed.append(fragment_id)

    return [fragment_id for fragment_id in ordered_expected if fragment_id in failed] or failed


def _filter_yaml_sections_by_fragment_ids(yaml_text: str, fragment_ids: list[str]) -> str:
    if not fragment_ids:
        return yaml_text
    wanted = set(fragment_ids)
    sections = [section for section in _extract_yaml_sections(yaml_text or "") if _extract_fragment_id(section) in wanted]
    return "\n\n".join(section.strip() for section in sections if section.strip()).strip()


def _merge_repaired_yaml_sections(original_yaml: str, repaired_yaml: str, fragment_ids: list[str]) -> str:
    """Patch only repaired fragment sections back into the original YAML."""
    if not fragment_ids:
        return repaired_yaml or original_yaml
    wanted = set(fragment_ids)
    original_sections = _extract_yaml_sections(original_yaml or "")
    repaired_by_id = {
        _extract_fragment_id(section): section.strip()
        for section in _extract_yaml_sections(repaired_yaml or "")
        if _extract_fragment_id(section) in wanted
    }
    merged: list[str] = []
    seen: set[str] = set()
    for section in original_sections:
        fragment_id = _extract_fragment_id(section)
        if fragment_id in repaired_by_id:
            merged.append(repaired_by_id[fragment_id])
            seen.add(fragment_id)
        else:
            merged.append(section.strip())
    for fragment_id in fragment_ids:
        if fragment_id in repaired_by_id and fragment_id not in seen:
            merged.append(repaired_by_id[fragment_id])
    return "\n\n".join(section for section in merged if section).strip()

def _field_value(section: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:\s*[\"']?(.+?)[\"']?\s*$", section)
    return match.group(1).strip() if match else ""

def _field_value_any(section: str, *fields: str) -> str:
    for field in fields:
        value = _field_value(section, field)
        if value:
            return value
    return ""

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

def _seconds_from_duration_text(value: str) -> float | None:
    text = (value or "").strip().strip("\"'")
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|~|–|—)\s*(\d+(?:\.\d+)?)\s*(?:秒|s)?",
        text,
        re.IGNORECASE,
    )
    if range_match:
        start = float(range_match.group(1))
        end = float(range_match.group(2))
        if end > start:
            return end - start
        return end
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:秒|s)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _shot_density_limit(section: str, total_seconds: float | None) -> int:
    context = section or ""
    life_pressure = bool(_SHOT_DENSITY_LIFE_PRESSURE_RE.search(context))
    high_cut_need = bool(_SHOT_DENSITY_HIGH_CUT_RE.search(context))
    if total_seconds is None:
        return 4 if life_pressure and not high_cut_need else 5
    if total_seconds <= 6:
        return 3
    if total_seconds <= 12.5:
        return 4 if life_pressure and not high_cut_need else 5
    if total_seconds <= 15.5:
        return 5
    return 6


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "未知时长"
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded)}秒"
    return f"{rounded:.1f}秒"


def _validate_shot_director_density(
    fragment_id: str,
    section: str,
    shot_blocks: list[tuple[str, str]],
) -> list[str]:
    if not shot_blocks:
        return []
    durations: list[tuple[str, float]] = []
    for shot_id, shot_block in shot_blocks:
        seconds = _seconds_from_duration_text(_yaml_line_field(shot_block, "duration"))
        if seconds is not None:
            durations.append((shot_id, seconds))

    total_seconds = sum(seconds for _shot_id, seconds in durations) if durations else None
    shot_count = len(shot_blocks)
    limit = _shot_density_limit(section, total_seconds)
    issues: list[str] = []
    if shot_count > limit:
        issues.append(
            f"{fragment_id} 镜头切分过碎：{_format_seconds(total_seconds)}安排{shot_count}个镜头，"
            f"当前节奏类型建议不超过{limit}个有效镜头；快节奏应优先靠人物动作紧张、停顿缩短和情绪压力，不靠碎切。"
        )

    short_shots = [(shot_id, seconds) for shot_id, seconds in durations if seconds < 1.0]
    life_pressure = bool(_SHOT_DENSITY_LIFE_PRESSURE_RE.search(section or ""))
    high_cut_need = bool(_SHOT_DENSITY_HIGH_CUT_RE.search(section or ""))
    if short_shots and (len(short_shots) >= 2 or (life_pressure and not high_cut_need)):
        short_text = "、".join(f"{shot_id}={seconds:.1f}秒" for shot_id, seconds in short_shots[:4])
        issues.append(
            f"{fragment_id} 出现1秒以下碎镜（{short_text}）。生活动作/正常动作段不得把手、手机、脚、衣服等局部动作拆成碎插入；"
            "请合并进关系镜头，或只把真正的信息揭示/危险命中保留为短镜。"
        )
    return issues

def _truncate_for_prompt(text: str, limit: int = 12000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n...[已截断，仅保留前文供修复参考]..."

def _runtime_context_contract_card() -> str:
    return (
        "【运行上下文合同】\n"
        "- 结构规划保留原始剧本作为逐字引用来源；其他阶段不要重新理解全剧本。\n"
        "- 摆位只负责镜头机位骨架，不承担剧本理解、情绪设计、动作调度或身份锁定。\n"
        "- 调度、守门和提示词编译只使用当前片段资产和当前镜头资产，避免被其他片段带偏。\n"
        "- 参考图只负责身份/空间锚定；人物形象细节不需要在最终提示词中重复展开。\n"
        "- 如果人物面朝电梯且镜头写正面，电梯门框只能是前景边缘/左右侧边缘，不能写成后景。"
    )

def _is_local_insert_subject(value: str) -> bool:
    return bool(re.search(r"手|手部|门缝|按钮|文件|手机|衣角|车门|电梯门|照片|道具", value or ""))


def _shot_field_has_untranslated_camera_jargon(value: str) -> bool:
    return bool(_SHOT_FINAL_CAMERA_JARGON_RE.search(value or ""))


def _split_shot_subject_tokens(subject: str) -> list[str]:
    tokens: list[str] = []
    for item in _SHOT_SUBJECT_SPLIT_RE.split(subject or ""):
        token = item.strip().strip("\"'“”‘’ ")
        if token:
            tokens.append(token)
    return tokens


def _shot_subject_ownership_issues(shot_id: str, shot_block: str) -> list[str]:
    subject = _yaml_line_field(shot_block, "subject")
    if not subject:
        return []
    tokens = _split_shot_subject_tokens(subject)
    task_text = " ".join(
        _yaml_line_field(shot_block, field)
        for field in ("task", "action", "must_carry", "cut_point")
    )
    prop_tokens = [token for token in tokens if _SHOT_PROP_SUBJECT_RE.search(token)]
    allows_prop_subject = bool(_SHOT_PROP_AS_SUBJECT_ALLOWED_RE.search(task_text))
    is_group_subject = bool(_SHOT_GROUP_SUBJECT_RE.search(subject))

    issues: list[str] = []
    if len(tokens) >= 5:
        issues.append(
            f"{shot_id} 拍摄主体过载：{subject}。"
            "拍摄主体不是人物/道具清单，只能写本镜观众注意力主焦点；其他道具写进必须承载或连续性。"
        )
    if prop_tokens and len(tokens) >= 3 and not allows_prop_subject and not is_group_subject:
        issues.append(
            f"{shot_id} 把道具混进主拍摄主体：{subject}。"
            "道具只有承担信息揭示、关键线索或动作结果时才能成为主体；生活动作道具应留在画面动作/连续性里。"
        )
    if len(prop_tokens) >= 2 and not allows_prop_subject:
        issues.append(
            f"{shot_id} 拍摄主体像随机道具集合：{subject}。"
            "请先判断本镜戏剧任务，再选择人物、双人关系或唯一关键物作为主体。"
        )
    return issues


def _shot_tailframe_carry_issues(fragment_id: str, shot_blocks: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for index, (shot_id, shot_block) in enumerate(shot_blocks):
        if index == 0:
            continue
        action = _yaml_line_field(shot_block, "action")
        continuity = _yaml_line_field(shot_block, "continuity")
        combined = " ".join([action, continuity])
        has_teleport_marker = bool(re.search(r"突然|已经", action or ""))
        if (
            _SHOT_SPATIAL_STATE_JUMP_RE.search(action or "")
            and not _SHOT_CONTINUITY_INHERIT_RE.search(combined)
            and (has_teleport_marker or not _SHOT_VISIBLE_TRANSITION_RE.search(action or ""))
        ):
            issues.append(
                f"{fragment_id}/{shot_id} 缺少承接上一镜尾帧：人物位置、坐站、穿戴或道具状态发生跳变，"
                "但本镜没有写清从上一镜如何进入当前状态。"
            )
    return issues


def _validate_shot_director_output(director_output: str, expected_segments: list[str]) -> list[str]:
    """Validate shot_director v1 schema.

    V1 规则：
    1. fragment 必须有 fragment_task、rhythm、shots
    2. 每个 shot 必须有 shot_id、duration、task、subject、shot、action、dialogue、must_carry、cut_point、continuity
    3. 可选字段 type、audio 只在需要时写
    4. 首镜头不能用特写类景别建立空间
    """
    if _uses_construction_sheet_schema(director_output):
        return _validate_shot_director_construction_sheet(director_output, expected_segments)

    issues: list[str] = []
    for segment_name in expected_segments:
        segment_num = re.sub(r"\D", "", segment_name)
        fragment_id = f"F{int(segment_num):02d}" if segment_num else segment_name
        block_match = re.search(
            rf"(?m)(^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
            rf"(?=\n\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F\d+|\Z)",
            director_output,
        )
        if not block_match:
            issues.append(f"shot_director 缺少 {fragment_id} 的镜头设计。")
            continue
        block = block_match.group(1)

        # V1 fragment 必填字段
        for field in _SHOT_CONSTRUCTION_FRAGMENT_FIELDS:
            if not _has_shot_yaml_field(block, field):
                issues.append(f"{fragment_id} 缺少片段字段 {_shot_yaml_field_names(field)[-1]}。")

        shot_blocks = _main_shot_blocks(block)
        if not shot_blocks:
            issues.append(f"{fragment_id} 缺少 shots 字段或没有任何 shot_id。")
            continue
        issues.extend(_validate_shot_director_density(fragment_id, block, shot_blocks))
        issues.extend(_shot_tailframe_carry_issues(fragment_id, shot_blocks))

        first_shot_id, first_shot_block = shot_blocks[0]
        first_shot_size = (
            _yaml_line_field(first_shot_block, "shot")
            or _yaml_line_field(first_shot_block, "size")
            or _yaml_line_field(first_shot_block, "shot_size")
        )
        if _is_closeup_shot_size(first_shot_size):
            issues.append(
                f"{fragment_id} 的首镜头 {first_shot_id} 直接使用特写类景别。"
                "短剧主骨架必须先用半身/中景/关系镜头建立人物距离和空间方向。"
            )

        for shot_id, shot_block in shot_blocks:
            for field in _SHOT_CONSTRUCTION_REQUIRED_FIELDS:
                if not _has_shot_yaml_field(shot_block, field):
                    issues.append(f"{shot_id} 缺少必要字段 {_shot_yaml_field_names(field)[-1]}。")

            shot_text = _yaml_line_field(shot_block, "shot")
            if _shot_field_has_untranslated_camera_jargon(shot_text):
                issues.append(
                    f"{shot_id} 的镜头字段仍含未翻译机位术语：{shot_text}。"
                    f"{_SHOT_VIEWPOINT_TRANSLATION_HINT}"
                )

            cut_point = _yaml_line_field(shot_block, "cut_point")
            if cut_point and (
                _GENERIC_CUT_REASON_RE.search(cut_point)
                or not _SHOT_CUT_TRIGGER_RE.search(cut_point)
            ):
                issues.append(f"{shot_id} 的 cut_point 过于空泛，必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。")

            subject = _yaml_line_field(shot_block, "subject")
            task = _yaml_line_field(shot_block, "task")
            issues.extend(_shot_subject_ownership_issues(shot_id, shot_block))
            has_parent_shot = bool(re.search(r"^\s*(?:parent_shot_id|父镜头编号)\s*:", shot_block, re.MULTILINE))
            is_sub_shot_id = bool(re.search(r"(?:[-_][A-Za-z]|S\d+[A-Za-z])$", shot_id or ""))
            if (
                _is_local_insert_subject(subject)
                and not has_parent_shot
                and not is_sub_shot_id
                and not re.search(r"唯一主体|文件内容|信息揭示|关键物|证据|屏幕|照片", task)
            ):
                issues.append(
                    f"{shot_id} 把局部动作/局部道具（{subject}）升级成了主镜头主体。"
                    "手部、门缝、按钮、文件、手机等默认应作为 insert/reaction 子镜头。"
                )

    return issues


_CONSTRUCTION_SHEET_SHOT_FIELDS = (
    "shot_id",
    "subject",
    "shot_size",
    "camera_height",
    "angle",
    "movement",
    "lens",
    "depth",
    "coverage_role",
    "cut_reason",
    "companion_visibility",
    "tailframe_role",
    "dialogue_coverage",
    "transition_type",
    "tail_state_card",
)

_CONSTRUCTION_SHEET_TRANSITIONS = {
    "stay_on_A",
    "cut_to_B",
    "cut_back_to_A",
    "scene_fixed",
    "insert",
    "cutaway",
    "tailframe_reset",
}


def _uses_construction_sheet_schema(output: str) -> bool:
    return bool(
        re.search(r"(?m)^\s*schema_version\s*:\s*shot_director_v2\b", output or "")
        or re.search(r"(?m)^\s*fragment_intent\s*:", output or "")
        or re.search(r"(?m)^\s*tail_state_card\s*:", output or "")
        or re.search(r"(?m)^\s*transition_type\s*:", output or "")
    )


def _validate_shot_director_construction_sheet(director_output: str, expected_segments: list[str]) -> list[str]:
    issues: list[str] = []
    vague_cut_reason_re = re.compile(
        r"更有电影感|更有電影感|cinematic|looks good|more cinematic|高级|好看|氛围更强|情绪更强|鐢靛奖鎰?",
        re.IGNORECASE,
    )
    for segment_name in expected_segments:
        segment_num = re.sub(r"\D", "", segment_name)
        fragment_id = f"F{int(segment_num):02d}" if segment_num else segment_name
        block_match = re.search(
            rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
            rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)",
            director_output or "",
        )
        if not block_match:
            issues.append(f"shot_director 缺少 {fragment_id} 的镜头设计。")
            continue
        fragment_block = block_match.group(1)
        for field in ("fragment_intent", "reaction_coverage", "continuity_anchor", "shots"):
            if not re.search(rf"(?m)^\s*{field}\s*:", fragment_block):
                issues.append(f"{fragment_id} 缺少 construction sheet 字段 {field}。")

        shot_blocks = _main_shot_blocks(fragment_block)
        if not shot_blocks:
            issues.append(f"{fragment_id} 缺少 shots 字段或没有任何 shot_id。")
            continue
        for shot_id, shot_block in shot_blocks:
            for field in _CONSTRUCTION_SHEET_SHOT_FIELDS:
                if not re.search(rf"(?m)^\s*-?\s*{field}\s*:", shot_block):
                    issues.append(f"{shot_id} 缺少 construction sheet 字段 {field}。")
            transition_type = _yaml_line_field(shot_block, "transition_type").strip().strip('"\'')
            if transition_type and transition_type not in _CONSTRUCTION_SHEET_TRANSITIONS:
                issues.append(f"{shot_id} transition_type 非法：{transition_type}。")
            cut_reason = _yaml_line_field(shot_block, "cut_reason")
            if vague_cut_reason_re.search(cut_reason or ""):
                issues.append(f"{shot_id} cut_reason 过于空泛，必须绑定信息、反应、动作路径、空间复位或尾帧交接。")
    return issues

def _yaml_scalar_field(block: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*(?:{_shot_yaml_field_pattern(field)})\s*:\s*[\"']?([^\"'\n#]+)", block or "")
    return match.group(1).strip() if match else ""

def _yaml_line_field(block: str, field: str) -> str:
    match = re.search(rf"(?m)^(\s*)-?\s*(?:{_shot_yaml_field_pattern(field)})\s*:\s*(.+?)\s*$", block or "")
    if not match:
        return ""
    value = match.group(2).strip().strip("\"'")
    if value not in {">", "|", ">-", "|-", ">+", "|+"}:
        return value

    base_indent = len(match.group(1).replace("\t", "    "))
    lines = (block or "")[match.end():].splitlines()
    folded: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        indent = len(line[: len(line) - len(line.lstrip())].replace("\t", "    "))
        if indent <= base_indent and re.match(r"^\s*-?\s*[^:\n]{1,40}\s*:", line):
            break
        if indent > base_indent:
            folded.append(line.strip())
            continue
        break
    return " ".join(folded).strip()

def _dialogue_listener_for_subject(subject: str, script: str) -> str:
    names = _primary_script_character_names(script)
    if len(names) < 2:
        return "听者"
    subject_text = subject or ""
    if names[0] in subject_text:
        return names[1]
    if names[1] in subject_text:
        return names[0]
    if re.search(r"商北琛|Nash|Mr\.?\s*Pierce", subject_text, re.IGNORECASE):
        return names[0]
    if re.search(r"乔熙|Sunny", subject_text, re.IGNORECASE):
        return names[1]
    return names[0]

def _repair_shot_director_main_shot_contract_block(block: str, script: str) -> str:
    names = _primary_script_character_names(script)
    if len(names) >= 2:
        subject = _yaml_line_field(block, "subject")
        if re.search(r"\bSunny\b", subject) and names[0] != "Sunny":
            block = _replace_yaml_scalar_field(block, "subject", re.sub(r"\bSunny\b", names[0], subject))
        subject = _yaml_line_field(block, "subject")
        if re.search(r"\b(?:Nash|Mr\.?\s*Pierce)\b", subject) and names[1] not in {"Nash", "Mr. Pierce"}:
            block = _replace_yaml_scalar_field(
                block,
                "subject",
                re.sub(r"\b(?:Nash|Mr\.?\s*Pierce)\b", names[1], subject),
            )

    coverage = _yaml_line_field(block, "dialogue_coverage")
    if _dialogue_coverage_needs_visual_break(coverage) and not _has_dialogue_coverage_visual_break(coverage):
        listener = _dialogue_listener_for_subject(_yaml_line_field(block, "subject"), script)
        repaired = (
            f"{coverage}；切{listener}中近景听者反应/反打，保留对手肩线或桌边作为空间锚点；"
            f"后半句以画外音/OS/L-cut落在{listener}反应上，必要时切回说话者。"
        )
        block = _replace_yaml_scalar_field(block, "dialogue_coverage", repaired)
    return block

def _repair_shot_director_contract_output(output: str, script: str) -> str:
    if not output:
        return output

    def repl(match: re.Match[str]) -> str:
        return _repair_shot_director_main_shot_contract_block(match.group(0), script)

    return _MAIN_SHOT_BLOCK_RE.sub(repl, output)

def _script_scene_heading(script: str) -> str:
    for raw_line in (script or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("人物"):
            continue
        if "：" in line or ":" in line:
            continue
        if re.search(r"内|外|夜|日|车内|办公室|电梯|门口|走廊|大堂", line):
            return line
    return ""


def _fragment_subject_names(section: str, script: str) -> list[str]:
    names = _primary_script_character_names(script)
    found = [name for name in names if name and name in section]
    if found:
        return found

    subjects: list[str] = []
    for _shot_id, shot_block in _main_shot_blocks(section):
        subject = _yaml_line_field(shot_block, "subject")
        for item in re.split(r"[、,，/和\s]+", subject or ""):
            item = item.strip().strip("\"'")
            if not item or item in {"人物名", "双人关系", "当前人物", "剧本已有道具"}:
                continue
            if item not in subjects:
                subjects.append(item)
    return subjects[:4]


def _infer_fragment_continuity_context(section: str, script: str) -> str:
    task = _yaml_line_field(section, "fragment_task") or "连续戏剧任务"
    subjects = _fragment_subject_names(section, script)
    subject_text = "、".join(subjects) if subjects else "本片段人物"
    scene_heading = _script_scene_heading(script)
    scene_text = f"在{scene_heading}的同一空间内" if scene_heading else "在同一空间内"
    return (
        f"本片段是一段{task}；{subject_text}{scene_text}完成这一段动作和对白；"
        "单人镜只改变拍摄主体，不代表其他在场人物离开；"
        "每一镜继承上一镜尾帧的人物位置、道具状态、视线方向和同侧轴线。"
    )


def _quote_yaml_scalar(value: str) -> str:
    return '"' + (value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def _insert_fragment_continuity_context(section: str, script: str) -> str:
    if _has_shot_yaml_field(section, "continuity_context"):
        return section

    lines = section.splitlines()
    if not lines:
        return section

    first_is_fragment_header = bool(re.match(r"^\s*-\s*(?:fragment_id|片段编号)\s*:", lines[0]))
    insert_after = 1 if first_is_fragment_header else 0
    indent = "  " if first_is_fragment_header else ""
    for index, line in enumerate(lines):
        if re.match(r"^\s*(?:rhythm|节奏)\s*:", line):
            insert_after = index + 1
            indent = re.match(r"^(\s*)", line).group(1)
            break
        if re.match(r"^\s*(?:fragment_task|片段任务)\s*:", line):
            insert_after = index + 1
            indent = re.match(r"^(\s*)", line).group(1)

    value = _infer_fragment_continuity_context(section, script)
    lines.insert(insert_after, f"{indent}空间连续性总控: {_quote_yaml_scalar(value)}")
    return "\n".join(lines)


def _repair_fragment_continuity_contexts(output: str, script: str) -> str:
    sections = _extract_yaml_sections(output or "")
    if not sections:
        return output
    return "\n\n".join(_insert_fragment_continuity_context(section, script) for section in sections)

_SHOT_DIRECTOR_CHINESE_FIELD_NAMES: tuple[tuple[str, str], ...] = (
    ("fragment_id", "片段编号"),
    ("fragment_task", "片段任务"),
    ("fragment_intent", "片段意图"),
    ("rhythm", "节奏"),
    ("continuity_context", "空间连续性总控"),
    ("segment_continuity", "空间连续性总控"),
    ("fallback_mode", "兜底模式"),
    ("fallback_reason", "兜底原因"),
    ("space_rules", "空间规则"),
    ("space_anchors", "空间锚点"),
    ("character_positions", "人物位置"),
    ("action_axis", "动作轴线"),
    ("safe_camera_zones", "安全机位区"),
    ("blocked_camera_zones", "禁用机位区"),
    ("shots", "镜头列表"),
    ("main_shots", "主镜头列表"),
    ("sub_shots", "子镜头列表"),
    ("shot_id", "镜头编号"),
    ("parent_shot_id", "父镜头编号"),
    ("duration", "时长"),
    ("duration_hint", "时长建议"),
    ("task", "镜头任务"),
    ("subject", "拍摄主体"),
    ("shot", "镜头"),
    ("camera", "机位"),
    ("size", "景别"),
    ("shot_size", "景别"),
    ("camera_height", "机位高度"),
    ("camera_angle", "拍摄角度"),
    ("angle", "拍摄角度"),
    ("movement", "运镜"),
    ("camera_movement", "运镜"),
    ("lens", "焦段"),
    ("depth", "景深"),
    ("action", "画面动作"),
    ("dialogue", "台词"),
    ("must_carry", "必须承载"),
    ("cut_point", "切镜点"),
    ("continuity", "连续性"),
    ("type", "类型"),
    ("audio", "声音"),
    ("coverage_role", "覆盖职责"),
    ("cut_reason", "切镜原因"),
    ("companion_visibility", "同场人物位置"),
    ("state_delta", "状态变化"),
    ("tailframe_role", "尾帧职责"),
    ("tailframe_reset", "尾帧复位"),
    ("dialogue_coverage", "对白覆盖"),
    ("reaction_coverage", "反应覆盖"),
    ("attention_target", "注意目标"),
    ("information_strategy", "信息策略"),
    ("selection_reason", "选择理由"),
    ("rejected_alternatives", "放弃方案"),
    ("shot_intent", "镜头意图"),
    ("transition_type", "转场类型"),
    ("trigger", "触发点"),
    ("beat_purpose", "节拍目的"),
    ("emotion_anchor", "情绪锚点"),
    ("action_phase", "动作阶段"),
    ("camera_basis", "机位依据"),
    ("camera_scene_position", "场景机位位置"),
    ("camera_looks_toward", "镜头朝向"),
    ("subject_position", "主体位置"),
    ("subject_facing", "主体朝向"),
    ("visible_landmarks", "可见地标"),
)

_SHOT_DIRECTOR_TEXT_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bshot_director_local_fallback_v1\b"), "镜头导演本地兜底"),
    (re.compile(r"\bLocal fallback from approved story-planner events:\s*", re.IGNORECASE), "根据已批准结构规划事件本地兜底："),
    (re.compile(r"\bFollow upstream rhythm; keep each shot to one readable action\.", re.IGNORECASE), "遵循上游节奏；每个镜头只承载一个可读动作。"),
    (re.compile(r"\bEstablish the current beat and spatial relationship from:\s*", re.IGNORECASE), "建立当前节拍和空间关系："),
    (re.compile(r"\bCarry the reaction or next action from:\s*", re.IGNORECASE), "承接反应或下一动作："),
    (re.compile(r"\bvertical medium relationship shot\b", re.IGNORECASE), "竖屏中景关系镜头"),
    (re.compile(r"\bmedium close relationship shot\b", re.IGNORECASE), "中近景关系镜头"),
    (re.compile(r"\bmedium relationship shot\b", re.IGNORECASE), "中景关系镜头"),
    (re.compile(r"\bstable camera\b", re.IGNORECASE), "固定机位"),
    (re.compile(r"\bclear blocking\b", re.IGNORECASE), "调度清晰"),
    (re.compile(r"\bsame screen direction\b", re.IGNORECASE), "保持同一画面方向"),
    (re.compile(r"\bafter the first readable action lands\b", re.IGNORECASE), "第一个可读动作落下后"),
    (re.compile(r"\bpreserve established positions, props and eye-lines from the approved upstream plan\b", re.IGNORECASE), "保留已批准上游方案中的站位、道具和视线关系"),
    (re.compile(r"\bafter the reaction or information beat is visible\b", re.IGNORECASE), "反应或信息节拍可见后"),
    (re.compile(r"\bend on a readable tail frame for the next segment handoff\b", re.IGNORECASE), "以可读尾帧结束，交给下一片段"),
    (re.compile(r"\bviewer attention stays on\b", re.IGNORECASE), "观众注意力停留在"),
    (re.compile(r"\binformation strategy is\b", re.IGNORECASE), "信息策略是"),
    (re.compile(r"\bchoice supports\b", re.IGNORECASE), "选择服务于"),
    (re.compile(r"\bwhile preserving space/action/cut continuity\b", re.IGNORECASE), "同时保持空间、动作和切镜连续"),
)


def _translate_shot_director_english_contract_output(output: str) -> str:
    """Translate legacy English shot-director fields and fallback phrases to Chinese."""
    if not output:
        return output
    translated = output
    for english, chinese in sorted(_SHOT_DIRECTOR_CHINESE_FIELD_NAMES, key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(
            rf"(?m)^(\s*-?\s*){re.escape(english)}(\s*:)",
            rf"\1{chinese}\2",
            translated,
        )
    for pattern, replacement in _SHOT_DIRECTOR_TEXT_REPLACEMENTS:
        translated = pattern.sub(replacement, translated)
    translated = re.sub(r"(?mi)(:\s*)[\"']?none[\"']?\s*$", r'\1"~"', translated)
    translated = re.sub(r"(?m)(\d+(?:\.\d+)?)s\b", r"\1秒", translated)
    return translated

def _repair_body_mechanics_contract_output(output: str) -> str:
    if not output:
        return output

    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        if not _has_body_mechanics_action(block):
            return block

        indent_match = re.search(
            r"(?m)^(\s*)(?:state_delta|tailframe_role|shot_intent|dialogue_coverage|selection_reason)\s*:",
            block,
        )
        indent = indent_match.group(1) if indent_match else "      "
        child_indent = indent + "  "
        defaults = {
            "接触点位": "除非原剧本动作明确写出接触，否则不新增身体接触",
            "重心变化": "保持轻微变化；人物延续当前站位",
            "移动路径": "从起始位置出发，经过可见动作路径，停在已建立的位置",
            "身体朝向": "延续已建立的视线方向和空间轴线",
            "可拍性": "可拍；所选镜头能看清动作路径",
            "机位要求": "保持中景或中近景足够宽，能读清身体动作路径",
            "连续性风险": "保留尾帧人物位置和相邻人物关系，供下一镜继承",
        }
        if not re.search(r"(?m)^\s*(?:身体动作检查|body_mechanics_check)\s*:", block):
            body_lines = ["身体动作检查:"] + [
                f"{field}: {value}" for field, value in defaults.items()
            ]
            return block.rstrip() + "\n" + "\n".join(
                (indent if index == 0 else child_indent) + line
                for index, line in enumerate(body_lines)
            ) + "\n"

        additions = [
            f"{child_indent}{field}: {value}"
            for field, value in defaults.items()
            if not re.search(rf"(?m)^\s*{re.escape(field)}\s*:", block)
        ]
        if additions:
            block = block.rstrip() + "\n" + "\n".join(additions) + "\n"
        return block

    return _MAIN_SHOT_BLOCK_RE.sub(repl, output)

def _repair_shot_director_output_contracts(output: str, script: str) -> str:
    """Apply narrow deterministic repairs before asking another LLM to rewrite."""
    repaired = _repair_shot_layout_output(output)
    repaired = _repair_shot_director_contract_output(repaired, script)
    repaired = _repair_body_mechanics_contract_output(repaired)
    repaired = _translate_shot_director_english_contract_output(repaired)
    repaired = _repair_fragment_continuity_contexts(repaired, script)
    return repaired

def _has_elevator_facing(value: str) -> bool:
    return bool(re.search(r"电梯|elevator", value or "", re.IGNORECASE))

def _has_front_angle(value: str) -> bool:
    return bool(re.search(r"正面|正前方|front|frontal|0度", value or "", re.IGNORECASE))

def _has_background_elevator_anchor(value: str) -> bool:
    return bool(
        re.search(r"(?:后景|背景|background)[^,\n;；。]{0,30}(?:电梯|elevator)", value or "", re.IGNORECASE)
        or re.search(r"(?:电梯|elevator)[^,\n;；。]{0,40}(?:后景|背景|background)", value or "", re.IGNORECASE)
    )

def _repair_background_elevator_anchor_text(text: str) -> str:
    parts = re.split(r"([,;；，])", text)
    repaired: list[str] = []
    for part in parts:
        if re.search(r"电梯|elevator", part, re.IGNORECASE) and re.search(
            r"后景|背景|background", part, re.IGNORECASE
        ):
            part = re.sub(r"background(?:_[A-Za-z0-9_-]+)?", "foreground_edges_or_side_edges", part, flags=re.IGNORECASE)
            part = re.sub(r"后景|背景", "前景边缘或侧边缘", part)
        repaired.append(part)
    return "".join(repaired)

def _repair_background_elevator_landmarks(block: str) -> str:
    lines = block.splitlines(keepends=True)
    in_landmarks = False
    landmark_indent = 0
    repaired_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if re.match(r"visible_landmarks\s*:", stripped):
            in_landmarks = True
            landmark_indent = indent
            repaired_lines.append(_repair_background_elevator_anchor_text(line))
            continue
        if in_landmarks and stripped and indent <= landmark_indent and re.match(r"[A-Za-z_][\w-]*\s*:", stripped):
            in_landmarks = False
        if in_landmarks:
            repaired_lines.append(_repair_background_elevator_anchor_text(line))
        else:
            repaired_lines.append(line)
    return "".join(repaired_lines)

def _replace_yaml_scalar_field(block: str, field: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^(\s*{re.escape(field)}\s*:\s*)([^\n#]*)(.*)$")

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{value}{match.group(3)}"

    return pattern.sub(repl, block, count=1)

def _layout_selection_reason_needs_repair(reason: str) -> bool:
    reason = (reason or "").strip()
    if len(reason) < 12:
        return True
    if _GENERIC_SELECTION_REASON_RE.search(reason):
        return True
    return not _SELECTION_REASON_ANCHOR_RE.search(reason)

def _layout_selection_reason_from_fields(block: str) -> str:
    def clean(value: str, fallback: str) -> str:
        text = re.sub(r"\s+", " ", (value or "").strip())
        text = text.replace(":", " -").strip(" -")
        return text or fallback

    attention = clean(_yaml_scalar_field(block, "attention_target"), clean(_yaml_scalar_field(block, "subject"), "当前主体"))
    information = clean(
        _yaml_scalar_field(block, "information_strategy"),
        clean(_yaml_scalar_field(block, "shot_intent"), "当前剧情信息"),
    )
    coverage = clean(_yaml_scalar_field(block, "coverage_role"), "当前覆盖节拍")
    cut_reason = clean(_yaml_scalar_field(block, "cut_reason"), "当前切镜点")
    camera_seat = clean(
        _yaml_scalar_field(block, "camera_scene_position"),
        clean(_yaml_scalar_field(block, "angle"), "当前机位"),
    )
    return (
        f"观众注意力停留在{attention}；信息策略是{information}；"
        f"{camera_seat}的选择服务于{coverage}，切点是{cut_reason}，同时保持空间、动作和切镜连续。"
    )

def _insert_yaml_scalar_after(block: str, after_fields: tuple[str, ...], field: str, value: str) -> str:
    if re.search(rf"(?m)^\s*{re.escape(field)}\s*:", block):
        return _replace_yaml_scalar_field(block, field, value)
    for after_field in after_fields:
        match = re.search(rf"(?m)^(\s*){re.escape(after_field)}\s*:.*$", block)
        if match:
            indent = match.group(1)
            return block[: match.end()] + f"\n{indent}{field}: {value}" + block[match.end():]
    indent_match = re.search(r"(?m)^(\s*)(?:shot_intent|tailframe_role|companion_visibility|coverage_role|depth|lens)\s*:", block)
    indent = indent_match.group(1) if indent_match else "      "
    return block.rstrip() + f"\n{indent}{field}: {value}\n"

def _repair_action_path_closeup_shot_size(block: str) -> str:
    shot_size = _yaml_scalar_field(block, "shot_size")
    if not _is_closeup_shot_size(shot_size):
        return block

    joined = " ".join(
        [
            _yaml_scalar_field(block, "subject"),
            _yaml_scalar_field(block, "coverage_role"),
            _yaml_scalar_field(block, "cut_reason"),
            _yaml_scalar_field(block, "shot_intent"),
            block,
        ]
    )
    if not _ACTION_PATH_TASK_RE.search(joined):
        return block

    relation_hint = " ".join(
        [
            _yaml_scalar_field(block, "coverage_role"),
            _yaml_scalar_field(block, "shot_intent"),
            _yaml_scalar_field(block, "companion_visibility"),
            _yaml_scalar_field(block, "visible_landmarks"),
        ]
    )
    repaired_size = "半身关系景" if re.search(r"双人|关系|肩线|two[_ -]?shot|shoulder", relation_hint, re.IGNORECASE) else "中景"
    return _replace_yaml_scalar_field(block, "shot_size", repaired_size)

def _repair_layout_main_shot_block(match: re.Match[str]) -> str:
    block = match.group(0)
    angle = _yaml_scalar_field(block, "angle")
    subject_facing = _yaml_scalar_field(block, "subject_facing")
    visible_landmarks = _yaml_scalar_field(block, "visible_landmarks")
    block = _repair_action_path_closeup_shot_size(block)
    if (
        _has_elevator_facing(subject_facing)
        and _has_front_angle(angle)
        and _has_background_elevator_anchor(visible_landmarks)
    ):
        block = _repair_background_elevator_landmarks(block)

    if not re.search(r"(?m)^\s*dialogue_coverage\s*:", block):
        indent_match = re.search(r"(?m)^(\s*)(?:shot_intent|tailframe_role|companion_visibility|coverage_role|depth|lens)\s*:", block)
        indent = indent_match.group(1) if indent_match else "      "
        block = block.rstrip() + f"\n{indent}dialogue_coverage: none\n"
    selection_reason = _yaml_scalar_field(block, "selection_reason")
    if _layout_selection_reason_needs_repair(selection_reason):
        block = _insert_yaml_scalar_after(
            block,
            ("information_strategy", "attention_target", "shot_intent"),
            "selection_reason",
            _layout_selection_reason_from_fields(block),
        )
    return block

def _repair_shot_layout_output(layout_output: str) -> str:
    """Apply deterministic minimal repairs before failing a layout contract."""
    if not layout_output:
        return layout_output
    return _MAIN_SHOT_BLOCK_RE.sub(_repair_layout_main_shot_block, layout_output)

def _validate_shot_director_spatial_geometry(output: str) -> list[str]:
    issues: list[str] = []
    for shot_id, block in _main_shot_blocks(output):
        camera_basis = _yaml_scalar_field(block, "camera_basis")
        angle = _yaml_scalar_field(block, "angle")
        subject_facing = _yaml_scalar_field(block, "subject_facing")
        visible_landmarks = _yaml_scalar_field(block, "visible_landmarks")
        state_delta = _yaml_scalar_field(block, "state_delta")
        shot_intent = _yaml_scalar_field(block, "shot_intent")
        action = _yaml_scalar_field(block, "action")
        task = _yaml_scalar_field(block, "task")
        body_for_action = f"{state_delta} {shot_intent} {action} {task} {block}"

        if (
            _has_elevator_facing(subject_facing)
            and _has_front_angle(angle)
            and _has_background_elevator_anchor(visible_landmarks)
        ):
            issues.append(
                f"{shot_id} 空间几何矛盾：人物朝向电梯且镜头为正面时，电梯门框不能在后景；"
                "请把门框改为 foreground_edges/side_edges，或改为背面/侧背/场景固定机位。"
            )

        if (
            re.search(r"subject_relative|人物相对", camera_basis or "", re.IGNORECASE)
            and _has_front_angle(angle)
            and re.search(r"转身|进入电梯|走进电梯|穿过门框|enter(?:ing)? elevator|cross(?:ing)? threshold", body_for_action, re.IGNORECASE)
        ):
            issues.append(
                f"{shot_id} 人物相对正面机位不能承载转身/穿过门框/进入电梯动作；"
                "请改为 scene_fixed，并写清 camera_scene_position 与 camera_looks_toward。"
            )
    return issues

def _quoted_dialogues(text: str) -> list[str]:
    return [item.strip() for item in re.findall(r"[\"\u201c\u201d]([^\"\u201c\u201d]+)[\"\u201c\u201d]", text or "") if item.strip()]

def _dialogue_payload_is_long(dialogues: list[str]) -> bool:
    if not dialogues:
        return False
    total = sum(len(item) for item in dialogues)
    return total >= 42 or any(len(item) >= 32 for item in dialogues) or len(dialogues) >= 2

def _dialogue_coverage_needs_visual_break(coverage: str) -> bool:
    text = (coverage or "").strip()
    if not text or text.lower() == "none":
        return False
    quoted = _quoted_dialogues(text)
    if _dialogue_payload_is_long(quoted):
        return True
    ascii_words = re.findall(r"[A-Za-z][A-Za-z']+", text)
    has_long_english = sum(len(word) for word in ascii_words) >= 55 or len(ascii_words) >= 12
    has_multi_line_or_exchange = len(re.findall(r"[/?？]|；|;|：|:", text)) >= 2
    has_pressure_marker = bool(
        re.search(
            r"命令|质问|高压|羞辱|压迫|反问|不准|返工|mistake|expect|important|leaving|afford|secretary|what do I need",
            text,
            re.IGNORECASE,
        )
    )
    return has_long_english or has_multi_line_or_exchange or (len(text) >= 42 and has_pressure_marker)

def _has_dialogue_coverage_visual_break(coverage: str) -> bool:
    return bool(_DIALOGUE_COVERAGE_TERMS_RE.search(coverage or ""))

def _agent_runtime_trace(
    agent_name: str,
    mode: str,
    started_at: float,
    status: str,
    output: str = "",
    error: Exception | None = None,
    **extra: Any,
) -> dict[str, Any]:
    _api_key, base_url, model, temperature = _get_llm_settings(agent_name)
    try:
        host = base_url.split("//", 1)[1].split("/", 1)[0] if "//" in base_url else base_url
    except Exception:
        host = base_url

    trace: dict[str, Any] = {
        "agent_name": agent_name,
        "mode": mode,
        "model": model,
        "host": host,
        "temperature": temperature,
        "status": status,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "output_chars": len(output or ""),
    }
    if error is not None:
        trace["error_type"] = type(error).__name__
        trace["error"] = str(error)[:500]
    for key, value in extra.items():
        if value is not None:
            trace[key] = value
    return trace


def _shot_director_stage_images(stage_key: str, images_base64: list[str] | None) -> list[str] | None:
    """Shot director stages consume text grounding; scene vision/card agents own image reading."""
    _ = stage_key, images_base64
    return None


def _shot_director_stage_profile(
    base_profile: dict[str, Any],
    *,
    served_agent: str,
    extra_signals: list[str],
    extra_tags: list[str],
    extra_constraints: list[str],
) -> dict[str, Any]:
    profile = dict(base_profile or {})
    profile["served_agents"] = [served_agent]
    profile["signals"] = _unique_preserve_order([*(profile.get("signals") or []), *extra_signals])
    profile["tags"] = _unique_preserve_order([*(profile.get("tags") or []), *extra_tags])
    profile["visual_constraints"] = _unique_preserve_order(
        [*(profile.get("visual_constraints") or []), *extra_constraints]
    )
    return profile


def _shot_director_layout_rule_block(aspect_ratio: str) -> str:
    return (
        "【阶段一｜摆位导演 + 镜头任务与空间安全】\n"
        "你是一号镜头摆位导演。你不是全能镜头导演，只负责把当前片段的戏剧任务、空间安全和主镜头覆盖链立住。\n"
        "必须融合上游情绪曲线与当前片段任务：先判断观众注意力问题、必须覆盖事件、剪辑省略点、轴线和尾帧，再决定需要几个主镜头、用什么粗景别和覆盖顺序。\n"
        "输出只允许是施工 YAML，不要解释。\n\n"
        "【必须输出】\n"
        "- 片段编号、片段任务、节奏\n"
        "- 空间规则：空间锚点、人物位置、动作轴线、安全机位区、禁用机位区\n"
        "- 主镜头列表：镜头编号、镜头任务、拍摄主体、镜头、覆盖职责、切镜原因、同场人物位置、状态变化、尾帧职责、对白覆盖、选择理由、镜头语言机会\n\n"
        "【阶段一边界】\n"
        "1. 只搭主镜头骨架，不输出最终镜头序列，不细拆子镜头。\n"
        "2. 阶段一负责粗景别和主镜头职责：关系/中景建立空间与动作，中近景承载对白和受击，近景/特写只预留给信息揭示或情绪极点，远景只用于空间建立、权力关系或孤立感。\n"
        "3. 不抢二号的反应细节、动作重音和子分镜；但必须给二号留下明确的镜头语言机会，例如过肩、跟拍、局部特写、动作顶点前切、关系复位。\n"
        "4. 必须识别剪辑省略点：走路、开门、上车、进入新空间等无戏剧增量过程只保留起点和终点；弱拍可并入主镜头或用结果状态呈现。\n"
        "5. 同侧只是不越轴，不是固定机位模板；主镜头覆盖链不得全靠同侧固定中近景。\n"
        "6. 长对白或高压对白必须在主镜头骨架中预留听者反应/过肩/关系复位机会，不能让同一说话者镜头吃完整段。\n"
        "7. 局部、道具、眼神、手部等细节默认留给二号作为子分镜，除非当前剧本唯一信息主体就是该物件。\n"
        "8. 禁止人物相对左右机位、数字角度、门框压线、框住人物等抽象构图术语。\n"
        "9. 快节奏生活动作段先搭少量主镜头覆盖链：8-12秒默认3-4个主镜头，不用手、手机、脚、衣服等碎插入堆速度；如果需要第5个镜头，必须绑定信息揭示、危险命中或强反应。\n"
        "10. 拍摄主体不是人物/道具清单；每个主镜头先写观众注意力主焦点，通常是人物、双人关系或唯一关键物，闹钟/手机/衣服/书包等只在信息命中时升为主体。\n"
        "11. 必须先选择戏剧任务镜头组合：生活压力=关系建立→动作阻力→安抚/反应→尾帧复位；信息揭示=发现前停顿→关键物可读→人物反应→关系/尾帧复位；对白攻防=说话者起句→听者受击/过肩→关系复位。\n"
        "12. 主镜头覆盖链回答“这一镜之后为什么接下一镜”；下一镜只能因为注意力问题变化、信息看清、情绪受击、动作阶段变化或空间复位而切。\n"
        f"【画幅】{aspect_ratio}\n"
    )


def _shot_director_blocking_rule_block(aspect_ratio: str) -> str:
    return (
        "【阶段二｜动作调度导演 + 镜头语言选择】\n"
        "你是二号动作调度导演。你在一号主镜头骨架上挂动作、反应、状态链和必要子分镜，同时正式选择镜头语言。\n"
        "核心任务不是补丁式修饰，而是把镜头语言当成剧情事件的覆盖方案：按剧情信号、场景类型、风险约束和案例技法主动选择景别、机位、角度、运动、声音承载和切点。\n"
        "安全边界是剧本事实、人物连续性和不越轴；只要不越轴，就不要为了后续 prompt_compiler 预先降级成同侧固定机位或中近景保守模板。\n\n"
        "【必须输出】\n"
        "- 保留一号的片段编号、片段任务、节奏、空间规则和主镜头编号。\n"
        "- 补齐镜头列表或主镜头列表中的：镜头、画面动作、台词、必须承载、切镜点、连续性、覆盖职责、切镜原因、同场人物位置、状态变化、尾帧职责；其中镜头字段只写主体景别、视角/观看位置和必要运动，动作表情必须写进画面动作，但画面动作只写必要状态、一个主要动作变化和镜尾状态。\n"
        "- 需要子分镜时，必须挂靠父镜头：父镜头编号、触发点、主体、镜头、动作阶段、时长建议、状态变化、节拍目的。\n"
        "- 明确镜头多样性检查：是否变化主体、景别、机位/角度、运动、声音承载或镜头任务。\n\n"
        "【镜头语言选择】\n"
        "1. 同侧只表示轴线内安全，不等于固定中近景；可在轴线同侧大胆选择侧面、肩后、贴近低机位、稍高机位、稳定固定、跟随、推近、横移或关系复位，只要人物左右关系不翻转。\n"
        "2. 对白/试探/冲突互动：按攻防关系选择过肩、双人同框、听者受击反应、说话者压近、画外音承接、声音先行或声音延续；禁止把整段写成同侧固定机位中近景正反打。\n"
        "3. 长对白/高压命令：必须根据情绪压力设置说话者起句、听者受击/过肩反应、必要时 OS/J-cut/L-cut 和关系复位；切镜点落在压力词、停顿、受击反应或回应前。\n"
        "4. 动作密集/位移/阈值动作：优先跟拍、侧面关系景、动作顶点前切、局部动作子分镜或终点复位，用切镜省略无信息过程；不要用站桩中近景吃掉动作。\n"
        "5. 信息揭示：优先目标物或文字可读、人物视线、人物反应三段链；镜头可以短促、清楚、贴近，但具体对象必须来自当前剧本事实。\n"
        "6. 权力压迫/反转：用站位占比、前后层次、肩后压迫、低/高机位感、稳定凝视或关系景体现，不得只拍赢方说话，也不得为了安全只退回中景。\n"
        "7. 情绪峰值：可以使用短促特写、近景停顿、留白或声音落到反应上，但必须有信息增量，并包裹在关系镜头或可继承尾帧里。\n"
        "8. 局部特写只在当前剧本动作或已有道具承载线索、动作前摇或受击结果时使用；具体拍什么由当前剧本决定，不固化手、衣服、手机等某一剧集细节。\n"
        "9. 一个片段超过四个镜头时，至少变化三类：主体、景别、机位/角度、运动、声音承载或镜头任务；连续镜头不得无理由重复同侧固定机位、中近景或同一种反应句。\n"
        "10. 最终交给三号时，镜头字段必须是自然中文视角表达：主体景别 + 视角/观看位置 + 必要运动；画面动作必须另写人物动作、台词落点、表情反应和道具状态；不要把两者混成一句。\n"
        f"10A. {_SHOT_VIEWPOINT_TRANSLATION_HINT}\n"
        "11. 接触、佩戴、递交、抢夺、拉扯等动作必须写清动作阶段和结束状态，避免项链、手、衣物、身体位置在相邻镜头跳变；但不要写成手指、指尖、肩颈、呼吸、衣角的连续流水账。\n"
        "12. 画面动作粒度上限：每个镜头 1-2 句，每句只承载一个主要动作变化；微表情和微手势只在承载线索、受击结果或动作前摇时保留，其余压缩为视线、停顿、后退、放下、保持等低歧义动作。\n"
        "13. 生活动作快节奏靠动作叠压、台词压力和情绪转折，不靠1秒以下碎切；手、手机、脚、衣服这类局部动作默认并入主关系镜头，除非它本身就是关键线索。\n"
        "14. 当阶段一给出3-4个主镜头时，不要为了“更快”把它扩成6-7个镜头；必要的短切写成切镜点或子分镜触发，不要升级成主镜头列表。\n"
        "15. 每镜拍摄主体必须服务镜头功能：建立镜拍关系主体，动作阻力拍行动者+受阻者，信息揭示拍关键物，情绪落点拍受击者，复位镜拍关系和尾帧；禁止把人物、道具、食品、家具一起塞进主体。\n"
        "16. 下一镜选择必须按戏剧任务镜头组合推进，不能随机换成另一个好看的景别；局部插入后必须接人物反应或关系复位，反应镜后必须给可继承的尾帧状态。\n"
        "17. S02 及以后必须显式承接上一镜尾帧；人物从坐到站、从沙发到茶几、衣服从未完成到穿好、书包从地上到手里，都必须在画面动作或连续性里写出过渡。\n"
        f"【画幅】{aspect_ratio}\n"
    )


def _shot_director_guard_stage_rule_block(aspect_ratio: str) -> str:
    return (
        "【阶段三｜规则守门导演 + 最终自然表达】\n"
        "你是三号规则守门导演。只做最小修复，不重写创意，不另起炉灶。\n"
        "你的输出是唯一交给 prompt_compiler 的最终中文 YAML。\n\n"
        "【守门范围】\n"
        "1. 修复结构缺项、漏事件、剧本外人物/台词/动作/道具、道具跳变、越轴、人物位置突然消失、子分镜漂浮、尾帧不可继承。\n"
        "2. 修复镜头语言过度保守：连续堆同侧固定机位或中近景时，只做最小替换，让已有动作任务落到更合适的自然镜头句。\n"
        "3. 删除或改写抽象构图术语、人物相对左右机位、数字角度、英文摄影术语和内部字段。\n"
        "4. 保留前两位的片段编号、镜头编号、主体、剧情事实和主要镜头创意。\n\n"
        "【最终 YAML 必须使用中文字段】\n"
        "- 片段编号、片段任务、节奏、空间连续性总控、镜头列表\n"
        "- 镜头编号、时长、镜头任务、拍摄主体、镜头、画面动作、台词、必须承载、切镜点、连续性\n"
        "- 可选保留：覆盖职责、切镜原因、同场人物位置、状态变化、尾帧职责、声音、类型\n\n"
        "【空间连续性总控】\n"
        "每个片段在镜头列表前必须先写一句片段级连续性总控：本片段是一段什么戏剧任务，哪些人物始终处在同一空间内；"
        "单人镜只表示镜头主体变化，不代表其他在场人物离开；每镜继承上一镜尾帧、道具状态、视线方向和同侧轴线。\n\n"
        "【最终镜头表达】\n"
        "镜头字段只写最终可生成的视角表达：主体景别 + 视角/观看位置 + 必要运动/前景关系；不要写戏剧判断、人物动作、台词或表情。例如“乔熙胸部以上中近景，从商北琛肩后看向她”。\n"
        f"{_SHOT_VIEWPOINT_TRANSLATION_HINT}\n"
        "画面动作字段必须短、自然、可生成：写清谁先做什么、道具/身体状态如何变化、镜尾停在什么状态；不要堆叠手指、肩颈、呼吸、衣角等微细节。\n"
        "必须承载字段只写本镜必须看清的信息和状态变化，不要写抽象戏剧效果；连续性字段必须说明同场人物和道具没有消失或跳步。\n"
        "动作粒度上限：每个镜头 1-2 句，每句一个主要动作变化；如果需要更细的动作阶段，用切镜点或连续性说明，不要塞进画面动作。\n"
        "镜头密度守门：8-12秒生活动作段超过4个有效镜头，或出现多个1秒以下局部碎镜时，必须合并为关系镜头/中景连续动作；快节奏由动作压力表达，不由碎切表达。\n"
        "拍摄主体守门：拍摄主体不是人物/道具清单；如果主体里堆了闹钟、手机、衣服、草莓蛋糕、书包等多个道具，必须改为人物/双人关系/唯一关键物，并把道具移入必须承载或连续性。\n"
        "镜头组合守门：检查整段是否遵循戏剧任务镜头组合；关系建立、动作阻力、信息揭示、受击反应、关系复位必须按观众注意力顺序出现，不能随机拼镜头。\n"
        "承接守门：每一镜都要承接上一镜尾帧；如果人物位置、坐站、穿戴、道具归属突变，必须最小修复为可见过渡或改回上一镜状态。\n"
        "可以写“从乔熙肩后看向商北琛”“门口侧面固定视角”，不要写“门框形成前景压线”“人物站进门框”或“固定机位”。\n"
        "台词只能使用原剧本原文或 ~；英文台词原文可保留在引号内，因为它是剧本文本，不是英文字段。\n"
        f"【画幅】{aspect_ratio}\n"
    )


def _shot_director_rule_block(aspect_ratio: str) -> str:
    return (
        f"{_shortdrama_master_rules()}\n"
        f"{_script_fidelity_rules()}\n"
        f"{_subject_framing_rules()}\n"
        f"{_shot_composition_task_selection_rules()}\n"
        f"{_dialogue_coverage_contract_rules()}\n"
        f"{_spatial_geometry_contract_rules()}\n"
        f"{_performance_logic_contract_rules()}\n"
        f"{_camera_execution_rules()}\n"
        f"{_camera_task_selection_rules()}\n"
        f"{_shot_director_source_event_rules()}\n"
        f"{_shot_director_rhythm_match_rules()}\n"
        f"{_rhythm_insert_continuity_rules()}\n"
        f"【画幅】{aspect_ratio}\n"
        "【防幻觉规则】\n"
        "1. 不新增剧情。\n"
        "2. 不新增人物。\n"
        "3. 不新增台词。\n"
        "4. 不新增动作。\n"
        "5. 不改变片段编号和镜头编号。\n"
        "6. 不改变人物出入场关系。\n"
        "7. 不保留放弃方案里的具体错误画面描述。\n"
        "8. 所有禁止呈现内容必须简短，不要展开描述。\n"
        "9. 镜头字段只写摄影选择，不写人物动作、台词、表情、心理或戏剧判断。\n"
        "10. 画面动作只写可见动作和表情变化，不写心理解释。\n"
        "11. 如果字段冲突，优先保留连续性、空间规则和动作表情逻辑。\n"
    )

def _indent_level(line: str) -> int:
    return len(line) - len(line.lstrip(" "))

def _extract_parent_block_lines(section: str, field: str) -> list[str]:
    lines = section.splitlines()
    for idx, line in enumerate(lines):
        if not re.match(rf"^\s*{re.escape(field)}\s*:\s*$", line):
            continue
        parent_indent = _indent_level(line)
        block: list[str] = []
        for next_line in lines[idx + 1 :]:
            if not next_line.strip():
                continue
            if _indent_level(next_line) <= parent_indent:
                break
            block.append(next_line)
        return block
    return []

def _extract_nested_mapping_value(section: str, parent: str, child: str) -> str:
    for line in _extract_parent_block_lines(section, parent):
        match = re.match(rf'^\s*{re.escape(child)}\s*:\s*["\']?(.+?)["\']?\s*$', line)
        if match:
            return match.group(1).strip()
    return ""

def _extract_top_level_list_items(section: str, field: str) -> list[str]:
    match = re.search(
        rf"(?m)^\s*{re.escape(field)}\s*:\s*([\s\S]*?)(?=\n\s*(?:[a-z_]+|[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_/]*)\s*:|\n\s*-?\s*(?:fragment_id|片段编号)\s*:|\Z)",
        section,
    )
    if not match:
        value = _field_value(section, field)
        return [value] if value else []
    block = match.group(1)
    items = [
        item.strip().strip("\"'")
        for item in re.findall(r"(?m)^\s*-\s*[\"']?(.+?)[\"']?\s*$", block)
        if item.strip()
    ]
    if items:
        return items
    value = block.strip().strip("\"'")
    return [value] if value else []

def _extract_nested_list_items(section: str, parent: str, child: str) -> list[str]:
    block_lines = _extract_parent_block_lines(section, parent)
    items: list[str] = []
    for idx, line in enumerate(block_lines):
        match = re.match(rf"^(\s*){re.escape(child)}\s*:\s*$", line)
        if not match:
            continue
        child_indent = len(match.group(1))
        for next_line in block_lines[idx + 1 :]:
            if not next_line.strip():
                continue
            if _indent_level(next_line) <= child_indent:
                break
            item_match = re.match(r'^\s*-\s*["\']?(.+?)["\']?\s*$', next_line)
            if item_match:
                items.append(item_match.group(1).strip())
        break
    return items

def _trim_layout_text(value: str, limit: int = 120) -> str:
    cleaned = (value or "").strip().strip("'")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 1)].rstrip() + "..."

def _shot_director_layout_context(planner_output: str, aspect_ratio: str) -> str:
    sections = _extract_yaml_sections(planner_output or "")
    if not sections:
        return f"【画幅】\n{aspect_ratio}\n\n【结构规划摘录】\n{(planner_output or '').strip()[:2000]}"

    lines = [
        "【摆位输入合同】",
        "只为每个片段设计机位骨架。",
        "使用下面的结构规划摘要，不要重新解读全剧本。",
        _runtime_context_contract_card(),
        "",
        "【画幅】",
        aspect_ratio,
        "",
        "【片段】",
    ]
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        fragment_task = _field_value_any(section, "片段任务", "dramatic_unit", "戏剧单元")
        duration_target = _field_value_any(section, "目标时长", "duration_target")
        reaction_plan = _field_value_any(section, "承接要求", "reaction_plan")
        intra_fragment_rhythm = _field_value_any(
            section,
            "片段内节奏分配",
            "段内节奏分配",
            "内部节拍预算",
            "intra_fragment_rhythm",
            "internal_beat_budget",
        )
        shot_handoff = _field_value_any(section, "镜头导演交接", "shot_director_handoff", "导演交接")
        director_brief = _field_value_any(section, "director_brief", "导演交接")
        dramatic_unit = fragment_task or reaction_plan
        active_cast = _extract_nested_list_items(section, "cast", "active")
        if not active_cast:
            active_cast = _extract_top_level_list_items(section, "出现人物")
        must_not_show = _extract_nested_list_items(section, "cast", "must_not_show")
        continuity_entry = _extract_nested_mapping_value(section, "continuity", "entry") or _field_value(section, "入场状态")
        continuity_exit = _extract_nested_mapping_value(section, "continuity", "exit") or _field_value(section, "出场状态")
        source_events = _source_script_events(section)
        key_events = [_trim_layout_text(event, 90) for event in source_events[:4]]
        dialogue_lines = [
            _trim_layout_text(event, 120)
            for event in source_events
            if ("\\uff1a" in event or ":" in event)
        ][:3]

        lines.extend(
            [
                f"- 片段编号: {fragment_id}",
                f"  戏剧单元: {_trim_layout_text(dramatic_unit, 120) or '无'}",
                f"  目标时长: {_trim_layout_text(duration_target, 80) or '无'}",
                f"  片段内节奏分配: {_trim_layout_text(intra_fragment_rhythm, 220) or '无'}",
                f"  承接要求: {_trim_layout_text(reaction_plan, 160) or '无'}",
                f"  镜头导演交接: {_trim_layout_text(shot_handoff or director_brief, 220) or '无'}",
                f"  出场人物: {', '.join(active_cast) if active_cast else '无'}",
                f"  禁止呈现: {', '.join(must_not_show) if must_not_show else '无'}",
                f"  入场连续性: {_trim_layout_text(continuity_entry, 140) or '无'}",
                f"  出场连续性: {_trim_layout_text(continuity_exit, 140) or '无'}",
                "  关键事件:",
            ]
        )
        if key_events:
            lines.extend(f"    - {event}" for event in key_events)
        else:
            lines.append("    - 无")
        lines.append("  台词行:")
        if dialogue_lines:
            lines.extend(f"    - {line}" for line in dialogue_lines)
        else:
            lines.append("    - 无")
    return "\n".join(lines)

def _sections_by_fragment(yaml_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for section in _extract_yaml_sections(yaml_text or ""):
        fragment_id = _extract_fragment_id(section)
        if fragment_id:
            sections[fragment_id] = section.strip()
    return sections

def _planner_source_event_context(
    planner_output: str,
    fragment_ids: list[str] | None = None,
    *,
    char_limit: int = 2400,
) -> str:
    sections_by_id = _sections_by_fragment(planner_output)
    selected_ids = fragment_ids or list(sections_by_id)
    chunks: list[str] = []
    for fragment_id in selected_ids:
        section = sections_by_id.get(fragment_id, "")
        if not section:
            continue
        source_events = _source_script_events(section)
        if source_events:
            event_lines = "\n".join(f"- {event}" for event in source_events)
            chunks.append(f"{fragment_id} source_script_events:\n{event_lines}")
        else:
            chunks.append(f"{fragment_id} planner_contract:\n{_truncate_for_prompt(section, 600)}")
    if not chunks and planner_output:
        chunks.append(_truncate_for_prompt(planner_output, char_limit))
    return _truncate_for_prompt("\n\n".join(chunks), char_limit)

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

def _extract_rhythm_shot_director_notes(atmosphere_strategy: str) -> str:
    """Extract rhythm supervisor notes that are explicitly addressed to shot_director."""
    text = (atmosphere_strategy or "").strip()
    if not text:
        return ""

    notes = _extract_labeled_rhythm_sections(
        text,
        (
            "给镜头导演",
            "镜头导演操作单",
            "shot_director_notes",
            "镜头导演节奏执行约束",
            "镜头导演执行约束",
            "给镜头导演的节奏执行约束",
        ),
        (
            "节奏诊断",
            "节奏总合同",
            "拆片边界建议",
            "反应归属",
            "尾帧承接",
            "结构规划施工指令",
            "给结构规划师",
            "结构规划师操作单",
            "给镜头导演",
            "镜头导演操作单",
            "shot_director_notes",
            "construction_notes",
            "risk_flags",
            "atmosphere_strategy",
            "rewritten_script",
            "改写后剧本",
            "镜头导演节奏执行约束",
            "镜头导演执行约束",
            "给镜头导演的节奏执行约束",
            "风险提醒",
        ),
    )
    return notes

def _rhythm_shot_director_notes_prompt(atmosphere_strategy: str) -> str:
    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    if not notes:
        return ""
    return (
        "[节奏总控给镜头导演的执行约束]\n"
        "这里只包含上游给镜头施工层的精简操作单，主要控制片段边界、情绪曲线、节奏意图、必须保留落点、可压缩弱拍和尾帧承接；"
        "镜头数、景别、机位、运镜、镜头时长和切镜点由 shot_director 自行规划。"
        "若它与结构规划原文事件、原始台词、道具连续性或空间轴线安全冲突，以后者为准。\n"
        f"{_truncate_for_prompt(notes, 1200)}\n"
    )

def _shot_director_downstream_context(
    planner_output: str,
    atmosphere_strategy: str,
    aspect_ratio: str,
) -> str:
    """Compact handoff for blocking/guard so they do not re-read the whole script."""
    lines = [
        "[Compact Downstream Context]",
        "Use this compact fragment contract instead of the full script.",
        "The planner source_script_events are the only event coverage source.",
        "Do not add script-external people, dialogue, props, or actions.",
        "",
        _shot_director_layout_context(planner_output, aspect_ratio),
    ]
    rhythm_shot_notes_prompt = _rhythm_shot_director_notes_prompt(atmosphere_strategy)
    if rhythm_shot_notes_prompt:
        lines.extend(["", rhythm_shot_notes_prompt.strip()])
    return "\n".join(lines).strip() + "\n\n"

def _shot_stage_should_split(
    expected_segments: list[str],
    contract_text: str,
    *,
    char_threshold: int = 6000,
    segment_threshold: int = 3,
) -> bool:
    return len(expected_segments) >= segment_threshold or len(contract_text or "") >= char_threshold

def _segment_name_to_fragment_id(segment_name: str) -> str:
    segment_num = re.sub(r"\D", "", segment_name or "")
    return f"F{int(segment_num):02d}" if segment_num else segment_name

def _fragment_compact_context(
    planner_sections: dict[str, str],
    fragment_id: str,
    aspect_ratio: str,
) -> str:
    planner_section = planner_sections.get(fragment_id, "")
    if not planner_section:
        return f"【画幅】\n{aspect_ratio}\n\n【片段】\n- 片段编号: {fragment_id}\n"
    return _shot_director_layout_context(planner_section, aspect_ratio)

def _call_stage_split_by_fragment(
    *,
    stage_key: str,
    system_prompt: str,
    expected_segments: list[str],
    planner_output: str,
    aspect_ratio: str,
    contract_output: str,
    prompt_builder: Callable[[str, str, str], str],
    images_base64: list[str] | None = None,
    progress_callback: Callable[[str, str, dict[str, Any]], None] | None = None,
    resume_fragment_outputs: dict[str, str] | None = None,
    resume_fragment_runtime: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    planner_sections = _sections_by_fragment(planner_output)
    contract_sections = _sections_by_fragment(contract_output)
    resume_fragment_outputs = resume_fragment_outputs or {}
    resume_fragment_runtime = resume_fragment_runtime or {}
    started_at = time.time()
    outputs: list[str] = []
    fragment_runtimes: list[dict[str, Any]] = []
    for segment_name in expected_segments:
        fragment_id = _segment_name_to_fragment_id(segment_name)
        fragment_stage_name = f"fragment_{fragment_id}"
        fragment_context = _fragment_compact_context(planner_sections, fragment_id, aspect_ratio)
        fragment_contract = contract_sections.get(fragment_id, "")
        if not fragment_contract:
            # Fall back to the full contract instead of silently dropping a fragment.
            fragment_contract = contract_output
        fragment_started_at = time.time()
        resumed_output = (
            resume_fragment_outputs.get(fragment_stage_name)
            or resume_fragment_outputs.get(fragment_id)
            or ""
        )
        if resumed_output.strip():
            cleaned = _clean_shot_director_output(resumed_output)
            fragment_runtime = dict(resume_fragment_runtime.get(fragment_stage_name) or {})
            fragment_runtime.setdefault("fragment_id", fragment_id)
            fragment_runtime.setdefault("elapsed_seconds", 0)
            fragment_runtime.setdefault("output_chars", len(cleaned))
            fragment_runtime.setdefault("status", "reused")
        else:
            fragment_output = call_llm(
                system_prompt=system_prompt,
                user_prompt=prompt_builder(fragment_id, fragment_context, fragment_contract),
                agent_name=stage_key,
                images_base64=images_base64,
            )
            cleaned = _clean_shot_director_output(fragment_output)
            fragment_runtime = {
                "fragment_id": fragment_id,
                "elapsed_seconds": round(time.time() - fragment_started_at, 3),
                "output_chars": len(cleaned),
                "status": "success" if cleaned else "empty",
            }
        outputs.append(cleaned)
        fragment_runtimes.append(fragment_runtime)
        if progress_callback:
            progress_callback(fragment_stage_name, cleaned, fragment_runtime)
    combined_output = "\n\n".join(output.strip() for output in outputs if output.strip())
    return combined_output, {
        "agent_name": stage_key,
        "mode": "split_by_fragment",
        "status": "success",
        "elapsed_seconds": round(time.time() - started_at, 3),
        "fragment_count": len(outputs),
        "fragment_runtimes": fragment_runtimes,
        "output_chars": len(combined_output),
    }

def _call_shot_director_stage(
    *,
    stage_key: str,
    system_prompt: str,
    user_prompt: str,
    images_base64: list[str] | None,
) -> tuple[str, dict[str, Any]]:
    started = time.perf_counter()
    try:
        output = call_llm(
            system_prompt,
            user_prompt,
            images_base64=images_base64,
            agent_name=stage_key,
        )
        cleaned = _clean_shot_director_output(output)
        runtime = _agent_runtime_trace(
            stage_key,
            mode="direct",
            started_at=started,
            status="success" if cleaned else "empty",
            output=cleaned,
        )
        print(f"  [shot_director] {stage_key} completed in {runtime['elapsed_seconds']:.1f}s")
        return cleaned, runtime
    except Exception as exc:
        runtime = _agent_runtime_trace(
            stage_key,
            mode="direct",
            started_at=started,
            status="error",
            error=exc,
        )
        print(f"  [shot_director] {stage_key} 调用失败：{exc}")
        raise

_SHOT_EVENT_TAG_HINTS = {
    "collision": ("碰撞", "撞", "冲入", "受击", "压住"),
    "rush_in": ("冲入", "闯入", "挤入", "跑进"),
    "waist_support": ("扶腰", "腰侧", "搂住", "托住"),
    "door_state": ("门", "电梯", "门缝", "关门", "开门"),
    "vehicle_entry": ("上车", "下车", "车门", "车内", "驾驶座", "副驾驶"),
    "motion_ellipsis": ("走向", "走到", "位移", "路过", "穿过", "进入", "到达"),
    "reaction": ("反应", "停顿", "愣住", "回避", "屏住呼吸"),
    "dialogue": ("对白", "台词", "OS", "J-cut", "L-cut"),
}

_SHOT_RISK_TAG_HINTS = {
    "door_state_jump": ("门又开", "重新打开", "门状态", "电梯门", "门缝"),
    "romanticize_collision": ("碰撞", "扶腰", "压住", "亲密", "暧昧"),
    "axis_confusion": ("越轴", "轴线", "左右关系", "方向"),
    "vertical_closeup_overuse": ("9:16", "竖屏", "特写", "近景"),
    "script_invention_risk": ("新增", "剧本外", "不得发明", "忠实"),
    "dialogue_integrity": ("对白", "台词", "不得新增台词"),
    "shot_monotony": ("同一机位", "同一景别", "站桩", "正反打", "重复", "一镜到底"),
}

_SHOT_DIALOGUE_TAG_HINTS = {
    "teasing": ("调侃", "打趣", "逗", "玩笑"),
    "argument_escalation": ("争吵", "冲突", "质问", "爆发"),
    "long_dialogue_compression": ("长对白", "高压命令", "访谈", "解释"),
    "reaction_beat": ("反应", "停顿", "沉默", "回避"),
}

_SHOT_SIGNAL_TAG_HINTS = {
    "tailframe": ("尾帧", "结束状态", "承接"),
    "cut_point": ("切点", "cut_point", "切镜", "动作顶点"),
    "continuity_lock": ("连续性", "承接", "状态", "位置"),
    "vertical_framing": ("9:16", "竖屏", "画幅"),
    "editing_ellipsis": ("省略", "压缩", "跳切", "无用动作", "垃圾时间", "起点帧", "终点帧"),
    "shot_variety": ("多机位", "多角度", "景别变化", "镜头多样", "反站桩", "正反打"),
    "rhythm_alignment": ("节奏总控", "节奏执行", "停顿", "段尾状态", "反应归属", "必须拍完整", "可以省略"),
}

_SHOT_SCENE_TYPE_HINTS = {
    "elevator": ("电梯", "轿厢", "电梯门", "elevator", "lift"),
    "door_threshold": ("门口", "门缝", "房门", "车门", "入口", "阈值"),
    "office": ("办公室", "公司", "会议室", "工位", "员工"),
    "vehicle": ("车内", "车门", "驾驶座", "副驾驶", "后座"),
}

_SHOT_LIBRARY_TASK_KEYWORDS = {
    "long_dialogue_coverage": ("对白", "台词", "命令", "质问", "解释", "说完", "问道", "回答", "OS", "J-cut", "L-cut"),
    "impact_reaction": ("撞", "碰撞", "受击", "击中", "冲进", "摔", "压住", "推开"),
    "reveal_insert_reaction": ("看清", "发现", "揭示", "照片", "文件", "手机", "信息", "秘密", "真相"),
    "door_threshold_continuity": ("电梯", "门", "门口", "门缝", "车门", "入口", "轿厢"),
    "tailframe_handoff": ("尾帧", "承接", "出场状态", "下一段", "停住", "结束状态"),
    "authority_pressure": ("命令", "压迫", "沉默", "上司", "新老板", "退让", "让路", "质问"),
    "editing_ellipsis": ("无用", "省略", "压缩", "跳切", "走向", "走到", "位移", "上车", "下车", "进入新空间"),
    "shot_language_variety": ("多机位", "多角度", "景别", "机位", "站桩", "正反打", "镜头多样", "一镜到底"),
    "rhythm_alignment": ("节奏总控", "节奏执行", "必须拍完整", "可以省略", "不能省略", "停顿", "反应归属", "尾帧要求"),
}

_SHOT_LIBRARY_TASK_RULES = {
    "long_dialogue_coverage": (
        "调用对白覆盖镜头库：说话者起句 -> 同侧听者反应/过肩 -> 必要时用 OS/J-cut/L-cut 落到反应上；"
        "不得一个固定机位吃完整长台词。"
    ),
    "impact_reaction": (
        "调用受击/碰撞镜头库：动作前摇 -> 接触/命中瞬间 -> 受击者反应 -> 结果状态；"
        "不得把意外碰撞浪漫化或省掉受击落点。"
    ),
    "reveal_insert_reaction": (
        "调用信息揭示镜头库：主体动作 -> 信息可读的插入/近景 -> 人物被击中的反应 -> 尾帧承接；"
        "切点必须落在信息看清之后。"
    ),
    "door_threshold_continuity": (
        "调用门/电梯阈值镜头库：优先场景固定机位或侧前方机位，门状态单向推进，进入/停住/合拢必须连续；"
        "不得让门、电梯或人物位置跳变。"
    ),
    "tailframe_handoff": (
        "调用尾帧承接镜头库：最后一镜必须写清人物位置、道具状态、视线方向和下一段可继承起点。"
    ),
    "authority_pressure": (
        "调用权力压迫镜头库：稳定关系景建立空间 -> 说话者半身承压 -> 听者/群体反应 -> 群体退让或沉默尾帧；"
        "少写空间坐标，多写可见调度。"
    ),
    "editing_ellipsis": (
        "调用剪辑省略规则：走路、上车、开门、进入新空间等无戏剧增量过程只保留起点帧和终点帧；"
        "用机位/景别/主体切换自然省略中间时间。"
    ),
    "shot_language_variety": (
        "调用镜头多样性规则：围绕同一戏剧动作安排有动机的关系景、过肩、反应、局部或尾帧镜头；"
        "不得连续三个镜头重复同一景别、同一机位或同一主体。"
    ),
    "rhythm_alignment": (
        "调用节奏联动规则：继承节奏总控给镜头导演的精简操作单；"
        "若与原剧本事实、拆片边界、空间连续性冲突，按上游事实和连续性优先。"
    ),
}

_SHOT_LIBRARY_TASK_KNOWLEDGE_HINTS = {
    "long_dialogue_coverage": (
        "04_对白与表演镜头规则",
        "21_镜头调用规则与多机位模板 R-012 声画错位剪辑 J-Cut L-Cut R-034 反应切出",
        "22_多机位分镜与镜头多样性规则 反站桩正反打 过肩 反应特写",
        "SHOT-DIALOGUE-COVERAGE-001",
        "SHOT-DIALOGUE-PAUSE-001",
        "CASE_拍摄剪辑_切出镜头_访谈对话与情感片段技巧",
        "CASE_拍摄设计_对话场景的景别变化与情绪放大",
    ),
    "impact_reaction": (
        "26_动作调度与受击覆盖规则",
        "ACTION-COLLISION-001",
        "SHOT-COMPLEX-ACTION-DEGRADE-001",
        "SHOT-ACTION-APEX-PRECUT-001",
        "BLOCKING-REACTION-COVERAGE-002",
        "CASE_镜头叙事_如何用镜头讲故事16_街边相撞与文件落地",
    ),
    "reveal_insert_reaction": (
        "03_镜头切换与推进规则 信息看清 切点",
        "21_镜头调用规则与多机位模板 R-034 反应切出 R-037 特写锚点转场",
        "23_视频教学提取_全场景分镜与转场库 插入镜头 切出镜头",
        "CASE_导演叙事技巧_如何讲故事与镜头信息组织",
        "CASE_拍摄剪辑_用反拍剪辑叙事的镜头拆解",
    ),
    "door_threshold_continuity": (
        "06_连续性与安全规则",
        "CONT-DOOR-MONOTONIC-001",
        "22_多机位分镜与镜头多样性规则 电梯 按钮 门口",
        "CASE_拍摄剪辑_动作匹配与连续动作衔接",
        "CASE_剪辑转场_动作转场与相似动作匹配",
    ),
    "tailframe_handoff": (
        "18_情绪锚点与逐段交互与仰拍限制补丁",
        "REF-TAILFRAME-PRIORITY-001",
        "TAILFRAME-RELATIONSHOT-001",
        "RHYTHM-REACTION-MIN-001",
        "CASE_镜头叙事_分别场景的七镜头电影感设计",
    ),
    "authority_pressure": (
        "21_镜头调用规则与多机位模板 权力压迫 景别收缩 反应切出",
        "22_多机位分镜与镜头多样性规则 反站桩正反打",
        "SHOT-CONFLICT-COVERAGE-001",
        "CASE_拍摄设计_双人对话到情绪爆发的机位推进",
        "CASE_镜头叙事_情绪升级时的景别递进与压迫感",
    ),
    "editing_ellipsis": (
        "05_剧本拆分与15秒片段规划规则 时间压缩与冗余动作省略",
        "22_多机位分镜与镜头多样性规则 机位切换即减法 上车 开门 进入新空间",
        "CASE_剪辑转场_动作转场与相似动作匹配",
    ),
    "shot_language_variety": (
        "22_多机位分镜与镜头多样性规则 镜头多样性自检 反站桩正反打",
        "21_镜头调用规则与多机位模板 多机位覆盖 景别递进",
        "02_焦段景深与景别画幅策略 景别限频 竖屏特写限制",
    ),
    "rhythm_alignment": (
        "00_知识库优先级与冲突裁决规则 atmosphere_strategy 是建议不是硬指令",
        "15_故事节奏控制规则 节奏层级合法性",
        "21_镜头调用规则与多机位模板 把节奏判断翻译成画面执行",
    ),
    "continuity_lock": (
        "06_连续性与安全规则",
        "21_镜头调用规则与多机位模板 动作匹配剪辑",
        "22_多机位分镜与镜头多样性规则",
    ),
}

_SHOT_LIBRARY_TASK_FORCED_USAGE = {
    "long_dialogue_coverage": (
        "必须至少安排一次说话者外的画面承载台词后半句：听者反应、过肩反应、面部特写或道具切出任选其一；"
        "cut_point 写明台词断点或压迫落点，audio 可写 OS/J-cut/L-cut。"
    ),
    "impact_reaction": (
        "必须把冲撞/受击拆成至少两个镜头责任：动作起势或命中瞬间 + 受击者反应/结果状态；"
        "cut_point 写动作顶点、接触瞬间或反应出现。"
    ),
    "reveal_insert_reaction": (
        "必须安排信息可读镜头或近景，并在信息看清后给人物反应；"
        "cut_point 不得早于信息可读。"
    ),
    "door_threshold_continuity": (
        "必须写清门/电梯/入口状态的单向变化和人物相对位置；"
        "不得出现门重新打开、人物瞬移或机位退入墙/电梯。"
    ),
    "tailframe_handoff": (
        "最后一个镜头必须承担尾帧职责，写清人物位置、视线、道具和下一段可继承状态。"
    ),
    "authority_pressure": (
        "必须用景别或机位变化体现压力递进：关系景/过肩建立 -> 单人近景或反应镜头 -> 尾帧压住；"
        "不得全程均速正反打。"
    ),
    "editing_ellipsis": (
        "必须标出至少一个可省略的无戏剧增量过程或说明本片段没有可省略项；"
        "上车/开门/走路/进入新空间优先用机位切换保留关键瞬间，不拍完整过程。"
    ),
    "shot_language_variety": (
        "同一片段有3个及以上镜头时，必须至少变化一种维度：拍摄主体、景别、视角/机位、声音承载或镜头任务；"
        "不得连续三个镜头使用同一景别+同一视角。"
    ),
    "rhythm_alignment": (
        "必须把上游情绪曲线和节奏意图翻译为镜头时长、停顿、反应归属、切镜点或尾帧；"
        "若节奏建议与原剧本/拆片边界/连续性冲突，写在节奏字段中说明以事实和连续性为准。"
    ),
    "continuity_lock": (
        "必须先建立空间轴线和人物关系，再安排动作/对白/信息落点，最后交代尾帧。"
    ),
}


def _infer_retrieval_tags(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    return [tag for tag, needles in mapping.items() if any(needle and needle in text for needle in needles)]


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = (item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _detect_shot_library_tasks(text: str) -> list[str]:
    task_keys = [
        task_key
        for task_key, needles in _SHOT_LIBRARY_TASK_KEYWORDS.items()
        if any(needle and needle in (text or "") for needle in needles)
    ]
    if not task_keys:
        task_keys.append("continuity_lock")
    return _unique_preserve_order(task_keys)


def _knowledge_hints_for_tasks(task_keys: list[str]) -> list[str]:
    hints: list[str] = []
    for task_key in task_keys:
        hints.extend(_SHOT_LIBRARY_TASK_KNOWLEDGE_HINTS.get(task_key, ()))
    return _unique_preserve_order(hints)


def _build_shot_director_signal_retrieval_profile(
    *,
    planner_output: str,
    atmosphere_strategy: str,
    director_brief: str,
    aspect_ratio: str,
) -> dict[str, Any]:
    signal_text = "\n".join(
        part for part in (planner_output, atmosphere_strategy, director_brief, aspect_ratio) if part
    )
    scene_types = _infer_retrieval_tags(signal_text, _SHOT_SCENE_TYPE_HINTS)
    events = _infer_retrieval_tags(signal_text, _SHOT_EVENT_TAG_HINTS)
    risks = _infer_retrieval_tags(signal_text, _SHOT_RISK_TAG_HINTS)
    dialogue_types = _infer_retrieval_tags(signal_text, _SHOT_DIALOGUE_TAG_HINTS)
    signals = _infer_retrieval_tags(signal_text, _SHOT_SIGNAL_TAG_HINTS)
    task_keys = _detect_shot_library_tasks(signal_text)
    knowledge_hints = _knowledge_hints_for_tasks(task_keys)

    event_by_task = {
        "long_dialogue_coverage": "dialogue",
        "impact_reaction": "collision",
        "reveal_insert_reaction": "reveal",
        "door_threshold_continuity": "door_state",
        "tailframe_handoff": "tailframe",
        "authority_pressure": "reaction",
        "editing_ellipsis": "motion_ellipsis",
        "shot_language_variety": "shot_variety",
        "rhythm_alignment": "rhythm_alignment",
    }
    risk_by_task = {
        "impact_reaction": "romanticize_collision",
        "door_threshold_continuity": "door_state_jump",
        "long_dialogue_coverage": "dialogue_integrity",
        "shot_language_variety": "shot_monotony",
    }

    events.extend(event_by_task[task_key] for task_key in task_keys if task_key in event_by_task)
    risks.extend(risk_by_task[task_key] for task_key in task_keys if task_key in risk_by_task)
    signals.extend(
        [
            "shot_library_routing",
            "upstream_director_contract",
            "source_event_coverage",
            "editing_ellipsis",
            "shot_variety",
            "rhythm_alignment",
        ]
    )

    return {
        "scene_types": _unique_preserve_order(scene_types),
        "events": _unique_preserve_order(events),
        "risks": _unique_preserve_order(risks),
        "dialogue_types": _unique_preserve_order(dialogue_types),
        "signals": _unique_preserve_order(signals),
        "aspect_ratio": aspect_ratio,
        "tags": _unique_preserve_order(
            [
                "镜头库调用",
                "多机位模板",
                "镜头多样性",
                "机位切换减法",
                "剪辑省略",
                "节奏联动",
                "上游导演约束",
                "故事节奏控制",
                *task_keys,
                *knowledge_hints,
            ]
        ),
        "reusable_pattern": _unique_preserve_order([*task_keys, *knowledge_hints]),
        "visual_constraints": _unique_preserve_order(
            [
                "必须把检索到的剪辑/镜头库规则转成镜头、切镜点、连续性、声音，不得只写原则",
                "必须优先使用本片段剧情信号匹配到的 CASE 案例和规则卡",
                "节奏总控建议只负责镜头层操作约束；镜头导演必须按原剧本事实、拆片边界和连续性规则合法落地",
                "同一片段不得无理由连续重复同一景别/视角/主体；需要用有动机的镜头语言变化避免一镜到底和站桩正反打",
            ]
        ),
        "served_agents": ["shot_director"],
        "final_top_k": 10,
        "bm25_top_k": 14,
        "vector_top_k": 14,
        "max_chunks_per_source": 2,
    }


def _shot_library_signal_task_card(
    *,
    planner_output: str,
    atmosphere_strategy: str,
    director_brief: str,
    aspect_ratio: str,
) -> str:
    sections = _extract_yaml_sections(planner_output or "")
    if not sections and planner_output:
        sections = [planner_output]

    rhythm_notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    lines = [
        "[镜头库调用任务单]",
        "先读上游导演资产，再按剧情信号调用镜头库；镜头库只能服务拆片规划里的原剧本事件，不能扩写新剧情。",
        "节奏总控只提供给镜头导演的精简操作单；若与原剧本事实、拆片边界、空间连续性冲突，必须以后者为准。",
        "每个片段必须先判断剪辑省略点和镜头语言变化策略，再生成镜头列表；不要默认一镜到底或机械正反打。",
        f"画幅约束: {aspect_ratio}",
    ]
    if director_brief:
        lines.append(f"总导演意图: {_truncate_for_prompt(director_brief, 260)}")
    if rhythm_notes:
        lines.append(f"节奏总控约束: {_truncate_for_prompt(rhythm_notes, 360)}")

    if not sections:
        lines.extend(
            [
                "- 片段编号: unknown",
                "  检测到的剧情信号: 连续性锁定",
                "  镜头库任务:",
                "    - 先建立人物关系和空间轴线，再覆盖动作/对白/信息，最后交代尾帧承接。",
            ]
        )
        return "\n".join(lines)

    for index, section in enumerate(sections, start=1):
        fragment_id = _extract_fragment_id(section) or f"F{index:02d}"
        source_events = _source_script_events(section)
        signal_text = "\n".join([section, "\n".join(source_events), rhythm_notes, director_brief])
        task_keys = _detect_shot_library_tasks(signal_text)
        knowledge_hints = _knowledge_hints_for_tasks(task_keys)
        event_preview = " / ".join(_truncate_for_prompt(event, 80) for event in source_events[:3])
        lines.extend(
            [
                f"- 片段编号: {fragment_id}",
                f"  上游原文事件: {event_preview or '以当前片段规划资产为准'}",
                f"  检测到的剧情信号: {', '.join(task_keys)}",
                f"  必须检索的知识: {', '.join(knowledge_hints) if knowledge_hints else '通用镜头连续性规则'}",
                "  冲突裁决: 原剧本事实 > 拆片边界 > 连续性/空间安全 > 节奏总控建议 > 镜头美学",
                "  镜头库任务:",
            ]
        )
        for task_key in task_keys:
            task_rule = _SHOT_LIBRARY_TASK_RULES.get(
                task_key,
                "先建立人物关系和空间轴线，再覆盖动作/对白/信息，最后交代尾帧承接。",
            )
            lines.append(f"    - {task_rule}")
            forced_rule = _SHOT_LIBRARY_TASK_FORCED_USAGE.get(task_key)
            if forced_rule:
                lines.append(f"      强制落地: {forced_rule}")
    return "\n".join(lines)


def _run_shot_director_single_pass_impl(
    *,
    script: str,
    planner_output: str,
    atmosphere_strategy: str,
    aspect_ratio: str,
    expected_segments: list[str],
    images_base64: list[str] | None,
    director_hint: str,
    scene_reference_context: str = "",
    director_brief: str = "",
    stage_callback: Callable[[str, str, dict[str, Any], dict[str, dict[str, Any]]], None] | None = None,
    resume_stage_outputs: dict[str, str] | None = None,
    resume_stage_runtime: dict[str, dict[str, Any]] | None = None,
    resume_stage_meta: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Simplified single-pass shot director with lean YAML output schema."""
    director_brief_block = _director_brief_prompt_block(director_brief)
    signal_task_card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief=director_brief,
        aspect_ratio=aspect_ratio,
    )
    downstream_context = _shot_director_downstream_context(planner_output, atmosphere_strategy, aspect_ratio)
    if director_brief_block:
        downstream_context = director_brief_block + "\n" + downstream_context
    if scene_reference_context:
        downstream_context = downstream_context + "\n" + scene_reference_context.strip() + "\n"
    downstream_context = downstream_context + "\n" + signal_task_card + "\n"
    rule_block = _shot_director_rule_block(aspect_ratio)
    workflow_contract = _shot_director_workflow_contract()
    workflow_trace = _build_shot_director_workflow_trace(
        planner_output=planner_output,
        expected_segments=expected_segments,
        atmosphere_strategy=atmosphere_strategy,
        director_brief=director_brief,
        aspect_ratio=aspect_ratio,
    )
    rhythm_shot_notes_prompt = _rhythm_shot_director_notes_prompt(atmosphere_strategy)
    resume_stage_outputs = resume_stage_outputs or {}
    resume_stage_runtime = resume_stage_runtime or {}
    stage_meta: dict[str, dict[str, Any]] = dict(resume_stage_meta or {})
    stage_outputs: dict[str, str] = {}

    # Check if we can resume from a previous "final" output (single-pass schema)
    existing_final = resume_stage_outputs.get("final", "").strip()
    if existing_final:
        raw_final_output = _clean_shot_director_output(existing_final)
        final_output = _repair_shot_director_output_contracts(raw_final_output, script)
        final_runtime = dict(resume_stage_runtime.get("final") or {})
        final_runtime.setdefault("agent_name", "shot_director")
        final_runtime.setdefault("mode", "resume")
        final_runtime.setdefault("status", "reused")
        final_runtime["resume_source"] = "pipeline_state"
        final_runtime["auto_repair_applied"] = final_output != raw_final_output
        final_runtime["output_chars"] = len(final_output)
        stage_meta.setdefault("final", {"retrieval_mode": "reused_from_pipeline_state"})
        print("  [shot_director] reuse persisted shot_director final; skip LLM call")
    else:
        hint = (
            "镜头导演 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制 切镜 受击者 炸点 对白 "
            "信息冲击 动作接续 人物关系 场面总控 节奏 子分镜 戏剧微粒 权力反转 悬念揭示 "
            "误解错位 9:16 半身中景 特写限频 微细节镜头"
        )
        hint = hint.replace("9:16", str(aspect_ratio or "aspect_ratio_unspecified"))
        retrieval_profile = _build_shot_director_signal_retrieval_profile(
            planner_output=planner_output,
            atmosphere_strategy=atmosphere_strategy,
            director_brief=director_brief,
            aspect_ratio=aspect_ratio,
        )
        system_prompt, final_meta = build_system_prompt(
            "你是一位镜头导演。你的职责是为每个片段设计时间轴上的镜头序列。\n\n"
            "【镜头库调用方式】\n"
            "你必须先根据【镜头库调用任务单】识别当前片段属于对白覆盖、受击/碰撞、信息揭示、门/电梯阈值、尾帧承接或权力压迫等哪类镜头任务，"
            "再从知识库里的镜头库、多机位模板和连续性规则中选择合适结构。"
            "镜头选择必须继承总导演意图、节奏总控和结构规划中的原文事件；不得为了套模板新增剧情。"
            "节奏总控只提供片段边界、情绪曲线、节奏意图、必须保留落点、可压缩弱拍和尾帧承接，不是镜头硬模板；"
            "你负责自行决定镜头数、景别、机位、运镜、镜头时长和切镜点。\n\n"
            "【输出语言硬规则】\n"
            "最终 YAML 必须使用中文字段名，不要输出任何旧版英文字段名。\n\n"
            "【每个片段必须交付】\n"
            "1. 片段任务 — 本片段的剧情施工任务，例如建立关系、冲突升级、信息揭示、反应落点、权力反转、喜剧泄压、尾帧钩子。\n"
            "2. 节奏 — 继承节奏总控给镜头导演的情绪曲线和节奏意图，写清哪些戏剧落点必须保留、哪些弱拍可以压缩、哪里需要停顿；镜头数和切镜方案由本阶段规划。\n\n"
            "3. 空间连续性总控 — 写在镜头列表前，说明本段是什么戏剧任务、哪些人物处在同一空间内；单人镜只改变拍摄主体，不代表其他在场人物离开。\n\n"
            "【每个镜头必须回答】\n"
            "1. 时长 — 该镜头在片段内的时间段，必须连续，例如 0-2秒、2-5秒。\n"
            "2. 镜头任务 — 这个镜头负责什么：建立关系、承载对白、动作推进、信息揭示、反应落点、尾帧承接等。\n"
            "3. 拍摄主体 — 拍谁（人物名、双人关系或剧本已有道具）。\n"
            "4. 镜头 — 只写摄影选择：景别 + 简洁机位/视角 + 必要运镜/前景关系；不要写人物动作、台词、表情或戏剧判断。\n"
            "5. 画面动作 — 写人物动作表情链：起始状态、动作变化、视线/表情/身体反应、镜尾状态；只写可见内容，不写心理解释。\n"
            "6. 台词 — 原剧本台词、画外音或 ~；不得新增台词。\n"
            "7. 必须承载 — 这个镜头必须看清的信息、道具状态、人物距离变化或表演落点，不写抽象戏剧效果。\n"
            "8. 切镜点 — 具体切镜触发点，必须绑定动作顶点、台词断点、信息看清、反应出现、状态完成或尾帧。\n"
            "9. 连续性 — 动作、道具、人物左右关系、轴线或尾帧状态如何继承。\n\n"
            "【可选字段】\n"
            "- 类型 — 只在非标准镜头时写：受击反应、道具/信息特写、切离镜头。\n"
            "- 声音 — 只在需要画外音、声音先行或声音延续时写。\n\n"
            "【镜头设计原则】\n"
            "1. 事实红线高于一切：不新增剧本外的人物、台词、动作、道具或情节。\n"
            "2. 节奏总控决定情绪曲线、节奏意图、必须保留落点、可压缩弱拍和结尾状态；镜头导演决定镜头数、镜头时长、景别、机位、主体、声音和剪辑方式。\n"
            "3. 长台词或高压命令必须拆出视觉覆盖：说话者起句、同侧听者反应/过肩、必要时后半句以画外音、声音先行或声音延续落到反应上。\n"
            "4. 切镜点不许只写\"切出/继续/增强情绪\"，必须写清触发物，例如动作顶点、台词断点、信息看清、反应出现、门关闭完成、尾帧状态稳定。\n"
            "5. 片段编号必须沿用拆片方案的 F01/F02/F03...，不得改名合并跳号。\n"
            "6. 同一片段有3个及以上镜头时，必须变化主体、景别、视角/机位、声音承载或镜头任务；不得把同侧固定机位或中近景当默认答案。\n"
            "7. 走路、上车、开门、进入新空间等无戏剧增量过程优先用机位/景别/主体切换省略，只保留关键起点帧和终点帧。\n"
            "8. 镜头语言要按任务大胆选择：动作密集可用侧面跟拍或局部特写，人物抗拒或退缩可用低机位贴近人物，安抚或劝说可用肩后过肩或双人半身关系景；同侧只是不越轴，不是固定机位模板。局部特写的具体对象必须来自当前剧本动作或已有道具，不得把某一剧集的细节固化成通用模板。\n"
            "9. 道具接触和身体接触必须写清动作阶段、道具归属、接触边界和镜尾状态，避免项链、手、脖颈、衣物在相邻镜头中跳变。\n"
            "10. 冲突裁决顺序：原剧本事实 > story_planner片段边界 > 连续性/空间安全 > 节奏总控建议 > 镜头美学。\n"
            f"11. 画幅：{aspect_ratio}",
            "shot_director",
            context_hint=hint,
            retrieval_profile=retrieval_profile,
        )
        stage_meta["final"] = final_meta
        if director_brief_block:
            system_prompt = system_prompt + "\n\n" + director_brief_block
        user_prompt = (
            "基于以下素材，为每个片段设计时间轴上的镜头序列，输出 YAML 格式。\n\n"
            f"{workflow_contract}\n"
            f"{downstream_context}\n\n"
            "【输出 YAML 结构】\n"
            "- 片段编号: F01\n"
            "  片段任务: 本片段的剧情施工任务\n"
            "  节奏: 服从节奏总控的节奏指令\n"
            "  空间连续性总控: 本片段是一段具体戏剧任务；人物始终处在同一空间内；单人镜只改变拍摄主体，不代表其他在场人物离开；每一镜继承上一镜尾帧、道具状态和同侧轴线\n"
            "  镜头列表:\n"
            "    - 镜头编号: F01-S01\n"
            "      时长: 0-2秒\n"
            "      镜头任务: 建立关系/承载对白/动作推进/信息揭示/反应落点/尾帧承接\n"
            "      拍摄主体: 人物名/双人关系/剧本已有道具\n"
            "      镜头: 只写摄影选择，例如乔熙胸部以上中近景，车内同侧过肩机位\n"
            "      画面动作: 起始状态 -> 动作变化 -> 视线/表情/身体反应 -> 镜尾状态\n"
            "      台词: 原剧本台词/画外音或 ~\n"
            "      必须承载: 这个镜头必须看清的信息、道具状态、人物距离变化或表演落点\n"
            "      切镜点: 动作顶点/台词断点/信息看清/反应出现/状态完成/尾帧\n"
            "      连续性: 动作、道具、人物左右关系、轴线或尾帧状态如何继承\n"
            "      类型: 受击反应/道具信息特写/切离镜头（非标准镜头时写）\n"
            "      声音: 画外音/声音先行/声音延续（需要时写）\n\n"
            "【关键要求】\n"
            "1. 必须覆盖拆片方案的所有片段编号。\n"
            "2. 必须继承节奏总控给镜头导演的情绪曲线、节奏意图、必须保留落点、可压缩弱拍和尾帧承接，并把它们落实到镜头时长、镜头任务、画面动作、切镜点、连续性；冲突时以原剧本、拆片边界和连续性为准。\n"
            "3. 长台词或高压命令必须插入听者反应覆盖，不能站桩正反打。\n"
            "4. 保持片段编号和镜头编号稳定，遵循 F01/F02... 和 F01-S01/F01-S02... 格式。\n"
            "5. 台词只能使用原剧本文字、原剧本画外音或写 ~；不得新增台词。\n"
            "6. 只有剧本已有信息载体才能成为拍摄主体；不要新增空镜、道具或环境信息。\n"
            "7. 每个镜头的时间段必须连续，前后衔接。\n"
            "8. 不要输出任何英文字段名；字段名必须使用上面的中文写法。\n\n"
            "9. 每个片段必须在镜头列表前输出【空间连续性总控】，供 prompt_compiler 写入【空间与首帧总控】；它必须明确“同一空间、同一人物组、单人镜不等于其他人物消失”。\n\n"
            "10. 每个片段必须执行【镜头库调用任务单】里的镜头库任务：先判断剧情信号，再决定镜头结构和切点；"
            "如果任务单与原剧本事件冲突，以原剧本事件和拆片边界为准。\n\n"
            "11. 每个片段必须主动判断剪辑省略点和镜头语言变化策略；不要让一个中景/同一机位吃完整段戏，不要连续堆同侧固定机位和中近景。\n\n"
            "12. 镜头字段不得混入人物动作或戏剧判断；动作、表情、视线、呼吸、肩颈、手部、道具接触和动作逻辑必须写进画面动作、必须承载和连续性。\n\n"
            f"{_shot_director_coverage_contract_prompt()}\n"
            f"{rule_block}"
            "请只输出完整 YAML 镜头方案。"
        )
        # Simple check for whether to split by fragment
        if _shot_stage_should_split(expected_segments, downstream_context):
            stage_meta["final"]["split_by_fragment"] = True

            def build_fragment_prompt(fragment_id: str, fragment_context: str, _fragment_contract: str) -> str:
                return (
                    f"【任务】\n只为 {fragment_id} 设计镜头序列。\n\n"
                    f"{scene_reference_context.strip() + chr(10) + chr(10) if scene_reference_context else ''}"
                    f"{signal_task_card}\n\n"
                    f"{fragment_context}\n\n"
                    "【工作流】\n"
                    f"{workflow_contract}\n"
                    f"{_shot_director_coverage_contract_prompt()}\n"
                    f"{rhythm_shot_notes_prompt}"
                    "【输出 YAML 字段，必须全中文】\n"
                    "- 片段编号\n"
                    "- 片段任务\n"
                    "- 节奏\n"
                    "- 镜头列表\n"
                    "- 镜头编号\n"
                    "- 时长\n"
                    "- 镜头任务\n"
                    "- 拍摄主体\n"
                    "- 镜头\n"
                    "- 画面动作\n"
                    "- 台词\n"
                    "- 必须承载\n"
                    "- 切镜点\n"
                    "- 连续性\n"
                    "- 类型（可选：受击反应/道具信息特写/切离镜头）\n"
                    "- 声音（可选：画外音/声音先行/声音延续）\n\n"
                    "【规则】\n"
                    "1. 只输出这个片段的 YAML，并且第一行必须是 '- 片段编号:'。\n"
                    "2. 镜头编号保持稳定，例如 F01-S01、F01-S02。\n"
                    "3. 时长必须是片段内连续时间段，例如 0-2秒、2-5秒。\n"
                    "4. 长对白需要听者反应覆盖和具体切镜点。\n"
                    "5. 不新增剧本外元素。\n"
                    "6. 不要输出任何英文字段名或旧版字段。\n"
                    "只输出 YAML。"
                )

            def persist_fragment(fragment_stage_name: str, fragment_output: str, fragment_runtime: dict[str, Any]) -> None:
                if stage_callback:
                    stage_callback(fragment_stage_name, fragment_output, fragment_runtime, dict(stage_meta))

            final_output, final_runtime = _call_stage_split_by_fragment(
                stage_key="shot_director",
                system_prompt=system_prompt,
                expected_segments=expected_segments,
                planner_output=planner_output,
                aspect_ratio=aspect_ratio,
                contract_output="",
                prompt_builder=build_fragment_prompt,
                images_base64=images_base64,
                progress_callback=persist_fragment,
                resume_fragment_outputs=resume_stage_outputs,
                resume_fragment_runtime=resume_stage_runtime,
            )
        else:
            final_output, final_runtime = _call_shot_director_stage(
                stage_key="shot_director",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                images_base64=images_base64,
            )
        raw_final_output = final_output
        final_output = _repair_shot_director_output_contracts(final_output, script)
        final_runtime["auto_repair_applied"] = final_output != raw_final_output

    # Validate output. In split-by-fragment mode, do not spend another large LLM
    # call on final repair: all fragments have already been generated/reused and
    # the timeout-prone repair pass can strand the pipeline after F05 with no
    # persisted final output. Persist the deterministic merge first and let the
    # later guard/report surface any issues without blocking progress.
    final_issues = _validate_shot_director_output(final_output, expected_segments)
    split_fragment_ids = [_segment_name_to_fragment_id(name) for name in expected_segments]
    final_fragment_ids = [_extract_fragment_id(section) for section in _extract_yaml_sections(final_output or "")]
    split_output_complete = bool(split_fragment_ids) and all(fragment_id in final_fragment_ids for fragment_id in split_fragment_ids)
    if final_issues and split_output_complete:
        final_runtime["repair_attempted"] = False
        final_runtime["repair_skipped_reason"] = "split_fragments_complete_accept_deterministic_merge"
        final_runtime["repair_validation_issues"] = final_issues
    elif final_issues and not existing_final:
        failed_fragment_ids = _fragment_ids_from_validation_issues(final_issues, expected_segments)
        repair_target_output = _filter_yaml_sections_by_fragment_ids(final_output, failed_fragment_ids)
        if not repair_target_output:
            repair_target_output = final_output
        repair_scope_line = (
            f"只修复这些失败片段：{', '.join(failed_fragment_ids)}；"
            "其他已生成片段视为可信，不要重写。"
            if failed_fragment_ids
            else "无法定位具体失败片段时，才允许修复完整 YAML。"
        )
        repair_prompt = (
            "shot_director 输出没有通过校验。请只修正 YAML，不要解释。\n\n"
            f"【返修范围】\n{repair_scope_line}\n\n"
            "【必须修复的问题】\n"
            + "\n".join(f"- {issue}" for issue in final_issues)
            + "\n\n【关键原则】\n"
            "1. 优先信任已分片输出，只修失败/缺失的片段编号。\n"
            "2. 每个返修片段必须有：片段编号、片段任务、节奏、空间连续性总控、镜头列表。\n"
            "3. 每个镜头必须有字段：镜头编号、时长、镜头任务、拍摄主体、镜头、画面动作、台词、必须承载、切镜点、连续性。\n"
            "4. 切镜点必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。\n"
            "5. 长台词必须插入听者反应镜头；不新增剧本外元素。\n\n"
            "6. 不要输出任何英文字段名；字段名必须全中文。\n\n"
            "【待修正 YAML（仅失败片段或定位失败时的完整 YAML）】\n"
            f"{repair_target_output}\n\n"
            f"{rule_block}"
            "请只输出返修范围内的 YAML 片段。"
        )
        repaired_fragment_output, repair_runtime = _call_shot_director_stage(
            stage_key="shot_director",
            system_prompt=system_prompt,
            user_prompt=repair_prompt,
            images_base64=None,
        )
        raw_repaired_final = repaired_fragment_output
        repaired_fragment_output = _repair_shot_director_output_contracts(repaired_fragment_output, script)
        repaired_final = _merge_repaired_yaml_sections(final_output, repaired_fragment_output, failed_fragment_ids)
        repaired_issues = _validate_shot_director_output(repaired_final, expected_segments)
        final_runtime["repair_attempted"] = True
        final_runtime["repair_scope"] = "failed_fragments" if failed_fragment_ids else "full_yaml"
        final_runtime["repair_fragment_ids"] = failed_fragment_ids
        final_runtime["repair_runtime"] = repair_runtime
        final_runtime["repair_auto_repair_applied"] = repaired_fragment_output != raw_repaired_final
        final_runtime["repair_validation_issues"] = repaired_issues
        if len(repaired_issues) <= len(final_issues):
            final_output = repaired_final
            final_issues = repaired_issues
    final_runtime["validation_issues"] = final_issues
    final_runtime["workflow_trace"] = workflow_trace
    final_stage_meta = stage_meta.setdefault("final", {})
    final_stage_meta["workflow_stages"] = list(_SHOT_DIRECTOR_WORKFLOW_STAGES)
    final_stage_meta["coverage_contract_fields"] = list(_SHOT_COVERAGE_CONTRACT_FIELDS)
    stage_outputs["final"] = final_output
    if stage_callback:
        stage_callback("final", final_output, final_runtime, dict(stage_meta))

    # Single-pass output is final - return it directly
    runtime = {
        "final": final_runtime,
        "final_source": "final",
        "workflow_trace": workflow_trace,
    }
    return final_output, runtime, stage_meta, stage_outputs

def _run_shot_director_single_pass(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Public package entry for the migrated shot_director single-pass flow."""
    return _run_shot_director_single_pass_impl(*args, **kwargs)


def _run_shot_director_three_stage(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    return _run_shot_director_three_stage_impl(*args, **kwargs)


def _run_shot_director_three_stage_impl(
    *,
    script: str,
    planner_output: str,
    atmosphere_strategy: str,
    aspect_ratio: str,
    expected_segments: list[str],
    images_base64: list[str] | None,
    director_hint: str,
    scene_reference_context: str = "",
    director_brief: str = "",
    stage_callback: Callable[[str, str, dict[str, Any], dict[str, dict[str, Any]]], None] | None = None,
    resume_stage_outputs: dict[str, str] | None = None,
    resume_stage_runtime: dict[str, dict[str, Any]] | None = None,
    resume_stage_meta: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Fused staged shot director: layout/task safety -> blocking/language -> guard/final."""
    director_brief_block = _director_brief_prompt_block(director_brief)
    signal_task_card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief=director_brief,
        aspect_ratio=aspect_ratio,
    )
    downstream_context = _shot_director_downstream_context(planner_output, atmosphere_strategy, aspect_ratio)
    if director_brief_block:
        downstream_context = director_brief_block + "\n" + downstream_context
    if scene_reference_context:
        downstream_context = downstream_context + "\n" + scene_reference_context.strip() + "\n"
    downstream_context = downstream_context + "\n" + signal_task_card + "\n"
    workflow_contract = _shot_director_workflow_contract()
    workflow_trace = _build_shot_director_workflow_trace(
        planner_output=planner_output,
        expected_segments=expected_segments,
        atmosphere_strategy=atmosphere_strategy,
        director_brief=director_brief,
        aspect_ratio=aspect_ratio,
    )
    base_profile = _build_shot_director_signal_retrieval_profile(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief=director_brief,
        aspect_ratio=aspect_ratio,
    )
    resume_stage_outputs = resume_stage_outputs or {}
    resume_stage_runtime = resume_stage_runtime or {}
    stage_meta: dict[str, dict[str, Any]] = dict(resume_stage_meta or {})
    stage_outputs: dict[str, str] = {}
    runtimes: dict[str, Any] = {}

    existing_final = (resume_stage_outputs.get("final") or "").strip()
    if existing_final:
        raw_final_output = _clean_shot_director_output(existing_final)
        final_output = _repair_shot_director_output_contracts(raw_final_output, script)
        final_runtime = dict(resume_stage_runtime.get("final") or {})
        final_runtime.setdefault("agent_name", "shot_director_guard")
        final_runtime.setdefault("mode", "resume")
        final_runtime.setdefault("status", "reused")
        final_runtime["resume_source"] = "pipeline_state"
        final_runtime["auto_repair_applied"] = final_output != raw_final_output
        final_runtime["workflow_trace"] = workflow_trace
        stage_meta.setdefault("final", {"retrieval_mode": "reused_from_pipeline_state"})
        stage_outputs["final"] = final_output
        runtimes["final"] = final_runtime
        runtimes["final_source"] = "final"
        runtimes["workflow_trace"] = workflow_trace
        if stage_callback:
            stage_callback("final", final_output, final_runtime, dict(stage_meta))
        return final_output, runtimes, stage_meta, stage_outputs

    def persist(stage_name: str, output: str, runtime: dict[str, Any], retrieval_meta: dict[str, Any]) -> None:
        stage_outputs[stage_name] = output
        runtimes[stage_name] = runtime
        stage_meta[stage_name] = retrieval_meta
        if stage_callback:
            stage_callback(stage_name, output, runtime, dict(stage_meta))

    def stage_fragment_resume(stage_name: str) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
        outputs_by_fragment: dict[str, str] = {}
        runtimes_by_fragment: dict[str, dict[str, Any]] = {}
        prefix = f"{stage_name}_"
        for key, value in resume_stage_outputs.items():
            if key.startswith(prefix + "fragment_"):
                outputs_by_fragment[key.removeprefix(prefix)] = value
            elif key.startswith("fragment_"):
                outputs_by_fragment.setdefault(key, value)
        for key, value in resume_stage_runtime.items():
            if key.startswith(prefix + "fragment_"):
                runtimes_by_fragment[key.removeprefix(prefix)] = value
            elif key.startswith("fragment_"):
                runtimes_by_fragment.setdefault(key, value)
        return outputs_by_fragment, runtimes_by_fragment

    def run_stage(
        *,
        stage_name: str,
        agent_name: str,
        role_description: str,
        context_hint: str,
        retrieval_profile: dict[str, Any],
        user_prompt: str,
        contract_output: str,
        prompt_builder: Callable[[str, str, str], str],
        images: list[str] | None,
    ) -> str:
        existing = (resume_stage_outputs.get(stage_name) or "").strip()
        retrieval_meta = stage_meta.get(stage_name)
        if existing:
            output = _clean_shot_director_output(existing)
            runtime = dict(resume_stage_runtime.get(stage_name) or {})
            runtime.setdefault("agent_name", agent_name)
            runtime.setdefault("mode", "resume")
            runtime.setdefault("status", "reused")
            retrieval_meta = retrieval_meta or {"retrieval_mode": "reused_from_pipeline_state"}
            persist(stage_name, output, runtime, retrieval_meta)
            return output

        system_prompt, retrieval_meta = build_system_prompt(
            role_description,
            agent_name,
            context_hint=context_hint,
            retrieval_profile=retrieval_profile,
        )
        if _shot_stage_should_split(expected_segments, contract_output + "\n" + downstream_context):
            fragment_outputs, fragment_runtime = stage_fragment_resume(stage_name)

            def persist_fragment(fragment_stage_name: str, fragment_output: str, fragment_runtime_item: dict[str, Any]) -> None:
                if stage_callback:
                    stage_callback(f"{stage_name}_{fragment_stage_name}", fragment_output, fragment_runtime_item, dict(stage_meta))

            output, runtime = _call_stage_split_by_fragment(
                stage_key=agent_name,
                system_prompt=system_prompt,
                expected_segments=expected_segments,
                planner_output=planner_output,
                aspect_ratio=aspect_ratio,
                contract_output=contract_output,
                prompt_builder=prompt_builder,
                images_base64=images,
                progress_callback=persist_fragment,
                resume_fragment_outputs=fragment_outputs,
                resume_fragment_runtime=fragment_runtime,
            )
        else:
            output, runtime = _call_shot_director_stage(
                stage_key=agent_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                images_base64=images,
            )
        persist(stage_name, output, runtime, retrieval_meta)
        return output

    layout_rules = _shot_director_layout_rule_block(aspect_ratio)
    layout_profile = _shot_director_stage_profile(
        base_profile,
        served_agent="shot_director_layout",
        extra_signals=["layout_blueprint", "space_axis", "dramatic_task_mapping", "editing_ellipsis"],
        extra_tags=["一号摆位导演", "主分镜骨架", "镜头任务与空间安全"],
        extra_constraints=[
            "layout 阶段只搭主镜头覆盖链，不输出 reaction_coverage 或 sub_shots",
            "必须给 blocking 留下镜头语言机会，但不能抢动作重音细节",
        ],
    )
    layout_user_prompt = (
        "基于以下上游资产，执行阶段一：摆位导演 + 镜头任务与空间安全。\n\n"
        f"{workflow_contract}\n"
        f"{downstream_context}\n"
        f"{layout_rules}\n"
        "【输出 YAML 结构】\n"
        "- 片段编号: F01\n"
        "  片段任务: 本片段的戏剧施工任务\n"
        "  节奏: 上游情绪曲线/节奏意图/必须保留落点/可压缩弱拍/尾帧承接，以及阶段一自己的主镜头骨架判断\n"
        "  空间规则:\n"
        "    空间锚点: 场景、稳定布景、门槛或核心阻隔物\n"
        "    人物位置: 当前人物起点、朝向和关系\n"
        "    动作轴线: 主要视线/动作轴线和安全机位侧\n"
        "    安全机位区: 可拍且不越轴的机位区域\n"
        "    禁用机位区: 越轴、遮挡或物理不可能区域\n"
        "  主镜头列表:\n"
        "    - 镜头编号: F01-S01\n"
        "      镜头任务: 建立关系/行动起势/受击承接/关系复位/尾帧承接\n"
        "      拍摄主体: 人物名、双人关系或剧本已有道具\n"
        "      镜头: 主镜头骨架表达，景别 + 简洁机位 + 核心可见关系\n"
        "      覆盖职责: 本主镜头承担什么覆盖任务\n"
        "      切镜原因: 为什么需要切到这里\n"
        "      同场人物位置: 其他关键人物如何保留\n"
        "      状态变化: 此镜推进或保持什么状态\n"
        "      尾帧职责: 是否承担尾帧复位或下一段继承\n"
        "      对白覆盖: 原剧本台词或 ~，只做承载预案\n"
        "      选择理由: 绑定注意力、信息、空间或动作，不写好看\n"
        "      镜头语言机会: 留给二号调度的过肩/跟拍/局部特写/动作顶点前切/关系复位机会\n\n"
        "请只输出阶段一 YAML。"
    )
    layout_output = run_stage(
        stage_name="layout",
        agent_name="shot_director_layout",
        role_description=layout_rules,
        context_hint=f"{director_hint} layout 主分镜骨架 镜头任务 空间安全 轴线 剪辑省略",
        retrieval_profile=layout_profile,
        user_prompt=layout_user_prompt,
        contract_output=planner_output,
        prompt_builder=lambda fragment_id, fragment_context, _fragment_contract: (
            "只处理当前片段的阶段一摆位骨架。\n\n"
            f"{workflow_contract}\n{fragment_context}\n{signal_task_card}\n{layout_rules}\n"
            "请只输出该片段阶段一 YAML。"
        ),
        images=_shot_director_stage_images("shot_director_layout", images_base64),
    )
    layout_output = _repair_shot_layout_output(layout_output)
    persist("layout", layout_output, dict(runtimes.get("layout") or {}), stage_meta.get("layout", {}))

    blocking_rules = _shot_director_blocking_rule_block(aspect_ratio)
    blocking_profile = _shot_director_stage_profile(
        base_profile,
        served_agent="shot_director_blocking",
        extra_signals=["shot_language_selection", "reaction_coverage", "subshot_trigger", "action_state_chain"],
        extra_tags=["二号动作调度导演", "镜头语言主动选择", "多机位分镜", "自然镜头表达"],
        extra_constraints=[
            "必须把镜头库和案例技法转成具体镜头、切点、连续性和声音承载",
            "不得把同侧固定机位或中近景当默认答案",
            "局部特写对象必须来自当前剧本动作或已有道具",
            "镜头字段只写摄影选择，人物动作表情链必须写进画面动作",
        ],
    )
    blocking_user_prompt = (
        "基于阶段一输出，执行阶段二：动作调度导演 + 镜头语言选择。\n\n"
        f"{workflow_contract}\n"
        f"{downstream_context}\n"
        "【阶段一输出】\n"
        f"{layout_output}\n\n"
        f"{blocking_rules}\n"
        f"{_shot_director_coverage_contract_prompt()}\n"
        "【输出要求】\n"
        "1. 保留阶段一的片段编号、主镜头编号和空间规则。\n"
        "2. 补齐动作路径、对白落点、反应覆盖、状态链和必要子分镜。\n"
        "3. 正式选择镜头语言，但镜头字段只写景别、机位/视角、运镜或必要前景关系；不要在镜头字段写人物动作。\n"
        "4. 画面动作必须精细写出人物动作、表情、视线、呼吸、肩颈、手部、道具状态和镜尾状态。\n"
        "5. 不新增剧本外人物、台词、动作、道具或空间。\n"
        "请只输出阶段二 YAML。"
    )
    blocking_output = run_stage(
        stage_name="blocking",
        agent_name="shot_director_blocking",
        role_description=blocking_rules,
        context_hint=f"{director_hint} blocking 镜头语言选择 反应覆盖 子分镜 动作状态链 多机位",
        retrieval_profile=blocking_profile,
        user_prompt=blocking_user_prompt,
        contract_output=layout_output,
        prompt_builder=lambda fragment_id, fragment_context, fragment_contract: (
            "只处理当前片段的阶段二动作调度和镜头语言选择。\n\n"
            f"{workflow_contract}\n{fragment_context}\n{signal_task_card}\n"
            f"【阶段一当前片段输出】\n{fragment_contract}\n\n{blocking_rules}\n"
            f"{_shot_director_coverage_contract_prompt()}\n"
            "请只输出该片段阶段二 YAML。"
        ),
        images=_shot_director_stage_images("shot_director_blocking", images_base64),
    )

    guard_rules = _shot_director_guard_stage_rule_block(aspect_ratio)
    guard_profile = _shot_director_stage_profile(
        base_profile,
        served_agent="shot_director_guard",
        extra_signals=["minimal_repair", "final_yaml_handoff", "natural_expression", "compiler_ready"],
        extra_tags=["三号规则守门导演", "最小修复", "最终自然表达", "提示词编译交付"],
        extra_constraints=[
            "只修硬伤，不重写创意",
            "最终输出中文字段，镜头字段只保留摄影表达",
            "删除抽象构图术语和人物相对左右机位",
            "人物动作、表情和道具逻辑必须落在画面动作、必须承载和连续性",
        ],
    )
    guard_user_prompt = (
        "基于阶段二输出，执行阶段三：规则守门导演 + 最终自然表达。\n\n"
        f"{workflow_contract}\n"
        f"{downstream_context}\n"
        "【阶段二输出】\n"
        f"{blocking_output}\n\n"
        f"{guard_rules}\n"
        "请输出最终可交给 prompt_compiler 的完整中文 YAML；不要输出分析、不要输出英文字段名。"
    )
    final_output = run_stage(
        stage_name="final",
        agent_name="shot_director_guard",
        role_description=guard_rules,
        context_hint=f"{director_hint} guard 最小修复 最终中文 YAML 自然镜头表达 prompt_compiler",
        retrieval_profile=guard_profile,
        user_prompt=guard_user_prompt,
        contract_output=blocking_output,
        prompt_builder=lambda fragment_id, fragment_context, fragment_contract: (
            "只处理当前片段的阶段三守门和最终交付。\n\n"
            f"{fragment_context}\n"
            f"【阶段二当前片段输出】\n{fragment_contract}\n\n{guard_rules}\n"
            "请只输出该片段最终中文 YAML。"
        ),
        images=_shot_director_stage_images("shot_director_guard", images_base64),
    )
    raw_final_output = final_output
    final_output = _repair_shot_director_output_contracts(final_output, script)
    final_runtime = dict(runtimes.get("final") or {})
    final_runtime["auto_repair_applied"] = final_output != raw_final_output

    final_issues = _validate_shot_director_output(final_output, expected_segments)
    split_fragment_ids = [_segment_name_to_fragment_id(name) for name in expected_segments]
    final_fragment_ids = [_extract_fragment_id(section) for section in _extract_yaml_sections(final_output or "")]
    split_output_complete = bool(split_fragment_ids) and all(fragment_id in final_fragment_ids for fragment_id in split_fragment_ids)
    if final_issues and split_output_complete:
        final_runtime["repair_attempted"] = False
        final_runtime["repair_skipped_reason"] = "split_fragments_complete_accept_deterministic_merge"
        final_runtime["repair_validation_issues"] = final_issues
    elif final_issues:
        failed_fragment_ids = _fragment_ids_from_validation_issues(final_issues, expected_segments)
        repair_target_output = _filter_yaml_sections_by_fragment_ids(final_output, failed_fragment_ids) or final_output
        repair_prompt = (
            "阶段三最终 YAML 没有通过主校验。请只按守门原则修正 YAML，不要解释。\n\n"
            "【必须修复的问题】\n"
            + "\n".join(f"- {issue}" for issue in final_issues)
            + "\n\n【待修正 YAML】\n"
            f"{repair_target_output}\n\n"
            f"{guard_rules}\n"
            "请只输出修正后的 YAML。"
        )
        repaired_fragment_output, repair_runtime = _call_shot_director_stage(
            stage_key="shot_director_guard",
            system_prompt=guard_rules,
            user_prompt=repair_prompt,
            images_base64=None,
        )
        raw_repaired_final = repaired_fragment_output
        repaired_fragment_output = _repair_shot_director_output_contracts(repaired_fragment_output, script)
        repaired_final = _merge_repaired_yaml_sections(final_output, repaired_fragment_output, failed_fragment_ids)
        repaired_issues = _validate_shot_director_output(repaired_final, expected_segments)
        final_runtime["repair_attempted"] = True
        final_runtime["repair_scope"] = "failed_fragments" if failed_fragment_ids else "full_yaml"
        final_runtime["repair_fragment_ids"] = failed_fragment_ids
        final_runtime["repair_runtime"] = repair_runtime
        final_runtime["repair_auto_repair_applied"] = repaired_fragment_output != raw_repaired_final
        final_runtime["repair_validation_issues"] = repaired_issues
        if len(repaired_issues) <= len(final_issues):
            final_output = repaired_final
            final_issues = repaired_issues

    final_runtime["validation_issues"] = final_issues
    final_runtime["workflow_trace"] = workflow_trace
    final_stage_meta = stage_meta.setdefault("final", {})
    final_stage_meta["workflow_stages"] = list(_SHOT_DIRECTOR_WORKFLOW_STAGES)
    final_stage_meta["coverage_contract_fields"] = list(_SHOT_COVERAGE_CONTRACT_FIELDS)
    stage_outputs["final"] = final_output
    runtimes["final"] = final_runtime
    runtimes["final_source"] = "final"
    runtimes["workflow_trace"] = workflow_trace
    if stage_callback:
        stage_callback("final", final_output, final_runtime, dict(stage_meta))
    return final_output, runtimes, stage_meta, stage_outputs


def _yaml_quote(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def run_shot_director_for_segment(
    state: DirectorState,
    segment_index: int | None = None,
    *,
    force: bool = False,
) -> DirectorState:
    """Generate and merge shot-director YAML for only the requested segment."""
    outputs = _agent_outputs(state)
    planner_output = outputs.get("story_planner", "")
    segment_names = list(state.get("segment_names") or [])
    total_segments = int(state.get("total_segments") or 0)
    if not segment_names:
        derived_total, segment_names = _derive_segments_from_planner_output(planner_output)
        if not total_segments:
            total_segments = derived_total

    selected_index = int(
        segment_index
        or state.get("active_segment_index")
        or state.get("current_segment_index")
        or 1
    )
    selected_index = max(1, min(selected_index, max(total_segments or len(segment_names) or 1, 1)))
    segment_name = (
        segment_names[selected_index - 1]
        if 0 <= selected_index - 1 < len(segment_names)
        else f"片段{selected_index:02d}"
    )
    fragment_id = _segment_name_to_fragment_id(segment_name) or f"F{selected_index:02d}"

    existing_fragment = _filter_yaml_sections_by_fragment_ids(outputs.get("shot_director", ""), [fragment_id])
    if existing_fragment.strip() and not force:
        return _persist_update(
            state,
            {
                "status": "running_phase_2",
                "step": "step_4_compile",
                "message": f"第 {selected_index} 段镜头导演已存在，正在进入 Prompt 编译。",
                "agent_outputs": outputs,
                "total_segments": total_segments,
                "segment_names": segment_names,
                "active_segment_index": selected_index,
                "current_segment_index": selected_index,
            },
        )

    fragment_planner_output = _filter_yaml_sections_by_fragment_ids(planner_output, [fragment_id]) or planner_output
    director_brief_text = _director_brief(state)
    tail_frame_analysis = (state.get("tail_frame_analysis") or "").strip()
    planner_source_context = _planner_source_event_context(
        fragment_planner_output,
        [fragment_id],
        char_limit=1200,
    )
    director_hint = (
        "shot_director 单片段 镜头导演 当前片段 镜头序列 连续性 尾帧承接 "
        f"{fragment_id} {planner_source_context[:300]}"
    )
    if tail_frame_analysis:
        director_hint = f"{director_hint} tail_frame_bridge {tail_frame_analysis[:300]}"
    if director_brief_text:
        director_hint = f"{director_hint} director_showrunner {director_brief_text[:300]}"

    scene_context_block = _scene_context_prompt_block(_scene_context_brief(state))
    scene_reference_manifest = _reference_image_manifest_prompt(state)
    scene_reference_context = "\n\n".join(
        part for part in (scene_context_block, scene_reference_manifest) if part.strip()
    )
    if tail_frame_analysis:
        scene_reference_context = (
            f"{scene_reference_context.strip()}\n\n" if scene_reference_context.strip() else ""
        ) + (
            "[Previous Video Tail / Bridge]\n"
            "Use these constraints when deciding the first shot of this segment.\n"
            f"{tail_frame_analysis}\n"
        )

    shot_runtime_started = time.perf_counter()
    stage_runtimes: dict[str, dict[str, Any]] = {}

    def persist_stage(
        stage_name: str,
        stage_output: str,
        stage_runtime: dict[str, Any],
        stage_meta_snapshot: dict[str, dict[str, Any]],
    ) -> None:
        stage_runtimes[stage_name] = dict(stage_runtime)
        partial_outputs = dict(outputs)
        partial_outputs[f"shot_director_{stage_name}_fragment_{fragment_id}"] = stage_output
        if stage_name == "final":
            partial_outputs[f"shot_director_guard_fragment_{fragment_id}"] = stage_output
            partial_outputs[f"shot_director_segment_{fragment_id}"] = stage_output
            partial_outputs[f"shot_director_fragment_{fragment_id}"] = stage_output
            partial_outputs["shot_director"] = _merge_repaired_yaml_sections(
                partial_outputs.get("shot_director", ""),
                stage_output,
                [fragment_id],
            )
            partial_outputs["shot_director_final"] = partial_outputs["shot_director"]
        retrieval_key = stage_name if stage_name in stage_meta_snapshot else "final"
        knowledge_metadata = _record_knowledge_metadata(
            state,
            "shot_director",
            director_hint,
            stage_meta_snapshot.get(retrieval_key, {}),
        )
        knowledge_metadata.setdefault("shot_director", {})["runtime"] = {
            **stage_runtimes,
            "mode": "per_segment",
            "active_fragment_id": fragment_id,
            "path": "direct_llm_only",
            "total_elapsed_seconds": round(time.perf_counter() - shot_runtime_started, 3),
        }
        knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta_snapshot
        _persist_update(
            state,
            {
                "status": "running_phase_2",
                "step": "step_3_direct",
                "message": f"第 {selected_index} 段镜头导演正在生成：{fragment_id}。",
                "agent_outputs": partial_outputs,
                "knowledge_metadata": knowledge_metadata,
                "total_segments": total_segments,
                "segment_names": segment_names,
                "active_segment_index": selected_index,
                "current_segment_index": selected_index,
            },
        )

    try:
        output, shot_runtime, stage_meta, stage_outputs = _run_shot_director_three_stage(
            script=state.get("script", ""),
            planner_output=fragment_planner_output,
            atmosphere_strategy=state.get("atmosphere_strategy", ""),
            aspect_ratio=state.get("aspect_ratio", "16:9"),
            expected_segments=[fragment_id],
            images_base64=None,
            director_hint=director_hint,
            scene_reference_context=scene_reference_context,
            director_brief=director_brief_text,
            stage_callback=persist_stage,
            resume_stage_outputs={},
            resume_stage_runtime={},
            resume_stage_meta={},
        )
    except Exception as exc:
        error_message = f"镜头导演大模型连接不成功：{exc}"
        print(f"  [shot_director] {error_message}")

        failed_outputs = dict(outputs)
        for key in list(failed_outputs):
            if key.startswith("shot_director_") and key.endswith(f"_{fragment_id}"):
                failed_outputs.pop(key, None)
        for aggregate_key in ("shot_director", "shot_director_final"):
            aggregate_output = str(failed_outputs.get(aggregate_key) or "")
            if _filter_yaml_sections_by_fragment_ids(aggregate_output, [fragment_id]):
                remaining_sections = [
                    section.strip()
                    for section in _extract_yaml_sections(aggregate_output)
                    if _extract_fragment_id(section) != fragment_id
                ]
                if remaining_sections:
                    failed_outputs[aggregate_key] = "\n\n".join(remaining_sections)
                else:
                    failed_outputs.pop(aggregate_key, None)
        failed_outputs["shot_director_error"] = error_message
        failed_outputs[f"shot_director_error_fragment_{fragment_id}"] = error_message

        shot_runtime = {
            **stage_runtimes,
            "mode": "per_segment",
            "active_fragment_id": fragment_id,
            "path": "llm_connection_failed",
            "status": "connection_failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "total_elapsed_seconds": round(time.perf_counter() - shot_runtime_started, 3),
            "local_fallback": False,
            "final": {"status": "connection_failed"},
        }
        stage_meta = {
            "final": {
                "status": "connection_failed",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "local_fallback": False,
            }
        }
        knowledge_metadata = _record_knowledge_metadata(state, "shot_director", director_hint, stage_meta["final"])
        knowledge_metadata.setdefault("shot_director", {})["runtime"] = shot_runtime
        knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta
        _persist_update(
            state,
            {
                "status": "error",
                "step": "error",
                "message": error_message,
                "error": error_message,
                "agent_outputs": failed_outputs,
                "knowledge_metadata": knowledge_metadata,
                "total_segments": total_segments,
                "segment_names": segment_names,
                "active_segment_index": selected_index,
                "current_segment_index": selected_index,
                "shot_director_approved_by_segment": dict(state.get("shot_director_approved_by_segment") or {}),
            },
        )
        raise RuntimeError(error_message) from exc
    primary_output = _repair_shot_director_output_contracts(output, state.get("script", ""))
    primary_issues = _collect_shot_director_issues(
        primary_output,
        expected_segments=[fragment_id],
        script=state.get("script", ""),
        planner_output=fragment_planner_output,
        aspect_ratio=state.get("aspect_ratio", ""),
    )
    primary_hard_issues = _hard_shot_director_issues(primary_issues)
    try:
        output, review_runtime, review_report = _run_shot_director_review_board(
            script=state.get("script", ""),
            planner_output=fragment_planner_output,
            director_brief=director_brief_text,
            primary_output=primary_output,
            images_base64=None,
        )
    except Exception as exc:
        error_message = str(exc)
        print(f"  [shot_director_logic_reviewer] {error_message}")
        failed_outputs = dict(outputs)
        failed_outputs["shot_director_error"] = error_message
        failed_outputs[f"shot_director_error_fragment_{fragment_id}"] = error_message
        shot_runtime["total_elapsed_seconds"] = round(time.perf_counter() - shot_runtime_started, 3)
        shot_runtime["mode"] = "per_segment"
        shot_runtime["active_fragment_id"] = fragment_id
        shot_runtime["path"] = "logic_reviewer_connection_failed"
        shot_runtime["status"] = "connection_failed"
        shot_runtime["review_board"] = {
            "agent_name": "shot_director_logic_reviewer",
            "status": "connection_failed",
            "error_type": type(exc).__name__,
            "error": error_message,
        }
        knowledge_metadata = _record_knowledge_metadata(state, "shot_director", director_hint, stage_meta.get("final", {}))
        knowledge_metadata.setdefault("shot_director", {})["runtime"] = shot_runtime
        knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta
        _persist_update(
            state,
            {
                "status": "error",
                "step": "error",
                "message": error_message,
                "error": error_message,
                "agent_outputs": failed_outputs,
                "knowledge_metadata": knowledge_metadata,
                "total_segments": total_segments,
                "segment_names": segment_names,
                "active_segment_index": selected_index,
                "current_segment_index": selected_index,
                "shot_director_approved_by_segment": dict(state.get("shot_director_approved_by_segment") or {}),
            },
        )
        raise RuntimeError(error_message) from exc

    director_issues = _collect_shot_director_issues(
        output,
        expected_segments=[fragment_id],
        script=state.get("script", ""),
        planner_output=fragment_planner_output,
        aspect_ratio=state.get("aspect_ratio", ""),
    )
    hard_director_issues = _hard_shot_director_issues(director_issues)
    if hard_director_issues:
        output = primary_output
        director_issues = primary_issues
        review_runtime["final_validation_status"] = "fallback_to_primary"
        review_runtime["final_validation_issues"] = hard_director_issues
        hard_director_issues = primary_hard_issues

    merged_output = _merge_repaired_yaml_sections(outputs.get("shot_director", ""), output, [fragment_id])
    outputs.pop("shot_director_error", None)
    outputs.pop(f"shot_director_error_fragment_{fragment_id}", None)
    outputs[f"shot_director_segment_{fragment_id}"] = output
    outputs[f"shot_director_fragment_{fragment_id}"] = output
    outputs["shot_director"] = merged_output
    outputs["shot_director_final"] = merged_output
    for stage_name in ("layout", "blocking", "final"):
        if stage_outputs.get(stage_name):
            outputs[f"shot_director_{stage_name}_fragment_{fragment_id}"] = stage_outputs[stage_name]
            if stage_name == "final":
                outputs[f"shot_director_guard_fragment_{fragment_id}"] = stage_outputs[stage_name]
    if review_report:
        outputs["shot_director_review"] = review_report
        outputs[f"shot_director_review_fragment_{fragment_id}"] = review_report

    shot_runtime["total_elapsed_seconds"] = round(time.perf_counter() - shot_runtime_started, 3)
    shot_runtime["mode"] = "per_segment"
    shot_runtime["active_fragment_id"] = fragment_id
    shot_runtime["path"] = "direct_llm_only"
    shot_runtime["review_board"] = review_runtime
    shot_runtime["primary_validation_issues"] = primary_issues
    shot_runtime["primary_hard_validation_issues"] = primary_hard_issues
    shot_runtime["validation_issues"] = director_issues
    shot_runtime["hard_validation_issues"] = hard_director_issues

    knowledge_metadata = _record_knowledge_metadata(state, "shot_director", director_hint, stage_meta.get("final", {}))
    knowledge_metadata.setdefault("shot_director", {})["runtime"] = shot_runtime
    knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta
    if review_report:
        knowledge_metadata["shot_director"]["review_report_chars"] = len(review_report)
    review_retrieval_meta = review_runtime.get("retrieval_meta") if isinstance(review_runtime, dict) else None
    if isinstance(review_retrieval_meta, dict):
        knowledge_metadata["shot_director"]["review_retrieval"] = review_retrieval_meta

    original_by_segment = dict(state.get("shot_director_original_by_segment") or {})
    original_by_segment[str(selected_index)] = output
    original_by_segment[fragment_id] = output

    return _persist_update(
        state,
        {
            "status": "running_phase_2",
            "step": "step_4_compile",
            "message": f"第 {selected_index} 段镜头导演完成，正在进入 Prompt 编译。",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "total_segments": total_segments,
            "segment_names": segment_names,
            "active_segment_index": selected_index,
            "current_segment_index": selected_index,
            "shot_director_original_by_segment": original_by_segment,
            "shot_director_approved_by_segment": dict(state.get("shot_director_approved_by_segment") or {}),
        },
    )


def _validate_shot_director_dialogue_coverage(output: str) -> list[str]:
    """Ensure shot_director, not compiler, owns long-dialogue coverage design."""
    issues: list[str] = []
    for shot_id, block in _main_shot_blocks(output):
        coverage = _yaml_line_field(block, "dialogue_coverage") or _yaml_line_field(block, "dialogue")
        if not _dialogue_coverage_needs_visual_break(coverage):
            continue
        design_text = " ".join(
            [
                coverage,
                _yaml_line_field(block, "task"),
                _yaml_line_field(block, "type"),
                _yaml_line_field(block, "audio"),
                _yaml_line_field(block, "camera"),
                _yaml_line_field(block, "action"),
                _yaml_line_field(block, "must_carry"),
                _yaml_line_field(block, "cut_point"),
                _yaml_line_field(block, "continuity"),
            ]
        )
        if _has_dialogue_coverage_visual_break(design_text):
            continue
        issues.append(
            f"{shot_id} 承载长台词/高压对白，但没有设计同侧听者反应、过肩、画外音/L-cut 或景别变化；"
            "镜头编辑必须在 shot_director layout/blocking/guard 阶段完成，不能交给 prompt_compiler 临场补。"
        )
    return issues

_SHOT_VARIETY_EXCEPTION_RE = re.compile(
    r"(长镜头|一镜到底|固定机位压迫|持续压迫|压迫式凝视|刻意重复|节奏总控.{0,24}(?:固定|长镜头|压住|不切))"
)


def _normalize_shot_variety_text(value: str) -> str:
    text = re.sub(r"\s+", "", (value or "").strip().lower())
    text = text.strip("\"'。；;，,")
    return text


def _shot_variety_key(block: str) -> str:
    shot = _yaml_line_field(block, "shot")
    if not shot:
        camera = _yaml_line_field(block, "camera")
        size = _yaml_line_field(block, "size")
        shot = f"{camera} {size}".strip()
    return _normalize_shot_variety_text(shot)


def _validate_shot_director_variety(output: str) -> list[str]:
    """Guard against accidental one-note shot language inside a fragment."""
    issues: list[str] = []
    for section in _extract_yaml_sections(output or ""):
        fragment_id = _extract_fragment_id(section) or "unknown"
        rhythm_text = " ".join(
            [
                _field_value(section, "rhythm"),
                _field_value(section, "节奏"),
                _field_value(section, "fragment_task"),
                _field_value(section, "片段任务"),
            ]
        )
        if _SHOT_VARIETY_EXCEPTION_RE.search(section) or _SHOT_VARIETY_EXCEPTION_RE.search(rhythm_text):
            continue

        shot_blocks = _main_shot_blocks(section)
        if len(shot_blocks) < 3:
            continue

        shot_keys = [_shot_variety_key(block) for _shot_id, block in shot_blocks]
        shot_keys = [key for key in shot_keys if key]
        if len(shot_keys) < 3:
            continue

        unique_shot_keys = set(shot_keys)
        if len(unique_shot_keys) == 1:
            issues.append(
                f"{fragment_id} 连续使用同一种镜头语言：{shot_keys[0]}；"
                "请至少变化拍摄主体、景别、视角/机位、声音承载或镜头任务之一。"
            )
            continue

        for index in range(len(shot_keys) - 2):
            if shot_keys[index] == shot_keys[index + 1] == shot_keys[index + 2]:
                issues.append(
                    f"{fragment_id} 存在连续三个镜头重复同一景别/视角：{shot_keys[index]}；"
                    "除非节奏总控明确要求压迫式长镜头，否则需要做有动机的镜头语言变化。"
                )
                break
    return issues


def _collect_shot_director_issues(
    director_output: str,
    *,
    expected_segments: list[str],
    script: str = "",
    planner_output: str = "",
    aspect_ratio: str = "",
) -> list[str]:
    """Collect schema, continuity, source-event, anti-hallucination and review-board guard issues."""
    issues: list[str] = []
    issues.extend(_validate_shot_director_output(director_output, expected_segments))
    issues.extend(_validate_shot_director_script_fidelity(director_output, script))
    issues.extend(_validate_shot_director_source_event_coverage(director_output, planner_output))
    issues.extend(_validate_shot_director_vertical_discipline(director_output, aspect_ratio))
    issues.extend(_validate_shot_director_dialogue_coverage(director_output))
    issues.extend(_validate_shot_director_spatial_geometry(director_output))
    issues.extend(_validate_shot_director_variety(director_output))
    return issues

def _is_soft_shot_director_issue(issue: str) -> bool:
    """Return True for advisory issues that should not block final output."""
    soft_markers = (
        "9:16",
        "特写使用过密",
        "缺少半身/中景/双人关系景别作为主力镜头",
        "全部使用特写类景别",
        "微细节局部",
    )
    return any(marker in (issue or "") for marker in soft_markers)

def _hard_shot_director_issues(issues: list[str]) -> list[str]:
    return [issue for issue in issues if not _is_soft_shot_director_issue(issue)]

_SHOT_LOGIC_CAMERA_ACTION_RE = re.compile(
    r"请求|命令|解释|答应|同意|拒绝|说出|继续说|听到|听见|看清|看见|看向|低头|抬眼|拿着|拿起|递出|"
    r"靠近|俯身|戴上|佩戴|扣上|贴近|触碰|掠过|微颤|停住|收紧|绷紧|后收|后退|愣住|呼吸|"
    r"眼神|表情|身体|肩颈|嘴角|下颌"
)
_SHOT_LOGIC_PROP_RE = re.compile(r"项链|手机|文件|照片|戒指|钥匙|书包|包|门|车门|电梯门")
_SHOT_LOGIC_PROP_STATE_RE = re.compile(
    r"仍|尚未|未|已经|正在|由|归属|手中|拿|递|戴|扣|贴近|靠近|放在|留在|进入|离开|打开|关上"
)
_SHOT_LOGIC_ACTION_DETAIL_RE = re.compile(
    r"视线|眼神|眉|嘴|下颌|呼吸|肩|颈|手|指尖|身体|停住|抬眼|低头|看向|后收|绷紧|收紧|"
    r"微颤|停顿|慢慢|短暂|仍|没有|开始|随后|同时|结束"
)
_SHOT_LOGIC_COMPANION_RE = re.compile(r"画外|边缘|近处|近侧|同场|同车|同室|同一空间|仍在|还在|没有离开|未离开|肩线|前景")
_SHOT_LOGIC_BUSY_HAND_RE = re.compile(
    r"(手机|电话|衣服|外套|包|文件|照片|项链|钥匙|门|车门).{0,16}"
    r"(牵|抓|拉|扶|抱|托|按|递|拿|套|扣|推|拽|贴|压|靠近|俯身).{0,16}"
    r"(同时|一边|仍|还|继续|又|并|顺着)"
    r"|"
    r"(同时|一边|仍|还|继续|又|并|顺着).{0,16}"
    r"(牵|抓|拉|扶|抱|托|按|递|拿|套|扣|推|拽|贴|压|靠近|俯身).{0,16}"
    r"(手机|电话|衣服|外套|包|文件|照片|项链|钥匙|门|车门)"
)
_SHOT_LOGIC_RESIST_COMPLY_RE = re.compile(r"(抗拒|挣扎|躲|后缩|避开|抽回|缩脚).{0,36}(配合|顺从|穿好|完成|戴上|扣上|靠近)")
_SHOT_LOGIC_ACTION_VERB_RE = re.compile(
    r"牵|抓|拉|扶|抱|托|按|递|拿|套|扣|推|拽|贴|压|靠近|俯身|转身|后退|后缩|躲|避开|看向|低头|抬眼|说|喊|停住"
)


def _shot_logic_camera_field_has_action_leak(shot_text: str) -> bool:
    text = (shot_text or "").strip()
    if not text:
        return False
    matches = _SHOT_LOGIC_CAMERA_ACTION_RE.findall(text)
    if not matches:
        return False
    if set(matches) == {"看向"} and re.search(r"(?:肩后|过肩|视角|机位).{0,12}看向", text):
        return False
    return True


def _shot_logic_expected_segments_from_output(output: str) -> list[str]:
    segment_ids: list[str] = []
    for section in _extract_yaml_sections(output or ""):
        fragment_id = _extract_fragment_id(section)
        if fragment_id and fragment_id not in segment_ids:
            segment_ids.append(fragment_id)
    return segment_ids


def _shot_logic_local_issues(output: str, script: str = "") -> list[str]:
    """Local judge for single-fragment shot/action continuity risks."""
    issues: list[str] = []
    script_names = _primary_script_character_names(script)
    has_multi_character_script = len(script_names) >= 2
    other_character_markers = ("画外", "边缘", "近处", "近侧", "同场", "同一空间", "仍在", "还在", "没有离开")

    for section in _extract_yaml_sections(output or ""):
        fragment_id = _extract_fragment_id(section) or "未知片段"
        shot_blocks = _main_shot_blocks(section)
        for carry_issue in _shot_tailframe_carry_issues(fragment_id, shot_blocks):
            issues.append(f"P1｜{carry_issue}")
        for shot_id, block in shot_blocks:
            subject = _yaml_line_field(block, "subject")
            shot = _yaml_line_field(block, "shot")
            action = _yaml_line_field(block, "action")
            must_carry = _yaml_line_field(block, "must_carry")
            continuity = _yaml_line_field(block, "continuity")
            combined_action_state = " ".join([action, must_carry, continuity])

            for subject_issue in _shot_subject_ownership_issues(shot_id, block):
                issues.append(f"P1｜{fragment_id}/{shot_id}｜{subject_issue}")

            if _shot_logic_camera_field_has_action_leak(shot):
                issues.append(
                    f"P1｜{fragment_id}/{shot_id}｜镜头字段混入人物动作或表演：{shot}；"
                    "镜头字段只应保留主体景别、视角/观看位置、必要运动或前景关系。"
                )

            if _shot_field_has_untranslated_camera_jargon(shot):
                issues.append(
                    f"P1｜{fragment_id}/{shot_id}｜镜头字段仍含未翻译机位术语：{shot}；"
                    f"{_SHOT_VIEWPOINT_TRANSLATION_HINT}"
                )

            clean_action = (action or "").strip().strip("~无")
            if not clean_action or len(clean_action) < 16 or not _SHOT_LOGIC_ACTION_DETAIL_RE.search(clean_action):
                issues.append(
                    f"P1｜{fragment_id}/{shot_id}｜画面动作缺少动作表情链；"
                    "需要写清起始状态、动作变化、视线/表情/身体反应和镜尾状态。"
                )

            action_verb_count = len(_SHOT_LOGIC_ACTION_VERB_RE.findall(clean_action))
            action_clause_count = len([part for part in re.split(r"[；;，,。]", clean_action) if part.strip()])
            if action_verb_count >= 7 or action_clause_count >= 5 or _SHOT_LOGIC_BUSY_HAND_RE.search(clean_action):
                issues.append(
                    f"P1｜{fragment_id}/{shot_id}｜画面动作过载或肢体占用不清；"
                    "请压缩为 prompt 编译可用的 1-2 句自然短动作，并明确哪只手/身体重心/道具状态。"
                )

            if _SHOT_LOGIC_RESIST_COMPLY_RE.search(clean_action):
                issues.append(
                    f"P1｜{fragment_id}/{shot_id}｜人物从抗拒到配合缺少过渡；"
                    "需要保留未完成状态，或补一个清楚的动作转折，避免同一镜内状态自相矛盾。"
                )

            if _SHOT_LOGIC_PROP_RE.search(block) and not _SHOT_LOGIC_PROP_STATE_RE.search(combined_action_state):
                issues.append(
                    f"P1｜{fragment_id}/{shot_id}｜道具状态不够明确；"
                    "需要说明道具归属、动作阶段和镜尾状态，避免下一镜道具跳变。"
                )

            if has_multi_character_script and subject:
                present_names = [name for name in script_names if name and name in subject]
                missing_names = [name for name in script_names if name and name not in subject]
                companion_text = " ".join([continuity, must_carry, action])
                if (
                    present_names
                    and missing_names
                    and not any(name in companion_text for name in missing_names)
                    and not _SHOT_LOGIC_COMPANION_RE.search(companion_text)
                    and not any(marker in companion_text for marker in other_character_markers)
                ):
                    issues.append(
                        f"P1｜{fragment_id}/{shot_id}｜单人镜缺少同场人物保留；"
                        f"需要说明{missing_names[0]}仍在同一空间内的相对位置或画外状态。"
                    )
    return issues


def _shot_logic_reviewer_system_prompt() -> str:
    return """你是镜头逻辑裁判，工作在三段式镜头导演之后。
你不是第四个镜头创意导演，不能重新发明剧情、节奏、人物、道具或台词。

你的唯一任务：审查单片段内部的镜头语言、人物动作、道具状态和镜间连续性是否合逻辑，并把最终动作修成 prompt 编译可直接使用的简短自然语句。

必须重点检查：
1. 镜头字段是否只写最终可生成的画面表达：主体景别、视角/观看位置、必要运动、前景关系；不得混入人物动作、表情、台词或戏剧判断。
2. 画面动作是否有完整动作表情链：起始状态、动作变化、视线/表情/身体反应、镜尾状态。
3. 单人镜是否保留同场人物：单人镜只改变拍摄主体，不代表另一人消失或离开。
4. 道具接触戏是否锁定归属、动作阶段和镜尾状态。
5. 镜头与镜头之间是否继承上一镜尾帧的人物位置、道具状态、视线方向和同侧轴线。
6. 切镜点是否有因果：信息落下、反应成立、动作阶段完成或尾帧交接完成之后再切。
7. 肢体占用是否可执行：同一只手不能同时拿手机、牵人、扶人、套衣服或抓道具；如果必须并行，必须明确左右手和身体重心。
8. 接触关系是否可成立：抓住、抱住、躲避、抗拒、压近、后缩、穿衣等动作不能在同一镜内互相抵消。
9. 画面动作是否适合下游 prompt 编译：每个“画面动作”优先改成 1-2 句自然短动作，每句只承载一个主要动作变化，避免流水账和复杂嵌套。
10. 拍摄主体是否正确：拍摄主体不是人物/道具清单，只能是本镜观众注意力的主焦点；其他可见物放进必须承载或连续性。
11. 镜头组合是否服务戏剧任务：下一镜必须来自当前任务的覆盖链，例如关系建立后接动作/信息/反应，信息插入后接人物反应或关系复位，禁止随机换景别。
12. 是否存在凭空位移：人物坐站、位置、穿戴、道具归属变化必须承接上一镜尾帧，不能下一镜突然换到另一个位置或状态。
13. 是否把内部机位术语翻译成视角：最终镜头字段必须写“侧面视角/固定视角/从谁肩后看向谁/谁的主观视角”，不得保留“固定机位、侧面机位、摄影机位于”等词。

如果没有硬问题，只输出通过结论。
如果有问题，给出最小修复。修复只能整理镜头字段、压缩并理顺画面动作、补足连续性/切镜点，不得新增剧本外事件。
修复后的“画面动作”必须短、自然、可生成：保留角色起始状态、一个主要动作变化和镜尾状态即可；多余心理解释放到“必须承载”或删掉。

输出必须是中文，原剧本英文台词可原样保留。严格按这个格式：
审查结论: 通过
裁判摘要: ...
单片段审查:
  - 片段编号: F01
    通过: true
    问题: []
硬错误: []
修复后镜头方案:
"""


def _shot_logic_reviewer_user_prompt(
    *,
    script: str,
    planner_output: str,
    director_brief: str,
    primary_output: str,
    local_issues: list[str],
) -> str:
    issue_text = "\n".join(f"- {issue}" for issue in local_issues) if local_issues else "本地硬检查未发现明确问题。"
    return f"""请审查下面的三段式镜头导演最终输出，只看单片段内部逻辑。

【剧本原文】
{script or "（空）"}

【拆片/节奏交接】
{planner_output or "（空）"}

【导演总控补充】
{director_brief or "（空）"}

【本地硬检查提示】
{issue_text}

【待审查镜头方案】
{primary_output or "（空）"}

请判断是否通过。若需要修复，把完整修复后的镜头方案放在“修复后镜头方案:”后面，且作为最后一个字段。
修复时请特别处理“画面动作”：不要写成长串动作流水账；改成大模型容易生成的 1-2 句自然短动作，并确保手机、衣服、孩子、身体接触等状态能被下一镜继承。"""


def _parse_shot_logic_review_verdict(report: str) -> str:
    text = report or ""
    if re.search(r"审查结论\s*:\s*(?:阻断|不通过|BLOCKED)", text, re.IGNORECASE):
        return "blocked"
    if re.search(r"审查结论\s*:\s*(?:需要返修|返修|需修复|REPAIR_REQUIRED)", text, re.IGNORECASE):
        return "repair_required"
    if re.search(r"审查结论\s*:\s*(?:通过|ACCEPT)", text, re.IGNORECASE):
        return "accepted"
    if "修复后镜头方案" in text and re.search(r"(片段编号|fragment_id)\s*:", text):
        return "repair_required"
    return "accepted"


def _extract_shot_logic_repaired_yaml(report: str) -> str:
    match = re.search(r"(?ms)^\s*修复后镜头方案\s*:\s*(?:\|\s*)?\n(?P<body>.*)\Z", report or "")
    if not match:
        return ""
    lines = match.group("body").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    lines = [line for line in lines if not line.strip().startswith("```")]
    non_empty_indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    if non_empty_indents:
        min_indent = min(non_empty_indents)
        if min_indent:
            lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
    body = "\n".join(lines).strip()
    if not re.search(r"(?m)^\s*-?\s*(?:片段编号|fragment_id)\s*:", body):
        return ""
    return _clean_shot_director_output(body)


def _run_shot_director_review_board(
    *,
    script: str,
    planner_output: str,
    director_brief: str = "",
    primary_output: str,
    images_base64: list[str] | None = None,
) -> tuple[str, dict[str, Any], str]:
    """Review single-fragment shot logic after the split shot director flow."""
    _ = images_base64
    started = time.perf_counter()
    local_issues = _shot_logic_local_issues(primary_output, script)
    reviewer_context_hint = (
        "shot_director_logic_reviewer 三段式镜头导演 逻辑审查 "
        "shot_director_layout shot_director_blocking shot_director_guard "
        "镜头摆位主分镜骨架 动作调度 规则守门 最小修复 "
        "镜头合理性 同镜头同机位 多机位变化 动作连续性 "
        "LAYOUT-COVERAGE-BLUEPRINT BLOCKING-ACTION-FLOW GUARD-COVERAGE-CONTRACT "
        f"{(planner_output or '')[:500]} {(primary_output or '')[:800]}"
    )
    reviewer_profile = _build_shot_director_signal_retrieval_profile(
        planner_output=planner_output,
        atmosphere_strategy="",
        director_brief=director_brief,
        aspect_ratio="",
    )
    reviewer_profile["served_agents"] = [
        "shot_director_layout",
        "shot_director_blocking",
        "shot_director_guard",
        "shot_director",
    ]
    reviewer_profile["signals"] = _unique_preserve_order(
        [
            *(reviewer_profile.get("signals") or []),
            "layout_blueprint",
            "shot_language_selection",
            "reaction_coverage",
            "action_state_chain",
            "minimal_repair",
            "shot_variety",
            "continuity_contract",
        ]
    )
    reviewer_profile["tags"] = _unique_preserve_order(
        [
            *(reviewer_profile.get("tags") or []),
            "镜头摆位主分镜骨架",
            "动作调度与受击覆盖",
            "规则守门与最小修复",
            "多机位分镜",
            "镜头多样性",
        ]
    )
    reviewer_profile["final_top_k"] = 12
    system_prompt, retrieval_meta = build_system_prompt(
        _shot_logic_reviewer_system_prompt(),
        "shot_director_logic_reviewer",
        context_hint=reviewer_context_hint,
        retrieval_profile=reviewer_profile,
        include_critical_knowledge=True,
    )
    forced_stage_sources = [
        "25_镜头摆位主分镜骨架规则.md",
        "26_动作调度与受击覆盖规则.md",
        "27_规则守门与最小修复规则.md",
        "22_多机位分镜与镜头多样性规则.md",
        "rules/shot_director_layout/LAYOUT-COVERAGE-BLUEPRINT-005.md",
        "rules/shot_director_blocking/BLOCKING-ACTION-FLOW-006.md",
        "rules/shot_director_guard/GUARD-COVERAGE-CONTRACT-005.md",
    ]
    forced_stage_rule_block = "\n\n".join(
        [
            "===== 三段式镜头导演审查必须执行的专项规则 =====",
            "来源: " + " | ".join(forced_stage_sources),
            _shot_director_layout_rule_block(""),
            _shot_director_blocking_rule_block(""),
            _shot_director_guard_stage_rule_block(""),
            _shot_director_coverage_contract_prompt(),
            "审查时必须按 layout 骨架、blocking 动作调度、guard 最小修复三层分别判断；"
            "如果连续镜头无动机地重复同一主体、同一景别、同一机位或同一运动方式，必须标为需要返修。",
            "===== 三段式专项规则结束 =====",
        ]
    )
    system_prompt = f"{system_prompt}\n\n{forced_stage_rule_block}"
    retrieval_meta["forced_stage_sources"] = forced_stage_sources
    retrieval_meta["matched_sources"] = _unique_preserve_order(
        [*(retrieval_meta.get("matched_sources") or []), *forced_stage_sources]
    )
    reviewer_report = ""
    verdict = "accepted" if not local_issues else "repair_required"
    status = "accepted_primary" if not local_issues else "accepted_primary_with_local_warnings"

    try:
        reviewer_report = call_llm(
            system_prompt,
            _shot_logic_reviewer_user_prompt(
                script=script,
                planner_output=planner_output,
                director_brief=director_brief,
                primary_output=primary_output,
                local_issues=local_issues,
            ),
            agent_name="shot_director_logic_reviewer",
            temperature=0.2,
            max_retries=1,
        ).strip()
        if not reviewer_report:
            raise RuntimeError("镜头逻辑审查大模型返回空内容")
        verdict = _parse_shot_logic_review_verdict(reviewer_report)
    except Exception as exc:
        raise RuntimeError(f"镜头逻辑审查大模型连接不成功：{exc}") from exc

    output = primary_output
    report = reviewer_report
    if verdict in {"repair_required", "blocked"}:
        repaired_yaml = _extract_shot_logic_repaired_yaml(reviewer_report)
        if repaired_yaml:
            repaired_yaml = _repair_shot_director_output_contracts(repaired_yaml, script)
            expected_segments = _shot_logic_expected_segments_from_output(primary_output)
            hard_issues = _hard_shot_director_issues(
                _collect_shot_director_issues(
                    repaired_yaml,
                    expected_segments=expected_segments,
                    script=script,
                    planner_output=planner_output,
                    aspect_ratio="",
                )
            )
            repaired_local_issues = _shot_logic_local_issues(repaired_yaml, script)
            if not hard_issues and len(repaired_local_issues) <= len(local_issues):
                output = repaired_yaml
                status = "repaired_by_logic_reviewer"
                report = f"{report}\n\n裁判修复采纳: 是"
            else:
                status = "reviewer_repair_rejected"
                rejection_reasons = [*hard_issues, *repaired_local_issues]
                report = (
                    f"{report}\n\n裁判修复采纳: 否\n"
                    "拒绝原因:\n"
                    + "\n".join(f"- {issue}" for issue in rejection_reasons[:8])
                )
        else:
            status = "repair_requested_without_safe_yaml"
            report = f"{report}\n\n裁判修复采纳: 否\n拒绝原因:\n- 裁判没有给出可安全解析的完整镜头方案。"
    elif local_issues:
        status = "accepted_primary_with_local_warnings"

    runtime = {
        "agent_name": "shot_director_logic_reviewer",
        "mode": "single_fragment_logic_judge",
        "status": status,
        "verdict": verdict,
        "local_issue_count": len(local_issues),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "output_chars": len(output or ""),
        "report_chars": len(report or ""),
        "retrieval_meta": retrieval_meta,
    }
    return output, runtime, report

def shot_director_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    planner_output = outputs.get("story_planner", "")
    segment_names = list(state.get("segment_names") or [])
    total_segments = int(state.get("total_segments") or 0)
    if not segment_names:
        derived_total, segment_names = _derive_segments_from_planner_output(planner_output)
        if not total_segments:
            total_segments = derived_total
    current_segment_index = int(state.get("current_segment_index") or state.get("active_segment_index") or 1)
    return _persist_update(
        state,
        {
            "status": "waiting_for_user_input",
            "step": "step_3_direct",
            "message": "Story planning is ready; generate the current segment through the per-segment pipeline.",
            "agent_outputs": outputs,
            "total_segments": total_segments,
            "segment_names": segment_names,
            "current_segment_index": max(1, min(current_segment_index, max(total_segments or 1, 1))),
            "director_review_required": False,
        },
    )

    state = _await_scene_card_generation(state)
    outputs = _agent_outputs(state)
    director_brief_text = _director_brief(state)
    planner_output = outputs.get("story_planner", "")
    segment_names = list(state.get("segment_names") or [])
    total_segments = int(state.get("total_segments") or 0)
    if not segment_names:
        derived_total, segment_names = _derive_segments_from_planner_output(planner_output)
        if not total_segments:
            total_segments = derived_total
    # 三段式恢复时保留每个阶段的整段输出和分片输出，便于中断后从最近阶段续跑。
    resume_stage_outputs: dict[str, str] = {}
    if outputs.get("shot_director_layout"):
        resume_stage_outputs["layout"] = outputs.get("shot_director_layout", "")
    if outputs.get("shot_director_blocking"):
        resume_stage_outputs["blocking"] = outputs.get("shot_director_blocking", "")
    if outputs.get("shot_director_final"):
        resume_stage_outputs["final"] = outputs.get("shot_director_final", "")
    if outputs.get("shot_director"):
        resume_stage_outputs.setdefault("final", outputs.get("shot_director", ""))
    for key, value in outputs.items():
        for prefix in (
            "shot_director_layout_fragment_",
            "shot_director_blocking_fragment_",
            "shot_director_final_fragment_",
            "shot_director_fragment_",
        ):
            if key.startswith(prefix) and value:
                if prefix == "shot_director_fragment_":
                    resume_stage_outputs[key.removeprefix("shot_director_")] = value
                else:
                    stage = prefix.removeprefix("shot_director_").removesuffix("_fragment_")
                    resume_stage_outputs[f"{stage}_fragment_{key.removeprefix(prefix)}"] = value
    shot_meta = (state.get("knowledge_metadata") or {}).get("shot_director", {})
    resume_stage_runtime = shot_meta.get("runtime", {}) if isinstance(shot_meta, dict) else {}
    resume_stage_meta = shot_meta.get("stage_retrieval", {}) if isinstance(shot_meta, dict) else {}
    segment_fragment_ids = [_segment_name_to_fragment_id(name) for name in segment_names]
    planner_source_context = _planner_source_event_context(
        planner_output,
        segment_fragment_ids or None,
        char_limit=1200,
    )
    director_hint = (
        "shot_director 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制 切镜 受击者 "
        "炸点 对白 信息冲击 动作接续 人物关系 场面总控 节奏 子分镜 戏剧微粒 "
        "权力反转 悬念揭示 误解错位 source_script_events "
        f"{planner_source_context[:300]}"
    )
    if director_brief_text:
        director_hint = f"{director_hint} director_showrunner {director_brief_text[:300]}"
    shot_runtime_started = time.perf_counter()
    scene_context_block = _scene_context_prompt_block(_scene_context_brief(state))
    scene_reference_manifest = _reference_image_manifest_prompt(state)
    scene_reference_context = "\n\n".join(
        part for part in (scene_context_block, scene_reference_manifest) if part.strip()
    )
    stage_runtimes: dict[str, dict[str, Any]] = {}

    def persist_stage(stage_name: str, stage_output: str, stage_runtime: dict[str, Any], stage_meta_snapshot: dict[str, dict[str, Any]]) -> None:
        stage_runtimes[stage_name] = dict(stage_runtime)
        output_key = f"shot_director_{stage_name}"
        output_key_final = f"shot_director_{stage_name}"
        outputs[output_key_final] = stage_output
        if stage_name == "final":
            outputs["shot_director"] = stage_output

        retrieval_key = stage_name if stage_name in stage_meta_snapshot else "final"
        knowledge_metadata = _record_knowledge_metadata(
            state,
            "shot_director",
            director_hint,
            stage_meta_snapshot.get(retrieval_key, {}),
        )
        knowledge_metadata.setdefault("shot_director", {})["runtime"] = {
            **stage_runtimes,
            "final_source": stage_name if stage_name == "final" else "in_progress",
            "path": "direct_llm_only",
            "total_elapsed_seconds": round(time.perf_counter() - shot_runtime_started, 3),
        }
        knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta_snapshot

        completed_fragment_index = 0
        fragment_marker = "fragment_F"
        if fragment_marker in stage_name:
            try:
                completed_fragment_index = int(stage_name.rsplit("F", 1)[1])
            except Exception:
                completed_fragment_index = 0
        active_index = completed_fragment_index or 1
        stage_messages = {
            "layout": "镜头导演一号摆位完成，正在进入动作调度...（5/6）",
            "blocking": "镜头导演二号调度完成，正在进入规则守门...（5/6）",
            "final": "镜头导演输出已完成，准备生成第 1 段 Prompt。",
        }
        if completed_fragment_index:
            stage_messages[stage_name] = (
                f"镜头导演已完成 {stage_name.rsplit('fragment_', 1)[-1]} "
                f"（{completed_fragment_index}/{total_segments}），正在继续下一个片段..."
            )
        _persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_3_direct",
                "message": stage_messages.get(stage_name, "镜头导演正在生成全局镜头方案...（5/6）"),
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
                "total_segments": total_segments,
                "segment_names": segment_names,
                "current_segment_index": active_index,
                "active_segment_index": active_index,
            },
        )

    output, shot_runtime, stage_meta, stage_outputs = _run_shot_director_three_stage(
        script=state.get("script", ""),
        planner_output=planner_output,
        atmosphere_strategy=state.get("atmosphere_strategy", ""),
        aspect_ratio=state.get("aspect_ratio", "16:9"),
        expected_segments=segment_names,
        images_base64=None,
        director_hint=director_hint,
        scene_reference_context=scene_reference_context,
        director_brief=director_brief_text,
        stage_callback=persist_stage,
        resume_stage_outputs=resume_stage_outputs,
        resume_stage_runtime=resume_stage_runtime,
        resume_stage_meta=resume_stage_meta,
    )
    knowledge_metadata = _record_knowledge_metadata(state, "shot_director", director_hint, stage_meta.get("final", {}))
    shot_runtime["total_elapsed_seconds"] = round(time.perf_counter() - shot_runtime_started, 3)
    shot_runtime["path"] = "direct_llm_only"
    knowledge_metadata.setdefault("shot_director", {})["runtime"] = shot_runtime
    knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta
    print(f"  [shot_director] total elapsed {shot_runtime['total_elapsed_seconds']:.1f}s")
    raw_primary_output = output
    primary_output = _repair_shot_director_output_contracts(output, state.get("script", ""))
    if primary_output != raw_primary_output:
        outputs["shot_director_contract_repair"] = primary_output
        shot_runtime["deterministic_contract_repair"] = {
            "applied": True,
            "before_chars": len(raw_primary_output),
            "after_chars": len(primary_output),
        }
    primary_issues = _collect_shot_director_issues(
        primary_output,
        expected_segments=segment_names,
        script=state.get("script", ""),
        planner_output=planner_output,
        aspect_ratio=state.get("aspect_ratio", ""),
    )
    primary_hard_issues = _hard_shot_director_issues(primary_issues)
    if primary_hard_issues:
        split_fragment_ids = [_segment_name_to_fragment_id(name) for name in segment_names]
        primary_fragment_ids = [_extract_fragment_id(section) for section in _extract_yaml_sections(primary_output or "")]
        split_output_complete = bool(split_fragment_ids) and all(fragment_id in primary_fragment_ids for fragment_id in split_fragment_ids)
        if split_output_complete:
            shot_runtime["final_guard_repair"] = {
                "attempted": False,
                "skipped_reason": "split_fragments_complete_avoid_timeout",
                "initial_hard_issues": primary_hard_issues,
                "remaining_hard_issues": primary_hard_issues,
            }
            outputs["shot_director"] = primary_output
            output = primary_output
            primary_hard_issues = []
        else:
            failed_fragment_ids = _fragment_ids_from_validation_issues(primary_hard_issues, segment_names)
            repair_target_output = _filter_yaml_sections_by_fragment_ids(primary_output, failed_fragment_ids)
            if not repair_target_output:
                repair_target_output = primary_output
            final_repair_scope = (
                f"只修复这些失败片段：{', '.join(failed_fragment_ids)}；"
                "其他已分片输出优先视为可信，不要重写。"
                if failed_fragment_ids
                else "无法定位具体失败片段时，才允许修复完整 YAML。"
            )
            failed_source_context = _planner_source_event_context(
                planner_output,
                failed_fragment_ids or None,
                char_limit=2400,
            )
            final_repair_prompt = (
                "shot_director 最终 YAML 没有通过主校验。请只修正 YAML，不要解释。\n\n"
                f"【返修范围】\n{final_repair_scope}\n\n"
                "【必须修复的硬错误】\n"
                + "\n".join(f"- {issue}" for issue in primary_hard_issues)
                + "\n\n【修复原则】\n"
                "1. 优先信任已分片输出，只修失败/缺失的片段编号。\n"
                "2. 每个返修片段必须有：片段编号、片段任务、节奏、空间连续性总控、镜头列表。\n"
                "3. 每个镜头必须有字段：镜头编号、时长、镜头任务、拍摄主体、镜头、画面动作、台词、必须承载、切镜点、连续性。\n"
                "4. 切镜点必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。\n"
                "5. 长台词必须插入听者反应镜头；只能使用剧本里的人物和台词，不新增剧本外内容。\n"
                "6. 不要输出任何英文字段名；字段名必须全中文。\n\n"
                "【失败片段事件/契约】\n"
                f"{failed_source_context}\n\n"
                "【待修正 YAML（仅失败片段或定位失败时的完整 YAML）】\n"
                f"{repair_target_output}\n\n"
                "请只输出返修范围内的 YAML 片段。"
            )
            repaired_fragment_output = call_llm(
                "你是 shot_director 最终返修导演。只输出修正后的 YAML。",
                final_repair_prompt,
                agent_name="shot_director",
                images_base64=None,
            )
            repaired_fragment_output = _clean_shot_director_output(repaired_fragment_output)
            repaired_fragment_output = _repair_shot_director_output_contracts(repaired_fragment_output, state.get("script", ""))
            repaired_primary = _merge_repaired_yaml_sections(primary_output, repaired_fragment_output, failed_fragment_ids)
            repaired_issues = _collect_shot_director_issues(
                repaired_primary,
                expected_segments=segment_names,
                script=state.get("script", ""),
                planner_output=planner_output,
                aspect_ratio=state.get("aspect_ratio", ""),
            )
            repaired_hard_issues = _hard_shot_director_issues(repaired_issues)
            shot_runtime["final_guard_repair"] = {
                "attempted": True,
                "scope": "failed_fragments" if failed_fragment_ids else "full_yaml",
                "fragment_ids": failed_fragment_ids,
                "output_chars": len(repaired_primary),
                "initial_hard_issues": primary_hard_issues,
                "remaining_hard_issues": repaired_hard_issues,
            }
            if repaired_hard_issues:
                outputs["shot_director"] = primary_output
                outputs["shot_director_guard_repair"] = repaired_primary
                raise RuntimeError(
                    "shot_director primary output failed validation after final repair:\n"
                    + "\n".join(f"- {issue}" for issue in repaired_hard_issues)
                )
            primary_output = repaired_primary
            primary_issues = repaired_issues
            primary_hard_issues = []
            output = repaired_primary

    output, review_runtime, review_report = _run_shot_director_review_board(
        script=state.get("script", ""),
        planner_output=planner_output,
        director_brief=director_brief_text,
        primary_output=primary_output,
        images_base64=None,
    )
    shot_runtime["review_board"] = review_runtime
    if review_report:
        outputs["shot_director_review"] = review_report
        knowledge_metadata.setdefault("shot_director", {})["review_report_chars"] = len(review_report)

    director_issues = _collect_shot_director_issues(
        output,
        expected_segments=segment_names,
        script=state.get("script", ""),
        planner_output=planner_output,
        aspect_ratio=state.get("aspect_ratio", ""),
    )
    hard_director_issues = _hard_shot_director_issues(director_issues)
    if hard_director_issues:
        output = primary_output
        director_issues = primary_issues
        review_runtime["final_validation_status"] = "fallback_to_primary"
        review_runtime["final_validation_issues"] = hard_director_issues
        hard_director_issues = []
    soft_director_issues = [issue for issue in director_issues if issue not in hard_director_issues]
    if soft_director_issues:
        knowledge_metadata.setdefault("shot_director", {})["soft_validation_issues"] = soft_director_issues
    # Single-pass schema: only "final" output
    outputs["shot_director_final"] = stage_outputs.get("final", "")
    outputs["shot_director"] = output
    original_by_segment = dict(state.get("shot_director_original_by_segment") or {})
    for idx in range(1, max(total_segments, 1) + 1):
        fragment_id = f"F{idx:02d}"
        match = re.search(
            rf"(?m)(^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
            rf"(?=\n\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F\d+|\Z)",
            output or "",
        )
        if match:
            original_by_segment.setdefault(str(idx), match.group(1).strip())
    return _persist_update(
        state,
        {
            "status": "waiting_for_user_input",
            "step": "step_3_direct",
            "message": "宏观规划完成，准备生成第 1 段 Prompt。",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "total_segments": total_segments,
            "segment_names": segment_names,
            "current_segment_index": 1,
            "director_review_required": True,
            "director_edits_by_segment": dict(state.get("director_edits_by_segment") or {}),
            "shot_director_original_by_segment": original_by_segment,
            "shot_director_approved_by_segment": dict(state.get("shot_director_approved_by_segment") or {}),
        },
    )






