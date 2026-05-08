"""Package-local planning context nodes (showrunner + scene analyst) extracted from legacy_impl."""
from __future__ import annotations

import re
from typing import Any

from .helpers import build_system_prompt
from .llm import _get_llm_settings, call_llm
from .state_store import _agent_outputs, _persist_update
from .types import DirectorState

# Import knowledge-base helpers locally to avoid a reverse dep on legacy_impl.
from ..knowledge_base import (
    get_agent_knowledge_files,
    get_full_knowledge_for_agent,
    get_smart_knowledge,
    load_knowledge_documents,
)


_DIRECTOR_SHOWRUNNER_FIELD_LABELS = {
    "film_tone": "影片气质",
    "visual_style": "视觉风格",
    "emotional_curve": "情绪曲线",
    "scene_goal": "场景目标",
    "shot_priority": "镜头优先级",
    "must_have": "硬性要求",
    "never_do": "禁止事项",
    "handoff_notes": "下游交接",
    "fallback_reason": "兜底原因",
}

_DIRECTOR_SHOWRUNNER_ROLE_LABELS = {
    "scene_analyst": "场景分析师",
    "story_planner": "结构规划师",
    "shot_director": "镜头导演",
    "prompt_compiler": "提示词编译器",
    "quality_inspector": "质量检查员",
}


def _localize_director_showrunner_output(output: str) -> str:
    text = output or ""
    for field, label in _DIRECTOR_SHOWRUNNER_FIELD_LABELS.items():
        text = re.sub(rf"(?m)^(\s*){re.escape(field)}\s*:", rf"\1{label}:", text)
    for role, label in _DIRECTOR_SHOWRUNNER_ROLE_LABELS.items():
        text = re.sub(rf"\b{re.escape(role)}\b", label, text)
    return text.strip()


def _record_knowledge_metadata(
    state: DirectorState,
    agent_name: str,
    context_hint: str,
    retrieval_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return agent_name-dimension knowledge metadata snapshot (dict[agent_name -> meta]).

    Returns the complete metadata dict (including historical agents); callers should
    assign it wholesale to state['knowledge_metadata'].
    """
    existing: dict[str, Any] = dict(state.get("knowledge_metadata") or {})
    existing[agent_name] = {
        "context_hint": context_hint,
        "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
        "all_sources": get_agent_knowledge_files(agent_name),
        **(retrieval_meta or {}),
    }
    return existing


def _scene_reference_images(state: DirectorState) -> list[str]:
    images = list(state.get("reference_image_b64s") or [])
    if not images:
        return []

    manifest = list(state.get("reference_image_manifest") or [])
    scene_markers = ("scene", "space", "location", "environment", "set", "场景", "空间", "环境", "地点", "场地")
    for index, item in enumerate(manifest):
        if index >= len(images):
            break
        haystack = " ".join(
            str(item.get(key) or "")
            for key in ("label", "filename", "purpose", "type", "role", "name")
        ).lower()
        if any(marker in haystack for marker in scene_markers):
            return [images[index]]

    return [images[0]]


def _reference_context(state: DirectorState) -> str:
    manifest = state.get("reference_image_manifest") or []
    notes = state.get("reference_images") or ""
    lines: list[str] = []
    for item in manifest:
        label = item.get("label") or ""
        filename = item.get("filename") or ""
        purpose = item.get("purpose") or "参考图"
        lines.append(f"{label} {filename}：{purpose}")
    if notes:
        lines.append(f"用户补充说明：{notes}")
    return "\n".join(lines)


def _director_brief(state: DirectorState | dict[str, object]) -> str:
    return str(state.get("director_brief") or "").strip()


def _director_brief_prompt_block(director_brief: str) -> str:
    director_brief = (director_brief or "").strip()
    if not director_brief:
        return ""
    return (
        "【总导演统筹简报】\n"
        "这是下游 agent 必须遵守的最高层创作契约。必须保留剧本事实，"
        "只用于确定表达重点、镜头优先级、节奏取舍和可接受的权衡。\n"
        f"{director_brief}\n"
    )


def _fallback_director_brief(state: DirectorState | dict[str, object], reason: str = "") -> str:
    reason_line = f"兜底原因: {reason[:180]}\n" if reason else ""
    return (
        "影片气质: 保留用户剧本原有气质，不新增剧情事实\n"
        "视觉风格: 清晰、可执行、优先保证连续性的电影化覆盖\n"
        "情绪曲线:\n"
        "  - 根据原剧本压力逐步推进，不额外制造新冲突\n"
        "  - 在关键受击点保留观众能读懂的反应空间\n"
        "场景目标: 让每个镜头都服务当前剧本的戏剧压力\n"
        "镜头优先级:\n"
        "  - 保留人物动机和原剧本事件\n"
        "  - 保持空间连续性和尾帧交接清晰\n"
        "  - 优先选择可生成、可执行的镜头，而不是炫技运镜\n"
        "硬性要求:\n"
        "  - 每个生成镜头都必须保护剧本忠实度\n"
        "  - 每个片段都必须给下一片段留下可继承的连续性状态\n"
        "禁止事项:\n"
        "  - 不新增剧本外人物、台词、道具或剧情节拍\n"
        "  - 不为了好看选择破坏地理关系或动作清晰度的镜头\n"
        "下游交接:\n"
        "  场景分析: 只提取剧本和参考图里明确存在的空间、人物和约束\n"
        "  结构规划: 按完整剧情任务拆分，不为普通停顿单独拆段\n"
        "  镜头导演: 把节奏重点落实到可执行镜头，不重写剧本\n"
        f"{reason_line}"
    ).strip()


def _script_fidelity_rules() -> str:
    return (
        "【剧本忠实度硬规则】\n"
        "1. 只能使用原剧本已经出现的人物、场景、动作、台词和信息点，禁止补写剧本外新事件。\n"
        "2. 禁止新增剧本中没有的台词、旁白、员工低语、心理活动或解释性信息；凡带引号的台词必须能在原剧本中找到。\n"
        "3. 若原剧本没有写员工说话，就不能写员工低声确认、新CEO到了、议论等补戏。\n"
        "4. 片段不足15秒时允许短于15秒，禁止为了凑时长添加新情节。\n"
    )


def director_showrunner_node(state: DirectorState) -> DirectorState:
    import time

    outputs = _agent_outputs(state)

    if bool(state.get("speed_mode", False)):
        output = _localize_director_showrunner_output(_fallback_director_brief(state, "快速模式"))
        outputs["director_showrunner"] = output
        knowledge_metadata = _record_knowledge_metadata(
            state,
            "director_showrunner",
            "speed_mode_director_brief",
            {
                "retrieval_mode": "speed_mode",
                "used_full_fallback": False,
                "matched_sources": [],
                "critical_sources": [],
                "result_count": 0,
            },
        )
        _api_key, base_url, model, temperature = _get_llm_settings("director_showrunner")
        try:
            host = base_url.split("//", 1)[1].split("/", 1)[0] if "//" in base_url else base_url
        except Exception:
            host = base_url
        knowledge_metadata.setdefault("director_showrunner", {})["runtime"] = {
            "agent_name": "director_showrunner",
            "status": "local_fallback",
            "reason": "speed_mode",
            "output_chars": len(output),
            "model": model,
            "host": host,
            "temperature": temperature,
        }
        return _persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_1_analyze",
                "message": "总导演统筹已完成，场景分析正在运行...",
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
                "director_brief": output,
            },
        )

    showrunner_hint = (
        "总导演 统筹 风格基准 情绪曲线 镜头优先级 "
        f"剧本忠实 视觉意图 画幅 {state.get('aspect_ratio', '16:9')}"
    )
    system_prompt, retrieval_meta = build_system_prompt(
        "你是 AI 短剧流水线里的总导演统筹。\n"
        "你的职责不是设计具体镜头，而是给所有下游智能体制定必须遵守的最高层创作契约。\n"
        "必须保留全部剧本事实，不得新增剧情、台词、人物、道具或故事事件。\n"
        "请把原始剧本和节奏指导整理成清晰的总导演简报，供场景分析、结构规划和镜头导演执行。\n"
        "输出必须是 YAML，字段名和说明内容全部使用中文；只有原剧本台词或专有名词可以保留原文。",
        "director_showrunner",
        context_hint=showrunner_hint,
    )
    user_prompt = (
        "【原始剧本】\n"
        f"{state.get('script', '')}\n\n"
        "【节奏与氛围指导】\n"
        f"{state.get('atmosphere_strategy', '') or '无'}\n\n"
        "【画幅】\n"
        f"{state.get('aspect_ratio', '16:9')}\n\n"
        "【必须输出的 YAML 字段】\n"
        "影片气质: 一句简洁判断\n"
        "视觉风格: 一句简洁判断\n"
        "情绪曲线: 按顺序列出 3-6 个情绪节拍\n"
        "场景目标: 一句话说明观众必须感受到或理解什么\n"
        "镜头优先级: 按顺序列出 3-5 条镜头取舍重点\n"
        "硬性要求: 列出不可妥协的创作要求\n"
        "禁止事项: 列出会破坏本场戏的禁用选择\n"
        "下游交接:\n"
        "  场景分析: 给场景分析师的简短交接\n"
        "  结构规划: 给结构规划师的简短交接\n"
        "  镜头导演: 给镜头导演的简短交接\n\n"
        "【决策边界】\n"
        "总导演简报可以选择表达重点和审美倾向，但不能改写剧本事实。\n"
        "优先选择可执行、连续性安全的方案，不要选择漂亮但不稳定的镜头方向。\n"
        "除原剧本台词或专有名词外，不要输出英文标签、英文小标题或英文字段名。\n"
    )

    started = time.perf_counter()
    try:
        output = call_llm(system_prompt, user_prompt, agent_name="director_showrunner")
        output = (output or "").strip() or _fallback_director_brief(state, "empty_showrunner_output")
        output = _localize_director_showrunner_output(output)
        runtime = {
            "agent_name": "director_showrunner",
            "mode": "direct",
            "status": "success",
            "output_chars": len(output),
        }
    except Exception as exc:
        output = _fallback_director_brief(state, f"{type(exc).__name__}: {exc}")
        output = _localize_director_showrunner_output(output)
        runtime = {
            "agent_name": "director_showrunner",
            "mode": "direct",
            "status": "fallback",
            "output_chars": len(output),
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }

    outputs["director_showrunner"] = output
    knowledge_metadata = _record_knowledge_metadata(state, "director_showrunner", showrunner_hint, retrieval_meta)
    knowledge_metadata.setdefault("director_showrunner", {})["runtime"] = runtime
    return _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_1_analyze",
            "message": "总导演统筹已完成，场景分析正在运行...",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "director_brief": output,
        },
    )


def scene_analyst_node(state: DirectorState) -> DirectorState:
    outputs = _agent_outputs(state)
    director_brief_block = _director_brief_prompt_block(_director_brief(state))

    if bool(state.get("speed_mode", False)):
        output = (
            "mode: fast_local_scene_card\n"
            f"aspect_ratio: {state.get('aspect_ratio', '16:9')}\n"
            "source: original_script_only\n"
            "director_brief: |\n"
            f"{director_brief_block or '  none'}\n"
            "notes:\n"
            "  - 快速模式跳过场景分析师LLM调用，后续节点必须直接以原始剧本为准。\n"
            "  - 禁止新增原剧本外人物、对白、事件、员工低语、旁白或解释性信息。\n"
            "  - 参考图只按清单用途调用，不改变剧情拆分。\n"
            "reference_manifest: |\n"
            f"{_reference_context(state) or '  无'}\n"
        )
        outputs["scene_analyst"] = output
        knowledge_metadata = _record_knowledge_metadata(
            state,
            "scene_analyst",
            "fast_mode_local_scene_card",
            {
                "retrieval_mode": "fast_mode",
                "used_full_fallback": False,
                "matched_sources": [],
                "critical_sources": [],
                "result_count": 0,
            },
        )
        return _persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_2_plan",
                "message": "快速模式：已跳过场景分析LLM，结构规划师正在拆片...（3/6）",
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
            },
        )

    scene_hint = f"场景分析 剧本拆解 核心动作 炸点 约束 导演意图 aspect_ratio {state.get('aspect_ratio', '16:9')}"
    system_prompt, retrieval_meta = build_system_prompt(
        "你是一位顶尖短剧场景分析师。你需要拆解用户提供的剧本，提取核心动作、炸点和约束。\n\n"
        "【绝对禁令】你只能提取剧本原文中明确存在的信息。\n"
        "禁止推测、补充或扩展剧本中没有出现的内容。\n"
        "禁止新增剧本中没有的员工反应、旁白、低声议论、表情反应或任何解释性信息。\n"
        "如果原剧本没有写员工说话，分析卡中不得出现员工对白或低语。\n"
        "如果原剧本没有写某个动作，分析卡中不得出现该动作。",
        "scene_analyst",
        context_hint=scene_hint,
    )
    user_prompt = (
        f"{director_brief_block}\n"
        f"分析以下剧本场景，填充完整的场景分析输入卡。\n\n"
        f"【剧本】\n{state['script']}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n\n"
        f"【参考图清单】\n{_reference_context(state)}\n\n"
        "【参考图使用边界】\n"
        "1. 参考图只用于提取空间、环境、人物站位、人物朝向、人物间距离、视线轴线和关键场景锚点。\n"
        "2. 不要展开人物五官、发型、服装细节；人物身份后续由 Seedance 参考图锁定，分析卡和最终 prompt 只需要使用人名。\n"
        "3. 场景分析必须把可见空间翻译成可继承的文字锚点：入口/电梯/门/走廊/前台/窗/桌椅等物体的相对方位，以及人物与这些锚点的关系。\n"
        "4. 如果参考图与剧本文字冲突，不得新增剧情，只能把参考图作为空间和环境基底说明。\n\n"
        f"{_script_fidelity_rules()}\n"
        f"请直接输出YAML分析卡片。"
    )
    ref_images = _scene_reference_images(state) or None
    agent_for_call = "scene_vision_analyst" if ref_images else "scene_analyst"
    knowledge_metadata = _record_knowledge_metadata(state, "scene_analyst", scene_hint, retrieval_meta)
    try:
        output = call_llm(system_prompt, user_prompt, images_base64=ref_images, agent_name=agent_for_call)
    except Exception as exc:
        if ref_images:
            raise
        print(f"  [scene_analyst] primary text model failed, retrying via story_planner channel: {exc}")
        # Keep text-only scene analysis away from the prompt_compiler channel.
        # prompt_compiler may be configured for heavier final prompt models, which
        # has caused Phase 1 to fail on upstream read timeouts before planning starts.
        output = call_llm(system_prompt, user_prompt, images_base64=None, agent_name="story_planner", max_retries=1)
    outputs["scene_analyst"] = output
    return _persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_2_plan",
            "message": "结构规划师正在拆片规划...（3/6）",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
        },
    )
