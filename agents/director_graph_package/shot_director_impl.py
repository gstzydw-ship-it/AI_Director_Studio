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
from .llm import _get_llm_settings, call_llm
from .prompting import build_system_prompt


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
_DIALOGUE_COVERAGE_TERMS_RE = re.compile(
    r"(反应|受击|听者|对手|对方|过肩|肩线|反打|视线|切回|切至|切到|切出|台词断点|画外音|OS|L-cut|J-cut|景别递进)"
)
_SHOT_CONSTRUCTION_FRAGMENT_FIELDS: tuple[str, ...] = ("fragment_task", "rhythm", "shots")
_SHOT_CONSTRUCTION_REQUIRED_FIELDS: tuple[str, ...] = (
    "shot_id",
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
)
_SHOT_COVERAGE_CONTRACT_FIELDS: tuple[str, ...] = (
    "coverage_role",
    "cut_reason",
    "companion_visibility",
    "state_delta",
    "tailframe_role",
)
_SHOT_DIRECTOR_WORKFLOW_STAGES: tuple[str, ...] = (
    "fact_extraction",
    "dramatic_task_mapping",
    "layout_blueprint",
    "blocking_and_subshots",
    "cut_timing",
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
        "1. fact_extraction：只提取当前 fragment 的人物、地点、动作、道具、对白和可见事实；禁止补剧情。\n"
        "2. dramatic_task_mapping：判断片段任务与节奏功能，例如建立关系、冲突升级、悬念揭示、情绪极点、钩子结尾。\n"
        "3. layout_blueprint：先决定主镜头数量、每镜拍谁、承担什么覆盖职责和必须承载的信息。\n"
        "4. blocking_and_subshots：再补动作路径、听者反应、子分镜重音；子分镜必须服务父镜头，不能漂浮。\n"
        "5. cut_timing：每个 cut_point 必须绑定动作顶点前、台词断点、信息看清、反应出现或尾帧完成。\n"
        "6. guard_minimal_repair：只做最小修复，检查剧本外内容、漏事件、道具跳变、越轴、特写过密、切点无信息变化。\n"
        "7. final_yaml_handoff：最后输出可交给 prompt_compiler 的 YAML 镜头施工单。\n"
        "每个 shot 除基础字段外，尽量补齐 coverage_role、cut_reason、companion_visibility、state_delta、tailframe_role，"
        "让下游无需猜测镜头职责、切镜原因、同场人物位置和尾帧状态。\n"
    )


def _shot_director_coverage_contract_prompt() -> str:
    return (
        "【每个 shot 需要补齐的镜头职责字段】\n"
        "- coverage_role：这镜负责什么覆盖任务，例如建立关系、承载对白、听者反应、道具信息、尾帧承接。\n"
        "- cut_reason：为什么必须在这里切，必须绑定动作顶点前、台词断点、信息看清、反应出现或尾帧完成。\n"
        "- companion_visibility：同场人物是否在画面里、在前景/背景/画外/过肩位置，避免人物位置突然消失。\n"
        "- state_delta：这一镜比上一镜多交代了什么信息、情绪或空间状态。\n"
        "- tailframe_role：这一镜尾帧怎样交给下一镜或下一片段。\n"
        "这些字段是给 prompt_compiler 的施工依据，不能写成空泛形容词。\n"
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
  
  
def _reference_images(state: DirectorState) -> list[str]:
    """Shot director consumes scene_analyst text; raw reference images stay scene-only."""
    _ = state
    return []
  
  
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
        "1. 当前轻量施工单不再输出 camera_basis 等内部字段；空间几何必须翻译进 camera 与 continuity。\n"
        "2. camera 必须写清摄影机相对人物或场景的位置，例如正前方、左前方45度、右侧90度、背后、桌侧固定机位、电梯门外固定机位。\n"
        "3. continuity 必须写清人物站位、朝向、左右关系、道具位置和可继承尾帧；不能只写\"保持连续\"。\n"
        "4. 人物转身、穿门、进电梯/车门/房门等阈值动作，优先使用侧面、背后或场景固定机位；不要用人物正前方固定机位硬拍动作路径。\n"
        "5. 如果人物面朝电梯/门口且镜头拍正面，门框只能是前景或侧边锚点，不能写成后景。\n"
        "6. 几何闭环优先于好听文案：camera、action、continuity 三者必须互相兼容。\n"
    )

def _camera_execution_rules() -> str:
    return (
        "【机位与运镜可执行硬规则】\n"
        "1. 每个时间段第一句必须写清：主体+景别+简洁机位+镜头高度+运镜方式；人物朝向只在动作需要时补一句。\n"
        "2. 摄影机位置优先使用大模型更稳的短词：正面、左前方、右前方、左侧、右侧、背后、左后方、右后方。只有空间易混淆时才补 0度/45度/90度/180度，不要每段都写数字角度。\n"
        "3. 镜头高度必须写成眼平高度、低机位仰拍、高机位俯拍之一；不要只写\"平视侧前方\"\"平视三分之四角度\"。\n"
        "4. 运镜必须写成固定机位、轨道前推 dolly-in、轨道后拉 dolly-out、稳定器跟拍 tracking shot、稳定器在人物前方同速后退、稳定器在人物背后同速前进、横移 truck left/right、摇镜 pan left/right 之一。\n"
        "5. 如果写\"跟随\"，必须说明摄影机在人物前方/背后/左侧/右侧，以及它是同速后退、同速前进还是平行横移；禁止写\"轻微前推跟随\"。\n"
        "6. 禁止使用模糊机位词：三分之四角度、斜侧、斜前方、轻微前推、轻微前推跟随、缓慢靠近、背影轻压。\n"
        "7. 禁止抽象判断句。不要写\"沉默就是回应\"\"权力关系锁住\"\"空气收紧\"\"命令落地即见效\"\"形成清晰钩子\"。必须改写成可见动作：停顿几秒、谁看向谁、谁后退半步、谁让出通道、电梯门停在什么开合状态。\n"
        "8. 可以使用专业术语，但最终 prompt 只保留可执行短句；例如\"商北琛半身中景，正面眼平，稳定器在他前方同速后退\"。\n"
    )

def _camera_task_selection_rules() -> str:
    return (
        "【镜头任务到机位选择硬规则】\n"
        "1. 先判断当前 shot 的 task，再决定 camera 与 size；不要先挑一个好听的机位，再把动作硬塞进去。\n"
        "2. 发言承载、正面施压、冷处理对峙：单段只能从 正前方0度、左前方30度/45度、右前方30度/45度 三类中**选一类并贯穿全段**——同段不得同时出现\"左前方\"和\"右前方\"这种 180° 跨轴。前提是人物朝向稳定，且没有转身、穿门、进电梯这类阈值动作。\n"
        "3. 听者受击、视线撞上、回神、表情冻结：受击者机位必须落在第 2 条选定的同侧；并保留对手肩线、门框、桌边或人物边缘虚化作为空间锚点。\n"
        "4. 动作路径、身体位移、擦身而过、碰撞、扶住、松手：优先 左侧90度、右侧90度、左后方135度、右后方135度，或 scene_fixed；目标是看清起点、路径、接触点和终点。整段保持选定一侧。\n"
        "5. 目标方向、走向门口、冲向门缝、进入电梯、穿过门框、离开画面：优先 背后180度、左后方135度、右后方135度，或 scene_fixed；目标是看清人物前方目标与阈值关系。\n"
        "6. 双人关系复位、群体关系复位、尾帧交接：优先 双人半身关系景 或 scene_fixed 关系景，重新交代距离、站位、轴线和谁仍在画内。\n"
        "7. **机内连续运动不计为切镜**：稳机推近 dolly-in、稳机后拉 dolly-out、上摇 tilt-up、下摇 tilt-down、横移 truck、跟拍 tracking 都属于同一镜头内部的镜头细分；优先用机内运动承担景别变化，而不是硬切。\n"
        "8. 同段切换只能发生在选定一侧内部（例如全段右前方，可以从右前方半身→右前方过肩→右前方双人关系景）；跨到另一侧本段不得擅自跨。\n"
        "9. 只有在 单一主体 + 单一动作 + 没有说话者切换 + 没有受击反应 + 没有进门/进电梯/过阈值 时，才允许单一主机位持续承担整段。\n"
        "10. 每次硬切都必须由 cut_point 解释，例如台词断点、动作顶点、信息看清、反应出现、space_reset、tailframe_reset；禁止 cut_point 写 axis_flip / reverse_angle / 反打。\n"
        "11. 如果一个 fragment 里有多个 shots，禁止所有 shot 都重复同一套 camera + size 直到片段结束。\n"
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
            r'(?mi)^\s*(?:shot_size|size)\s*:\s*["\']?([^"\n#]+?)["\']?\s*$',
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
        rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)",
        text,
    )
    return match.group(1).strip() if match else ""

_MAIN_SHOT_BLOCK_RE = re.compile(
    r"(?ms)^\s*-\s*shot_id\s*:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$"
    r"([\s\S]*?)(?=^\s*-\s*shot_id\s*:|^\s*sub_shots\s*:|^\s*-\s*fragment_id\s*:|\Z)"
)

def _main_shot_blocks(output: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for match in _MAIN_SHOT_BLOCK_RE.finditer(output or ""):
        blocks.append((match.group(1).strip(), match.group(0)))
    return blocks

def _fragment_line_pattern() -> str:
    return r"^-?\s*fragment_id\s*:\s*[\"']?F[\w-]+[\"']?"

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

def _field_value(section: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:\s*[\"']?(.+?)[\"']?\s*$", section)
    return match.group(1).strip() if match else ""

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

def _validate_shot_director_output(director_output: str, expected_segments: list[str]) -> list[str]:
    """Validate the active shot construction-sheet schema.

    Current runtime output is intentionally lightweight, but it must be
    executable by prompt_compiler: fragment_task/rhythm at fragment level and
    duration/task/must_carry/cut_point/continuity at shot level. Legacy
    main_shots are still tolerated for older saved states and guard fixtures.
    """
    issues: list[str] = []
    for segment_name in expected_segments:
        segment_num = re.sub(r"\D", "", segment_name)
        fragment_id = f"F{int(segment_num):02d}" if segment_num else segment_name
        block_match = re.search(
            rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
            rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)",
            director_output,
        )
        if not block_match:
            issues.append(f"shot_director 缺少 {fragment_id} 的镜头设计。")
            continue
        block = block_match.group(1)

        # Legacy saved states/tests may still use main_shots. Keep that path
        # readable, but enforce the new construction-sheet contract for shots.
        if re.search(r"(?m)^\s*main_shots\s*:", block) and not re.search(r"(?m)^\s*shots\s*:", block):
            for field in ["shot_id", "subject"]:
                if not re.search(rf"^\s*-?\s*{field}\s*:", block, re.MULTILINE):
                    issues.append(f"{fragment_id} 的 main_shots 缺少字段 {field}。")
            continue

        for field in _SHOT_CONSTRUCTION_FRAGMENT_FIELDS:
            if not re.search(rf"(?m)^\s*{field}\s*:", block):
                issues.append(f"{fragment_id} 缺少 {field} 字段。")

        shot_blocks = _main_shot_blocks(block)
        if not shot_blocks:
            issues.append(f"{fragment_id} 缺少 shots 字段或没有任何 shot_id。")
            continue

        for shot_id, shot_block in shot_blocks:
            for field in _SHOT_CONSTRUCTION_REQUIRED_FIELDS:
                if not re.search(rf"(?m)^\s*-?\s*{field}\s*:", shot_block):
                    issues.append(f"{shot_id} 缺少字段 {field}。")

            duration = _yaml_line_field(shot_block, "duration")
            if duration and not _SHOT_DURATION_RE.search(duration):
                issues.append(f"{shot_id} 的 duration 必须写成 '0-2秒' 或 '2秒' 这种秒数格式。")

            cut_point = _yaml_line_field(shot_block, "cut_point")
            if cut_point:
                if re.fullmatch(r"[\"']?(?:切出|切到下个镜头|下个镜头)[\"']?", cut_point.strip()):
                    issues.append(f"{shot_id} 的 cut_point 过于空泛，必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。")
                elif not _SHOT_CUT_TRIGGER_RE.search(cut_point):
                    issues.append(f"{shot_id} 的 cut_point 缺少可执行切镜触发点。")

    return issues

def _yaml_scalar_field(block: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(field)}\s*:\s*[\"']?([^\"'\n#]+)", block or "")
    return match.group(1).strip() if match else ""

def _yaml_line_field(block: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(field)}\s*:\s*(.+?)\s*$", block or "")
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
            "contact_points": "none unless explicitly stated by the source action",
            "weight_shift": "minimal; characters hold existing office positions",
            "movement_path": "start position -> visible action path -> stop at established desk/standing position",
            "body_facing": "preserve established eyeline and desk axis",
            "feasibility": "valid; movement remains readable in the selected shot",
            "camera_requirement": "keep medium/medium-close framing wide enough to read the action path",
            "continuity_risk": "preserve final body position and desk-side relationship for the next shot",
        }
        if not re.search(r"(?m)^\s*body_mechanics_check\s*:", block):
            body_lines = ["body_mechanics_check:"] + [
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
        f"【画幅】{aspect_ratio}\n\"        \"【防幻觉规则】\n"
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
        dramatic_unit = _field_value(section, "dramatic_unit")
        active_cast = _extract_nested_list_items(section, "cast", "active")
        must_not_show = _extract_nested_list_items(section, "cast", "must_not_show")
        continuity_entry = _extract_nested_mapping_value(section, "continuity", "entry")
        continuity_exit = _extract_nested_mapping_value(section, "continuity", "exit")
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

def _extract_rhythm_shot_director_notes(atmosphere_strategy: str) -> str:
    """Extract rhythm supervisor notes that are explicitly addressed to shot_director."""
    text = (atmosphere_strategy or "").strip()
    if not text:
        return ""

    label_pattern = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?shot_director_notes\s*[：:]\s*(.*)$")
    match = label_pattern.search(text)
    if not match:
        return ""

    stop_pattern = re.compile(
        r"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?"
        r"(?:rhythm_diagnosis|construction_notes|shot_director_notes|atmosphere_strategy|rewritten_script|改写后剧本)"
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
        "[Rhythm Supervisor Shot Notes]\n"
        "These are upstream shot-construction instructions for reaction ownership, pauses, "
        "cut landing points, and tailframe handoff. Obey them unless they conflict with "
        "source_script_events, original dialogue, prop continuity, or spatial axis safety.\n"
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
) -> tuple[str, dict[str, Any]]:
    planner_sections = _sections_by_fragment(planner_output)
    contract_sections = _sections_by_fragment(contract_output)
    started_at = time.time()
    outputs: list[str] = []
    fragment_runtimes: list[dict[str, Any]] = []
    for segment_name in expected_segments:
        fragment_id = _segment_name_to_fragment_id(segment_name)
        fragment_context = _fragment_compact_context(planner_sections, fragment_id, aspect_ratio)
        fragment_contract = contract_sections.get(fragment_id, "")
        if not fragment_contract:
            # Fall back to the full contract instead of silently dropping a fragment.
            fragment_contract = contract_output
        fragment_started_at = time.time()
        fragment_output = call_llm(
            system_prompt=system_prompt,
            user_prompt=prompt_builder(fragment_id, fragment_context, fragment_contract),
            agent_name=stage_key,
            images_base64=None,
        )
        cleaned = _clean_shot_director_output(fragment_output)
        outputs.append(cleaned)
        fragment_runtimes.append(
            {
                "fragment_id": fragment_id,
                "elapsed_seconds": round(time.time() - fragment_started_at, 3),
                "output_chars": len(cleaned),
            }
        )
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

def _run_shot_director_single_pass_impl(
    *,
    script: str,
    planner_output: str,
    atmosphere_strategy: str,
    aspect_ratio: str,
    expected_segments: list[str],
    images_base64: list[str] | None,
    director_hint: str,
    director_brief: str = "",
    stage_callback: Callable[[str, str, dict[str, Any], dict[str, dict[str, Any]]], None] | None = None,
    resume_stage_outputs: dict[str, str] | None = None,
    resume_stage_runtime: dict[str, dict[str, Any]] | None = None,
    resume_stage_meta: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Simplified single-pass shot director with lean YAML output schema."""
    director_brief_block = _director_brief_prompt_block(director_brief)
    downstream_context = _shot_director_downstream_context(planner_output, atmosphere_strategy, aspect_ratio)
    if director_brief_block:
        downstream_context = director_brief_block + "\n" + downstream_context
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
        system_prompt, final_meta = build_system_prompt(
            "你是一位镜头导演。你的职责是为每个片段设计时间轴上的镜头序列。\n\n"
            "【每个片段必须交付】\n"
            "1. fragment_task — 本片段的剧情施工任务，例如建立关系、冲突升级、信息揭示、反应落点、权力反转、喜剧泄压、尾帧钩子。\n"
            "2. rhythm — 服从 rhythm supervisor/story_planner 的节奏指令，例如压缩、放慢、停顿、卡断、短促泄压。\n\n"
            "【每个镜头必须回答】\n"
            "1. duration — 该镜头在片段内的时间段，必须连续，例如 0-2秒、2-5秒。\n"
            "2. task — 这个镜头负责什么：建立关系、承载对白、动作推进、信息揭示、反应落点、尾帧承接等。\n"
            "3. subject — 拍谁（人物名、双人关系或剧本已有道具）。\n"
            "4. camera — 从哪拍（机位、角度、运镜，必须可执行）。\n"
            "5. size — 多大景（全景/中景/半身/中近景/特写等）。\n"
            "6. action — 在干嘛（可见动作，不写心理）。\n"
            "7. dialogue — 原剧本台词、OS、画外音或 ~；不得新增台词。\n"
            "8. must_carry — 这个镜头必须承载的剧情信息或表演落点。\n"
            "9. cut_point — 具体切镜触发点，必须绑定动作顶点、台词断点、信息看清、反应出现、状态完成或尾帧。\n"
            "10. continuity — 动作、道具、人物左右关系、轴线或尾帧状态如何继承。\n\n"
            "【可选字段】\n"
            "- type — 只在非标准镜头时写：reaction（受击反应）、insert（道具/信息特写）、cutaway（切离镜头）。\n"
            "- audio — 只在需要 OS / J-cut / L-cut / 画外音时写。\n\n"
            "【镜头设计原则】\n"
            "1. 事实红线高于一切：不新增剧本外的人物、台词、动作、道具或情节。\n"
            "2. 节奏施工指令是创作节奏主控；镜头导演只负责把它合法施工成主体、景别、机位、时长和切点。\n"
            "3. 长台词或高压命令必须拆出视觉覆盖：说话者起句、同侧听者反应/过肩、必要时后半句以 OS/J-cut/L-cut 落到反应上。\n"
            "4. 时长按戏剧任务分配，不平均切：建立关系 1-2秒，信息插入 0.5-1.5秒，对白/动作推进 2-4秒，反应/停顿 1-2秒，尾帧钩子 0.5-2秒。\n"
            "5. cut_point 不许只写“切出”，必须写清触发物，例如“动作顶点前→镜头2”“台词断点切至乔熙反应”“文件内容看清后切出”。\n"
            "6. fragment_id 必须沿用拆片方案的 F01/F02/F03...，不得改名合并跳号。\n"
            f"7. 画幅：{aspect_ratio}",
            "shot_director",
            context_hint=hint,
        )
        stage_meta["final"] = final_meta
        if director_brief_block:
            system_prompt = system_prompt + "\n\n" + director_brief_block
        user_prompt = (
            "基于以下素材，为每个片段设计镜头序列，输出 YAML 格式。\n\n"
            f"{workflow_contract}\n"
            f"{downstream_context}\n\n"
            "【输出 YAML 结构】\n"
            "- fragment_id: (F01, F02, ...)\n"
            "  fragment_task: (本片段剧情施工任务)\n"
            "  rhythm: (压缩/放慢/停顿/卡断/短促泄压等)\n"
            "  shots:\n"
            "    - shot_id: (F01-S01, F01-S02, ...)\n"
            "      duration: (0-2秒, 2-5秒... 必须连续)\n"
            "      task: (建立关系/承载对白/动作推进/信息揭示/反应落点/尾帧承接)\n"
            "      subject: (人物名或道具)\n"
            "      camera: (机位、角度、运镜)\n"
            "      size: (全景/中景/半身/中近景/特写等)\n"
            "      action: (可见动作描述)\n"
            "      dialogue: (原剧本台词 或 ~)\n"
            "      must_carry: (本镜头必须承载的剧情信息/动作/反应)\n"
            "      cut_point: (动作顶点/台词断点/信息看清/反应出现/尾帧完成等具体触发)\n"
            "      continuity: (动作、道具、站位、轴线、尾帧如何继承)\n"
            "      type: (可选：reaction / insert / cutaway)\n\n"
            "【关键要求】\n"
            "1. 必须覆盖拆片方案的所有 fragment_id。\n"
            "2. 必须服从节奏总控施工指令，把快慢、停顿、卡断、反应归属落实到 duration/task/must_carry/cut_point。\n"
            "3. 长台词或高压命令必须插入听者反应镜头，不能站桩正反打。\n"
            "4. 保持 fragment_id 和 shot_id 稳定，遵循 F01/F02... 和 F01-S01/F01-S02... 格式。\n"
            "5. dialogue 字段可写 ~，仅用原剧本文字或原剧本 OS。\n"
            "6. 只有剧本已有信息载体才能写 insert；不要新增空镜、道具或环境信息。\n\n"
            f"{_shot_director_coverage_contract_prompt()}\n"
            f"{rule_block}"
            "请输出完整 YAML 镜头方案。"
        )
        # Simple check for whether to split by fragment
        if _shot_stage_should_split(expected_segments, downstream_context):
            stage_meta["final"]["split_by_fragment"] = True

            def build_fragment_prompt(fragment_id: str, fragment_context: str, _fragment_contract: str) -> str:
                return (
                    f"[Task]\nDesign shot sequence for {fragment_id} only.\n\n"
                    f"{fragment_context}\n\n"
                    "[Workflow]\n"
                    f"{workflow_contract}\n"
                    f"{_shot_director_coverage_contract_prompt()}\n"
                    f"{rhythm_shot_notes_prompt}"
                    "[Output YAML fields]\n"
                    "- fragment_task\n"
                    "- rhythm\n"
                    "- shot_id\n"
                    "- duration\n"
                    "- task\n"
                    "- subject\n"
                    "- camera\n"
                    "- size\n"
                    "- action\n"
                    "- dialogue\n"
                    "- must_carry\n"
                    "- cut_point\n"
                    "- continuity\n"
                    "- coverage_role\n"
                    "- cut_reason\n"
                    "- companion_visibility\n"
                    "- state_delta\n"
                    "- tailframe_role\n"
                    "- type (optional: reaction/insert/cutaway)\n"
                    "- audio (optional: OS/J-cut/L-cut)\n\n"
                    "[Rules]\n"
                    "1. Output YAML for this fragment only, starting with '- fragment_id:'.\n"
                    "2. Keep shot_id stable, e.g. F01-S01, F01-S02.\n"
                    "3. Duration must be continuous inside the fragment, e.g. 0-2秒, 2-5秒.\n"
                    "4. Long dialogue needs listener reaction shots and concrete cut_point triggers.\n"
                    "5. No script-external elements.\n"
                    "Output YAML only."
                )

            final_output, final_runtime = _call_stage_split_by_fragment(
                stage_key="shot_director",
                system_prompt=system_prompt,
                expected_segments=expected_segments,
                planner_output=planner_output,
                aspect_ratio=aspect_ratio,
                contract_output="",
                prompt_builder=build_fragment_prompt,
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

    # Validate output
    final_issues = _validate_shot_director_output(final_output, expected_segments)
    if final_issues and not existing_final:
        repair_prompt = (
            "shot_director 输出没有通过校验。请只修正 YAML，不要解释。\n\n"
            "【必须修复的问题】\n"
            + "\n".join(f"- {issue}" for issue in final_issues)
            + "\n\n【关键原则】\n"
            "1. 必须覆盖所有 fragment_id。\n"
            "2. 每个 fragment 必须有 fragment_task、rhythm、shots。\n"
            "3. 每个 shot 必须有 shot_id、duration、task、subject、camera、size、action、dialogue、must_carry、cut_point、continuity。\n"
            "4. duration 必须连续，cut_point 必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。\n"
            "5. 长台词必须插入听者反应镜头；不新增剧本外元素。\n\n"
            "【待修正 YAML】\n"
            f"{final_output}\n\n"
            f"{rule_block}"
            "请输出修正后的完整 YAML。"
        )
        repaired_final, repair_runtime = _call_shot_director_stage(
            stage_key="shot_director",
            system_prompt=system_prompt,
            user_prompt=repair_prompt,
            images_base64=None,
        )
        raw_repaired_final = repaired_final
        repaired_final = _repair_shot_director_output_contracts(repaired_final, script)
        repaired_issues = _validate_shot_director_output(repaired_final, expected_segments)
        final_runtime["repair_attempted"] = True
        final_runtime["repair_runtime"] = repair_runtime
        final_runtime["repair_auto_repair_applied"] = repaired_final != raw_repaired_final
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
    # For single-pass schema, check for "final" output instead of layout/blocking/guard
    resume_stage_outputs = {
        "final": outputs.get("shot_director", "")
    } if outputs.get("shot_director") else {}
    shot_meta = (state.get("knowledge_metadata") or {}).get("shot_director", {})
    resume_stage_runtime = shot_meta.get("runtime", {}) if isinstance(shot_meta, dict) else {}
    resume_stage_meta = shot_meta.get("stage_retrieval", {}) if isinstance(shot_meta, dict) else {}
    director_hint = f"镜头导演 焦段景深 景别画幅 连续性 情绪锚点 仰拍限制 切镜 受击者 炸点 对白 信息冲击 动作接续 人物关系 场面总控 节奏 子分镜 戏剧微粒 权力反转 悬念揭示 误解错位 9:16 半身中景 特写限频 微细节镜头 {state['script'][:200]}"
    if director_brief_text:
        director_hint = f"{director_hint} director_showrunner {director_brief_text[:300]}"
    shot_runtime_started = time.perf_counter()
    reference_images = _reference_images(state) or None
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

        stage_messages = {
            "final": "镜头导演输出已完成，准备生成第 1 段 Prompt。",
        }
        _persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_3_direct",
                "message": stage_messages.get(stage_name, "镜头导演正在生成全局镜头方案...（4/6）"),
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
                "total_segments": total_segments,
                "segment_names": segment_names,
                "current_segment_index": 1,
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
        final_repair_prompt = (
            "shot_director 最终 YAML 没有通过主校验。请只修正 YAML，不要解释。\n\n"
            "【必须修复的硬错误】\n"
            + "\n".join(f"- {issue}" for issue in primary_hard_issues)
            + "\n\n【修复原则】\n"
            "1. 每个 fragment_id 都必须在输出中。\n"
            "2. 每个 fragment 必须有：fragment_task、rhythm、shots。\n"
            "3. 每个 shot 必须有：shot_id、duration、task、subject、camera、size、action、dialogue、must_carry、cut_point、continuity。\n"
            "4. duration 必须连续；cut_point 必须绑定动作顶点、台词断点、信息看清、反应出现或尾帧状态。\n"
            "5. 长台词必须插入听者反应镜头；只能使用剧本里的人物和台词，不新增剧本外内容。\n\n"
            "【原始剧本】\n"
            f"{state.get('script', '')}\n\n"
            "【拆片方案】\n"
            f"{planner_output}\n\n"
            "【待修正 YAML】\n"
            f"{primary_output}\n\n"
            "请输出修正后的完整 YAML。"
        )
        repaired_primary = call_llm(
            "你是 shot_director 最终返修导演。只输出修正后的 YAML。",
            final_repair_prompt,
            agent_name="shot_director",
            images_base64=None,
        )
        repaired_primary = _clean_shot_director_output(repaired_primary)
        repaired_primary = _repair_shot_director_output_contracts(repaired_primary, state.get("script", ""))
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
        },
    )






