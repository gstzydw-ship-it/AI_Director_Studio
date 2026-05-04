"""Storyboard flowchart designer implementation.

Generates professional storyboard sketch prompts for each segment using
gpt-image-2 (or compatible image generation API). The designer takes:
- Shot director output for the current segment
- Character/scene reference images
- Story planner fragment context

and produces a structured visual storyboard prompt that can be sent to
an image generation API to render a professional storyboard flowchart
on a single image.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

from .helpers import _extract_fragment_id, _extract_yaml_sections, _truncate_for_prompt
from .llm import call_llm, resolve_llm_settings
from .state_store import _agent_outputs, _persist_update
from .types import DirectorState, OUTPUT_DIR


# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------
_STORYBOARD_SYSTEM_PROMPT = (
    "You are a professional storyboard flowchart prompt engineer specializing in AI video generation pipelines.\n"
    "Your task is to convert a segment's shot-by-shot director design into a structured, "
    "visually-grounded storyboard sketch prompt that can be rendered by an image generation API "
    "(gpt-image-2 / DALL-E 3 / GPT-Image-1).\n\n"
    "Rules:\n"
    "1. You MUST output ONLY the final image-generation prompt text. No markdown code fences, no explanations.\n"
    "2. The prompt must describe a SINGLE cohesive storyboard sheet image containing all shots in sequence.\n"
    "3. Preserve every shot's: shot number, duration, framing (shot size), camera angle / height, movement, "
    "subject action, and emotional beat.\n"
    "4. Include spatial layout instructions: panel grid, arrows indicating camera movement, cut markers.\n"
    "5. Inject character appearance and scene reference details so the image model can draw consistent figures.\n"
    "6. Use cinematic, visual vocabulary (not internal jargon like 'coverage_role' or 'cut_reason').\n"
    "7. If reference images are provided, instruct the image model to match those character designs, "
    "costumes, and scene aesthetics.\n"
    "8. The output must be in English (image models perform best with English prompts) unless the user "
    "explicitly requests another language.\n"
    "9. Keep the prompt under 4000 characters when possible; compress repetitive framing info into patterns.\n"
)

_STORYBOARD_OUTPUT_CONTRACT = (
    "【Storyboard Prompt Output Contract】\n"
    "You must produce a single text block with this structure:\n\n"
    "Line 1: A header sentence describing the overall composition.\n"
    "Line 2+: Panel-by-panel descriptions, each containing:\n"
    "  - Panel number and duration\n"
    "  - Shot size (Extreme Wide / Wide / Medium / Close-Up / Extreme Close-Up)\n"
    "  - Camera angle and height (low-angle, eye-level, high-angle, Dutch, POV, over-shoulder)\n"
    "  - Movement (static, push-in, pull-out, pan left/right, tilt up/down, dolly in/out, handheld)\n"
    "  - Subject framing and action\n"
    "  - Lighting / mood note\n"
    "  - Cut transition to next panel (hard cut, match cut, dissolve, etc.)\n\n"
    "Final line: Overall style instructions (sketch style, ink lines, gray wash, storyboard paper texture, "
    "annotated camera arrows, duration labels, aspect-ratio indicators).\n"
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

    # Find the positions of every ``shot_id:`` line in the segment.
    indices = [m.start() for m in re.finditer(r"(?m)^\s*-?\s*shot_id\s*:", director_segment)]
    if not indices:
        return shots

    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(director_segment)
        block = director_segment[start:end]

        shot: dict[str, str] = {}
        for key in ("shot_id", "duration", "task", "subject", "camera", "size",
                    "action", "dialogue", "must_carry", "cut_point", "continuity"):
            m = re.search(rf"(?m)^\s*-?\s*{key}\s*:\s*(.+)$", block)
            if m:
                shot[key] = m.group(1).strip().strip('"').strip("'")
        if shot:
            shots.append(shot)

    return shots


def _extract_fragment_task_and_rhythm(director_segment: str) -> tuple[str, str]:
    """Pull fragment-level task and rhythm notes."""
    task_match = re.search(r"(?m)^\s*fragment_task\s*:\s*(.+)$", director_segment)
    rhythm_match = re.search(r"(?m)^\s*rhythm\s*:\s*(.+)$", director_segment)
    return (
        (task_match.group(1).strip().strip('"').strip("'") if task_match else ""),
        (rhythm_match.group(1).strip().strip('"').strip("'") if rhythm_match else ""),
    )


def _format_shot_for_storyboard(shot: dict[str, str], index: int) -> str:
    """Convert a parsed shot dict into a compact visual description."""
    parts = [f"Panel {index + 1}"]
    dur = shot.get("duration", "?")
    parts.append(f"({dur}s)")

    size = shot.get("size", "")
    camera = shot.get("camera", "")
    action = shot.get("action", "")
    subject = shot.get("subject", "")
    cut = shot.get("cut_point", "")

    if size:
        parts.append(f"| {size}")
    if camera:
        parts.append(f"| cam: {camera}")
    if subject:
        parts.append(f"| subject: {subject}")
    if action:
        parts.append(f"| action: {action}")
    if cut:
        parts.append(f"| cut: {cut}")

    return " ".join(parts)


def _build_character_reference_notes(state: DirectorState) -> str:
    """Assemble character/scene reference notes from uploaded images."""
    manifest = state.get("reference_image_manifest") or []
    if not manifest:
        return ""

    notes: list[str] = ["[Reference Images Available]"]
    for item in manifest:
        desc = item.get("description") or item.get("filename") or "reference image"
        notes.append(f"- {desc}")
    notes.append(
        "Instructions for image model: Match character designs, costumes, hairstyles, "
        "and scene aesthetics shown in the reference images. Maintain visual consistency "
        "across all panels."
    )
    return "\n".join(notes)


def _segment_block(text: str, segment_index: int) -> str:
    """Extract the YAML block for a single fragment by F{segment_index:02d}."""
    fragment_id = f"F{segment_index:02d}"
    match = re.search(
        rf"(?m)(^\s*-?\s*fragment_id\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*fragment_id\s*:\s*[\"']?F\d+|\Z)",
        text,
    )
    return match.group(1).strip() if match else ""


def _planner_segment_block(planner_output: str, segment_index: int) -> str:
    """Extract planner segment for additional context."""
    return _segment_block(planner_output, segment_index)


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
    reference_notes: str,
    aspect_ratio: str,
) -> str:
    """Construct the user prompt sent to the LLM to generate the storyboard prompt."""
    lines: list[str] = [
        f"Generate a professional storyboard sketch prompt for segment {segment_index}: {segment_name}",
        "",
        f"Aspect Ratio: {aspect_ratio}",
        "",
    ]

    if fragment_task:
        lines.append(f"Fragment Task: {fragment_task}")
    if rhythm:
        lines.append(f"Rhythm: {rhythm}")
    lines.append("")

    if planner_context:
        lines.append("[Story Planner Context]")
        lines.append(_truncate_for_prompt(planner_context, 600))
        lines.append("")

    lines.append(f"[Shot List — {len(shots)} shots]")
    for idx, shot in enumerate(shots):
        lines.append(_format_shot_for_storyboard(shot, idx))
    lines.append("")

    if reference_notes:
        lines.append(reference_notes)
        lines.append("")

    lines.append(_STORYBOARD_OUTPUT_CONTRACT)
    lines.append("")
    lines.append(
        "Now generate the final English image-generation prompt. "
        "Remember: output ONLY the prompt text, no markdown fences, no extra commentary."
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
    # We use call_llm with a special system prompt tailored for image generation.
    # For gpt-image-2 and similar models, the prompt itself is the image description.
    system = (
        "You are an expert storyboard artist. Render the following description as a "
        "single professional storyboard flowchart image. Output the image directly."
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
        return f"[Image generation failed: {exc}]"

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
      - agent_outputs["storyboard_prompt_seg{N}"]  → the gpt-image-2 prompt text
      - agent_outputs["storyboard_image_seg{N}"]   → path/URI to generated image
      - storyboard_images_by_segment                → mapping in state root
    """
    segment_index = int(
        state.get("active_segment_index")
        or state.get("current_segment_index")
        or 1
    )
    total_segments = int(state.get("total_segments") or 1)
    outputs = _agent_outputs(state)

    # ------------------------------------------------------------------
    # 1. Extract segment-level assets
    # ------------------------------------------------------------------
    director_output = outputs.get("shot_director", "")
    director_segment = _segment_block(director_output, segment_index)

    if not director_segment:
        # If shot_director hasn't produced this segment yet, skip silently.
        return _persist_update(
            state,
            {
                "message": (
                    f"Storyboard designer skipped: no shot_director output for segment {segment_index}."
                ),
            },
        )

    shots = _extract_shots_from_director_segment(director_segment)
    if not shots:
        return _persist_update(
            state,
            {
                "message": (
                    f"Storyboard designer skipped: no parseable shots in segment {segment_index}."
                ),
            },
        )

    fragment_task, rhythm = _extract_fragment_task_and_rhythm(director_segment)
    planner_output = outputs.get("story_planner", "")
    planner_context = _planner_segment_block(planner_output, segment_index)
    reference_notes = _build_character_reference_notes(state)
    aspect_ratio = str(state.get("aspect_ratio") or "16:9")

    segment_names = state.get("segment_names") or []
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
        reference_notes=reference_notes,
        aspect_ratio=aspect_ratio,
    )

    storyboard_prompt = call_llm(
        system_prompt=_STORYBOARD_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images_base64=None,  # text-only prompt generation
        temperature=0.3,
        agent_name="storyboard_designer",
    )

    # Clean up the prompt — strip fences if the LLM ignored instructions.
    storyboard_prompt = re.sub(r"^```(?:\w+)?\n?|\n?```$", "", storyboard_prompt.strip()).strip()

    # ------------------------------------------------------------------
    # 3. Call image generation API with reference images (if any)
    # ------------------------------------------------------------------
    reference_b64s = state.get("reference_image_b64s") or []
    image_result = _call_image_generation_api(
        prompt=storyboard_prompt,
        images_base64=reference_b64s if reference_b64s else None,
        agent_name="storyboard_designer",
    )

    # ------------------------------------------------------------------
    # 4. Persist results
    # ------------------------------------------------------------------
    from ..request_context import request_session_id

    session_id = request_session_id.get("local")
    image_path_or_uri: str | None = None
    if image_result and not image_result.startswith("["):
        image_path_or_uri = _save_storyboard_image(image_result, segment_index, session_id)

    prompt_key = f"storyboard_prompt_seg{segment_index:02d}"
    image_key = f"storyboard_image_seg{segment_index:02d}"

    updated_outputs = dict(outputs)
    updated_outputs[prompt_key] = storyboard_prompt
    if image_path_or_uri:
        updated_outputs[image_key] = image_path_or_uri

    storyboard_images = dict(state.get("storyboard_images_by_segment") or {})
    storyboard_images[str(segment_index)] = image_path_or_uri or ""

    return _persist_update(
        state,
        {
            "agent_outputs": updated_outputs,
            "storyboard_images_by_segment": storyboard_images,
            "message": (
                f"分镜流程图已生成（第 {segment_index}/{total_segments} 段）"
                f"{(' → ' + str(image_path_or_uri)) if image_path_or_uri else ''}"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Standalone helper (for CLI / testing)
# ---------------------------------------------------------------------------
def generate_storyboard_for_segment(
    state: DirectorState,
    segment_index: int | None = None,
) -> dict[str, str]:
    """Non-graph helper: generate storyboard prompt + image for a specific segment.

    Returns a dict with keys:
      - prompt: the gpt-image-2 prompt text
      - image_path: saved image path (or empty string)
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
