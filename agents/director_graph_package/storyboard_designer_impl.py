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
    "你是分镜首帧图设计师，服务于 Seedance 2.0 视频生成流程。\n"
    "你的任务不是重新导演剧情，也不是画动作漫画，而是把镜头导演给出的每个镜头，"
    "转换成该镜头开始瞬间的静止首帧画面提示词。\n\n"
    "硬规则：\n"
    "1. 只输出最终给生图接口使用的提示词，不要解释，不要代码块。\n"
    "2. 一个片段输出一张分镜首帧图；整张图的宽高比例必须与视频画幅完全一致，9:16 就生成竖版 9:16，16:9 就生成横版 16:9。\n"
    "3. 图中每个格子对应一个镜头编号，必须在格子左上角写清“镜头1 / 镜头2 / 镜头3...”这类中文编号。\n"
    "4. 每格只展示该镜头开始时的静止状态：人物位置、身体朝向、视线方向、道具位置、场景锚点、景别和机位。\n"
    "5. 禁止展示动作过程、运动轨迹、台词文字、对白气泡、漫画拟声词、情绪说明文字。\n"
    "   也不要在画面里画人物运动方向箭头；运动方向只保留在文字说明里供视频生成理解。\n"
    "6. 必须严格服从镜头导演的镜头编号、拍摄主体、镜头/景别/机位、切镜点和连续性，不得新增剧情、人物、道具或空间。\n"
    "7. 场景参考图里的固定家具和空间锚点位置必须锁死，例如茶几、沙发、窗户、门、地毯、床、柜子等；"
    "不得为了构图便利移动、替换或新建这些物体。\n"
    "8. 如果镜头需要特写道具，只能从参考场景原位置进行裁切、推近或换机位拍摄，不能把道具挪到旁边台面、床头或新位置。\n"
    "9. 参考图只用于锁定人物脸、发型、服装、场景空间、光线、道具外观和位置关系。\n"
    "10. 输出必须是中文，字段和说明都不要使用英文。\n"
    "11. 目标是给 Seedance 2.0 提供首帧锚点，让后续视频按首帧图和镜头导演方案生成。\n"
)

_STORYBOARD_OUTPUT_CONTRACT = (
    "【分镜首帧图输出合同】\n"
    "必须生成一段给生图接口使用的中文提示词，结构如下：\n\n"
    "第一行：说明这是一张片段分镜首帧图，明确写出整张图必须使用与视频一致的画幅比例，不允许做成普通长图或横竖比例错误的拼图。\n"
    "第二行：说明包含多少个镜头格子，按镜头编号顺序排列；每个格子左上角必须显示中文编号：镜头1、镜头2、镜头3……\n"
    "统一要求：所有格子只画镜头开始瞬间，不画动作过程，不出现台词文字、对白气泡、字幕、运动轨迹、人物运动箭头或解释性文字。\n"
    "每个镜头格子必须写清：\n"
    "  - 镜头编号，以及画面中显示的中文格子标签，例如：镜头1\n"
    "  - 起始站位\n"
    "  - 拍摄主体\n"
    "  - 景别/机位/视角\n"
    "  - 人物身体朝向和视线方向\n"
    "  - 道具与空间锚点位置\n"
    "  - 固定家具位置锁定：明确写出茶几、沙发、窗户、地毯等关键物体必须保持参考场景中的相对位置，只能裁切或推近，不能搬动\n"
    "  - 与上一镜的连续性\n\n"
    "最后一行：统一画面风格，要求干净分镜图、清晰分格、格子编号清楚、弱化装饰、无对白字、无动作线、无人物运动箭头，适合给 Seedance 2.0 当首帧参考。"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _extract_shots_from_director_segment(director_segment: str) -> list[dict[str, str]]:
    """Parse shot YAML block into structured shot records.

    Splits on ``shot_id:`` boundaries and extracts each shot's fields via
    line-based regex so that YAML list markers ``-`` do not confuse the
    parser.
    """
    shots: list[dict[str, str]] = []

    # Find the positions of every shot id line in the segment.
    indices = [m.start() for m in re.finditer(r"(?m)^\s*-?\s*(?:shot_id|镜头编号)\s*:", director_segment)]
    if not indices:
        return shots

    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(director_segment)
        block = director_segment[start:end]

        shot: dict[str, str] = {}
        for key in ("shot_id", "duration", "task", "subject", "camera", "size",
                    "shot", "type", "action", "dialogue", "must_carry",
                    "cut_point", "continuity"):
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
    shot_id = shot.get("shot_id") or f"第{index + 1}镜"
    duration = shot.get("duration") or "按镜头导演方案"
    task = shot.get("task") or "承接镜头导演任务"
    subject = shot.get("subject") or "按镜头导演指定主体"
    camera_bits = [shot.get("shot", ""), shot.get("size", ""), shot.get("camera", "")]
    camera = " / ".join(bit for bit in camera_bits if bit) or "按镜头导演指定镜头"
    action = shot.get("action") or "根据镜头任务判断起始状态"
    must_carry = shot.get("must_carry") or "镜头导演要求的关键信息"
    cut_point = shot.get("cut_point") or "仅用于理解镜头顺序"
    continuity = shot.get("continuity") or "继承上一镜尾帧空间关系"

    return "\n".join(
        [
            f"镜头 {shot_id} 首帧格：",
            f"- 时长参考：{duration}",
            f"- 镜头任务：{task}",
            f"- 拍摄主体：{subject}",
            f"- 景别/机位/视角：{camera}",
            "- 首帧状态：只画该镜头开始的一瞬间，人物已经处在起始站位；不画完整动作过程。",
            f"- 原动作参考：{action}；只用于判断首帧起点和后续运动方向，不在图里生成动作轨迹、动作线、箭头或过程画面。",
            f"- 必须可见：{must_carry}",
            f"- 连续性锚点：{continuity}",
            "- 固定空间锁定：茶几、沙发、窗户、门、地毯、床、柜子等固定家具必须保持参考场景中的原始相对位置；近景和特写只能通过裁切、推近或换机位实现，不得把道具移动到旁边台面、床头或新位置。",
            f"- 切镜点参考：{cut_point}；只用于镜头顺序理解，不在画面中写字或画箭头。",
        ]
    )


def _build_character_reference_notes(state: DirectorState) -> str:
    """Assemble character/scene reference notes from uploaded images."""
    manifest = state.get("reference_image_manifest") or []
    if not manifest:
        return ""

    notes: list[str] = ["【参考图使用规则】"]
    for index, item in enumerate(manifest, start=1):
        label = item.get("label") or f"@图片{index}"
        filename = item.get("filename") or "未命名参考图"
        purpose = item.get("purpose") or "视觉参考"
        desc = item.get("description") or item.get("note") or ""
        suffix = f"：{desc}" if desc else ""
        notes.append(f"- {label}（{filename}）：{purpose}{suffix}")
    notes.append(
        "人物参考图只用于锁定脸型、五官、发型、服装和身份一致性；"
        "场景参考图用于强制锁定空间结构、光线方向、色调、固定家具和主要道具的相对位置；"
        "茶几、沙发、窗户、门、地毯等固定空间锚点不得移动、替换或重新摆放；"
        "多人位置图只用于锁定站位关系和空间轴线；不得照抄参考图里的动作。"
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
        rf"(?:片段编号\s*[：:]\s*{re.escape(fragment_id)})",
        rf"(?:片段\s*{segment_index}\b)",
        rf"(?:第\s*{segment_index}\s*段)",
    )
    start_re = "|".join(segment_patterns)
    next_re = r"(?:片段编号\s*[：:]\s*F\d{2,}|片段\s*\d+\b|第\s*\d+\s*段)"
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
) -> str:
    """Construct the prompt that turns shot design into first-frame panels."""
    lines: list[str] = [
        f"生成片段 {segment_index} 的分镜首帧图提示词：{segment_name}",
        "",
        f"【视频画幅】{aspect_ratio}",
        f"【分镜图画幅硬要求】整张分镜首帧图必须严格使用 {aspect_ratio} 比例，不能改变成其他比例；格子只能在这个画幅内部排布。",
        "",
    ]

    if fragment_task:
        lines.append(f"【片段任务】{fragment_task}")
    if rhythm:
        lines.append(f"【节奏】{rhythm}")
    lines.append("")

    if planner_context:
        lines.append("【拆片规划上下文】")
        lines.append(_truncate_for_prompt(planner_context, 600))
        lines.append("")

    if script_context:
        lines.append("【当前片段增强剧本参考】")
        lines.append(_truncate_for_prompt(script_context, 900))
        lines.append("使用规则：只用它核对人物、道具、台词事实和动作起点；镜头排布仍以镜头导演为准。")
        lines.append("")

    lines.append(f"【镜头导演首帧格清单，共 {len(shots)} 镜】")
    for idx, shot in enumerate(shots):
        lines.append(_format_shot_for_storyboard(shot, idx))
    lines.append("")

    if reference_notes:
        lines.append(reference_notes)
        lines.append("")

    lines.append(_STORYBOARD_OUTPUT_CONTRACT)
    lines.append("")
    lines.append(
        "现在只输出最终给生图接口使用的一段中文提示词。"
        f"必须是一张 {aspect_ratio} 比例的图，包含本片段全部镜头首帧格子；"
        "每个格子左上角必须有“镜头1 / 镜头2 / 镜头3...”编号；每格只画静止起始状态，"
        "不出现台词文字、字幕、对白气泡、动作线、运动轨迹、人物运动箭头或解释性文字；"
        "每格都要写清固定家具位置锁定，尤其茶几、沙发、窗户和地毯必须保持参考场景里的相对位置，"
        "不能出现“旁边台面”“床头边缘”“另一个桌面”等会改变空间位置的替代说法。"
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
        "你是分镜首帧图生成模型。请把下面的中文提示词渲染成一张专业分镜首帧图："
        "一段一张图，整张图必须严格遵守提示词写明的视频画幅比例。"
        "每个格子对应一个镜头编号，并且必须在格子左上角写清“镜头1 / 镜头2 / 镜头3...”。"
        "只画镜头开始瞬间的静止状态。"
        "场景参考图中的固定家具和空间锚点必须保持原始相对位置；近景只能裁切或推近，不得移动茶几、沙发、窗户、地毯等固定物。"
        "不要生成台词文字、对白气泡、字幕、动作线、运动轨迹、人物运动箭头或解释性文字。"
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
        return f"[生图失败：{exc}]"

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
) -> str:
    """Save the generated storyboard image to disk and return its path.

    *data* may be:
      - a file path
      - a data URI (data:image/...;base64,...)
      - a raw URL
    """
    output_dir = os.path.join(OUTPUT_DIR, "sessions", session_id, "storyboards")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"storyboard_seg{segment_index:02d}.png"
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
      - agent_outputs["storyboard_prompt_seg{N}"]  → the image prompt text

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
                "message": (
                    f"分镜首帧图已跳过：第 {segment_index} 段还没有镜头导演输出。"
                ),
            },
        )

    shots = _extract_shots_from_director_segment(director_segment)
    if not shots:
        return _persist_update(
            state,
            {
                "message": (
                    f"分镜首帧图已跳过：第 {segment_index} 段没有可识别的镜头列表。"
                ),
            },
        )

    fragment_task, rhythm = _extract_fragment_task_and_rhythm(director_segment)
    planner_output = outputs.get("story_planner", "")
    planner_context = _planner_segment_block(planner_output, segment_index, current_fragment_id)
    script_context = _current_script_excerpt(state, segment_index, current_fragment_id)
    reference_notes = _build_character_reference_notes(state)
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
    )

    storyboard_prompt = call_llm(
        system_prompt=_STORYBOARD_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images_base64=None,  # text-only prompt generation
        temperature=0.3,
        agent_name="storyboard_prompt_designer",
    )

    # Clean up the prompt — strip fences if the LLM ignored instructions.
    storyboard_prompt = re.sub(r"^```(?:\w+)?\n?|\n?```$", "", storyboard_prompt.strip()).strip()

    prompt_key = f"storyboard_prompt_seg{segment_index:02d}"

    updated_outputs = dict(outputs)
    updated_outputs[prompt_key] = storyboard_prompt

    return _persist_update(
        state,
        {
            "agent_outputs": updated_outputs,
            "message": (
                f"分镜首帧图提示词已生成（第 {segment_index}/{total_segments} 段），"
                "请审核后再手动生成图片。"
            ),
        },
    )


def generate_storyboard_image_for_segment(
    state: DirectorState,
    segment_index: int | None = None,
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
        raise RuntimeError(f"第 {selected_index} 段还没有分镜首帧图提示词，无法生图。")

    reference_b64s = state.get("reference_image_b64s") or []
    image_result = _call_image_generation_api(
        prompt=prompt,
        images_base64=reference_b64s if reference_b64s else None,
        agent_name="storyboard_designer",
    )
    if not image_result or image_result.startswith("["):
        raise RuntimeError(image_result or "生图接口没有返回图片。")

    from ..request_context import request_session_id

    session_id = request_session_id.get("local")
    image_path_or_uri = _save_storyboard_image(image_result, selected_index, session_id)

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
            "message": f"分镜首帧图片已生成（第 {selected_index} 段） → {image_path_or_uri}",
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
