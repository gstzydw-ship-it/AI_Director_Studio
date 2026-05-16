"""Prompt compiler implementation extracted from legacy_impl.

Owns prompt compilation guard helpers and the package runtime prompt_compiler node.
"""
from __future__ import annotations

import re
from typing import Any

from .types import DirectorState
from . import legacy_impl as _legacy

# Runtime schema contract: shot_director outputs shot_director_coverage_v3 with
# coverage_plan, template_plan.shots, guard_result, and per-shot fields consumed
# by the final Seedance prompt compiler.
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
    _has_yaml_field,
    _dialogue_payload_is_long,
    _MAIN_SHOT_BLOCK_RE,
    _DIALOGUE_COVERAGE_TERMS_RE,
    _fragment_id_for_segment_index,
    _segment_block_by_fragment_id,
    _primary_script_character_names,
)
from .llm import call_llm
from .prompting import build_system_prompt
from .seedance_contracts import (
    NO_TEXT_HARD_CONSTRAINT,
    abstract_viewpoint_terms,
    extract_seedance_contract_flags,
    format_seedance_contract_block,
    prompt_contract_issues,
    seedance_qc_issues,
)
from .state_store import _agent_outputs, _persist_update

_LOCAL_FALLBACK_INPUT_MARKERS = (
    "本地兜底编译",
    "本地兜底",
    "镜头导演本地兜底",
    "shot_director_local_fallback_v1",
    "local fallback",
    "deterministic fallback",
)

JIMENG_PROMPT_CHAR_LIMIT = 2000
_JIMENG_PROMPT_SAFE_LIMIT = 1950
_PROMPT_HANDOFF_TAIL_RE = re.compile(
    r"\n*\s*片段\s*\d+\s*prompt\s*已输出[\s\S]*$",
    re.IGNORECASE,
)


def _contains_local_fallback_input(value: Any) -> bool:
    text = str(value or "")
    lowered = text.lower()
    return any(marker in text or marker in lowered for marker in _LOCAL_FALLBACK_INPUT_MARKERS)


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
_SUBJECT_RELATIVE_LEFT_RIGHT_CAMERA_RE = re.compile(
    r"(?:摄影机|机位|镜头)?(?:位于|在)?"
    r"(?:商北琛|乔熙|严飞|苏小可|小豆丁|人物|主体|他|她|两人).{0,8}"
    r"(?:左前方|右前方|左后方|右后方)"
)
_SAFE_CAMERA_POSITION_RE = re.compile(
    r"(?:"
    r"(?:摄影机|机位|镜头).{0,40}"
    r"(?:同侧正面微侧|同侧过肩|同侧固定|办公桌侧面|门口侧面|正面|正前方|侧面|侧背|背后|过肩|桌边侧|门框侧|走廊侧|电梯侧|固定机位|平稳跟拍|背后跟拍|肩后)"
    r"|(?:同侧正面微侧机位|同侧过肩机位|同侧固定机位|办公桌侧面固定机位|门口侧面固定机位|正面固定机位|侧面固定机位|背后跟拍|平稳跟拍)"
    r")"
)
_SILENT_CUT_TRIGGER_RE = _legacy._SILENT_CUT_TRIGGER_RE
_NEW_SUBJECT_FRAMING_RE = _legacy._NEW_SUBJECT_FRAMING_RE
_SHOT_DENSITY_LIFE_PRESSURE_RE = re.compile(
    r"生活|赶时间|穿衣|上学|孩子|小豆丁|闹钟|电话|手机|草莓|安抚|哄|抗拒|乱蹬|缩手|踢开|书包|紧凑生活",
    re.IGNORECASE,
)
_SHOT_DENSITY_HIGH_CUT_RE = re.compile(
    r"追逐|打斗|抢夺|闯入|冲进|救援|爆炸|车祸|急救|信息揭示|照片|文件|真相|证据|屏幕|监控|"
    r"亲子鉴定|高压对白|长对白|权力压迫|外部打断|宴会|群体|反转",
    re.IGNORECASE,
)


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
_UNSTABLE_FRAME_COMPOSITION_RE = re.compile(
    r"(?:"
    r"站在(?:门框|窗框|框架)里|"
    r"(?:门框|窗框).{0,8}(?:形成|构成).{0,8}(?:前景|压线|框景)|"
    r"前景压线|框住人物|被(?:门框|窗框|框架)框住|框景压迫"
    r")"
)
_PSEUDO_RELATION_VIEWPOINT_RE = re.compile(
    r"("
    r"[\u4e00-\u9fff]{1,8}(?:与|和|及)[\u4e00-\u9fff]{1,8}之间的关系视角|"
    r"(?:沙发|地毯|茶几|书包|门口|桌边|窗边|客厅|卧室|办公室|空间|场景|前景|后景|人物|双人|同场).{0,10}"
    r"(?:关系|复位|承接).{0,6}(?:视角|观看位置|机位)|"
    r"(?:空间关系|前后景关系|关系复位|尾帧承接|覆盖职责|动作主链|状态单向推进).{0,6}(?:视角|观看位置|机位)"
    r")"
)
_SHOT_ACTION_OVERLOAD_RE = re.compile(
    r"(?:放下|放到|拿起|抓起|拎起|拉|扯|按住|按下|看向|瞥向|说出|急声|移开|松开|伸向|接触|缩回|扭开|后退|扒|整理|扣好|起身|停住)"
)
_SHOT_PROP_OR_BODY_RE = re.compile(
    r"(?:手机|闹钟|书包|衣服|衣摆|衣袖|手臂|手指|肩膀|脚|茶几|沙发|地毯|坐垫)"
)
_NATURAL_VIEWPOINT_RE = re.compile(
    r"(?:正面|侧面|背后|肩后|客厅一侧|客厅侧面|沙发旁|地毯旁|茶几旁|门口|桌边|走廊侧面|电梯口)"
    r".{0,8}(?:平视|视角|固定视角|观察视角|中景|半身景|关系景|双人中景|看向)"
)


def _reaction_cut_and_action_path_rules() -> str:
    return (
        "【反应切镜与自然动作句硬规则】\n"
        "1. 时间轴内可以也必须写清镜头切换。凡出现受击、回神、视线相撞、表情一僵、听完反应、松手等反应落点，必须明确写\"镜头切至/切回\"谁；单段内禁止写反打。\n"
        "2. 反应镜头写成自然画面句：镜头切至乔熙中近景，商北琛肩线留在前景，乔熙听完后抬眼停住。\n"
        "3. 如果同一时间段内有\"说话 -> 听者受击 -> 继续说话 -> 回神动作\"，至少拆成说话镜头和听者反应镜头；不要全塞在同一个双人中景里。\n"
        "4. 动作描述遵循 Seedance 自然语言：主体 + 一个主要动作 + 情绪/视线落点。只写观众能看懂的大动作，不把每根手指、厘米距离、起点路径终点写成说明书。\n"
        "5. 只有接触、碰撞、抢夺、摔倒、危险身体动作或关键道具移动，才补一句简短的安全状态，例如\"扶住她的腰侧，动作停住\"或\"手松开后落回身侧\"。\n"
        "6. 禁止写\"手弹开\"\"从西装前襟弹开\"\"飞开\"\"甩开\"\"弹向空中\"\"猛地弹开\"\"身体弹开\"\"突然闪开\"。这些词会让视频模型生成肢体乱甩或空间跳变。\n"
        "7. 正确示例：乔熙松开商北琛的西装前襟，双手收回身侧，眼神短暂停住。\n"
        "8. 反应镜头只保留必要画面锚点：谁在前景、谁是主体、关键道具是否仍可见；不要展开空间坐标说明。\n"
        "9. 每个非末尾镜头行必须写清切镜时机，格式优先用括号：\"（切镜时机：台词压力词落下后切至镜头2）\"、\"（切镜时机：照片内容看清后切至镜头3）\"。末尾镜头写\"尾帧：...\"，不写空泛的\"自然切\"。\n"
        "10. 切镜时机必须绑定信息增量：动作顶点、台词压力词、听者受击、信息看清、外部打断、尾帧完成；不要写成\"更有节奏\"\"更有电影感\"。\n"
        "11. 明确切镜不等于频繁碎切。13秒以内片段通常控制在2-3个有效镜头；只有上游明确给出关键 sub_shot 时才允许更多。\n"
        "12. 单个2秒以内时间段禁止同时承载\"局部插入镜头 + 切回人物中近景 + 一整句长台词\"。长台词至少给3秒左右，手部/道具插入镜头应放在台词前后，或并入双人中景完成。\n"
        "13. 反应切镜要服务信息增量：说话者镜头、同侧听者反应、动作复位可以各自成镜；不要为了每个微动作单独切镜。\n"
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
        "7. \"凝滞/粘滞/暧昧感/张力\"必须改成身体距离、视线时长、动作速度和表情落点：两人相距半步、对视1秒、手停在身体一侧不移动、人物嘴唇停住。\n"
        "8. \"气口/留白/回味/泄压\"必须改成时间和画面状态：停0.5-1秒、无人说话、人物停在原位、镜头保持固定、呼吸放慢。\n"
        "9. 正确示例：\"镜头切至人物B和几名旁观者胸部以上中近景；人物B微微低头，旁观者肩膀收紧、屏住呼吸、避开人物A视线。\"\n"
        "10. 错误示例：\"稳定器在同一运动里带到人物B和旁观者胸部以上受压反应。\" 这类句子像导演现场口令，不能作为最终 Seedance prompt。\n"
        "11. 上游若写\"纵深中全景到半身中景\"\"中景转关系景\"\"同轴线偏右\"\"眼平高度\"\"truck right/left\"，最终必须降级为一个简单镜头基底：\"空间全景\"、\"人物A半身中景\"、\"关键空间锚点固定中景\"、\"正面平稳跟拍\"。\n"
        "12. 禁止把\"动作主链\"\"状态单向推进\"\"关系建立\"\"尾帧承接\"\"抗拒位置\"这类内部判断写进最终 prompt；它们必须翻译成观众能看见的手、道具、身体距离和站位。\n"
        "13. 复杂生活动作先压成自然可拍动作句：主体 + 一个主要动作 + 必要情绪/视线落点 + 尾帧状态；不要逐项写起点、路径、厘米距离、手指开合或身体部位说明。\n"
        "14. 并行动作必须做取舍：同一镜头只保留影响剧情或连续性的主动作；另一个并行动作只在必要时写成简短结果状态，避免模型同时执行过多肢体任务。\n"
        "15. 状态连续不能写成抽象约束替代画面。应写\"文件仍在人物A手里\"\"门保持半开\"\"人物B退开半步停住\"，不要只写\"状态单向推进\"。\n"
        "16. 抗拒、躲避、挣脱写成低歧义大动作：人物B后退半步、避开视线、停在门口；只有接触、抢夺、摔倒或危险动作才补简短接触状态。\n"
        "17. 每个短镜头最多承载1-2个可见动作；如果一句里同时有道具移动、台词、接触、挣脱、位移、尾帧锁定，必须拆成相邻镜头或局部插入镜。\n"
        "18. 分类翻译表必须通用化，使用人物A/人物B/道具X/空间锚点/位置A/位置B等槽位，不能把当前剧本专名写进规则模板。\n"
        "    - 建立/复位类 -> 人物A和人物B同框，距离、朝向、视线方向、空间锚点清楚可见。\n"
        "    - 轴线/视线类 -> 保持人物A在画面同侧，人物B看向同一方向；切镜时保留肩线或视线目标。\n"
        "    - blocking调度类 -> 人物从位置A走到位置B，停在空间锚点旁，身体朝向人物B或道具X。\n"
        "    - 动作路径类 -> 压成一个主动作和结果状态，不展开起点/路径/终点；例：人物A把文件放到桌上后停住。\n"
        "    - 接触/碰撞类 -> 只写必要接触部位和结果状态；例：人物A扶住人物B腰侧，两人停住。\n"
        "    - 道具连续类 -> 道具X归属和结束位置清楚即可；例：文件仍在人物A手里，道具Y停在桌边。\n"
        "    - 情绪反应类 -> 抽象情绪改成肩颈、下颌、呼吸、视线、手部停顿、身体后缩等表演。\n"
        "    - 对白覆盖类 -> 说话者起句、听者反应、画外音延续、切回关系景，不能单镜吃完整压迫对白。\n"
        "    - 插入镜/切点类 -> 信息看清、动作顶点、视线撞上、手刚碰到道具时切镜。\n"
        "    - 运镜降级类 -> pan/tilt/truck/dolly/follow/rack focus 只保留一种，并绑定主体和方向。\n"
        "    - 尾帧类 -> 最后0.5-1秒保持可继承姿势：人物位置、视线、道具、门/车/衣物等状态不变。\n"
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


def _prompt_base_section(prompt: str) -> str:
    return _prompt_section(prompt, "画面基底") or _prompt_section(prompt, "空间与首帧总控")


def _prompt_title_line(prompt: str) -> str:
    for line in (prompt or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _compact_prompt_text(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate_at_sentence(text: str, limit: int) -> str:
    text = _compact_prompt_text(text)
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[: max(0, limit)]
    candidate = text[: limit - 1].rstrip()
    sentence_end = max(candidate.rfind("。"), candidate.rfind("；"), candidate.rfind("\n"))
    if sentence_end >= max(20, int(limit * 0.55)):
        candidate = candidate[: sentence_end + 1].rstrip()
    return candidate.rstrip("，、；：。") + "…"


def _fit_lines_to_budget(lines: list[str], budget: int) -> list[str]:
    kept: list[str] = []
    used = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        cost = len(stripped) + (1 if kept else 0)
        if used + cost <= budget:
            kept.append(stripped)
            used += cost
            continue
        remaining = budget - used - (1 if kept else 0)
        if remaining > 24:
            kept.append(_truncate_at_sentence(stripped, remaining))
        break
    return kept


def _limit_seedance_prompt_for_jimeng(prompt: str) -> str:
    """Return the submit-ready prompt body within Jimeng's 2000 character limit."""
    text = _compact_prompt_text(_PROMPT_HANDOFF_TAIL_RE.sub("", prompt or ""))
    if len(text) <= _JIMENG_PROMPT_SAFE_LIMIT:
        return text

    title = _prompt_title_line(text)
    style = _prompt_section(text, "风格锚点")
    ratio = _prompt_section(text, "画幅锚点")
    space = _prompt_base_section(text)
    shots = _prompt_section(text, "镜头序列") or _prompt_section(text, "时间轴")
    constraints = _prompt_section(text, "约束")
    reference_call = _prompt_section(text, "参考调用")

    fixed_constraint = (
        "严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌；"
        "人物、空间、道具、轴线和尾帧状态必须连续。"
    )
    if "员工" in text or "群演" in text:
        fixed_constraint += " 员工/群演不得与命名人物同脸、相似或重复。"
    if "电梯" in text:
        fixed_constraint += " 电梯门后只允许封闭金属轿厢、侧壁/后壁/控制面板。"
    if constraints and "参考图" in constraints:
        fixed_constraint += " 参考图只隐性约束身份、空间和道具，不输出编号。"

    parts: list[str] = []
    if title:
        parts.append(_truncate_at_sentence(title, 90))
    if style:
        parts.append("【风格锚点】\n" + _truncate_at_sentence(style, 70))
    if ratio:
        parts.append("【画幅锚点】\n" + _truncate_at_sentence(ratio, 35))
    if space:
        parts.append("【空间与首帧总控】\n" + _truncate_at_sentence(space, 220))

    prefix = "\n\n".join(parts)
    suffix = "【约束】\n" + fixed_constraint
    shot_budget = _JIMENG_PROMPT_SAFE_LIMIT - len(prefix) - len(suffix) - 8
    if shots and shot_budget > 120:
        shot_lines = _fit_lines_to_budget(shots.splitlines(), shot_budget - len("【时间轴】\n"))
        parts.append("【时间轴】\n" + "\n".join(shot_lines))
    parts.append(suffix)
    if reference_call:
        parts.append("【参考调用】\n" + "\n".join(_fit_lines_to_budget(reference_call.splitlines(), 220)))

    fitted = _compact_prompt_text("\n\n".join(part for part in parts if part.strip()))
    if len(fitted) <= _JIMENG_PROMPT_SAFE_LIMIT:
        return fitted
    return _truncate_at_sentence(fitted, _JIMENG_PROMPT_SAFE_LIMIT)


def _prompt_execution_text(prompt: str) -> str:
    sections = [
        _prompt_section(prompt, "镜头序列"),
        _prompt_section(prompt, "时间轴"),
    ]
    text = "\n".join(section for section in sections if section)
    return text or (prompt or "")


def _prompt_uses_shot_sequence(prompt: str) -> bool:
    return bool(
        re.search(r"【画面基底】[\s\S]*【镜头序列】[\s\S]*【约束】", prompt or "")
        and re.search(r"(?m)^镜头\s*\d+\s*【", prompt or "")
    )


def _meaningful_sentence_count(text: str) -> int:
    pieces = re.split(r"[。！？\n]+", text or "")
    return len([piece for piece in pieces if piece.strip()])


def _quoted_dialogues(text: str) -> list[str]:
    return [item.strip() for item in re.findall(r"[\"\u201c\u201d]([^\"\u201c\u201d]+)[\"\u201c\u201d]", text or "") if item.strip()]


_PROMPT_PRESSURE_DIALOGUE_RE = re.compile(
    r"命令|质问|逼问|羞辱|威胁|拒绝|不准|离婚|结婚|爸爸|孩子|老板|ex-husband|daddy|boss|"
    r"meeting|directors|above|be there|don't|can't|won't|why|what|never|secretary|afford|mistake",
    re.IGNORECASE,
)


def _dialogue_block_requires_visual_break(dialogues: list[str]) -> bool:
    if not dialogues:
        return False
    if len(dialogues) >= 2:
        return True
    text = dialogues[0].strip()
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_words = re.findall(r"[A-Za-z][A-Za-z']+", text)
    ascii_chars = sum(len(word) for word in english_words)
    is_long = cjk_chars >= 24 or len(english_words) >= 12 or ascii_chars >= 58 or len(text) >= 70
    is_pressure = bool(_PROMPT_PRESSURE_DIALOGUE_RE.search(text))
    return is_long or (is_pressure and (cjk_chars >= 14 or len(english_words) >= 8 or ascii_chars >= 42))


_PROMPT_VISIBLE_ACTION_RE = re.compile(
    r"伸手|按停|放回|拿起|提起|递出|推开|拉住|缩回|后退|退开|避开|躲开|蹲近|伸脚|停在|停住|"
    r"转向|转身|看向|望向|抬头|低头|站稳|小跑|拉开|迈出|走进|走向|坐上|靠近|抱住|握紧|"
    r"捡起|塞回|托住|晃动|回神|僵住|出镜|入画|留在|说出"
)


def _has_prompt_performance_beat(body: str) -> bool:
    return bool(_PERFORMANCE_BEAT_RE.search(body or "") or _PROMPT_VISIBLE_ACTION_RE.search(body or ""))


def _prompt_performance_count(body: str) -> int:
    text = body or ""
    return len(_PERFORMANCE_BEAT_RE.findall(text)) + len(_PROMPT_VISIBLE_ACTION_RE.findall(text))


_PROMPT_SPATIAL_ANCHOR_RE = re.compile(
    r"沙发|茶几|书包|衣服|手机|闹钟|草莓蛋糕|客厅|公寓|床|桌|车|车门|酒店|餐厅|码头|游艇|"
    r"办公室|门口|门边|电梯|大堂|走廊|房门|前台|台阶"
)


def _has_prompt_spatial_anchor(body: str) -> bool:
    return bool(_SPATIAL_ANCHOR_RE.search(body or "") or _PROMPT_SPATIAL_ANCHOR_RE.search(body or ""))


def _has_internal_dialogue_visual_coverage(body: str) -> bool:
    quote_matches = list(re.finditer(r"[\"\u201c\u201d]([^\"\u201c\u201d]+)[\"\u201c\u201d]", body or ""))
    dialogues = [match.group(1).strip() for match in quote_matches if match.group(1).strip()]
    if not _dialogue_block_requires_visual_break(dialogues):
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
    return _limit_seedance_prompt_for_jimeng(text)


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

    shot_matches = list(
        re.finditer(
            r"(?m)^镜头\s*\d+\s*【\s*(?:(\d+(?:\.\d+)?)\s*[-~—]\s*)?(\d+(?:\.\d+)?)\s*秒\s*】",
            prompt or "",
        )
    )
    current = 0.0
    for index, match in enumerate(shot_matches):
        if match.group(1) is not None:
            start = float(match.group(1))
            end = float(match.group(2))
        else:
            duration = float(match.group(2))
            start = current
            end = current + duration
        body_start = match.end()
        body_end = shot_matches[index + 1].start() if index + 1 < len(shot_matches) else len(prompt)
        blocks.append((start, end, prompt[body_start:body_end].strip()))
        current = end
    return blocks


def _shot_density_limit(context: str, total_seconds: float | None) -> int:
    life_pressure = bool(_SHOT_DENSITY_LIFE_PRESSURE_RE.search(context or ""))
    high_cut_need = bool(_SHOT_DENSITY_HIGH_CUT_RE.search(context or ""))
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


def _prompt_shot_density_issues(
    prompt: str,
    planner_segment: str,
    director_segment: str,
    timeline_blocks: list[tuple[float, float, str]],
) -> list[str]:
    if not _prompt_uses_shot_sequence(prompt) or not timeline_blocks:
        return []
    total_seconds = max((end for _start, end, _body in timeline_blocks), default=0.0)
    total_seconds = total_seconds if total_seconds > 0 else None
    context = "\n".join([prompt or "", planner_segment or "", director_segment or ""])
    limit = _shot_density_limit(context, total_seconds)
    shot_count = len(timeline_blocks)
    issues: list[str] = []
    if shot_count > limit:
        issues.append(
            f"- 镜头切分过碎：{_format_seconds(total_seconds)}安排{shot_count}个镜头，"
            f"当前片段建议不超过{limit}个有效镜头；快节奏应靠人物动作紧张、停顿缩短和情绪压力，不靠碎切。"
        )

    short_blocks = [
        (index, end - start)
        for index, (start, end, _body) in enumerate(timeline_blocks, start=1)
        if 0 < end - start < 1.0
    ]
    life_pressure = bool(_SHOT_DENSITY_LIFE_PRESSURE_RE.search(context))
    high_cut_need = bool(_SHOT_DENSITY_HIGH_CUT_RE.search(context))
    if short_blocks and (len(short_blocks) >= 2 or (life_pressure and not high_cut_need)):
        short_text = "、".join(f"镜头{index}={seconds:.1f}秒" for index, seconds in short_blocks[:4])
        issues.append(
            f"- 1秒以下碎镜过多：{short_text}。生活动作/正常动作段不得把手、手机、脚、衣服等局部动作拆成碎插入；"
            "请合并进关系镜头，或只保留真正的信息揭示/危险命中短镜。"
        )
    return issues


def _seedance_contract_card(planner_segment: str, director_segment: str) -> str:
    text = "\n".join([planner_segment or "", director_segment or ""])
    flags = extract_seedance_contract_flags(text)
    if not any(
        flags.get(key)
        for key in ("template_id", "template_level", "reference_need", "tail_state", "model_complexity_score")
    ):
        return "未检测到 Seedance 2.0 合同字段；必须由上游补齐 template_id、template_level、reference_need、tail_state、model_complexity_score 后再编译。"
    return format_seedance_contract_block(
        template_id=flags.get("template_id"),
        template_level=flags.get("template_level"),
        reference_need=flags.get("reference_need"),
        tail_state=flags.get("tail_state"),
        complexity_score=flags.get("model_complexity_score"),
    )


def _seedance_contract_is_explicit(planner_segment: str, director_segment: str) -> bool:
    text = "\n".join([planner_segment or "", director_segment or ""])
    return bool(
        re.search(
            r"(?im)^\s*(?:template_id|coverage_template_id|template_level)\s*[:=]",
            text,
        )
    )


def _seedance_issue_to_compiler_message(issue: str) -> str:
    if "seedance_template_id_missing" in issue or "seedance_template_level_missing" in issue:
        return "- [SEEDANCE-CONTRACT-GATE-001] Seedance 合同字段不完整：缺少 template_id/template_level。prompt_compiler 必须先拿到 coverage 白名单边界再编译。"
    if "seedance_template_x_forbidden" in issue:
        return "- [SEEDANCE-COVERAGE-TEMPLATE-GATE-001] shot_director 选择了 X 禁用 coverage 模板，不能交给 prompt_compiler 生成。"
    if "seedance_template_candidate" in issue:
        return "- [SEEDANCE-COVERAGE-TEMPLATE-GATE-001] coverage 模板仍是 candidate/untested，必须先通过 Seedance 测试或降级到 W1/W2。"
    if "seedance_r1_reference_missing" in issue:
        return "- [SEEDANCE-COVERAGE-TEMPLATE-GATE-001] R1 参考驱动模板缺少视频参考/关键帧/动作参考绑定，必须拆分或降级。"
    if "seedance_complexity_score>=5" in issue:
        match = re.search(r"score=(\d+)", issue)
        score = match.group(1) if match else "5+"
        return f"- [SEEDANCE-COMPLEXITY-GATE-001] model_complexity_score={score}：Seedance 2.0 生产边界禁止单段直接生成，必须拆分、降级或改用视频参考。"
    if "seedance_complexity_score=3-4" in issue:
        match = re.search(r"score=(\d+)", issue)
        score = match.group(1) if match else "3-4"
        return f"- [SEEDANCE-COMPLEXITY-GATE-001] model_complexity_score={score}：中复杂度片段必须写明降级、压缩、白名单模板或参考驱动策略。"
    if "seedance_tail_state_missing" in issue:
        return "- [SEEDANCE-TAIL-STATE-GATE-001] tail_state 不清，必须返修为可继承的角色位置、视线/注意力、道具/门状态和未解决问题。"
    if "seedance_text_dependency" in issue:
        return "- [SEEDANCE-NO-TEXT-DEPENDENCY-001] 输入依赖字幕/屏幕文字/文件文字传达剧情；必须改成演员动作、视线、道具状态或对白声音信息。"
    return f"- [SEEDANCE-CONTRACT-GATE-001] {issue}"


def _seedance_contract_guard_issues(
    prompt: str,
    planner_segment: str,
    director_segment: str,
) -> list[str]:
    if not _seedance_contract_is_explicit(planner_segment, director_segment):
        return []
    combined = "\n".join([planner_segment or "", director_segment or "", prompt or ""])
    return [_seedance_issue_to_compiler_message(issue) for issue in seedance_qc_issues(combined)]


def _compiler_guard_report(prompt: str, script: str, planner_segment: str, director_segment: str) -> str:
    issues: list[str] = []
    execution_text = _prompt_execution_text(prompt)
    uses_shot_sequence = _prompt_uses_shot_sequence(prompt)
    base_report = _prompt_guard_report(prompt, script, planner_segment, director_segment)
    if base_report:
        issues.extend(line for line in base_report.splitlines() if line.strip())
    for contract_issue in prompt_contract_issues(prompt):
        issues.append(f"- [FINAL-SEEDANCE-PROMPT-CONTRACT] {contract_issue}")
    for term in abstract_viewpoint_terms("\n".join([prompt or "", director_segment or ""])):
        issues.append(
            f"- [SEEDANCE-ABSTRACT-VIEWPOINT-GATE] forbidden abstract viewpoint '{term}'; repair_route=shot_director/prompt_compiler."
        )

    if _INTERNAL_FIELD_LEAK_RE.search(prompt or ""):
        issues.append("- Prompt 泄漏了上游内部字段名：必须把 fragment_task、must_carry、cut_point 等翻译成自然中文镜头语言。")

    if re.search(r"机位|摄影机位于|机位在", execution_text):
        issues.append(
            "- Prompt 残留未翻译机位术语：最终镜头行必须写成视角/观看位置，"
            "例如“侧面视角”“固定视角”“从乔熙肩后看向小豆丁”，不要写“固定机位/侧面机位/摄影机位于”。"
        )

    uses_seedance_shot_contract = any(
        _has_yaml_field(director_segment or "", field)
        for field in ("duration", "must_carry", "cut_point", "continuity")
    )
    director_geometry_issues = [] if uses_seedance_shot_contract else _validate_spatial_geometry_contract(director_segment or "")
    if any("缺少空间几何字段" in issue for issue in director_geometry_issues):
        issues.append(
            "- 镜头资产缺少空间几何合同：shots 必须包含 camera_basis、camera_scene_position、"
            "camera_looks_toward、subject_position、subject_facing、visible_landmarks，compiler 不应凭空补前后景。"
        )
    for issue in director_geometry_issues:
        if "缺少空间几何字段" not in issue:
            issues.append(f"- 镜头资产空间几何合同错误：{issue}")

    if not re.search(r"(商北琛|乔熙|小豆丁|严飞|苏小可|众主管|众员工|他|她|两人|众人).{0,24}(半身中景|中景|近景|特写|中近景|全景|远景|胸部以上|关系景|七分身)", prompt):
        issues.append("- Prompt 缺少明确的主体+景别表达。")

    ambiguous_camera_terms = [term for term in _AMBIGUOUS_PROMPT_CAMERA_TERMS if term in prompt]
    if ambiguous_camera_terms:
        issues.append(
            "- 机位/运镜存在模糊描述："
            + "、".join(ambiguous_camera_terms[:6])
            + "。请改成简洁视角，例如从对方肩后看向人物、同侧固定视角、正面微侧视角、办公桌侧面固定视角、背后跟随视角。"
        )

    abstract_action_terms = (
        "动作主链",
        "双人关系主链",
        "状态单向推进",
        "单向推进",
        "关系建立",
        "抗拒位置",
        "尾帧承接",
        "动作叠压",
        "动作链",
        "画面主链",
        "状态链",
        "状态推进",
        "状态发生变化",
        "状态变化",
        "关系复位",
        "空间复位",
        "同场关系保留",
        "信息落点",
        "情绪落点",
        "可见落点",
        "尾帧锁定",
        "画面任务",
        "节奏落点",
        "轴线锁定",
        "视线匹配",
        "空间压迫",
        "空间打开",
        "人物消失感",
        "高信息密度",
        "动作过密",
        "跨镜连续",
        "覆盖职责",
        "情绪升级",
        "关系升级",
        "压力升级",
        "连续性锁定",
        "继承位置",
        "更有电影感",
        "更抓人",
    )
    abstract_terms = [term for term in (*_ABSTRACT_PROMPT_TERMS, *abstract_action_terms) if term in prompt]
    if abstract_terms:
        issues.append(
            "- Prompt 包含不可生成的抽象情绪判断："
            + "、".join(abstract_terms[:12])
            + "。请改写为手从哪里到哪里、接触哪个道具/身体部位、视线方向、身体距离、站位变化和结束停留位置等可见画面。"
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
            + "。请降级为 Seedance 稳定短句：一个主体焦点、一个景别、一个视角/观看位置、最多一种运动；反应落点改为同侧切镜。"
        )
    unstable_frame_terms = sorted(set(match.group(0) for match in _UNSTABLE_FRAME_COMPOSITION_RE.finditer(execution_text)))
    if unstable_frame_terms:
        issues.append(
            "- Prompt 包含不稳定构图表达："
            + "、".join(unstable_frame_terms[:5])
            + "。请改成自然可执行表达，例如\"从乔熙肩后看向门口，小豆丁站在门口等她\"；"
            "门、窗、桌等只作为空间边界或阻隔物，不写成框住人物的构图术语。"
        )
    pseudo_viewpoint_terms = sorted(set(match.group(0) for match in _PSEUDO_RELATION_VIEWPOINT_RE.finditer(execution_text)))
    if pseudo_viewpoint_terms:
        issues.append(
            "- Prompt 包含伪镜头视角："
            + "、".join(pseudo_viewpoint_terms[:5])
            + "。最终镜头只能写真实可拍的观看位置，例如“客厅侧面平视”“沙发旁固定半身景”“地毯旁双人中景”或“从乔熙肩后看向小豆丁”；"
            "不要把空间关系、尾帧承接、覆盖职责或道具之间的关系写成视角。"
        )

    space_section = _prompt_base_section(prompt)
    if space_section:
        spatial_terms = _SPATIAL_OVEREXPLAIN_TERMS_RE.findall(space_section)
        if len(space_section) > 220 or _meaningful_sentence_count(space_section) > 3 or len(spatial_terms) > 7:
            issues.append(
                "- 空间与首帧总控过载（新版为画面基底）：只保留2-3句不可变硬锚点（场景类型、1-3个空间关键节点、人物首帧站位与光线），"
                "不要反复解释前景/中景/后景/左右/远端/近侧/尽头；把镜头调度、动作和表情放回时间轴。"
            )
        if _SPACE_SECTION_ACTION_RE.search(space_section):
            issues.append("- 空间与首帧总控混入动作（新版为画面基底）：该段只写首帧静态关系，走、让、散开、进入、门合拢等动作必须放在镜头序列。")

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

    if not (_SAFE_CAMERA_POSITION_RE.search(prompt) or _NATURAL_VIEWPOINT_RE.search(prompt)):
        issues.append('- Prompt 缺少可执行摄影机位置/视角/观看位置：至少一个时间段应明确简洁视角，例如"从对方肩后看向人物/同侧固定视角/正面微侧视角/办公桌侧面固定视角/背后跟随视角"。')

    unsafe_action_terms = [term for term in _UNSAFE_ACTION_TERMS if term in prompt]
    if unsafe_action_terms:
        issues.append(
            "- 动作路径存在失控词："
            + "、".join(unsafe_action_terms[:6])
            + "。请改成自然稳定动作句，例如手松开西装前襟后落回身侧，身体停住。"
        )

    has_reaction_beat = any(term in prompt for term in _REACTION_BEAT_TERMS)
    has_explicit_reaction_cut = re.search(r"(?:镜头)?(?:切至|切到|切回)|反打至|反打镜头", prompt)
    if has_reaction_beat and not has_explicit_reaction_cut:
        issues.append('- 受击/反应落点缺少明确切镜：请写清"镜头切至谁、什么景别、什么视角/观看位置、画面里保留谁/什么空间锚点"。')

    all_dialogues = _quoted_dialogues(prompt)
    if _dialogue_block_requires_visual_break(all_dialogues) and not _DIALOGUE_VISUAL_CUT_RE.search(prompt):
        issues.append(
                "- 长台词/高压对白被单镜头吃完：完整发言单元要保持语义连续，但必须加入同侧听者反应、过肩、画外音或景别变化。"
        )

    over_precise_action = re.search(r"(?:起点|终点|路径|厘米|一掌距离|接触/避让对象|手指张开).{0,40}(?:起点|终点|路径|厘米|一掌距离|接触/避让对象|手指张开)", prompt)
    if over_precise_action:
        issues.append("- 动作描述过细：请合并为自然动作句，只保留主体、主要动作、必要情绪/视线落点和尾帧状态。")

    shot_sequence = _prompt_section(prompt, "镜头序列")
    if shot_sequence:
        shot_lines = [
            line.strip()
            for line in shot_sequence.splitlines()
            if re.match(r"^镜头\s*\d+\s*【", line.strip())
        ]
        for index, line in enumerate(shot_lines):
            action_count = len(_SHOT_ACTION_OVERLOAD_RE.findall(line))
            prop_or_body_count = len(set(_SHOT_PROP_OR_BODY_RE.findall(line)))
            has_dialogue = bool(_quoted_dialogues(line) or re.search(r"说[：:]", line))
            if action_count >= 7 or (action_count >= 5 and prop_or_body_count >= 4 and has_dialogue):
                issues.append(
                    f"- 镜头{index + 1}动作过载：3-5秒镜头最多承载一个主动作、一个辅助状态和一句台词；"
                    "请把道具移动、穿衣整理、孩子反应和尾帧状态压成自然动作句，必要时切成相邻镜头。"
                )
                break
            is_last = index == len(shot_lines) - 1
            if is_last:
                if not re.search(r"尾帧|最后|结尾|保持|仍在|停住|不切|收束", line):
                    issues.append("- 末尾镜头缺少尾帧状态：请写清人物位置、视线、道具或门/车/电梯状态如何保持。")
                continue
            if not re.search(r"切镜时机|切镜触发|切至镜头|切到镜头|切回镜头|转入镜头|进入镜头|→\s*镜头|切至|切到|切回", line):
                issues.append(
                    "- 镜头序列缺少切镜时机：每个非末尾镜头必须用括号写明动作顶点、台词压力词、信息看清或反应出现后切至下一镜。"
                )
                break

    timeline_blocks = _timeline_blocks(prompt)
    issues.extend(_prompt_shot_density_issues(prompt, planner_segment, director_segment, timeline_blocks))
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        block_dialogues = _quoted_dialogues(body)
        if _dialogue_block_requires_visual_break(block_dialogues) and not _has_internal_dialogue_visual_coverage(body):
            issues.append(
                f"- 时间轴第 {index} 个时间段让长台词/高压对白停留在单一画面：人物说话时严禁一个镜头、一个景别或一个视角说完整句；"
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
        if not _has_prompt_performance_beat(body):
            issues.append(
                f"- 时间轴第 {index} 个时间段缺少人物动作/表情落点：不要只写空间和机位，"
                "至少写清一个可见动作、视线或表情反应。"
            )
            break

    if not uses_shot_sequence:
        for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
            spatial_count = len(_SPATIAL_OVEREXPLAIN_TERMS_RE.findall(body))
            performance_count = _prompt_performance_count(body)
            if spatial_count > 6 and performance_count < 4:
                issues.append(
                    f"- 时间轴第 {index} 个时间段空间描写过载：每段只保留当前镜头必要的0-1个空间锚点，"
                    "不要解释前景/中景/后景/左右边缘；把文字预算让给动作、视线和表情。"
                )
                break

    if not uses_shot_sequence:
        for index, (_start, _end, body) in enumerate(timeline_blocks[1:], start=2):
            prefix = body[:120]
            if not _TIMELINE_BRIDGE_RE.search(prefix):
                issues.append(f'- 时间轴第 {index} 个时间段缺少段内交接词：请以"同一机位继续/延续上一镜/镜头切至/切回"承接上一时间段，单段内禁止反打。')
                break

    if not uses_shot_sequence:
        for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
            if not _TIMELINE_END_STATE_RE.search(body[-120:]):
                issues.append(f"- 时间轴第 {index} 个时间段缺少结束状态：请写清谁停在什么位置、朝向、画内/画外、门/道具/距离状态。")
                break

    for _start, _end, body in timeline_blocks:
        if _TIMELINE_BRIDGE_RE.search(body) and not _has_prompt_spatial_anchor(body):
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
    if not uses_shot_sequence:
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
    space_anchor_section = _prompt_base_section(prompt)
    if space_anchor_section and not uses_shot_sequence:
        pixel_hits = len(set(_PIXEL_ANCHOR_TERMS_RE.findall(space_anchor_section)))
        if pixel_hits < 2:
            issues.append(
                "- [PROMPT-FIRST-FRAME-PIXEL-LOCK-001] 空间与首帧总控缺少像素锚点（新版为画面基底）："
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
    for index, (_start, _end, body) in enumerate(timeline_blocks, start=1):
        if _SUBJECT_RELATIVE_LEFT_RIGHT_CAMERA_RE.search(body):
            issues.append(
                f"- [PROMPT-AXIS-LOCK-PER-SEGMENT-001] 时间轴第 {index} 个时间段使用了人物相对左右机位："
                "人物正面、背面或转身后左/右会反，视频模型无法稳定理解。请改成同侧轴线内的简洁机位，"
                '例如"同侧过肩机位""同侧固定机位""同侧正面微侧机位""办公桌侧面固定机位"。'
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

    if director_segment and not _has_yaml_field(director_segment, "shots"):
        issues.append("- 当前片段镜头资产缺少 shots 骨架。")

    issues.extend(_seedance_contract_guard_issues(prompt, planner_segment, director_segment))

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


def _director_shot_rows(director_segment: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in _MAIN_SHOT_BLOCK_RE.finditer(director_segment or ""):
        block = match.group(0)
        rows.append(
            {
                "shot_id": match.group(1).strip(),
                "duration": _yaml_line_field(block, "duration") or "2s",
                "task": _yaml_line_field(block, "task"),
                "subject": _yaml_line_field(block, "subject") or "current subject",
                "shot": _yaml_line_field(block, "shot")
                or _yaml_line_field(block, "camera")
                or _yaml_line_field(block, "size")
                or "stable medium shot",
                "action": _yaml_line_field(block, "action")
                or _yaml_line_field(block, "task")
                or _yaml_line_field(block, "must_carry")
                or "continue the approved action beat",
                "dialogue": _yaml_line_field(block, "dialogue"),
                "must_carry": _yaml_line_field(block, "must_carry"),
                "cut_point": _yaml_line_field(block, "cut_point") or "cut after the visible action lands",
                "continuity": _yaml_line_field(block, "continuity") or _yaml_line_field(block, "must_carry"),
                "coverage_role": _yaml_line_field(block, "coverage_role"),
                "cut_reason": _yaml_line_field(block, "cut_reason"),
                "companion_visibility": _yaml_line_field(block, "companion_visibility"),
                "state_delta": _yaml_line_field(block, "state_delta"),
                "tailframe_role": _yaml_line_field(block, "tailframe_role"),
            }
        )
    return rows


def _source_event_lines(planner_segment: str, script_context: str) -> list[str]:
    source_events_block = re.search(r"source_script_events\s*:([\s\S]*?)(?=\n[a-z_]+\s*:|\Z)", planner_segment or "")
    events = [
        event.strip().strip("\"'")
        for event in re.findall(r"-\s*(.+)", source_events_block.group(1) if source_events_block else "")
    ]
    events = [event for event in events if event]
    if events:
        return events[:5]
    fallback = [line.strip() for line in re.split(r"[\n。.!?]+", script_context or "") if line.strip()]
    return fallback[:5]


def _normalise_reference_label(label: Any, index: int) -> str:
    text = str(label or "").strip()
    match = re.match(r"^@(图片|image|Image)\s*(\d+)$", text)
    if match:
        return f"@图片{match.group(2)}"
    if text.startswith("@图片"):
        return text
    return f"@图片{index + 1}"


def _reference_role_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("role", "type", "asset_type", "purpose", "source", "filename", "description", "note")
    ).lower()


def _reference_explicit_role_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("role", "type", "asset_type", "source", "selected_by")
    ).lower()


def _is_previous_tail_reference(item: dict[str, Any]) -> bool:
    role_text = _reference_explicit_role_text(item)
    return (
        "previous_segment_tail_frame" in role_text
        or "previous_segment_video_tail_frame" in role_text
        or "provided_tail_frame" in role_text
    )


def _is_previous_storyboard_reference(item: dict[str, Any]) -> bool:
    role_text = _reference_explicit_role_text(item)
    return (
        "previous_segment_storyboard_crop" in role_text
        or "previous_storyboard_last_panel" in role_text
        or "last_storyboard_crop" in role_text
    )


def _reference_descriptor(item: dict[str, Any]) -> str:
    purpose = str(item.get("purpose") or "").strip()
    filename = str(item.get("filename") or "").strip()
    if purpose and filename:
        return f"{purpose}（{filename}）"
    return purpose or filename or "参考图"


def _reference_usage_line(item: dict[str, Any], index: int) -> str:
    label = _normalise_reference_label(item.get("label"), index)
    descriptor = _reference_descriptor(item)
    role_text = _reference_role_text(item)

    if _is_previous_tail_reference(item):
        return (
            f"{label} 是上一段实际尾帧/抽帧参考图：{descriptor}；仅用于锁定本段首帧承接："
            "人物最终站位、朝向、姿态、道具状态、空间轴线和光线；不得新增剧情或强行沿用不可见内容。"
        )
    if _is_previous_storyboard_reference(item):
        return (
            f"{label} 是上一段分镜尾格参考图：{descriptor}；仅在没有实际视频尾帧、且同场景连续时作为"
            "首帧承接的次级依据；不得新增剧情或强行沿用不可见内容。"
        )
    if any(marker in role_text for marker in ("character", "portrait", "人物", "角色", "服装", "外观", "演员")):
        return (
            f"{label} 是人物参考图：{descriptor}；仅用于锁定对应人物的身份、面部形象、发型、服装、"
            "体态和可见随身道具一致性；不得把参考图当作剧情道具或新增动作。"
        )
    if any(marker in role_text for marker in ("scene", "space", "location", "room", "场景", "空间", "地点", "母版", "九宫格")):
        return (
            f"{label} 是场景参考图：{descriptor}；仅用于锁定空间结构、固定家具/道具、光线方向、"
            "色调和基础轴线；不得复述成建筑说明书，不得新增场景区域。"
        )
    if any(marker in role_text for marker in ("prop", "item", "道具", "物件", "项链", "手机", "文件")):
        return (
            f"{label} 是道具参考图：{descriptor}；仅用于锁定道具外观、材质、尺寸关系和持有状态；"
            "不得新增道具用途或剧情。"
        )
    return (
        f"{label} 是视觉参考图：{descriptor}；仅用于锁定已标明的外观、空间或道具事实；"
        "不得新增人物、剧情、台词、文字或字幕。"
    )


_REFERENCE_TOKEN_SPLIT_RE = re.compile(r"[\s,，;；:：|｜/／\\()（）\[\]【】{}《》<>\"'“”‘’、]+")
_REFERENCE_GENERIC_TOKENS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "scene",
    "card",
    "layout",
    "grid",
    "image",
    "reference",
    "auto",
    "自动匹配",
    "参考图",
    "人物参考图",
    "场景参考图",
    "道具参考图",
    "人物",
    "角色",
    "场景",
    "空间",
    "道具",
    "命中",
    "只锁定",
    "用于",
    "日常",
    "礼服",
    "居家服",
    "年轻",
    "补充",
}
_REFERENCE_TOKEN_SUFFIXES = (
    "人物参考图",
    "场景参考图",
    "道具参考图",
    "参考图",
    "人物图",
    "场景图",
    "道具图",
    "人物",
    "场景",
    "道具",
)


def _reference_match_terms(item: dict[str, Any]) -> list[str]:
    raw_parts: list[str] = []
    for key in ("filename", "name", "label", "matched_tokens", "description", "note", "purpose"):
        value = str(item.get(key) or "").strip()
        if value:
            raw_parts.append(value)

    terms: list[str] = []

    def add_term(token: str) -> None:
        token = token.strip().strip(".")
        if token.startswith("@图片") or token.startswith("@image"):
            return
        if len(token) < 2:
            return
        if token.lower() in _REFERENCE_GENERIC_TOKENS or token in _REFERENCE_GENERIC_TOKENS:
            return
        if token not in terms:
            terms.append(token)

    for raw in raw_parts:
        stem = re.sub(r"\.(?:png|jpe?g|webp|gif)$", "", raw, flags=re.IGNORECASE)
        for token in [stem, *_REFERENCE_TOKEN_SPLIT_RE.split(stem), *re.split(r"[-_]+", stem)]:
            add_term(token)
            for suffix in _REFERENCE_TOKEN_SUFFIXES:
                if token.endswith(suffix):
                    add_term(token[: -len(suffix)])
    return sorted(terms, key=lambda text: (-len(text), text))


def _reference_matches_context(item: dict[str, Any], current_context: str) -> bool:
    if not current_context.strip():
        return True
    context = current_context.lower()
    return any(term.lower() in context for term in _reference_match_terms(item))


def _seedance_reference_items(
    state: DirectorState | dict[str, Any],
    *,
    segment_index: int | None = None,
    current_context: str = "",
) -> list[tuple[int, dict[str, Any]]]:
    manifest = state.get("reference_image_manifest") or []
    selected: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(manifest):
        if not isinstance(item, dict):
            continue
        if _is_previous_tail_reference(item) or _is_previous_storyboard_reference(item):
            if segment_index is not None and segment_index <= 1:
                continue
            selected.append((index, item))
            continue
        if _reference_matches_context(item, current_context):
            selected.append((index, item))
    return selected


def _seedance_reference_context(
    state: DirectorState | dict[str, Any],
    *,
    segment_index: int | None = None,
    current_context: str = "",
) -> str:
    lines: list[str] = []
    for _index, item in _seedance_reference_items(
        state,
        segment_index=segment_index,
        current_context=current_context,
    ):
        label = item.get("label") or ""
        filename = item.get("filename") or ""
        purpose = item.get("purpose") or "参考图"
        lines.append(f"{label} {filename}：{purpose}")
    notes = state.get("reference_images") or ""
    if notes and not current_context.strip():
        lines.append(f"用户补充说明：{notes}")
    return "\n".join(lines)


def _seedance_reference_prompt_block(
    state: DirectorState | dict[str, Any],
    *,
    segment_index: int | None = None,
    current_context: str = "",
) -> str:
    manifest = state.get("reference_image_manifest") or []
    lines: list[str] = []
    for index, item in _seedance_reference_items(
        state,
        segment_index=segment_index,
        current_context=current_context,
    ):
        if isinstance(item, dict):
            lines.append(_reference_usage_line(item, index))
    if not lines:
        if manifest:
            return "当前片段未匹配到可用参考图；不得编造 @图片1、@图片2、@图片3 或任何参考图占位。"
        return "无参考图；不得编造 @图片1、@图片2、@图片3 或任何参考图占位。"
    return "\n".join(lines)


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
        "你的输出必须严格按系统固定的 Gold Standard 结构，不得增删段落、不得使用 YAML、不得使用教学标签：\n\n"
        "```\n"
        "片段N｜场景名｜情绪/动作关键词(用+连接)｜~秒数秒\n\n"
        "【风格锚点】\n"
        "一句话定义现实短剧风格、光线气质与表演基调。\n\n"
        "【画幅锚点】\n"
        "9:16竖屏。\n\n"
        "【空间与首帧总控】\n"
        "最多 2-3 句：场景 + 1-3 个不可变硬锚点 + 本片段出现人物的身份/服装/当前状态 + 光线。"
        "如果镜头资产包含“空间连续性总控”，第一句必须先继承它：这是一段什么戏剧任务，哪些人物在同一空间内；单人镜只表示主体变化，不代表其他人物离开。"
        "禁止：堆砌前景/中景/后景/左右/远近的层级链条；推理门后空间；把场景图复述成建筑说明书；写动作动词（走进、迈入、冲来、转身等）。\n\n"
        "【时间轴】\n\n"
        "0-X秒：主体、景别、视角/观看位置。主体 + 一个主要动作/反应 + 必要台词/信息落点 + 结束状态。（切镜时机：动作顶点/台词压力词/信息看清/反应出现后进入下一时间段）\n\n"
        "X-Y秒：承接上一时间段人物位置、道具和轴线；必要时用画外音或声音桥把台词压到听者反应上。（切镜时机：具体触发点后进入下一时间段）\n\n"
        "末尾时间段必须写清“尾帧：人物位置、视线、道具、门/车/电梯状态如何保持”，不写切到下一镜。\n\n"
        "每一段都必须来自上游 shot 的 duration、subject、shot、action、dialogue、must_carry、cut_point、continuity；"
        "如果上游有 coverage_role、cut_reason、companion_visibility、state_delta、tailframe_role，也必须翻译进自然镜头句；不得泄漏这些字段名。\n\n"
        "【Seedance 2.0 合同编译 gate】\n"
        "如果当前片段资产包含 template_id、template_level、reference_need、tail_state、model_complexity_score，必须先按这些字段决定是否可编译，再写 prompt。\n"
        "1. template_id/template_level 是 coverage 白名单边界：W1 可直接编译；W2 必须压动作和切点；R1 必须有真实绑定的视频参考、关键帧或动作/运镜参考；X 禁止继续编译，只能要求拆分、后期或人工处理。\n"
        "2. 默认假设没有参考视频；reference_need 只表示需要，不表示已经有。identity_reference 锁人物，scene_reference 锁空间，prop_reference 锁道具；motion_reference/camera_reference 必须有 reference_bindings/reference_asset/video_path/keyframe_path 等真实绑定才可用，不得编造不存在的参考。\n"
        "3. model_complexity_score 为 3-4 时必须降级或拆分；5 及以上不得单段生成。\n"
        "4. tail_state 必须落实为末尾镜头的可继承尾帧：角色位置、视线/注意力、道具/门/车状态和未解决问题必须清楚。\n"
        "5. 禁止依赖字幕、屏幕文字、手机/文件可读文字传达剧情；改用演员动作、视线、道具状态或已有对白。compiler 只返修/降级上游资产，不新增剧情或镜头事件。\n\n"
        "【约束】\n"
        "空间轴线、人物服装发型、道具连续性、禁止项。必须包含：严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌。简洁列出；不得写“主体锁定”“不抢中心”“镜头保持稳定”等压死调度的霸王约束。\n\n"
        "【参考调用】\n"
        "如有参考图，只写每张参考图的唯一职责；无参考图则省略本段。\n\n"
        "片段N prompt 已输出。\n"
        "请生成视频后，上传：\n\n"
        "片段N的尾帧截图\n"
        "当前人物位置关系（若有变化）\n\n"
        "我将基于实际尾帧继续输出片段N+1。\n"
        "```\n\n"
        "【参考图使用硬约束】\n"
        "1. 参考图只作为编译期约束；如需输出，只能写入【参考调用】段，不得输出【参考图说明】段、文件名或图片用途清单。\n"
        "2. 人物参考图只用于锁定人物身份、面部形象、发型、服装、体态和可见随身道具一致性；不得把人物参考图当作剧情动作、台词或场景来源。\n"
        "3. 场景参考图只用于锁定空间结构、固定家具/道具、光线方向、色调和基础轴线；不得把场景参考图扩写成建筑说明书。\n"
        "4. 上一段尾帧/抽帧参考图只用于本段首帧承接：人物最终站位、朝向、姿态、道具状态、空间轴线和光线；不能覆盖当前片段的剧本事实。\n"
        "5. 最终 Prompt 的参考图效果自然落入【空间与首帧总控】【时间轴】【约束】，参考资产职责只在【参考调用】中简洁说明。\n\n"
        "【语言风格硬约束】\n"
        "1. 用简洁的导演调度语言，不用文学化描写。\n"
        "2. 表情只写关键状态，不堆砌微表情。\n"
        "3. 内部机位术语必须翻译为最终视角语言：写“侧面视角、固定视角、从谁肩后看向谁、谁的主观视角”，不要在最终 Prompt 中写“固定机位/侧面机位/摄影机位于”。\n"
        "4. 一句一个动作，句子简短有力，不在一句中塞多个并列描写。\n"
        "5. 台词直接嵌入动作描述中，不单独列出。\n\n"
        "【Seedance 2.0 优质短剧 Prompt 框架】\n"
        "1. 每个镜头按“景别 + 主体 + 一个主动作 + 场景锚点 + 真实可拍视角/观看位置 + 切镜触发”写，不按空间几何说明书写。\n"
        "2. 真实可拍视角只允许这类表达：正面平视、侧面平视、略低视角、略高视角、客厅一侧固定观察视角、沙发旁固定半身景、地毯旁双人中景、从A肩后看向B。\n"
        "3. 禁止伪视角：不要写“沙发与地毯之间的关系视角”“空间关系视角”“关系复位视角”“尾帧承接视角”“覆盖职责视角”“前后景关系视角”。这些是内部 blocking 语言，不是视频模型能拍的镜头。\n"
        "4. 镜头运动只保留一种：固定镜头、缓慢推近、轻微拉开、侧向跟拍、轻微手持感或插入特写；不要把推近、横移、摇摄、回到主位塞进同一镜头。\n"
        "5. 生活短剧优先“关系景 -> 必要切近 -> 回关系景”的稳定组合；不要为手机、衣角、脚、手指等微动作连续切碎，除非该物件承载剧情信息。\n\n"
        "【动作粒度上限】\n"
        "1. 最终镜头句只保留：主体、一个主要动作变化、必要情绪/视线落点；不要把每根手指、衣角、呼吸、肩颈、眼角连续写成动作流水账。\n"
        "2. 生活动作只写模型容易稳定生成的大动作：拿起、放下、后退、停住、看向、递出、推开、进入、离开；微动作只在承载线索、受击结果或动作前摇时保留一次。\n"
        "3. 如果上游 action 太细，先合并为 1-2 句自然动作；删除厘米级路径、手指开合、起点/落点流水账，只保留会影响剧情理解的接触、安全状态和尾帧。\n"
        "4. Seedance prompt 优先 35-80 词级别的自然镜头语言；图生视频更短，重点写人物动作、镜头运动和情绪，不复述参考图已包含的对象。\n\n"
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
        "2. 如果上游资产明确给出 shot_director_coverage_v3.template_plan.shots，你可以在同一片段内自然承接炸点命中、受击落点、双人关系变化；但必须写出连续过渡，不能伪造剪辑软件式瞬切。\n"
        "3. 不得无动机跳轴、跳空间、跳主体。主体重心变化必须来自上游主分镜骨架，并在时间轴中写出动作或视线过渡。\n"
        "4. 若上游明确要求受击落点留在片段内，不能为了省事把受击者降成背景虚化。\n"
        "5. 若上游明确要求下一独立片段再承接受击，则当前片段也不得提前偷跑完整反应。\n\n"
        "【视频模型物理限制——必须服从但不能误解】\n"
        "1. 整个片段仍是连续视频流，所以每个时间段的画面必须从上一个时间段自然演变。\n"
        "2. 禁止180度视角翻转，展示背影必须靠人物自然转身。\n"
        "3. 景别变化必须通过动作、视线、调度或运镜自然过渡。\n"
        "4. 如果时间轴出现第二人物的反应，必须保证它来自当前空间关系与上游 coverage_plan/template_plan，而不是凭空切去另一个场景。\n"
        "5. 近景里不要描述超出当前画面可见范围的大量背景动作。\n"
        "6. 原则：把每个时间段想象成同一段导演编排在连续视频里自然展开。\n\n"
        "【Seedance 2.0 空间极简策略——最重要规则】\n"
        "1. **严禁空间过载**：时间轴的重点是\"动作、情绪、视角\"。绝不允许堆叠\"前景、中景、后景、远端、近侧、边缘、画面左、画面右\"等冗余方位词。\n"
        "2. 每个时间段最多保留 1 个必需的空间锚点（如\"电梯门旁\"），超过 1 个即为违规。\n"
        "3. 遇到上游提供的复杂 `geom:` 字段，**必须大幅裁剪**。只提取能说明机位和人物朝向的最少词汇，其余一律丢弃，绝不能逐字翻译。\n"
        "4. 【空间与首帧总控】最多 2-3 句，极简点明场景、人物首帧状态、光线和不可变硬锚点，禁止写出详细的建筑结构或人物的精确坐标。\n"
        "5. 空间简写不等于剪辑省略；【时间轴】必须把切镜时机写成括号触发句；单段内禁止写\"反打至/反打镜头\"。\n"
        "6. compiler 不重新设计教学视频里的拍摄技巧，只忠实保留上游镜头资产已有的动作匹配、视线引导、听者反应、景别递进、出画入画等设计；若上游写了反打，必须提示拆段或打回 shot_director。\n"
        "7. 每个镜头行必须至少有一个人物动作或表情/视线落点；如果空间锚点和表演落点冲突，优先保留表演落点。\n"
        "8. 背后、侧后方、180度必须绑定人物，不绑定场景。正确写法是\"商北琛背后中景/商北琛侧后方中景\"；禁止写\"电梯门外背后180度\"\"电梯口背后\"\"大堂中轴背后\"。\n"
        "9. 表现人物与电梯关系时，从人物背后或侧后方看他走向/进入电梯，不要让文字暗示从电梯里面向外拍。\n"
        "10. 电梯场景硬锁：电梯门打开后只能是封闭金属轿厢、侧壁/后壁/控制面板；禁止生成办公室、会议区、走廊、窗户、另一片大堂或会客区。\n"
        "11. 群演硬锁：只有命名人物使用清晰身份参考；员工/路人必须是匿名差异化面孔、侧脸、背影或轻虚，不得与主角或助理同脸。\n\n"
        "【成功案例镜头链条】\n"
        "遇到职场权威入场、冷处理问候、平静下令、群体退让这类片段时，优先学习这种结构：\n"
        "1. 用一个局部动作或人物半身建立节奏，例如皮鞋落地、手部动作、人物稳定步速；不要先写大段空间说明。\n"
        "2. 问候/对峙用双人关系景、听者反应或从一人肩后看向另一人的可拍视角，重点写谁说话、谁不回应、视线如何移开。\n"
        "3. 命令句用半身景承载，必要时插入一次眼神/表情局部特写，再切回半身收完整句。\n"
        "4. 命令生效用群体关系景收束，写主管/员工如何停步、让路、四散、退回边线；不要补复杂南北东西或远近层级。\n"
        "5. 最终时间轴应读起来像\"镜头视角变化 + 人物动作表情 + 台词落点\"，而不是空间坐标说明书。\n\n"
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
    if _contains_local_fallback_input(current_director_segment_raw or outputs.get("shot_director", "")):
        raise RuntimeError(
            f"片段 {segment_index} Prompt 编译失败：上游三段式镜头导演输出来自本地兜底，"
            "已拒绝继续编译。请先重跑三段式镜头导演并确保大模型调用成功。"
        )
    current_director_segment = _compress_director_for_compiler(current_director_segment_raw)
    current_frame_control_contract = (
        outputs.get(f"frame_control_contract_seg{segment_index:02d}")
        or outputs.get(f"frame_control_contract_seg{segment_index}")
        or ""
    )
    current_seedance_contract = _seedance_contract_card(current_planner_segment, current_director_segment_raw)
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
            "1. 如果视频分析里的 next_segment_start_mode.mode 是 image_start，【空间与首帧总控】必须继承 selected_candidate 对应的可见人物位置、朝向、道具和空间状态。\n"
            "2. 如果 next_segment_start_mode.mode 是 direct_cut，禁止强行沿用上一段尾帧；应按当前片段规划资产重新开镜、闪回、换场或做空间复位。\n"
            "3. 如果 bridge_frame.usable_as_start_image=false，不能把该帧当作下一段首帧，只能继承明确可见的道具/空间状态。\n"
            "4. 如果 continuity_constraints.must_reset_space=true，当前片段开头必须用关系景、中景或明确空间状态重建，不要从局部特写硬接。\n"
            "5. 本桥接决策高于下面旧的尾帧继承规则；direct_cut 时，“必须以视频最终位置为准”只适用于明确可继承的道具/空间状态，不适用于人物首帧站位。"
        )
    reference_match_context = "\n\n".join(
        part
        for part in (current_source_events, current_planner_segment, current_director_segment_raw)
        if part
    )
    reference_context = _seedance_reference_context(
        state,
        segment_index=segment_index,
        current_context=reference_match_context,
    )
    reference_prompt_block = _seedance_reference_prompt_block(
        state,
        segment_index=segment_index,
        current_context=reference_match_context,
    )
    reference_usage_instruction = (
        "只允许使用【当前片段参考图约束】中列出的当前片段参考图作为隐性约束；"
        "人物图只锁定身份/五官/服装，场景图只锁定空间/光线/轴线。"
        "最终 Prompt 禁止输出【参考图说明】段、文件名或图片用途清单；如有参考图，只能在【参考调用】段写唯一职责。\n\n"
        if reference_context.strip()
        else "本次未提供参考图；最终 Prompt 中严禁编造 @图片1、@图片2、@图片3 或任何参考图占位。\n\n"
    )
    # --- final Seedance prompt contract validation ---
    minimum_contract_issues: list[str] = []
    if "rhythm_operation_sheet_ref" not in current_planner_segment and "rhythm_operation_sheet" not in str(outputs.get("rhythm_rewrite_director", "")):
        minimum_contract_issues.append("missing rhythm_operation_sheet handoff")
    for field in (
        "generation_unit_id",
        "source_script_events",
        "event_atom",
        "duration_target",
        "model_complexity_score",
        "reference_needs",
        "tail_state_required",
        "shot_director_handoff",
    ):
        if field not in current_planner_segment:
            minimum_contract_issues.append(f"generation_unit missing {field}")
    if "shot_director_coverage_v3" not in current_director_segment_raw:
        minimum_contract_issues.append("shot_director schema_version must be shot_director_coverage_v3")
    for field in ("coverage_plan", "template_plan", "guard_result", "template_id", "template_level", "tail_state"):
        if field not in current_director_segment_raw:
            minimum_contract_issues.append(f"shot_director coverage_v3 missing {field}")
    if "tail_state" not in current_director_segment_raw and "tail_state_required" not in current_planner_segment and "tailframe_state" not in current_frame_control_contract:
        minimum_contract_issues.append("missing tailframe_contract/tail_state")
    if minimum_contract_issues:
        raise RuntimeError(
            "[FINAL-SEEDANCE-PROMPT-GATE] prompt_compiler refused to compile incomplete upstream contracts.\n"
            + "\n".join(f"  - {issue}" for issue in minimum_contract_issues)
            + "\nrepair_route=story_planner/shot_director/storyboard_designer before prompt_compiler."
        )
    user_prompt = (
        f"=== 当前片段压缩上下文 ===\n\n"
        f"{_runtime_context_contract_card()}\n\n"
        f"【场景空间记忆卡】\n{scene_memory}\n\n"
        f"【当前片段原文事件】\n{current_source_events}\n\n"
        f"【当前片段规划资产】\n{current_planner_segment}\n\n"
        f"【Seedance 2.0 合同字段卡（必须保留并用于编译决策，不得作为最终字段名输出）】\n{current_seedance_contract}\n\n"
        f"【当前片段镜头资产】\n{current_director_segment}\n\n"
        f"【frame_control_contract / tailframe_contract】\n{current_frame_control_contract or 'none'}\n\n"
        f"【final_seedance_prompt required】\nstyle_anchor; aspect_anchor=9:16竖屏; continuity_contract; reference_binding_contract; timeline; tailframe_contract; hard_constraints; {NO_TEXT_HARD_CONSTRAINT}\n\n"
        f"【上一段人物最终姿势/视频分析（最高优先级空间参考）】\n{tail_frame_memory}\n\n"
        f"⚠️ 【空间与首帧总控的核心规则】\n"
        f"如果上方存在【上一段人物最终姿势/视频分析】内容，则该分析描述的是上一段视频的**实际生成结果**。\n"
        f"你在编写【空间与首帧总控】时，**必须以该视频分析中描述的人物最终位置、朝向、姿态和空间布局为准**，\n"
        f"而非照搬任何全局镜头预案。预先规划是理想状态，实际视频可能有偏差。\n"
        f"具体要求：\n"
        f"1. 首帧中人物的站位、朝向必须与视频分析中描述的【最终状态】完全一致。\n"
        f"2. 空间锚点（门、走廊、电梯等）的相对位置必须与视频分析中描述的【空间轴线】一致。\n"
        f"3. 如果视频分析提到了续接约束，必须严格执行。\n"
        f"4. 不要在【空间与首帧总控】中扩写复杂场景说明；只保留1-3个关键节点和首帧人物关系，其他信息交给【时间轴】中的视角、动作和切镜时机。\n"
        f"5. 如果场景关系不确定，禁止补写门后、走廊尽头、办公室延伸等推理空间。\n\n"
        f"【当前片段参考图约束（仅供编译，不得作为最终段落输出）】\n"
        f"{reference_prompt_block if reference_context.strip() else '无'}\n\n"
        f"{revision_block}\n"
        f"【当前任务】\n"
        f"请专门为【片段 {segment_index}】编译最终 Seedance Prompt。\n\n"
        "你必须严格服从【当前片段规划资产】与【当前片段镜头资产】：\n"
        "1. 当前片段的 shot_director_coverage_v3.template_plan.shots 决定戏剧骨架，不得随意删掉其中的动作单元。\n"
        "2. coverage_role、cut_reason、must_carry、cut_point、tailframe_role 决定炸点、受击、表情重音和尾帧落点；不得把这些落点随意抹平成背景附带。\n"
        "3. 若上游要求受击在片段内承接，时间轴必须真正写出该受击/反应的可见落点。\n"
        "4. 若上游要求完整发言单元保持连续，意思是语义和声音连续，不是单镜头吃完整段台词；必须保留上游给出的听者反应、关系景、画外音或景别变化；若上游写了反打，单段内改写为同侧听者反应，真反打必须拆段。\n"
        "5. source_script_events 必须全部覆盖，不得遗漏。\n"
        "6. 若合同字段卡出现 template_id、template_level、reference_need、tail_state、model_complexity_score，必须逐项使用：X/candidate/R1无参考/复杂度超限/尾帧不清/文字依赖都要输出明确返修或降级内容，不得直接扩写生成。\n\n"
        "【镜头覆盖字段翻译规则】\n"
        "如果镜头资产包含新施工单字段 duration / task / must_carry / cut_point / continuity，以及三号守门字段 coverage_role / cut_reason / companion_visibility / state_delta / tailframe_role，必须按下面方式编译成【时间轴】：\n"
        "0. 空间连续性总控 必须转译进【空间与首帧总控】开头：说明本片段戏剧任务、同一空间、同一人物组和单人镜不代表其他人物离场；不要泄漏字段名。\n"
        "1. duration 只进入镜头编号后的秒数，例如 镜头1【4秒】；不要在最终 prompt 里写 duration 字段名。\n"
        "2. task 决定镜头功能，但最终只写成自然镜头动作，不要输出 task 字段名。\n"
        "3. subject + shot 只合成镜头行开头的自然视角表达；shot 若是新版输出，只把它当成景别、视角/观看位置、运动或前景关系，不要从 shot 字段抽取人物动作；若上游仍写“机位”，最终必须翻译成“视角”。\n"
        "4. action + dialogue 是镜头行主体；动作、表情、视线、呼吸、肩颈、手部、道具接触和台词落点必须主要来自 action，台词直接嵌入动作句中，画外音或声音桥写成自然中文。\n"
        "5. must_carry 必须转译成画面里看得见的信息、道具状态、人物距离变化或反应结果，不能只放到约束里，也不能写成抽象戏剧效果。\n"
        "6. cut_point 必须放进括号，统一写成（切镜时机：动作顶点前切至镜头2）、（切镜时机：台词断点时切至乔熙反应镜头）、（切镜时机：文件内容看清后切至镜头3）这类自然中文触发句；禁止使用箭头式表达。\n"
        "7. continuity 必须落实到镜头行或【约束】里，写清上一镜结束状态如何被下一镜继承：人物站位、道具在谁手里、手停在哪里、距离是否变化；不要只写“状态单向推进”“不得回弹”这类抽象约束。\n"
        "8. coverage_role 决定这一镜的信息任务，但最终不得写“本镜负责建立关系/承载对白/尾帧承接”。必须改成可见画面：人物A和人物B同框站在空间锚点两侧、道具X仍在人物A手里、道具Y停在已改变或未完成状态。\n"
        "9. cut_reason / 切镜原因 必须和 cut_point 合并成括号里的切镜触发，绑定动作顶点、台词断点、信息看清、反应出现或尾帧完成；不能写成“更有电影感”。\n"
        "10. companion_visibility 必须转译为镜头行里的同场关系保留：画面边缘、画外左/右侧、同框或明确出画/入画原因；避免单人镜让其他人物像消失。\n"
        "11. state_delta / 状态变化 必须写成本镜相对上一镜新增的可见变化：视线转向谁、身体退开或停住、道具归属如何变化、门缝变宽或变窄；不能只写“情绪变化”“状态变化发生”。\n"
        "12. tailframe_role / 尾帧职责 必须落实到末尾镜头的“尾帧：...”或【约束】中，写清下一镜/下一段可继承的人物位置、视线、道具、门/车/电梯状态；不要写“尾帧承接”“抗拒位置”这种内部标签。\n"
        "13. 若三号守门字段与基础字段重复，保留一次自然表达即可；若三号指出硬伤修复，以三号字段为准。\n"
        "14. 如果上游 shot 字段混有动作，必须拆开处理：摄影信息放镜头行开头，人物动作和表情并入 action 的自然句，避免最终 prompt 一句里同时塞摄影和动作导致模型误画。\n"
        "15. 最终 prompt 禁止出现 fragment_task、must_carry、cut_point、continuity、coverage_role、cut_reason、companion_visibility、state_delta、tailframe_role、shot_id、fragment_id 等内部字段名。\n\n"
        "【伪镜头语言降级规则】\n"
        "1. 如果上游 shot 写成“X与Y之间的关系视角”“空间关系视角”“关系复位视角”，必须改成真实观看位置：例如“客厅侧面平视”“沙发旁固定半身景”“地毯旁双人中景”。\n"
        "2. 如果上游 action 写得过细，优先合并为一个主动作；例如“手机从耳侧移向沙发坐垫、底部接触、手指松开、不滑走”改成“乔熙把手机放到沙发坐垫上，空出双手继续给孩子整理衣服”。\n"
        "3. 如果约束里禁止屏幕文字，就不要要求闹钟、手机或文件上的数字/文字清楚可读；改为“闹钟响着，乔熙看向闹钟，表现快迟到”。\n\n"
        "【Seedance 2.0 场景简写与表演优先规则】\n"
        "1. 最终 Prompt 不要把场景空间写成说明书；空间只服务连续性，不承担戏剧表达。\n"
        "2. 【空间与首帧总控】最多2-3句，只写不可变硬锚点：场景类型、入口/门/电梯/桌边等关键节点、人物首帧站位、人物身份服装、光线。\n"
        "3. 每个镜头行优先写：景别/视角、谁做什么、视线看向谁、表情怎样变化、结束时停在哪里；不要写起点/路径/终点说明书。\n"
        "4. 每个镜头行的空间锚点最多0-1个短语，且必须是当前镜头确实需要看见的节点；不要反复堆叠前景/中景/后景/左右/远近/边缘。\n"
        "5. 空间信息可以少，但切镜时机不能省；每个非末尾镜头都必须写“（切镜时机：...切至镜头N）”，禁止单段内写\"反打至\"。\n"
        "6. compiler 只翻译上游导演输出，不新增拍摄技巧；但如果上游写了动作匹配、视线引导、听者反应、出画入画、景别递进等设计，必须保留成可执行时间轴语言。\n"
        "7. 背后、侧后方、180度是人物相对机位，不是场景相对机位；只写\"商北琛背后中景/商北琛侧后方中景\"，不要写\"电梯门外背后180度\"。\n"
        "8. 电梯开门/入电梯时只需写\"封闭金属轿厢\"，必要时加\"控制面板\"；并在约束中禁止\"办公区、会议区、走廊、窗户、另一片大堂\"。\n"
        "9. 有众员工/群演时，必须在约束中写明：员工不得与命名人物相似、重复或同脸，优先用匿名差异化面孔、侧脸、背影、轻虚。\n\n"
        "【生活动作可拍化规则】\n"
        "1. 遇到生活动作、冲突动作、道具动作、进入/离开、拉扯、躲避、翻找、收拾等行为，先压成自然动作句：主体 + 一个主要动作 + 必要接触/方向 + 尾帧状态。\n"
        "2. 不要输出\"动作叠压\"\"动作主链\"\"关系建立后\"\"状态单向推进\"\"抗拒位置\"；改写为\"人物A把道具X移到位置B\"\"人物A扶住/松开人物B\"\"人物B后退半步停住\"这类短句。\n"
        "3. 如果一个镜头里有两个并行动作，只保留影响剧情或连续性的那个；另一个写进必须承载或连续性，避免模型同时执行过多肢体任务。\n"
        "4. 局部近景只在信息必须看清时拍可见接触点；不要为手指、衣角、嘴唇、眼角、鞋尖、肩颈等微细节单独扩写，除非它是当前剧本唯一信息主体。\n"
        "5. 尾帧不能写成职责标签，必须写成姿势：人物A保持道具X在目标位置；人物B退开半步停住；道具Y保持未完成或已改变状态。\n\n"
        "【最终约束固定项】\n"
        "【约束】段必须明确写入：严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌；禁止生成招牌文字、手机屏幕文字、文件可读字、UI文字和片内字幕。\n\n"
        "【空间几何字段翻译规则——严禁透传】\n"
        "镜头资产中的 camera_basis / camera_scene_position / camera_looks_toward / subject_position / subject_facing / visible_landmarks 是上游内部结构化字段。\n"
        "你必须将它们翻译成自然中文导演语言，绝对禁止在最终 Prompt 中出现 key=value 格式（如 camera_basis=scene_fixed、visible_landmarks=lobby_entrance=background_center）。\n"
        "1. camera_basis=scene_fixed 时，时间轴写成\"固定视角\"或\"电梯口固定视角\"等短词，不要展开成长空间说明，也不要改成人物正前方视角。\n"
        "2. camera_basis=subject_relative 时，只能用于人物朝向和位置稳定的说话/反应镜头；人物穿过门框、进入电梯、进入车门时必须改用 scene_fixed。\n"
        "3. visible_landmarks 只允许挑选当前镜头最必要的1-2个可见锚点翻译，不得把全部锚点硬塞进前景/中景/后景说明。\n"
        "4. subject_facing 和 angle 冲突时，优先修正 angle 或 visible_landmarks；不要保留互相打架的\"正面+朝门+后景门框\"。\n"
        "5. camera_scene_position → 只在必须保持空间连续时翻译成短句；如果会造成歧义，改成同侧轴线内的简洁视角，如\"从对方肩后看向人物\"\"办公桌侧面固定视角\"。\n"
        "6. visible_landmarks → 只挑一个当前镜头必要锚点写成短语，如\"电梯门旁\"；不要翻译成长串前景/中景/后景说明。\n"
        "7. subject_position/subject_facing → 只在必要时翻译成人物站位和朝向，如\"商北琛站在通道中，面朝电梯\"；不要写南侧/远端/近侧/外侧/内侧等多重方位链。\\n"
        "8. 摄影机后退可行性：如果人物面朝电梯/门口且机位在正前方0度，同速后退会让摄影机退进电梯/撞墙；"
        "必须改用侧面跟随视角、背后跟随视角、门口侧面固定视角或固定视角，不得改用人物左前方/右前方。\n"
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
        "2. 是否包含【风格锚点】【画幅锚点】【空间与首帧总控】【时间轴】【约束】五个固定段落？如有参考图，是否只额外包含【参考调用】？是否没有【画面基底】【镜头序列】【人物】【参考图说明】段？\n"
        "3. 每个时间轴条目是否为 X-Y秒：主体+景别+简洁视角+自然动作/对白+括号切镜时机？末尾时间段是否写清尾帧？\n"
        "4. 每个镜头行是否有至少1个可见动作、信息或情绪落点？\n"
        "5. 每个镜头行是否自然简短，不靠堆空间词凑字？\n"
        "6. 是否存在场景名+景别的违规写法？\n"
        "7. 是否存在剧本外编造的台词或情节？\n"
        f"8. 末尾是否包含尾帧上传提示（片段{segment_index} prompt 已输出...）？\n"
        "9. 拆片方案中当前片段的 source_script_events 是否全部被覆盖？有无遗漏事件（尤其是片段末尾的悬点/收束动作）？\n"
        "10. 节奏是否合理——建立段是否简洁、炸点/受击段是否留足空间？是否存在表情堆砌导致剧情推进过慢的问题？\n"
        "11. 【空间连续性】每个时间段的画面是否从上一时间段自然演变？是否存在空间跳变或视角翻转？\n"
        "12. 【主体递进而非硬切】主体重心变化是否严格来自上游 template_plan.shots、coverage_role、cut_point 和 tailframe_role，且通过动作/视线/调度自然过渡？\n"
        "13. 【空间与首帧总控无动作】空间与首帧总控中是否包含了动作动词（走进、迈入、冲来、转身等）？\n"
        "    如果有，必须改为纯静态描述（站在、位于、面朝），动作只能出现在【时间轴】中。\n"
        "14. 是否还存在三分之四角度、侧前方、轻微前推跟随、沉默就是回应、权力关系锁住、空气收紧等模糊或抽象描述？如有必须改成明确左右机位、角度、运镜和可见动作。\n"
        "15. 受击反应是否写清\"镜头切至谁/什么景别/什么机位/画面中保留谁\"？关键动作是否合并成主体+主要动作+必要接触/方向+尾帧状态？是否还存在弹开、飞开、甩开、突然闪开等失控动作词？\n"
        "16. 每个镜头是否继承上一镜头结束状态？除第一个镜头外，是否用动作、视线、道具或轴线明确交接？是否误写了单段反打？每次切镜是否保留必要空间锚点？\n"
        "17. 【禁止透传内部字段】最终输出中是否存在 camera_basis=、camera_scene_position=、camera_looks_toward=、subject_position=、subject_facing=、visible_landmarks= 等 key=value 格式？如有必须全部改写为自然中文句子。\n"
        "18. 【空间与首帧总控简写】空间与首帧总控是否超过3句或反复解释前景/中景/后景/左右/远近？如果是，删到只剩1-3个硬锚点。\n"
        "19. 【表演优先】每个镜头行是否至少有一个人物动作、视线或表情落点？如果没有，不要继续补空间，改补人物调度。\n"
        "20. 【电梯硬锁】电梯门后是否被写成办公区/会议区/走廊/窗户/另一片大堂？如果是，改为封闭金属轿厢，并加入禁止项。\n"
        "21. 【群演同脸】有众员工/群演时，是否明确禁止与命名人物同脸、相似或重复？如果没有，必须加入约束。\n"
        "22. 【对白覆盖】长台词、高压命令、质问或揭晓句是否被一个固定视角从头吃到尾？如果是，必须保留/恢复听者反应、关系景、画外音或景别变化；真反打必须拆到相邻片段。\n"
        "23. 【摄影机后退可行性】如果某个时间段写了'正前方0度+同速后退'且人物面朝电梯/门口，检查摄影机后退方向是否会退进电梯/撞墙？如果会，改用侧面跟拍或场景固定机位。\n"
        "24. 【近侧/远端一致性】'近侧侧边''远端''前景''后景'是否与当前摄影机位置和人物朝向的实际几何关系一致？人物面朝电梯+摄影机拍正面时，电梯门框只能在前景/侧边，不能在后景/远端。\n"
        "25. 【空间方位词密度】每个时间段的空间方位词（前景/中景/后景/远端/近侧/边缘/侧边/画面左/画面右/前方/后方/左侧/右侧）是否超过3个？如果超过，只保留最必要的0-1个锚点。\n"
        "26. 【视角翻转铺垫】相邻两个时间段之间是否存在从正面突变为背面（或反之）的视角翻转？如果有，必须在文本中铺垫人物转身动作，或插入侧面过渡机位。\n"
        "27. 【内部字段泄漏】是否出现 fragment_task、must_carry、cut_point、continuity、coverage_role、cut_reason、companion_visibility、state_delta、tailframe_role、空间连续性总控、shot_id、fragment_id 等字段名？如有必须改写成自然中文镜头语言。\n"
        "28. 【导演口语翻译】时间轴里是否还残留\"稳定器在同一运动里带到\"\"顺势带到\"\"受压反应\"\"权力压住\"\"压入\"\"卡断\"\"炸点\"\"钩子\"\"凝滞\"\"留白\"等导演调度口语？如有必须改成镜头从谁到谁、景别、运动方向、触发动作和低头/屏息/肩膀收紧/眼神回避等可见表演。\n"
        "29. 【三号守门成果落地】若当前片段镜头资产包含覆盖职责、切镜原因、同场人物位置、状态变化、尾帧职责，是否已经分别落进镜头信息任务、切镜触发、同场关系、可见状态变化和尾帧继承？不能只把它们留在上游资产里。\n"
        "30. 【参考图隐性落地】是否只把参考图约束自然落进人物、空间、道具连续性里，没有输出 @图片编号、文件名或参考图用途清单？\n"
        "31. 【无文字字幕】约束段是否明确禁止任何文字、字幕、水印、logo、屏幕文字和可读标牌？\n"
        "32. 【动作可拍化】是否还残留\"动作主链\"\"关系建立\"\"状态单向推进\"\"抗拒位置\"\"动作叠压\"等抽象词？如有必须改成手、道具、身体距离、接触点、移动方向和结束姿势。\n"
        "全部通过后再输出。"
    )
    output = call_llm(
        system_prompt,
        user_prompt,
        images_base64=None,
        agent_name="prompt_compiler",
    )
    _ = reference_prompt_block
    retrieval_meta["compiler_mode"] = "llm_required"
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
