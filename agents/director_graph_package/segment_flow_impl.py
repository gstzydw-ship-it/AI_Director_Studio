"""Segment flow nodes (wait_for_segment_request + segment_complete + route_after_segment)."""
from __future__ import annotations

import base64
import os
import re
from datetime import datetime
from typing import Any, Literal

from .llm import call_llm
from .types import DirectorState, OUTPUT_DIR


def wait_for_segment_request_node(state: DirectorState) -> DirectorState:
    import agents.director_graph as dg
    from langgraph.types import interrupt
    import os

    segment_index = int(state.get("current_segment_index") or 1)
    total_segments = int(state.get("total_segments") or 1)
    payload = interrupt(
        {
            "type": "segment_request",
            "segment_index": segment_index,
            "total_segments": total_segments,
            "message": f"等待生成第 {segment_index} 段 Prompt。",
        }
    )
    if not isinstance(payload, dict):
        payload = {}

    requested_segment = int(payload.get("segment_index") or segment_index)
    requested_segment = max(1, min(requested_segment, total_segments))
    next_segment_context = _next_segment_bridge_context(state, requested_segment)

    video_path = payload.get("video_path")
    if video_path and os.path.exists(video_path):
        try:
            tail_frame_analysis = _analyze_video_segment(video_path, requested_segment, next_segment_context)
        except Exception as exc:
            fallback_tail_b64 = payload.get("tail_frame_b64")
            tail_frame_note = ""
            if not fallback_tail_b64:
                fallback_tail_b64, tail_frame_path, tail_frame_error = _extract_tail_frame_from_video(
                    video_path,
                    requested_segment,
                )
                if tail_frame_path:
                    tail_frame_note = f"已从视频自动抽取尾帧：{tail_frame_path}\n"
                elif tail_frame_error:
                    tail_frame_note = f"自动抽取尾帧也失败：{tail_frame_error}\n"
            fallback = _analyze_tail_frame(fallback_tail_b64, requested_segment, next_segment_context)
            tail_frame_analysis = (
                f"上一段完整视频分析失败，已自动降级为尾帧连续性分析。失败原因：{exc}\n\n"
                f"{tail_frame_note}"
                f"{fallback}"
            )
    else:
        tail_frame_analysis = _analyze_tail_frame(payload.get("tail_frame_b64"), requested_segment, next_segment_context)

    return dg._persist_update(
        state,
        {
            "status": "running_phase_2",
            "step": "step_4_compile",
            "message": f"Seedance编译师正在生成第 {requested_segment} 段 Prompt...（5/6）",
            "active_segment_index": requested_segment,
            "tail_frame_analysis": tail_frame_analysis,
            "qc_retry_count": 0,
            "revision_instruction": "",
        },
    )


def segment_complete_node(state: DirectorState) -> DirectorState:
    import agents.director_graph as dg

    outputs = dg._agent_outputs(state)
    segment_index = int(state.get("active_segment_index") or state.get("current_segment_index") or 1)
    total_segments = int(state.get("total_segments") or 1)
    next_segment = segment_index + 1
    combined = _combined_prompt(outputs)

    if next_segment > total_segments:
        return dg._persist_update(
            state,
            {
                "status": "done",
                "step": "",
                "message": "全部片段 Prompt 已生成完成。",
                "current_segment_index": next_segment,
                "result": combined,
                "agent_outputs": outputs,
            },
        )

    return dg._persist_update(
        state,
        {
            "status": "waiting_for_user_input",
            "step": "step_5_inspect",
            "message": f"第 {segment_index} 段完成，等待尾帧后生成第 {next_segment} 段。",
            "current_segment_index": next_segment,
            "result": combined,
            "agent_outputs": outputs,
        },
    )


def route_after_segment(state: DirectorState) -> Literal["wait_for_segment_request", "__end__"]:
    from langgraph.graph import END

    if state.get("status") == "done":
        return END
    return "wait_for_segment_request"


# ----------------------------------------------------------------------
# Helpers used by the above nodes – imported from legacy_impl to keep
# the nodes clean while the monolith is being dismantled.
# ----------------------------------------------------------------------
def _combined_prompt(agent_outputs: dict[str, str]) -> str:
    from .legacy_impl import _combined_prompt as _impl
    return _impl(agent_outputs)


def _segment_block(text: str, segment_index: int) -> str:
    from .legacy_impl import _segment_block as _impl
    return _impl(text, segment_index)


def _truncate_bridge_text(text: str, limit: int = 1800) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated for bridge analysis]..."


def _next_segment_bridge_context(state: DirectorState, segment_index: int) -> str:
    outputs = dict(state.get("agent_outputs") or {})
    planner_segment = _segment_block(outputs.get("story_planner", ""), segment_index)
    director_segment = _segment_block(outputs.get("shot_director", ""), segment_index)
    scene_memory = _truncate_bridge_text(outputs.get("scene_analyst", ""), 900)

    lines = [
        "[Next Segment Bridge Target]",
        f"segment_index: {segment_index}",
        "Use this to decide whether the previous video's tail should become an image_start or a direct_cut.",
        "",
        "[Scene Memory]",
        scene_memory or "n/a",
        "",
        "[Next Segment Planner Asset]",
        _truncate_bridge_text(planner_segment, 1800) or "n/a",
        "",
        "[Next Segment Shot Asset]",
        _truncate_bridge_text(director_segment, 1800) or "n/a",
    ]
    return "\n".join(lines).strip()


def _bridge_frame_output_contract() -> str:
    return (
        "Output in this exact YAML-like shape:\n"
        "bridge_frame:\n"
        "  selected: true|false\n"
        "  selected_candidate: candidate_01|candidate_02|candidate_03|candidate_04|candidate_05|none\n"
        "  time_position: \"tail section time or unknown\"\n"
        "  frame_type: character_relation|character_closeup|prop_insert|empty_scene|unreadable\n"
        "  usable_as_start_image: true|false\n"
        "  reason: \"why this frame can or cannot connect to the next segment\"\n"
        "next_segment_start_mode:\n"
        "  mode: image_start|direct_cut\n"
        "  reason: \"same-scene continuation, action carryover, scene change, flashback, or space reset\"\n"
        "continuity_constraints:\n"
        "  character_position: \"visible inherited position or unknown\"\n"
        "  character_facing: \"visible facing or unknown\"\n"
        "  prop_state: \"visible prop state or unknown\"\n"
        "  space_state: \"visible space state or unknown\"\n"
        "  must_reset_space: true|false\n"
        "do_not_infer:\n"
        "  - \"facts that are not visible in the previous video or not required by the next segment\"\n"
    )


def _bridge_candidate_manifest(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "No extracted tail-section candidate frames are available."
    lines = ["Extracted tail-section candidate frames, in the same order as attached images:"]
    for candidate in candidates:
        lines.append(
            "- {id}: time={time_seconds:.2f}s frame={frame_index} path={path}".format(**candidate)
        )
    return "\n".join(lines)


def _extract_bridge_frame_candidates(
    video_path: str,
    segment_index: int,
    *,
    max_candidates: int = 5,
    tail_seconds: float = 2.5,
    max_edge_px: int = 768,
) -> tuple[list[dict[str, Any]], str | None]:
    """Extract labeled frame candidates from the previous video's tail section."""
    if not video_path or not os.path.exists(video_path):
        return [], "video file does not exist"

    cap = None
    try:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return [], "OpenCV cannot open video"

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if frame_count <= 0:
            return [], "video has no readable frame count"
        if fps <= 0:
            fps = 24.0

        tail_frame_count = max(1, int(round(fps * tail_seconds)))
        start = max(0, frame_count - tail_frame_count)
        end = max(0, frame_count - 1)
        if max_candidates <= 1 or start == end:
            positions = [end]
        else:
            positions = sorted(
                {
                    int(round(start + (end - start) * idx / (max_candidates - 1)))
                    for idx in range(max_candidates)
                }
            )

        output_dir = os.path.join(OUTPUT_DIR, "auto_bridge_frames")
        os.makedirs(output_dir, exist_ok=True)
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.splitext(os.path.basename(video_path))[0]).strip("._")
        safe_stem = safe_stem or "segment"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidates: list[dict[str, Any]] = []

        for ordinal, position in enumerate(positions, start=1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue

            height, width = frame.shape[:2]
            longest_edge = max(width, height)
            if longest_edge > max_edge_px:
                scale = max_edge_px / float(longest_edge)
                frame = cv2.resize(frame, (max(1, int(width * scale)), max(1, int(height * scale))))

            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not ok:
                continue

            candidate_id = f"candidate_{ordinal:02d}"
            time_seconds = position / fps if fps else 0.0
            output_path = os.path.join(
                output_dir,
                f"{stamp}_segment{segment_index}_{safe_stem}_{candidate_id}_{int(time_seconds * 1000)}ms.jpg",
            )
            encoded_bytes = encoded.tobytes()
            with open(output_path, "wb") as f:
                f.write(encoded_bytes)
            candidates.append(
                {
                    "id": candidate_id,
                    "time_seconds": time_seconds,
                    "frame_index": position,
                    "path": output_path,
                    "b64": base64.b64encode(encoded_bytes).decode("utf-8"),
                }
            )

        return candidates, None if candidates else "no candidate frames could be encoded"
    except Exception as exc:
        return [], f"failed to extract bridge frame candidates: {exc}"
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def _tail_frame_system_prompt() -> str:
    return (
        "你是视频桥接连续性分析师。只提取可见事实，不扩写剧情。"
        "你的任务不是重新设计镜头，而是判断上一段画面能否服务下一段开头。"
    )


def _tail_frame_user_prompt(segment_index: int, next_segment_context: str) -> str:
    target_context = next_segment_context or "[Next Segment Bridge Target]\nn/a"
    return (
        f"请分析第 {segment_index - 1} 段的尾帧，用于第 {segment_index} 段开头桥接。\n\n"
        f"{target_context}\n\n"
        "如果尾帧是人物关系帧，才允许建议 image_start；如果是人物特写、道具特写、空镜、不可读，"
        "通常建议 direct_cut 或 space_reset。\n"
        f"{_bridge_frame_output_contract()}"
    )


def _analyze_tail_frame(
    tail_frame_b64: str | None,
    segment_index: int,
    next_segment_context: str = "",
) -> str:
    if not tail_frame_b64:
        return (
            "bridge_frame:\n"
            "  selected: false\n"
            "  selected_candidate: none\n"
            "  time_position: \"none\"\n"
            "  frame_type: unreadable\n"
            "  usable_as_start_image: false\n"
            "  reason: \"No previous tail frame was provided.\"\n"
            "next_segment_start_mode:\n"
            "  mode: direct_cut\n"
            "  reason: \"No visual bridge is available; compile the next segment from its own scene and shot assets.\"\n"
            "continuity_constraints:\n"
            "  character_position: unknown\n"
            "  character_facing: unknown\n"
            "  prop_state: unknown\n"
            "  space_state: unknown\n"
            "  must_reset_space: true\n"
        )

    return call_llm(
        _tail_frame_system_prompt(),
        _tail_frame_user_prompt(segment_index, next_segment_context),
        images_base64=[tail_frame_b64],
        temperature=0.2,
        agent_name="shot_director",
    )


def _extract_tail_frame_from_video(video_path: str, segment_index: int = 0) -> tuple[str | None, str | None, str | None]:
    from .legacy_impl import _extract_tail_frame_from_video as _impl
    return _impl(video_path, segment_index)


def _video_bridge_system_prompt() -> str:
    return (
        "你是视频桥接连续性分析师。你会看到上一段完整视频，以及从视频尾部自动抽取的候选帧。"
        "你必须结合下一段开头资产，判断应该使用候选截图作为 image_start，还是 direct_cut 重新开镜。"
        "只记录可见事实和桥接决策，不重写剧情，不重新设计镜头。"
    )


def _video_bridge_user_prompt(segment_index: int, next_segment_context: str, candidate_manifest: str) -> str:
    target_context = next_segment_context or "[Next Segment Bridge Target]\nn/a"
    return (
        f"请分析第 {segment_index - 1} 段的实际生成视频，目标是为第 {segment_index} 段找到最合适的开头方式。\n\n"
        f"{target_context}\n\n"
        f"[Tail Bridge Candidates]\n{candidate_manifest}\n\n"
        "决策规则：\n"
        "1. 如果下一段与上一段同场景、同动作连续，并且某个候选帧能清楚继承人物位置/朝向/道具/空间关系，选择 image_start。\n"
        "2. 如果下一段换场景、闪回、时间跳转、需要重新建立空间，选择 direct_cut。\n"
        "3. 如果候选帧是脸部特写、道具特写、空镜或不可读，但下一段需要人物空间关系，选择 direct_cut 或 must_reset_space=true。\n"
        "4. 不要默认选择最后一帧；优先从尾部候选帧里挑最适合下一段开头的一帧。\n"
        "5. 如果选择 image_start，selected_candidate 必须写 candidate_01..candidate_05 中的一个；否则写 none。\n\n"
        f"{_bridge_frame_output_contract()}"
    )


def _analyze_video_segment(video_path: str, segment_index: int, next_segment_context: str = "") -> str:
    try:
        with open(video_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as exc:
        return f"Video file read failed: {exc}. Use direct_cut unless a user-provided tail frame is available."

    candidates, candidate_error = _extract_bridge_frame_candidates(video_path, segment_index)
    candidate_manifest = _bridge_candidate_manifest(candidates)
    if candidate_error:
        candidate_manifest = f"{candidate_manifest}\nCandidate extraction note: {candidate_error}"

    video_data_uri = f"data:video/mp4;base64,{video_b64}"
    images_base64 = [video_data_uri] + [candidate["b64"] for candidate in candidates]
    analysis = call_llm(
        _video_bridge_system_prompt(),
        _video_bridge_user_prompt(segment_index, next_segment_context, candidate_manifest),
        images_base64=images_base64,
        temperature=0.2,
        agent_name="video_analyst",
        bypass_proxy=True,
    )
    return f"[Auto Bridge Candidate Frames]\n{candidate_manifest}\n\n[Video Bridge Analysis]\n{analysis}"
