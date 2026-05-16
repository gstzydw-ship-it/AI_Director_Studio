"""Storyboard first-frame designer implementation.

Generates one storyboard sheet per segment. Each panel is the first frame of
one shot from the shot director output, intended as a Seedance 2.0 visual
anchor rather than a comic/action storyboard.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

from .helpers import (
    _extract_fragment_id,
    _extract_yaml_sections,
    _fragment_id_for_segment_index,
    _segment_block_by_fragment_id,
    _truncate_for_prompt,
    _yaml_line_field,
)
from .llm import call_llm, resolve_llm_settings
from .state_store import _agent_outputs, _persist_update
from .types import DirectorState, OUTPUT_DIR


# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------
_STORYBOARD_SYSTEM_PROMPT = (
    "浣犳槸鍒嗛暅棣栧抚鍥捐璁″笀锛屾湇鍔′簬 Seedance 2.0 瑙嗛鐢熸垚娴佺▼銆俓n"
    "浣犵殑浠诲姟涓嶆槸閲嶆柊瀵兼紨鍓ф儏锛屼篃涓嶆槸鐢诲姩浣滄极鐢伙紝鑰屾槸鎶婇暅澶村婕旂粰鍑虹殑姣忎釜闀滃ご锛?"
    "杞崲鎴愯闀滃ご寮€濮嬬灛闂寸殑闈欐棣栧抚鐢婚潰鎻愮ず璇嶃€俓n\n"
    "纭鍒欙細\n"
    "1. 鍙緭鍑烘渶缁堢粰鐢熷浘鎺ュ彛浣跨敤鐨勬彁绀鸿瘝锛屼笉瑕佽В閲婏紝涓嶈浠ｇ爜鍧椼€俓n"
    "2. 涓€涓墖娈佃緭鍑轰竴寮犲垎闀滈甯у浘锛涙暣寮犲浘鐨勫楂樻瘮渚嬪繀椤讳笌瑙嗛鐢诲箙瀹屽叏涓€鑷达紝9:16 灏辩敓鎴愮珫鐗?9:16锛?6:9 灏辩敓鎴愭í鐗?16:9銆俓n"
    "3. 鍥句腑姣忎釜闀滃ご蹇呴』鎸変竴琛屼笁鏍忔帓鐗堬細宸︽爮鏄垎闀滈甯х敾闈紝涓爮鏄暅澶村弬鏁板拰鍔ㄤ綔瑕佺偣锛屽彸鏍忔槸淇鏈轰綅鍥俱€俓n"
    "4. 姣忚宸︽爮鍙睍绀鸿闀滃ご寮€濮嬫椂鐨勯潤姝㈢姸鎬侊細浜虹墿浣嶇疆銆佽韩浣撴湞鍚戙€佽绾挎柟鍚戙€侀亾鍏蜂綅缃€佸満鏅敋鐐广€佹櫙鍒拰鏈轰綅銆俓n"
    "5. 鍙虫爮鏈轰綅鍥惧繀椤绘槸绠€娲佷刊瑙嗙ず鎰忓浘锛氱敤 CAM 涓夎褰㈣〃绀烘憚褰辨満锛岀敤褰╄壊鍦嗙偣琛ㄧず浜虹墿/鍏抽敭鐗╋紝鐢ㄨ绾挎墖褰㈡垨闀滃ご鏈濆悜绾胯〃绀烘媿鎽勬柟鍚戯紝鏍囧嚭杞寸嚎鍜岃閲庤寖鍥淬€俓n"
    "6. 绂佹灞曠ず鍔ㄤ綔杩囩▼銆佽繍鍔ㄨ建杩广€佸彴璇嶆枃瀛椼€佸鐧芥皵娉°€佹极鐢绘嫙澹拌瘝銆佹儏缁鏄庢枃瀛椼€俓n"
    "   宸︽爮鍒嗛暅鐢婚潰涓嶈鐢讳汉鐗╄繍鍔ㄦ柟鍚戠澶达紱鍙虫爮鏈轰綅鍥惧彧鍏佽鍑虹幇鎽勫奖鏈烘湞鍚戙€佽绾胯酱绾垮拰瑙嗛噹鑼冨洿绠ご銆俓n"
    "7. 蹇呴』涓ユ牸鏈嶄粠闀滃ご瀵兼紨鐨勯暅澶寸紪鍙枫€佹媿鎽勪富浣撱€侀暅澶?鏅埆/鏈轰綅銆佸垏闀滅偣鍜岃繛缁€э紝涓嶅緱鏂板鍓ф儏銆佷汉鐗┿€侀亾鍏锋垨绌洪棿銆俓n"
    "8. 鍦烘櫙鍙傝€冨浘閲岀殑鍥哄畾瀹跺叿鍜岀┖闂撮敋鐐逛綅缃繀椤婚攣姝伙紝渚嬪鑼跺嚑銆佹矙鍙戙€佺獥鎴枫€侀棬銆佸湴姣€佸簥銆佹煖瀛愮瓑锛?"
    "涓嶅緱涓轰簡鏋勫浘渚垮埄绉诲姩銆佹浛鎹㈡垨鏂板缓杩欎簺鐗╀綋銆俓n"
    "9. 濡傛灉闀滃ご闇€瑕佺壒鍐欓亾鍏凤紝鍙兘浠庡弬鑰冨満鏅師浣嶇疆杩涜瑁佸垏銆佹帹杩戞垨鎹㈡満浣嶆媿鎽勶紝涓嶈兘鎶婇亾鍏锋尓鍒版梺杈瑰彴闈€佸簥澶存垨鏂颁綅缃€俓n"
    "10. 鍙傝€冨浘鍙敤浜庨攣瀹氫汉鐗╄劯銆佸彂鍨嬨€佹湇瑁呫€佸満鏅┖闂淬€佸厜绾裤€侀亾鍏峰瑙傚拰浣嶇疆鍏崇郴銆俓n"
    "11. 杈撳嚭蹇呴』鏄腑鏂囷紝瀛楁鍜岃鏄庨兘涓嶈浣跨敤鑻辨枃銆俓n"
    "12. 鐩爣鏄粰 Seedance 2.0 鎻愪緵棣栧抚閿氱偣鍜屾満浣嶆牳瀵瑰浘锛岃鍚庣画瑙嗛鎸夐甯у浘鍜岄暅澶村婕旀柟妗堢敓鎴愩€俓n"
)

_STORYBOARD_OUTPUT_CONTRACT = (
    "銆愬垎闀滄晠浜嬫澘杈撳嚭鍚堝悓銆慭n"
    "蹇呴』鐢熸垚涓€娈电粰鐢熷浘鎺ュ彛浣跨敤鐨勪腑鏂囨彁绀鸿瘝锛岀粨鏋勫涓嬶細\n\n"
    "绗竴琛岋細璇存槑杩欐槸涓€寮犵墖娈靛垎闀滄晠浜嬫澘锛屾槑纭啓鍑烘暣寮犲浘蹇呴』浣跨敤涓庤棰戜竴鑷寸殑鐢诲箙姣斾緥锛屼笉鍏佽鍋氭垚鏅€氶暱鍥炬垨妯珫姣斾緥閿欒鐨勬嫾鍥俱€俓n"
    "绗簩琛岋細璇存槑鍖呭惈澶氬皯涓暅澶磋锛屾寜闀滃ご缂栧彿浠庝笂鍒颁笅鎺掑垪锛涙瘡琛屽乏涓婅蹇呴』鏄剧ず涓枃缂栧彿锛氶暅澶?銆侀暅澶?銆侀暅澶?鈥︹€n"
    "鐗堝紡瑕佹眰锛氭瘡涓暅澶村崰涓€琛岋紝琛屽唴蹇呴』鏄笁鏍忕粨鏋勶細宸︽爮绾?55% 涓哄垎闀滈甯у浘锛屼腑鏍忕害 25% 涓洪暅澶村弬鏁板崱锛屽彸鏍忕害 20% 涓轰刊瑙嗘満浣嶅浘銆俓n"
    "缁熶竴瑕佹眰锛氬乏鏍忓彧鐢婚暅澶村紑濮嬬灛闂达紝涓嶇敾鍔ㄤ綔杩囩▼锛屼笉鍑虹幇鍙拌瘝鏂囧瓧銆佸鐧芥皵娉°€佸瓧骞曘€佽繍鍔ㄨ建杩广€佷汉鐗╄繍鍔ㄧ澶存垨瑙ｉ噴鎬ф枃瀛楋紱涓爮鍙厑璁哥煭鍙傛暟鏂囧瓧锛涘彸鏍忓彧鍏佽鏈轰綅鍥炬爣绛俱€佹憚褰辨満鏈濆悜鍜岃閲庤寖鍥淬€俓n"
    "姣忎釜闀滃ご琛屽繀椤诲啓娓咃細\n"
    "  - 闀滃ご缂栧彿锛屼互鍙婄敾闈腑鏄剧ず鐨勪腑鏂囪鏍囩锛屼緥濡傦細闀滃ご1\n"
    "  - 宸︽爮鍒嗛暅棣栧抚锛氳捣濮嬬珯浣嶃€佹媿鎽勪富浣撱€佹櫙鍒?鏈轰綅/瑙嗚銆佷汉鐗╄韩浣撴湞鍚戝拰瑙嗙嚎鏂瑰悜銆侀亾鍏蜂笌绌洪棿閿氱偣浣嶇疆\n"
    "  - 涓爮鍙傛暟鍗★細鏃堕暱銆侀暅澶翠换鍔°€佷富浣撱€佹櫙鍒€佹満浣嶃€佸姩浣滆捣鐐广€佸繀椤诲彲瑙佷俊鎭€佽繛缁€ч敋鐐筡n"
    "  - 鍙虫爮淇鏈轰綅鍥撅細CAM 鎽勫奖鏈轰笁瑙掑舰銆佷汉鐗╁僵鑹插渾鐐广€佸叧閿浐瀹氱墿绠€鍖栧潡銆佽绾胯酱绾裤€侀暅澶存湞鍚戠嚎銆丗OV 瑙嗛噹鎵囧舰銆佷汉鐗╃浉瀵硅窛绂籠n"
    "  - 鍥哄畾瀹跺叿浣嶇疆閿佸畾锛氭槑纭啓鍑鸿尪鍑犮€佹矙鍙戙€佺獥鎴枫€佸湴姣瓑鍏抽敭鐗╀綋蹇呴』淇濇寔鍙傝€冨満鏅腑鐨勭浉瀵逛綅缃紝鍙兘瑁佸垏鎴栨帹杩戯紝涓嶈兘鎼姩\n"
    "  - 涓庝笂涓€闀滅殑杩炵画鎬n\n"
    "Final line: clean director storyboard, horizontal shot rows, three aligned columns, clear shot numbers, right column is a simple camera plan, no dialogue text, no motion lines, no character movement arrows."
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _extract_shots_from_director_segment(director_segment: str) -> list[dict[str, str]]:
    """Parse shot YAML block into structured shot records."""

    # Find the positions of every shot id line in the segment.
    indices = [m.start() for m in re.finditer(r"(?m)^\s*-?\s*(?:shot_id|闀滃ご缂栧彿)\s*:", director_segment)]
    if not indices:
        return []

    shots: list[dict[str, str]] = []

    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(director_segment)
        block = director_segment[start:end]

        shot: dict[str, str] = {}
        for key in (
            "shot_id",
            "duration",
            "task",
            "main_subject",
            "supporting_subjects",
            "subject",
            "template_id",
            "template_level",
            "coverage_role",
            "shot",
            "action",
            "must_carry",
            "cut_point",
            "continuity",
            "continuity_anchor",
            "dialogue",
            "dialogue_coverage",
            "reaction_coverage",
        ):
            value = _yaml_line_field(block, key)
            if value:
                shot[key] = value
        if shot:
            shots.append(shot)

    return shots

def _extract_fragment_task_and_rhythm(director_segment: str) -> tuple[str, str]:
    """Pull fragment-level task and rhythm notes."""
    return (
        _yaml_line_field(director_segment, "fragment_task"),
        _yaml_line_field(director_segment, "rhythm"),
    )


def _format_shot_for_storyboard(shot: dict[str, str], index: int) -> str:
    """Convert one shot into a first-frame storyboard requirement."""
    shot_id = shot.get("shot_id") or f"镜头 {index + 1}"
    duration = shot.get("duration") or "4-6s"
    task = shot.get("task") or shot.get("coverage_role") or "镜头推进与关系承接"
    subject = shot.get("main_subject") or shot.get("subject") or "主角与关键人物"
    template_id = shot.get("template_id") or "未指定模板"
    template_level = shot.get("template_level") or shot.get("template_status") or "W1"
    coverage = shot.get("coverage_role") or shot.get("dialogue_coverage") or shot.get("reaction_coverage") or "关系延续"
    action = shot.get("action") or shot.get("must_carry") or "无复杂动作"
    continuity = shot.get("continuity") or shot.get("continuity_anchor") or "延续主镜头关系"
    cut_point = shot.get("cut_point") or "默认按拍序切换"

    return "\n".join([
        f"镜头 {shot_id} 首帧",
        f"- 时长：{duration}",
        f"- 任务：{task}",
        f"- 主体：{subject}",
        f"- 参考模板：{template_id}（{template_level}）",
        f"- 关系：{coverage}",
        f"- 动作与关系：{action}",
        f"- 连续性锚点：{continuity}",
        f"- 切点约束：{cut_point}",
    ])


def _frame_control_contract(shots: list[dict[str, str]]) -> str:
    """Summarize first/key/tail frame state without adding or reordering shots."""
    first = shots[0] if shots else {}
    last = shots[-1] if shots else {}
    key_changes = []
    for shot in shots:
        shot_id = shot.get("shot_id") or "shot"
        state_delta = shot.get("state_delta") or shot.get("action") or shot.get("must_carry") or "no new state"
        key_changes.append(f"    - {shot_id}: {state_delta}")
    return "\n".join(
        [
            "frame_control_contract:",
            f"  first_frame_state: {first.get('continuity') or first.get('tail_state') or first.get('action') or 'inherit planner entry state'}",
            "  keyframe_state_changes:",
            *(key_changes or ["    - none"]),
            f"  tailframe_state: {last.get('tail_state') or last.get('continuity') or last.get('tailframe_role') or 'inherit final shot state'}",
            f"  character_positions: {last.get('companion_visibility') or last.get('subject') or 'preserve current shot subjects'}",
            f"  prop_states: {last.get('must_carry') or last.get('continuity') or 'preserve prop ownership from shot_director'}",
            f"  gaze_direction: {last.get('action') or 'preserve visible attention direction'}",
            f"  hand_state: {last.get('tail_state') or last.get('continuity') or 'preserve visible hand/prop state'}",
            f"  door_or_vehicle_or_elevator_state: {last.get('continuity') or last.get('tail_state') or 'unchanged unless shot_director states otherwise'}",
            "  forbidden:",
            "    - add_new_shots",
            "    - reorder_shots",
            "    - add_new_camera_language",
        ]
    )

def _reference_usage_for_item(item: dict[str, Any]) -> str:
    """Describe how one image reference may influence the storyboard prompt."""
    role_text = " ".join(
        str(item.get(key) or "")
        for key in ("role", "type", "purpose", "name", "filename", "label", "description", "note")
    ).lower()

    if any(marker in role_text for marker in ("previous_segment_tail_frame", "tail_frame", "tailframe")):
        return "Previous segment tail frame: lock only inheritable character position, facing, posture, prop state, and visible spatial relation."
    if any(marker in role_text for marker in ("previous_segment_storyboard_crop", "last_storyboard_crop", "鍒嗛暅瑁佸垏")):
        return "Previous storyboard crop: use only as a secondary continuity reference for first-frame state."
    if any(marker in role_text for marker in ("annotated_scene_layout", "scene_layout_annotation", "scene_layout", "淇", "鏍囩偣", "绔欎綅")):
        return "Scene layout reference: lock initial positions, fixed objects, and baseline axis only; do not create motion paths."
    if any(marker in role_text for marker in ("character", "portrait", "浜虹墿", "瑙掕壊", "鏈嶈", "澶栬", "婕斿憳")):
        return "Character reference: lock appearance, hair, costume, identity consistency, and visible personal props only."
    if any(marker in role_text for marker in ("scene", "space", "location", "room", "鍦烘櫙", "绌洪棿", "鍦扮偣", "姣嶇増")):
        return "Scene reference: lock space, light direction, fixed furniture, main props, and relative positions only."
    return "Visual reference: lock only the explicitly marked appearance, space, or prop facts; do not add plot, characters, props, or locations."


def _previous_segment_tail_frame_b64(state: DirectorState) -> str:
    """Return a previous-segment tail frame image when the caller provided one."""
    for key in ("previous_segment_tail_frame", "previous_segment_tail_frame_b64", "tail_frame_b64"):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _has_previous_segment_tail_frame_reference(state: DirectorState) -> bool:
    """Return whether a tail-frame continuity reference is present in state."""
    if _previous_segment_tail_frame_b64(state):
        return True
    asset = state.get("previous_continuity_asset")
    if isinstance(asset, dict):
        source = str(asset.get("source") or "")
        if "tail_frame" in source:
            return True
    manifest = state.get("reference_image_manifest") or []
    for item in manifest:
        if not isinstance(item, dict):
            continue
        role_text = " ".join(str(item.get(key) or "") for key in ("role", "type", "purpose", "source"))
        if "previous_segment_tail_frame" in role_text or "tail_frame" in role_text or "tailframe" in role_text:
            return True
    return False


def _previous_segment_storyboard_crop_b64(state: DirectorState) -> str:
    """Return the previous segment's last storyboard-panel crop if available."""
    for key in (
        "previous_segment_last_storyboard_crop",
        "previous_segment_last_storyboard_crop_b64",
        "previous_segment_storyboard_crop",
        "previous_segment_storyboard_crop_b64",
    ):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _reference_images_for_storyboard(state: DirectorState) -> list[str]:
    """Return images in the exact order sent to the image-generation API."""
    images = list(state.get("reference_image_b64s") or [])
    tail_frame = _previous_segment_tail_frame_b64(state)
    storyboard_crop = _previous_segment_storyboard_crop_b64(state)
    if tail_frame:
        images.append(tail_frame)
    elif storyboard_crop:
        images.append(storyboard_crop)
    return images


def _line_field_by_names(block: str, names: tuple[str, ...]) -> str:
    pattern = "|".join(re.escape(name) for name in names)
    match = re.search(rf"(?m)^\s*-?\s*(?:{pattern})\s*:\s*(.+?)\s*$", block or "")
    return match.group(1).strip().strip("\"'") if match else ""


def _segment_scene_label(planner_segment: str) -> str:
    return _line_field_by_names(
        planner_segment,
        ("scene", "scene_id", "鍦烘櫙", "鍦烘櫙缂栧彿", "鍦烘櫙鍚嶇О", "鍦扮偣", "绌洪棿"),
    )


def _segment_exit_state(planner_segment: str) -> str:
    return _line_field_by_names(
        planner_segment,
        ("exit_state", "final_state", "tail_state_required"),
    )


def _normalise_scene_label(scene: str) -> str:
    return re.sub(r"\s+", "", scene or "").strip().lower()


def _tail_analysis_requests_reset(tail_frame_analysis: str) -> bool:
    text = tail_frame_analysis or ""
    return bool(
        re.search(r"(?im)^\s*mode\s*:\s*direct_cut\s*$", text)
        or re.search(r"(?im)^\s*must_reset_space\s*:\s*true\s*$", text)
    )


def _build_storyboard_continuity_notes(
    state: DirectorState,
    *,
    segment_index: int,
    planner_output: str,
    current_fragment_id: str,
) -> str:
    """Compile segment-to-segment continuity rules for storyboard prompts."""
    notes: list[str] = []
    planner_segment = _planner_segment_block(planner_output, segment_index, current_fragment_id)
    scene_label = _segment_scene_label(planner_segment)
    exit_state = _segment_exit_state(planner_segment)
    if scene_label:
        notes.append(f"current_scene: {scene_label}")
    if exit_state:
        notes.append(f"current_exit_state: {exit_state}")
    if segment_index > 1:
        previous_fragment_id = f"F{segment_index - 1:02d}"
        previous_planner_segment = _planner_segment_block(planner_output, segment_index - 1, previous_fragment_id)
        previous_scene = _segment_scene_label(previous_planner_segment)
        previous_exit = _segment_exit_state(previous_planner_segment)
        if previous_scene and scene_label and _normalise_scene_label(previous_scene) == _normalise_scene_label(scene_label) and previous_exit:
            notes.append(f"inherit_previous_tail_state: {previous_exit}")
    if _has_previous_segment_tail_frame_reference(state):
        notes.append("previous_tail_frame_reference: first-frame continuity only; do not add shots or rewrite script.")
    if _previous_segment_storyboard_crop_b64(state) and not _previous_segment_tail_frame_b64(state):
        notes.append("previous_storyboard_crop: secondary continuity reference only.")
    if not notes:
        return ""
    return "frame continuity notes:\n" + "\n".join(f"- {note}" for note in notes)

def _build_character_reference_notes(state: DirectorState) -> str:
    """Assemble character/scene reference notes from uploaded images."""
    manifest = [dict(item) if isinstance(item, dict) else {} for item in list(state.get("reference_image_manifest") or [])]
    api_images = _reference_images_for_storyboard(state)
    if not manifest and not api_images:
        return ""

    while len(manifest) < len(state.get("reference_image_b64s") or []):
        manifest.append({})

    tail_frame = _previous_segment_tail_frame_b64(state)
    storyboard_crop = _previous_segment_storyboard_crop_b64(state)
    if len(api_images) > len(manifest):
        if tail_frame:
            manifest.append(
                {
                    "label": f"@image{len(manifest) + 1}",
                    "filename": "previous_segment_tail_frame",
                    "purpose": "previous segment tail frame",
                    "role": "previous_segment_tail_frame",
                }
            )
        elif storyboard_crop:
            manifest.append(
                {
                    "label": f"@image{len(manifest) + 1}",
                    "filename": "previous_segment_last_storyboard_crop",
                    "purpose": "previous segment last storyboard crop",
                    "role": "previous_segment_storyboard_crop",
                }
            )

    notes: list[str] = ["Reference image usage rules: keep API input order."]
    for index, item in enumerate(manifest[:len(api_images) or len(manifest)], start=1):
        label = item.get("label") or f"@image{index}"
        filename = item.get("filename") or "unnamed_reference"
        purpose = item.get("purpose") or item.get("role") or item.get("type") or "visual_reference"
        desc = item.get("description") or item.get("note") or ""
        suffix = f"; note: {desc}" if desc else ""
        usage = _reference_usage_for_item(item)
        notes.append(f"- reference_image_{index}: api_order={index}; label={label}; filename={filename}; usage={usage}; purpose={purpose}{suffix}")
    notes.append(
        "Global rule: character references lock identity and wardrobe only; scene references lock space and fixed anchors only; "
        "previous tail frames lock continuity state. Do not move or redesign fixed anchors such as sofa, table, window, door, rug, or vehicle. "
        "Do not copy action from reference images and do not add shots."
    )
    return "\n".join(notes)


def _segment_block(text: str, segment_index: int, fragment_id: str | None = None) -> str:
    """Extract the YAML block for a single fragment by F{segment_index:02d}."""
    selected_fragment_id = fragment_id or _fragment_id_for_segment_index([], segment_index)
    return _segment_block_by_fragment_id(text, selected_fragment_id)


def _planner_segment_block(planner_output: str, segment_index: int, fragment_id: str | None = None) -> str:
    """Extract planner segment for additional context."""
    return _segment_block(planner_output, segment_index, fragment_id)


def _current_script_excerpt(
    state: DirectorState,
    segment_index: int,
    fragment_id: str,
) -> str:
    """Extract the current segment's enhanced script excerpt when available."""
    script = str(
        state.get("enhanced_script")
        or state.get("script")
        or state.get("original_script")
        or ""
    ).strip()
    if not script:
        return ""

    marked_block = _segment_block_by_fragment_id(script, fragment_id)
    if marked_block:
        return _truncate_for_prompt(marked_block, 1200)

    segment_patterns = (
        rf"(?:鐗囨缂栧彿\s*[锛?]\s*{re.escape(fragment_id)})",
        rf"(?:鐗囨\s*{segment_index}\b)",
        rf"(?:绗琝s*{segment_index}\s*娈?",
    )
    start_re = "|".join(segment_patterns)
    next_re = r"(?:鐗囨缂栧彿\s*[锛?]\s*F\d{2,}|鐗囨\s*\d+\b|绗琝s*\d+\s*娈?"
    match = re.search(rf"(?ms)(?:^|\n)\s*(?:{start_re}).*?(?=\n\s*{next_re}|\Z)", script)
    if match:
        return _truncate_for_prompt(match.group(0).strip(), 1200)

    return _truncate_for_prompt(script, 1200)


# ---------------------------------------------------------------------------
# LLM prompt builders
# ---------------------------------------------------------------------------
def _build_storyboard_user_prompt(
    *,
    segment_index: int,
    segment_name: str,
    fragment_task: str,
    rhythm: str,
    shots: list[dict[str, str]],
    planner_context: str,
    script_context: str,
    reference_notes: str,
    aspect_ratio: str,
    continuity_notes: str = "",
) -> str:
    """Construct the prompt that turns shot design into storyboard frame states."""
    lines: list[str] = [
        f"Build storyboard frame-control prompt for segment {segment_index}: {segment_name}",
        "",
        f"video_aspect_ratio: {aspect_ratio}",
        f"storyboard_canvas_requirement: keep the complete storyboard in {aspect_ratio}; do not change aspect ratio.",
        "",
    ]

    if fragment_task:
        lines.append(f"segment_task: {fragment_task}")
    if rhythm:
        lines.append(f"rhythm_context: {rhythm}")
    lines.append("")

    if planner_context:
        lines.append("planner_generation_unit_context:")
        lines.append(_truncate_for_prompt(planner_context, 600))
        lines.append("")

    if script_context:
        lines.append("current_script_excerpt:")
        lines.append(_truncate_for_prompt(script_context, 900))
        lines.append("Use this only for character, prop, dialogue fact, and action start-state checks; keep shot order from shot_director.")
        lines.append("")

    lines.append(f"shot_director_locked_shot_list: count={len(shots)}")
    for idx, shot in enumerate(shots):
        lines.append(_format_shot_for_storyboard(shot, idx))
    lines.append("")

    if reference_notes:
        lines.append(reference_notes)
        lines.append("")

    if continuity_notes:
        lines.append(continuity_notes)
        lines.append("")

    lines.append(_STORYBOARD_OUTPUT_CONTRACT)
    lines.append("")
    lines.append(
        "Output only the final prompt for the image model. It must describe first_frame_state, keyframe_state_changes, "
        "tailframe_state, character_positions, prop_states, gaze_direction, hand_state, and door_or_vehicle_or_elevator_state. "
        "Do not add shots, reorder shots, invent new camera positions, add subtitles, add readable text, or add explanatory overlays."
    )

    return "\n".join(lines)
# ---------------------------------------------------------------------------
# Image generation helpers
# ---------------------------------------------------------------------------
def _call_image_generation_api(
    prompt: str,
    images_base64: list[str] | None = None,
    agent_name: str = "storyboard_designer",
) -> str | None:
    """Call the image generation API via the LLM layer (gpt-image-2 / compatible).

    Returns a data URI or file path string, or None on failure.
    """
    # The prompt is already the image description; the system message only locks
    # the target format for compatible image-generation backends.
    system = (
        "Render a professional director storyboard from the provided prompt. "
        "Keep the requested video aspect ratio exactly. Each shot occupies one row. "
        "Show only locked first-frame/key-frame/tail-frame state, camera plan, and continuity anchors. "
        "Do not add subtitles, readable text, speech bubbles, motion arrows, action trails, overlays, or extra explanatory text."
    )

    try:
        # Pass the prompt as user content; image models often ignore system prompt
        # but we keep it for compatibility.  If images_base64 are provided, include
        # them as reference images for visual consistency.
        result = call_llm(
            system_prompt=system,
            user_prompt=prompt,
            images_base64=images_base64,
            temperature=0.4,
            agent_name=agent_name,
        )
    except Exception as exc:
        return f"[image_generation_failed: {exc}]"

    # The result may be a markdown image link, a raw URL, or plain text.
    # Try to extract a URL / data URI.
    url_match = re.search(r"https?://\S+\.(?:png|jpg|jpeg|webp|gif)", result, re.IGNORECASE)
    if url_match:
        return url_match.group(0)

    data_uri_match = re.search(r"data:image/\w+;base64,[A-Za-z0-9+/=]+", result)
    if data_uri_match:
        return data_uri_match.group(0)

    # If the model returned raw base64 without data URI prefix, wrap it.
    stripped = result.strip()
    if re.fullmatch(r"[A-Za-z0-9+/=]+", stripped):
        return f"data:image/png;base64,{stripped}"

    return result.strip()


def _save_storyboard_image(
    data: str,
    segment_index: int,
    session_id: str,
    candidate_index: int | None = None,
) -> str:
    """Save the generated storyboard image to disk and return its path.

    *data* may be:
      - a file path
      - a data URI (data:image/...;base64,...)
      - a raw URL
    """
    output_dir = os.path.join(OUTPUT_DIR, "sessions", session_id, "storyboards")
    os.makedirs(output_dir, exist_ok=True)
    suffix = f"_cand{candidate_index:02d}" if candidate_index else ""
    filename = f"storyboard_seg{segment_index:02d}{suffix}.png"
    filepath = os.path.join(output_dir, filename)

    # If it's already a local file path, just return it.
    if os.path.exists(data):
        return data

    # If it's a data URI, decode and save.
    if data.startswith("data:"):
        header, _, b64 = data.partition(",")
        try:
            raw = base64.b64decode(b64)
            with open(filepath, "wb") as f:
                f.write(raw)
            return filepath
        except Exception:
            pass

    # If it's a URL, download it.
    if data.startswith("http"):
        try:
            import httpx

            with httpx.Client(timeout=60.0) as client:
                resp = client.get(data)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                return filepath
        except Exception:
            pass

    # Fallback: write whatever text we got as a placeholder text file so the
    # pipeline does not crash.
    txt_path = filepath.replace(".png", ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(data)
    return txt_path


# ---------------------------------------------------------------------------
# Public node
# ---------------------------------------------------------------------------
def storyboard_designer_node(state: DirectorState) -> DirectorState:
    """Generate a storyboard flowchart for the CURRENT segment.

    This node is designed to run **after** shot_director and **before**
    wait_for_segment_request, so that every segment gets its own visual
    storyboard before entering the prompt-compilation phase.

    State contract:
      - active_segment_index (or current_segment_index) tells us which segment
      - agent_outputs["shot_director"] holds the full shot-director YAML
      - agent_outputs["story_planner"] holds the full planner YAML
      - reference_image_b64s / reference_image_manifest provide visual refs
      - aspect_ratio is used to hint panel layout

    Writes back:
      - agent_outputs["storyboard_prompt_seg{N}"]  鈫?the image prompt text

    Image generation is intentionally separate: the UI lets the user review the
    prompt first, then explicitly call the image API.
    """
    segment_index = int(
        state.get("active_segment_index")
        or state.get("current_segment_index")
        or 1
    )
    total_segments = int(state.get("total_segments") or 1)
    outputs = _agent_outputs(state)
    segment_names = state.get("segment_names") or []
    current_fragment_id = _fragment_id_for_segment_index(segment_names, segment_index)

    # ------------------------------------------------------------------
    # 1. Extract segment-level assets
    # ------------------------------------------------------------------
    director_output = outputs.get("shot_director", "")
    director_segment = _segment_block(director_output, segment_index, current_fragment_id)

    if not director_segment:
        # If shot_director hasn't produced this segment yet, skip silently.
        return _persist_update(
            state,
            {
                "message": f"Storyboard prompt skipped: segment {segment_index} has no shot_director output.",
            },
        )

    shots = _extract_shots_from_director_segment(director_segment)
    if not shots:
        return _persist_update(
            state,
            {
                "message": f"Storyboard prompt skipped: segment {segment_index} has no recognizable shot list.",
            },
        )

    fragment_task, rhythm = _extract_fragment_task_and_rhythm(director_segment)
    planner_output = outputs.get("story_planner", "")
    planner_context = _planner_segment_block(planner_output, segment_index, current_fragment_id)
    script_context = _current_script_excerpt(state, segment_index, current_fragment_id)
    reference_notes = _build_character_reference_notes(state)
    continuity_notes = _build_storyboard_continuity_notes(
        state,
        segment_index=segment_index,
        planner_output=planner_output,
        current_fragment_id=current_fragment_id,
    )
    aspect_ratio = str(state.get("aspect_ratio") or "16:9")

    segment_name = (
        segment_names[segment_index - 1]
        if 0 <= segment_index - 1 < len(segment_names)
        else f"Segment {segment_index}"
    )

    # ------------------------------------------------------------------
    # 2. Build user prompt and call LLM to generate the image-gen prompt
    # ------------------------------------------------------------------
    user_prompt = _build_storyboard_user_prompt(
        segment_index=segment_index,
        segment_name=segment_name,
        fragment_task=fragment_task,
        rhythm=rhythm,
        shots=shots,
        planner_context=planner_context,
        script_context=script_context,
        reference_notes=reference_notes,
        aspect_ratio=aspect_ratio,
        continuity_notes=continuity_notes,
    )

    try:
        storyboard_prompt = call_llm(
            system_prompt=_STORYBOARD_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            images_base64=None,  # text-only prompt generation
            temperature=0.3,
            agent_name="storyboard_prompt_designer",
        )
    except Exception as exc:
        raise RuntimeError(f"storyboard prompt model call failed: {exc}") from exc

    # Clean up the prompt 鈥?strip fences if the LLM ignored instructions.
    storyboard_prompt = re.sub(r"^```(?:\w+)?\n?|\n?```$", "", storyboard_prompt.strip()).strip()

    prompt_key = f"storyboard_prompt_seg{segment_index:02d}"

    updated_outputs = dict(outputs)
    updated_outputs[prompt_key] = storyboard_prompt
    updated_outputs[f"frame_control_contract_seg{segment_index:02d}"] = _frame_control_contract(shots)

    return _persist_update(
        state,
        {
            "agent_outputs": updated_outputs,
            "message": f"Storyboard prompt generated for segment {segment_index}/{total_segments}; review before image generation.",
        },
    )


def generate_storyboard_image_for_segment(
    state: DirectorState,
    segment_index: int | None = None,
    candidate_index: int | None = None,
) -> dict[str, str]:
    """Generate the storyboard image from an already-reviewed prompt."""
    selected_index = int(
        segment_index
        or state.get("active_segment_index")
        or state.get("current_segment_index")
        or 1
    )
    outputs = _agent_outputs(state)
    prompt = (
        outputs.get(f"storyboard_prompt_seg{selected_index:02d}")
        or outputs.get(f"storyboard_prompt_seg{selected_index}")
        or outputs.get("storyboard_designer")
        or ""
    ).strip()
    if not prompt:
        raise RuntimeError(f"Segment {selected_index} has no storyboard prompt; cannot generate image.")

    reference_b64s = _reference_images_for_storyboard(state)
    image_result = _call_image_generation_api(
        prompt=prompt,
        images_base64=reference_b64s if reference_b64s else None,
        agent_name="storyboard_designer",
    )
    if not image_result or image_result.startswith("["):
        raise RuntimeError(image_result or "image generation API returned no image.")

    from ..request_context import request_session_id

    session_id = request_session_id.get("local")
    if candidate_index is None:
        image_path_or_uri = _save_storyboard_image(image_result, selected_index, session_id)
    else:
        image_path_or_uri = _save_storyboard_image(
            image_result,
            selected_index,
            session_id,
            candidate_index=candidate_index,
        )

    image_key = f"storyboard_image_seg{selected_index:02d}"
    updated_outputs = dict(outputs)
    updated_outputs[image_key] = image_path_or_uri

    storyboard_images = dict(state.get("storyboard_images_by_segment") or {})
    storyboard_images[str(selected_index)] = image_path_or_uri

    _persist_update(
        state,
        {
            "agent_outputs": updated_outputs,
            "storyboard_images_by_segment": storyboard_images,
            "message": f"鍒嗛暅棣栧抚鍥剧墖宸茬敓鎴愶紙绗?{selected_index} 娈碉級 鈫?{image_path_or_uri}",
        },
    )
    return {
        "prompt": prompt,
        "image_path": image_path_or_uri,
    }


# ---------------------------------------------------------------------------
# Standalone helper (for CLI / testing)
# ---------------------------------------------------------------------------
def generate_storyboard_for_segment(
    state: DirectorState,
    segment_index: int | None = None,
) -> dict[str, str]:
    """Non-graph helper: generate a storyboard prompt for a specific segment.

    Returns a dict with keys:
      - prompt: the image prompt text
      - image_path: existing saved image path when one is already present
    """
    if segment_index is not None:
        state = dict(state)
        state["active_segment_index"] = segment_index

    result = storyboard_designer_node(state)
    seg = str(segment_index or state.get("active_segment_index", 1))
    outputs = result.get("agent_outputs") or {}
    return {
        "prompt": outputs.get(f"storyboard_prompt_seg{int(seg):02d}", ""),
        "image_path": (result.get("storyboard_images_by_segment") or {}).get(seg, ""),
    }


