"""Segment flow nodes (wait_for_segment_request + segment_complete + route_after_segment)."""
from __future__ import annotations

from typing import Any, Literal

from .types import DirectorState


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

    video_path = payload.get("video_path")
    if video_path and os.path.exists(video_path):
        try:
            tail_frame_analysis = _analyze_video_segment(video_path, requested_segment)
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
            fallback = _analyze_tail_frame(fallback_tail_b64, requested_segment)
            tail_frame_analysis = (
                f"上一段完整视频分析失败，已自动降级为尾帧连续性分析。失败原因：{exc}\n\n"
                f"{tail_frame_note}"
                f"{fallback}"
            )
    else:
        tail_frame_analysis = _analyze_tail_frame(payload.get("tail_frame_b64"), requested_segment)

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


def _analyze_tail_frame(tail_frame_b64: str | None, segment_index: int) -> str:
    from .legacy_impl import _analyze_tail_frame as _impl
    return _impl(tail_frame_b64, segment_index)


def _extract_tail_frame_from_video(video_path: str, segment_index: int = 0) -> tuple[str | None, str | None, str | None]:
    from .legacy_impl import _extract_tail_frame_from_video as _impl
    return _impl(video_path, segment_index)


def _analyze_video_segment(video_path: str, segment_index: int) -> str:
    from .legacy_impl import _analyze_video_segment as _impl
    return _impl(video_path, segment_index)
