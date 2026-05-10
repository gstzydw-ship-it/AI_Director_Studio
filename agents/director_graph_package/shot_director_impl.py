"""Shot director implementation split from the legacy director graph module."""
from __future__ import annotations  
  
import re  
import time  
from typing import Any, Callable  
  
from ..knowledge_base import get_agent_knowledge_files  
from .helpers import _primary_script_character_names  
from .state_store import _persist_update  
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
_SHOT_CONSTRUCTION_FRAGMENT_FIELDS: tuple[str, ...] = ("fragment_task", "rhythm", "shots")
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
    "fact_extraction",
    "rhythm_intent_reading",
    "editing_strategy",
    "dramatic_task_mapping",
    "layout_blueprint",
    "shot_language_variety",
    "blocking_and_subshots",
    "cut_timing",
    "conflict_resolution",
    "guard_minimal_repair",
    "final_yaml_handoff",
)
_SHOT_DURATION_RE = re.compile(r"^\s*[\"']?(?:\d+(?:\.\d+)?\s*(?:-|~|–|—)\s*)?\d+(?:\.\d+)?\s*秒[\"']?\s*$")
_SHOT_CUT_TRIGGER_RE = re.compile(
    r"(动作顶点|台词(?:断点|落下|结束)?|反应(?:出现|落点)?|信息(?:看清|揭示)|看清|停住|完成|命中|落桌|撞上|尾帧|切出|切至|切到|→)"
)

def _shot_director_workflow_contract() -> str:
    return (
        "【shot_director 显式工作流】\n"
        "在输出最终 YAML 前，必须按顺序完成以下内部步骤，不能直接套模板生成镜头：\n"
        "1. 事实提取：只提取当前片段的人物、地点、动作、道具、对白和可见事实；禁止补剧情。\n"
        "2. 节奏意图读取：只提取节奏总控里的快慢、停顿、反应归属、卡断、尾帧要求；不得把建议当成改剧情命令。\n"
        "3. 剪辑策略判断：判断哪些位移/开门/上车/走路等无戏剧增量动作应省略，哪些点必须切镜或给反应。\n"
        "4. 戏剧任务判断：判断片段任务与节奏功能，例如建立关系、冲突升级、悬念揭示、情绪极点、钩子结尾。\n"
        "5. 镜头骨架：先决定主镜头数量、每镜拍谁、承担什么覆盖职责和必须承载的信息。\n"
        "6. 镜头语言变化：同一片段内主动安排不同主体、景别、角度或机位；禁止无理由连续重复同一种镜头。\n"
        "7. 动作与子镜头：再补动作路径、听者反应、子分镜重音；子分镜必须服务父镜头，不能漂浮。\n"
        "8. 切镜时机：每个切镜点必须绑定动作顶点前、台词断点、信息看清、反应出现或尾帧完成。\n"
        "9. 冲突裁决：原剧本事实 > 拆片边界 > 连续性/空间安全 > 节奏总控建议 > 镜头美学。\n"
        "10. 最小修复：只做最小修复，检查剧本外内容、漏事件、道具跳变、越轴、特写过密、切点无信息变化、镜头语言重复。\n"
        "11. 最终交付：最后输出可交给提示词编译师的中文 YAML 镜头施工单。\n"
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
                "source_event_count": len(source_events),
                "source_event_preview": [_truncate_for_prompt(event, 180) for event in source_events[:3]],
                "reaction_plan": _truncate_for_prompt(_field_value(section, "reaction_plan"), 240),
                "director_brief": _truncate_for_prompt(_field_value(section, "director_brief"), 240),
            }
        )

    if not fragments:
        fragments = [
            {
                "fragment_id": fragment_id,
                "source_event_count": 0,
                "source_event_preview": [],
                "reaction_plan": "",
                "director_brief": "",
            }
            for fragment_id in expected_segments
        ]

    rhythm_shot_notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    return {
        "mode": "explicit_internal_pipeline",
        "stages": list(_SHOT_DIRECTOR_WORKFLOW_STAGES),
        "required_shot_fields": list(_SHOT_CONSTRUCTION_REQUIRED_FIELDS),
        "coverage_contract_fields": list(_SHOT_COVERAGE_CONTRACT_FIELDS),
        "aspect_ratio": aspect_ratio,
        "rhythm_guidance_present": bool((atmosphere_strategy or "").strip()),
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
        "3. 正确写法示例：商北琛半身中景、乔熙胸部以上中近景、两人双人中景、腕表局部特写。\n"
        "4. 空间只能写作环境关系，例如\"大堂纵深关系清楚\"，不能写成\"大堂中景\"。\n"
    )

def _spatial_geometry_contract_rules() -> str:
    return (
        "【空间几何合同硬规则】\n"
        "1. 当前轻量施工单不再输出 camera_basis 等内部字段；空间几何必须翻译进 shot 与 continuity。\n"
        "2. shot 只写【视角+景别】，例如过肩视角半身以上中景、侧面视角双人中景、背后视角半身中景；不要写复杂机位坐标或运镜说明。\n"
        "3. continuity 必须写清人物站位、朝向、左右关系、道具位置和可继承尾帧；不能只写\"保持连续\"。\n"
        "4. 人物转身、穿门、进电梯/车门/房门等阈值动作，优先使用侧面、背后或场景固定机位；不要用人物正前方固定机位硬拍动作路径。\n"
        "5. 如果人物面朝电梯/门口且镜头拍正面，门框只能是前景或侧边锚点，不能写成后景。\n"
        "6. 几何闭环优先于好听文案：shot、action、continuity 三者必须互相兼容。\n"
    )

def _camera_execution_rules() -> str:
    return (
        "【机位与运镜可执行硬规则】\n"
        "1. 内部镜头设计必须保留完整镜头语法：主体+主体景别、焦段、景深、机位高度、拍摄角度、唯一运镜、动作/表演、光源；不得因为最终要给 Seedance 就提前丢掉焦段/景深/高度/角度判断。\n"
        "2. 每个 shot 只能有一个主体焦点、一个景别基底、一个主导运镜；景别可以在子分镜内递进，但不能写成\"纵深中全景到半身中景\"这种单字段混合景别。\n"
        "3. 机位高度从仰拍、平视、俯拍、顶拍、虫眼中选择；普通关系/对白可用平视，权力压制可用仰拍，弱势/群体散开可用俯拍。最终 prompt 可把\"平视\"译成自然短句，避免机械写\"眼平高度\"。\n"
        "4. 拍摄角度从正面、左前方、右前方、左侧、右侧、背后、过肩、荷兰角、POV 中选择；POV 必须先有建立镜头说明谁在看，禁止直接跳 POV。\n"
        "5. 运镜从推镜、拉镜、横移、横摇、垂直摇、升降、变焦、稳定器跟拍、手持、固定机位中选唯一主导运镜；禁止在一个 shot 内同时推近、横移、摇摄、再回主位。\n"
        "6. 运镜必须服务镜头目的：推近/切近/转特写只能服务信息逼近、情绪暴露、压迫上升、受击反应变重要、道具或局部动作成为焦点；禁止把慢推近当通用情绪模板。\n"
        "7. 反应落点优先按层级处理：主分镜负责主体关系和空间重心，子分镜负责受击、表情重音、局部动作；不要把\"同一运动里带到反应再回主位\"写成一个复杂主镜头。\n"
        "8. 禁止复合景别/复合机位：不要写\"纵深中全景到半身中景\"\"中景转电梯口关系景\"\"右后方中景转固定机位\"\"同轴线偏右侧\"\"前后景关系\"。改成结构化字段：shot_size=MS/MCU，angle=正面/斜侧面/背面，movement=固定/跟拍。\n"
        "9. 禁止使用模糊机位词：三分之四角度、斜侧、斜前方、轻微前推、轻微前推跟随、缓慢靠近、背影轻压。\n"
        "10. 禁止抽象判断句。不要写\"沉默就是回应\"\"权力关系锁住\"\"空气收紧\"\"命令落地即见效\"\"形成清晰钩子\"。必须改写成可见动作：停顿几秒、谁看向谁、谁后退半步、谁让出通道、电梯门停在什么开合状态。\n"
        "11. 内部可以技术化，最终编译必须感知化：85mm浅景深可译为\"背景虚化、主体突出\"，深景深可译为\"前后景都清楚\"，不得把\"电影感/高级感\"写成空壳标签。\n"
    )

def _camera_task_selection_rules() -> str:
    return (
        "【镜头任务到机位选择硬规则】\n"
        "1. 先判断当前 main_shot 的 coverage_role 与 shot_intent，再决定 shot_size、camera_height、angle、movement、lens、depth；不要先挑一个好看的机位再硬套剧情。\n"
        "2. 主分镜只在主体关系变化、场面权力关系变化、叙事重心变化、空间观察点变化、当前主镜头无法承载下一动作单元时新开；不要用主分镜机械对应每句台词。\n"
        "3. 完整发言单元优先保持在同一主分镜内；长挑衅/揭晓/质问台词超过2秒时，用子分镜/L-cut 切受击者，让后半句以画外音落在反应上。\n"
        "4. 听者受击、视线撞上、回神、表情冻结：优先挂到现有主镜头或新增 sub_shot；受击者机位必须落在同侧轴线内，并写 companion_visibility，不要靠横移摆尾带到反应。\n"
        "5. 动作路径、身体位移、擦身而过、碰撞、扶住、松手：优先左侧、右侧、左后方、右后方或 scene_fixed；目标是看清起点、路径、接触点和终点。整段保持选定轴线一侧。\n"
        "6. 目标方向、走向门口、冲向门缝、进入电梯、穿过门框、离开画面：优先背面、斜侧面或 scene_fixed；目标是看清人物前方目标与阈值关系。\n"
        "7. 9:16 主力景别为半身景/中景/MS，MCU 只用于压迫段或信息逼近中间层，CU 只用于信息炸点/受击反应/情绪顶点；禁止长期只在 MCU 与 CU 之间摆动。\n"
        "8. 群体调度必须保留空间容量：群体四散、主管退让、员工让路不能用面部特写承接，优先中景关系、半身关系或 scene_fixed。\n"
        "9. 每个 main_shot 必须有 cut_reason，回答为什么从上一主镜头切到这里；有效理由包括台词落点后切听者反应、动作中间态切接续、需要回关系景确认距离/门状态、tailframe_reset。\n"
        "10. sub_shot 必须有 parent_shot_id、trigger、shot_size、cut_point、companion_visibility、state_delta、beat_purpose、emotion_anchor、duration_hint、action_phase；每个片段最多2个子分镜。\n"
        "11. 如果一个 fragment 里有多个 main_shots，禁止所有 shot 都重复同一套 shot_size + angle + movement；但变化必须有叙事动机，禁止假丰富感。"
    )

def _space_rules_contract_rules() -> str:
    return (
        "[Scene Map Contract]\n"
        "1. Every fragment must include space_rules before shots. This is the floor-plan contract for layout, blocking, guard, and compiler.\n"
        "2. space_rules.space_anchors must name the stable set pieces / thresholds / landmarks and their relative directions, such as door=north, table=center, window=east.\n"
        "3. space_rules.character_positions must describe each active character's start position, end position when known, and body facing relative to the anchors.\n"
        "4. space_rules.action_axis must define the main eyeline/action axis and which side is the safe camera side.\n"
        "5. space_rules.safe_camera_zones must list physically valid camera zones that preserve the axis and keep required bodies/landmarks visible.\n"
        "6. space_rules.blocked_camera_zones must list forbidden or risky zones, such as axis-crossing seats, occluded corners, impossible doorway positions, or positions that hide the body path.\n"
        "7. main_shot.camera_scene_position and visible_landmarks must be compatible with space_rules. If a shot uses scene_fixed, it must come from a safe_camera_zones entry or explain the exception in selection_reason.\n"
    )

def _best_shot_selection_rules() -> str:
    return (
        "[Best Shot Selection Contract]\n"
        "1. Do not choose a shot only because it matches a rule category. First decide the viewer's attention job.\n"
        "2. Every main_shot must include attention_target: who or what the viewer must watch at this exact moment.\n"
        "3. Every main_shot must include information_strategy: what the shot reveals, delays, hides, or lets the viewer miss.\n"
        "4. Every main_shot must include selection_reason: why this specific shot size / angle / camera seat is the strongest choice now.\n"
        "5. Every main_shot must include rejected_alternatives: at least one tempting but weaker option and why it was rejected.\n"
        "6. selection_reason cannot be generic words such as cinematic, looks good, follows rules, or more emotional. Tie it to attention, information, space, body action, or cut continuity.\n"
        "7. If the shot is a reaction, explain why the viewer needs the receiver now instead of the speaker; if it is an action path, explain why the body path must stay readable; if it is a relation reset, explain what spatial confusion it repairs.\n"
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
        "2. 场次标题、人物行、source_script_events 的可见事实优先级高于英文台词里的词义联想；例如 OS 里出现 \"wake up\" 只表示乔熙自我提醒，不能改拍成乔熙睡觉、睁眼或被伴侣叫醒。\n"
        "3. 场景空间必须继承场次标题和 source_script_events；公寓不能改成车内，门口不能改成大堂，集团门口不能改成办公室。\n"
        "4. subject 只能来自当前片段的人物行、source_script_events 中的可见人物/群体/道具/车辆；不能把 OS 里的昵称或英文名当成画面主体替换角色名。\n"
        "5. 必须继承上游的道具状态和空间状态：照片在桌上就保持在桌上，书包在小豆丁身上就保持在小豆丁身上，不得为了情绪镜头改写为攥在手里或塞回书包。\n"
        "6. 低歧义画面优先：优先使用站位、视线、停顿、桌面、门口、车辆到达、下车等稳定可见动作；避免把简单动作改成掌心、指尖、指节、发丝等微观细节。\n"
        "7. 先判断当前片段的节奏任务，再匹配镜头语言；必须先回答这是权力反转、冲突升级、悬念揭示、误解错位、情绪极点还是钩子结尾，再决定要不要切镜、切几镜，不能先拿模板再套剧情。\n"
        "8. 9:16 竖屏默认以半身、中景、双人关系景别承担叙事；特写只给炸点、受击、情绪峰值或关键信息插入。一个片段的面部特写最多一次，不得把特写当默认景别。\n"
        "9. 没必要每个细节动作都给镜头：如果主镜头已经能看清动作和关系，就不要再为手指、掌心、鞋尖、袖口、嘴唇、眼角等微细节单独开镜头；只有线索揭示、动作前摇或受击落点无法看清时才允许插入。\n"
        "10. 悬念揭示优先采用\"停顿/发现前逼近 -> 关键物或文字 -> 人物反应\"；冲突升级优先采用\"施压 -> 受击 -> 短暂停顿\"；误解错位优先提升听者反应镜头，而不是让说话者一直占满画面。\n"
        "11. shot_director 不得重新判断整体节奏，必须服从 atmosphere_strategy / rhythm supervisor 给出的快慢、停顿、卡断、反应归属、尾帧承接。\n"
        "12. 若节奏建议与剧本事实、台词原文、动作道具连续性、人物位置、空间轴线安全冲突，后者优先。\n"
    )

def _shot_director_rhythm_match_rules() -> str:
    return (
        "【节奏与镜头匹配规则（参考《AI 导演系统工程文档规范》）】\n"
        "0. shot_director 只执行 story_planner 与 rhythm supervisor 给出的片段节奏指令，不得重新判断整体节奏；必须服从 atmosphere_strategy 的快慢、停顿、卡断、反应归属、尾帧承接。\n"
        "1. 先识别戏剧微粒，再决定镜头：权力反转看压制与失势，冲突升级看施压与受击，悬念揭示看发现与停顿，误解错位看听者反应，情绪极点看停住后的内压，钩子结尾看最后的悬住点。\n"
        "2. 镜头数量由节奏任务决定，不由镜头库模板决定；能用 1 个主镜头讲清的动作，不要硬拆成 3 个细碎镜头。\n"
        "3. 需要切镜时，只切信息增量最大的节点：动作前摇、揭示落点、受击反应、关系变化、关键道具或文字出现。走近、弯腰、拿起、站定等中间过渡默认省略。\n"
        "4. 权力反转优先用站位高低、画面占比、稳定推进和反应落点表达，不靠堆叠特写表达压迫。\n"
        "5. 冲突升级优先 2-3 秒短镜，保留施压、受击和停顿，切掉无信息量动作过程。\n"
        "6. 悬念揭示里的关键物、文件、屏幕、照片要稳拍可读；不要为了好看加花哨运动，文字类信息优先静态或极轻微推进。\n"
        "7. 情绪极点允许更稳、更长一点，但仍应以简单背景、少动作、少机位运动为前提；9:16 下优先稳住半身或中景，再考虑是否真的需要更近景别。\n"
        "8. 9:16 竖屏下，半身/中景/双人关系镜头是主力，特写是强调而不是默认。若一个片段出现多次面部特写，必须有明确的炸点、受击或揭示理由，否则视为过度设计。\n"
        "9. 微细节镜头只用于关键信息，不用于堆砌存在感。手、嘴唇、眼角、袖口、鞋尖、发丝等局部如果不承载线索、动作前摇或受击结果，就不要单独给镜头。\n"
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

    required_terms = [
        "乔熙",
        "小豆丁",
        "苏小可",
        "严飞",
        "商北琛",
        "照片",
        "桌",
        "书包",
        "门口",
        "秘书",
        "主管",
        "队列",
        "劳斯莱斯",
        "车门",
        "咖啡杯",
    ]
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

def _truncate_for_prompt(text: str, limit: int = 12000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n...[已截断，仅保留前文供修复参考]..."

def _runtime_context_contract_card() -> str:
    return (
        "[Runtime Context Contract]\n"
        "- story_planner 保留原始剧本作为逐字引用来源；其他阶段不要重新理解全剧本。\n"
        "- layout 只负责 shots 机位骨架，不承担剧本理解、情绪设计、动作调度或身份锁定。\n"
        "- blocking/guard/prompt_compiler 只使用当前片段资产和当前镜头资产，避免被其他片段带偏。\n"
        "- 参考图只负责身份/空间锚定；人物形象细节不需要在最终 prompt 中重复展开。\n"
        "- 如果人物面朝电梯且镜头写正面，电梯门框只能是前景边缘/左右侧边缘，不能写成后景。"
    )

def _is_local_insert_subject(value: str) -> bool:
    return bool(re.search(r"手|手部|门缝|按钮|文件|手机|衣角|车门|电梯门|照片|道具", value or ""))


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

            cut_point = _yaml_line_field(shot_block, "cut_point")
            if cut_point and (
                _GENERIC_CUT_REASON_RE.search(cut_point)
                or not _SHOT_CUT_TRIGGER_RE.search(cut_point)
            ):
                issues.append(f"{shot_id} 的 cut_point 过于空泛，必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。")

            subject = _yaml_line_field(shot_block, "subject")
            task = _yaml_line_field(shot_block, "task")
            if _is_local_insert_subject(subject) and not re.search(r"唯一主体|文件内容|信息揭示|关键物|证据|屏幕|照片", task):
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
    match = re.search(rf"(?m)^\s*-?\s*(?:{_shot_yaml_field_pattern(field)})\s*:\s*(.+?)\s*$", block or "")
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")

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

    attention = clean(_yaml_scalar_field(block, "attention_target"), clean(_yaml_scalar_field(block, "subject"), "current subject"))
    information = clean(
        _yaml_scalar_field(block, "information_strategy"),
        clean(_yaml_scalar_field(block, "shot_intent"), "current story information"),
    )
    coverage = clean(_yaml_scalar_field(block, "coverage_role"), "coverage beat")
    cut_reason = clean(_yaml_scalar_field(block, "cut_reason"), "this cut point")
    camera_seat = clean(
        _yaml_scalar_field(block, "camera_scene_position"),
        clean(_yaml_scalar_field(block, "angle"), "this camera seat"),
    )
    return (
        f"viewer attention stays on {attention}; information strategy is {information}; "
        f"the {camera_seat} choice supports {coverage} at {cut_reason} while preserving space/action/cut continuity"
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
    has_long_english = sum(len(word) for word in ascii_words) >= 42 or len(ascii_words) >= 8
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

def _shot_director_rule_block(aspect_ratio: str) -> str:
    return (
        f"{_shortdrama_master_rules()}\n"
        f"{_script_fidelity_rules()}\n"
        f"{_subject_framing_rules()}\n"
        f"{_shot_composition_task_selection_rules()}\n"
        f"{_dialogue_coverage_contract_rules()}\n"
        f"{_spatial_geometry_contract_rules()}\n"
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
        "5. 不改变 id 和 fragment_id。\n"
        "6. 不改变人物出入场关系。\n"
        "7. 不保留 rejected_alternatives 的具体错误画面描述。\n"
        "8. 所有 must_not_show 必须简短，不要展开描述。\n"
        "9. action 只写可见动作，不写心理解释。\n"
        "10. 如果字段冲突，优先保留 continuity、space_rules、shots.action。\n"
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
        return f"[Aspect Ratio]\n{aspect_ratio}\n\n[Planner Excerpt]\n{(planner_output or '').strip()[:2000]}"

    lines = [
        "[Layout Input Contract]",
        "Design only the camera skeleton for each fragment.",
        "Use the planner summary below. Do not re-interpret the whole script.",
        _runtime_context_contract_card(),
        "",
        "[Aspect Ratio]",
        aspect_ratio,
        "",
        "[Fragments]",
    ]
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        dramatic_unit = _field_value(section, "dramatic_unit") or _field_value(section, "片段任务") or _field_value(section, "承接要求")
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
                f"- fragment_id: {fragment_id}",
                f"  dramatic_unit: {_trim_layout_text(dramatic_unit, 120) or 'n/a'}",
                f"  active_cast: {', '.join(active_cast) if active_cast else 'n/a'}",
                f"  must_not_show: {', '.join(must_not_show) if must_not_show else 'n/a'}",
                f"  continuity_entry: {_trim_layout_text(continuity_entry, 140) or 'n/a'}",
                f"  continuity_exit: {_trim_layout_text(continuity_exit, 140) or 'n/a'}",
                "  key_events:",
            ]
        )
        if key_events:
            lines.extend(f"    - {event}" for event in key_events)
        else:
            lines.append("    - n/a")
        lines.append("  dialogue_lines:")
        if dialogue_lines:
            lines.extend(f"    - {line}" for line in dialogue_lines)
        else:
            lines.append("    - none")
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

def _extract_rhythm_shot_director_notes(atmosphere_strategy: str) -> str:
    """Extract rhythm supervisor notes that are explicitly addressed to shot_director."""
    text = (atmosphere_strategy or "").strip()
    if not text:
        return ""

    label_pattern = re.compile(
        r"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?"
        r"(?:shot_director_notes|镜头导演节奏执行约束|镜头导演执行约束|给镜头导演的节奏执行约束)"
        r"\s*[：:]\s*(.*)$"
    )
    match = label_pattern.search(text)
    if not match:
        return ""

    stop_pattern = re.compile(
        r"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?"
        r"(?:rhythm_diagnosis|rhythm_contract|segment_boundary_advice|reaction_ownership|tailframe_handoff|"
        r"construction_notes|shot_director_notes|risk_flags|atmosphere_strategy|rewritten_script|改写后剧本|"
        r"节奏总合同|拆片边界建议|反应归属|尾帧承接|结构规划施工指令|"
        r"镜头导演节奏执行约束|镜头导演执行约束|给镜头导演的节奏执行约束|风险提醒)"
        r"\s*[：:]"
    )
    lines: list[str] = []
    first_line = match.group(1).strip()
    if first_line:
        lines.append(first_line)

    for line in text[match.end() :].splitlines():
        if stop_pattern.match(line):
            break
        lines.append(line.rstrip())

    return "\n".join(lines).strip()

def _rhythm_shot_director_notes_prompt(atmosphere_strategy: str) -> str:
    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    if not notes:
        return ""
    return (
        "[节奏总控给镜头导演的执行约束]\n"
        "这是上游给镜头施工层的节奏约束，主要控制反应归属、停顿、切点、无效过渡压缩和尾帧承接。"
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
    if atmosphere_strategy:
        lines.extend(
            [
                "",
                "[Atmosphere Excerpt]",
                _truncate_for_prompt(atmosphere_strategy, 1600),
            ]
        )
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
        return f"[Aspect Ratio]\n{aspect_ratio}\n\n[Fragment]\n- fragment_id: {fragment_id}\n"
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
    "rhythm_alignment": ("节奏总控", "节奏执行", "停顿", "卡断", "反应归属", "快慢"),
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
    "rhythm_alignment": ("节奏总控", "节奏执行", "快慢", "停顿", "卡断", "反应归属", "尾帧要求"),
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
        "调用节奏联动规则：继承节奏总控的快慢、停顿、反应归属和尾帧意图；"
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
        "必须把节奏总控建议翻译为时长、停顿、反应归属、切镜点或尾帧；"
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
                "节奏总控建议只负责快慢、停顿、反应归属、卡断和尾帧意图；镜头导演必须按原剧本事实、拆片边界和连续性规则合法落地",
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
        "节奏总控只提供快慢、停顿、反应归属、卡断和尾帧意图；若与原剧本事实、拆片边界、空间连续性冲突，必须以后者为准。",
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
        signal_text = "\n".join([section, "\n".join(source_events), atmosphere_strategy, director_brief])
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
            "镜头选择必须继承总导演意图、节奏总控和 story_planner 的 source_script_events；不得为了套模板新增剧情。"
            "节奏总控是节奏意图来源，不是镜头硬模板；你负责把快慢、停顿、反应归属、卡断和尾帧要求合法转译成镜头语言。\n\n"
            "【输出语言硬规则】\n"
            "最终 YAML 必须使用中文字段名，不要输出 fragment_id、shot_id、duration、task、subject、must_carry、cut_point、continuity 等英文字段名。\n\n"
            "【每个片段必须交付】\n"
            "1. 片段任务 — 本片段的剧情施工任务，例如建立关系、冲突升级、信息揭示、反应落点、权力反转、喜剧泄压、尾帧钩子。\n"
            "2. 节奏 — 继承节奏总控和拆片规划的节奏意图，例如压缩、放慢、停顿、卡断、短促泄压；若发生冲突，说明按原剧本/连续性优先。\n\n"
            "【每个镜头必须回答】\n"
            "1. 时长 — 该镜头在片段内的时间段，必须连续，例如 0-2秒、2-5秒。\n"
            "2. 镜头任务 — 这个镜头负责什么：建立关系、承载对白、动作推进、信息揭示、反应落点、尾帧承接等。\n"
            "3. 拍摄主体 — 拍谁（人物名、双人关系或剧本已有道具）。\n"
            "4. 镜头 — 只写【视角+景别】，例如过肩视角半身以上中景、侧面视角双人中景、背后视角半身中景。\n"
            "5. 画面动作 — 在干嘛（可见动作，不写心理）。\n"
            "6. 台词 — 原剧本台词、画外音或 ~；不得新增台词。\n"
            "7. 必须承载 — 这个镜头必须承载的剧情信息或表演落点。\n"
            "8. 切镜点 — 具体切镜触发点，必须绑定动作顶点、台词断点、信息看清、反应出现、状态完成或尾帧。\n"
            "9. 连续性 — 动作、道具、人物左右关系、轴线或尾帧状态如何继承。\n\n"
            "【可选字段】\n"
            "- 类型 — 只在非标准镜头时写：受击反应、道具/信息特写、切离镜头。\n"
            "- 声音 — 只在需要画外音、声音先行或声音延续时写。\n\n"
            "【镜头设计原则】\n"
            "1. 事实红线高于一切：不新增剧本外的人物、台词、动作、道具或情节。\n"
            "2. 节奏总控决定快慢、停顿、反应归属、卡断和尾帧意图；镜头导演决定用哪些景别、机位、主体、声音和剪辑方式合法落地。\n"
            "3. 长台词或高压命令必须拆出视觉覆盖：说话者起句、同侧听者反应/过肩、必要时后半句以画外音、声音先行或声音延续落到反应上。\n"
            "4. 切镜点不许只写\"切出/继续/增强情绪\"，必须写清触发物，例如动作顶点、台词断点、信息看清、反应出现、门关闭完成、尾帧状态稳定。\n"
            "5. 片段编号必须沿用拆片方案的 F01/F02/F03...，不得改名合并跳号。\n"
            "6. 同一片段有3个及以上镜头时，必须至少变化一种维度：拍摄主体、景别、视角/机位、声音承载或镜头任务；不得无理由连续重复。\n"
            "7. 走路、上车、开门、进入新空间等无戏剧增量过程优先用机位/景别/主体切换省略，只保留关键起点帧和终点帧。\n"
            "8. 冲突裁决顺序：原剧本事实 > story_planner片段边界 > 连续性/空间安全 > 节奏总控建议 > 镜头美学。\n"
            f"9. 画幅：{aspect_ratio}",
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
            "  镜头列表:\n"
            "    - 镜头编号: F01-S01\n"
            "      时长: 0-2秒\n"
            "      镜头任务: 建立关系/承载对白/动作推进/信息揭示/反应落点/尾帧承接\n"
            "      拍摄主体: 人物名/双人关系/剧本已有道具\n"
            "      镜头: 视角+景别，例如过肩视角半身以上中景\n"
            "      画面动作: 可见动作，不写心理\n"
            "      台词: 原剧本台词/画外音或 ~\n"
            "      必须承载: 这个镜头必须承载的剧情信息或表演落点\n"
            "      切镜点: 动作顶点/台词断点/信息看清/反应出现/状态完成/尾帧\n"
            "      连续性: 动作、道具、人物左右关系、轴线或尾帧状态如何继承\n"
            "      类型: 受击反应/道具信息特写/切离镜头（非标准镜头时写）\n"
            "      声音: 画外音/声音先行/声音延续（需要时写）\n\n"
            "【关键要求】\n"
            "1. 必须覆盖拆片方案的所有片段编号。\n"
            "2. 必须继承节奏总控施工意图，把快慢、停顿、卡断、反应归属落实到时长、镜头任务、画面动作、切镜点、连续性；冲突时以原剧本、拆片边界和连续性为准。\n"
            "3. 长台词或高压命令必须插入听者反应覆盖，不能站桩正反打。\n"
            "4. 保持片段编号和镜头编号稳定，遵循 F01/F02... 和 F01-S01/F01-S02... 格式。\n"
            "5. 台词只能使用原剧本文字、原剧本画外音或写 ~；不得新增台词。\n"
            "6. 只有剧本已有信息载体才能成为拍摄主体；不要新增空镜、道具或环境信息。\n"
            "7. 每个镜头的时间段必须连续，前后衔接。\n"
            "8. 不要输出任何英文字段名；字段名必须使用上面的中文写法。\n\n"
            "9. 每个片段必须执行【镜头库调用任务单】里的镜头库任务：先判断剧情信号，再决定镜头结构和切点；"
            "如果任务单与原剧本事件冲突，以原剧本事件和拆片边界为准。\n\n"
            "10. 每个片段必须主动判断剪辑省略点和镜头语言变化策略；不要让一个中景/同一机位吃完整段戏。\n\n"
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
            "2. 每个返修片段必须有：片段编号、片段任务、节奏、镜头列表。\n"
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
    """Backward-compatible alias retained for orchestration tests and monkeypatch hooks."""
    return _run_shot_director_single_pass(*args, **kwargs)


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

def _run_shot_director_review_board(
    *,
    script: str,
    planner_output: str,
    director_brief: str = "",
    primary_output: str,
    images_base64: list[str] | None = None,
) -> tuple[str, dict[str, Any], str]:
    """Package-local review board for the split shot_director flow.

    This conservative review board does not reinterpret overall rhythm. It
    validates the primary YAML against script facts, source_event coverage,
    continuity/hallucination guards and vertical-format discipline, then returns
    the primary output unless a future deterministic or LLM repair is added.
    """
    _ = (script, planner_output, director_brief, images_base64)
    started = time.perf_counter()
    report = "shot_director review board: accepted primary output; no rhythm re-judgement performed."
    runtime = {
        "agent_name": "shot_director_review_board",
        "mode": "deterministic_guard",
        "status": "accepted_primary",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "output_chars": len(primary_output or ""),
    }
    return primary_output, runtime, report

def shot_director_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    director_brief_text = _director_brief(state)
    planner_output = outputs.get("story_planner", "")
    segment_names = list(state.get("segment_names") or [])
    total_segments = int(state.get("total_segments") or 0)
    if not segment_names:
        derived_total, segment_names = _derive_segments_from_planner_output(planner_output)
        if not total_segments:
            total_segments = derived_total
    # For single-pass schema, check for "final" output; for split runs, also
    # keep completed fragment outputs so a restart resumes from the first
    # unfinished fragment instead of rerunning every fragment.
    resume_stage_outputs: dict[str, str] = {}
    if outputs.get("shot_director"):
        resume_stage_outputs["final"] = outputs.get("shot_director", "")
    for key, value in outputs.items():
        prefix = "shot_director_fragment_"
        if key.startswith(prefix) and value:
            resume_stage_outputs[key.removeprefix("shot_director_")] = value
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
    reference_images = _reference_images(state) or None
    scene_reference_context = _reference_image_manifest_prompt(state)
    stage_runtimes: dict[str, dict[str, Any]] = {}

    def persist_stage(stage_name: str, stage_output: str, stage_runtime: dict[str, Any], stage_meta_snapshot: dict[str, dict[str, Any]]) -> None:
        stage_runtimes[stage_name] = dict(stage_runtime)
        output_key = f"shot_director_{stage_name}"
        output_key_final = f"shot_director_{stage_name}"
        outputs[output_key_final] = stage_output
        if stage_name == "final":
            outputs["shot_director"] = stage_output

        retrieval_key = "final" if "final" in stage_meta_snapshot else stage_name
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
            "mcp_enabled": False,
            "total_elapsed_seconds": round(time.perf_counter() - shot_runtime_started, 3),
        }
        knowledge_metadata["shot_director"]["stage_retrieval"] = stage_meta_snapshot

        completed_fragment_index = 0
        if stage_name.startswith("fragment_F"):
            try:
                completed_fragment_index = int(stage_name.rsplit("F", 1)[1])
            except Exception:
                completed_fragment_index = 0
        active_index = completed_fragment_index or 1
        stage_messages = {
            "final": "镜头导演输出已完成，准备生成第 1 段 Prompt。",
        }
        if completed_fragment_index:
            stage_messages[stage_name] = (
                f"镜头导演已完成 {stage_name.removeprefix('fragment_')} "
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

    output, shot_runtime, stage_meta, stage_outputs = _run_shot_director_single_pass(
        script=state.get("script", ""),
        planner_output=planner_output,
        atmosphere_strategy=state.get("atmosphere_strategy", ""),
        aspect_ratio=state.get("aspect_ratio", "16:9"),
        expected_segments=segment_names,
        images_base64=reference_images,
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
    shot_runtime["mcp_enabled"] = False
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
                "2. 每个返修片段必须有：片段编号、片段任务、节奏、镜头列表。\n"
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
        images_base64=reference_images,
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






