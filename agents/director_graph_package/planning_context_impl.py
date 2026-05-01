"""Package-local planning context nodes (showrunner + scene analyst) extracted from legacy_impl."""
from __future__ import annotations

from typing import Any

DirectorState = dict[str, Any]


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


def _fallback_director_brief(state: DirectorState | dict[str, Any], reason: str = "") -> str:
    reason_line = f"fallback_reason: {reason[:180]}\n" if reason else ""
    return (
        "film_tone: preserve the user's script tone; do not invent new plot facts\n"
        "visual_style: clear, executable, continuity-first cinematic coverage\n"
        "scene_goal: make every shot serve the script's current dramatic pressure\n"
        "shot_priority:\n"
        "  - preserve character motivation and source-script events\n"
        "  - keep spatial continuity and tail-frame handoff readable\n"
        "  - prefer executable camera choices over flashy camera moves\n"
        "must_have:\n"
        "  - every generated shot must protect script fidelity\n"
        "  - every segment must leave a usable continuity state for the next segment\n"
        "never_do:\n"
        "  - do not add script-external people, dialogue, props, or story beats\n"
        "  - do not choose a beautiful shot that breaks geography or action clarity\n"
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
    import agents.director_graph as dg
    import time

    outputs = dg._agent_outputs(state)

    if bool(state.get("speed_mode", False)):
        output = _fallback_director_brief(state, "speed_mode")
        outputs["director_showrunner"] = output
        knowledge_metadata = dg._record_knowledge_metadata(
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
        _api_key, base_url, model, temperature = dg._get_llm_settings("director_showrunner")
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
        return dg._persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_1_analyze",
                "message": "Director showrunner brief ready; scene analyst is running...",
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
                "director_brief": output,
            },
        )

    showrunner_hint = (
        "director showrunner style bible emotional curve shot priority "
        f"script fidelity visual intent {state.get('script', '')[:200]}"
    )
    system_prompt, retrieval_meta = dg.build_system_prompt(
        "You are the Director Showrunner for an AI short-film pipeline.\n"
        "Your job is not to design detailed shots. Your job is to define the "
        "top-level creative contract that every downstream agent must obey.\n"
        "Preserve all script facts. Do not add plot, dialogue, people, props, "
        "or new story events. Turn the script and rhythm guidance into a clear "
        "director brief for scene analysis, story planning, and shot direction.\n"
        "Output YAML only.",
        "director_showrunner",
        context_hint=showrunner_hint,
    )
    user_prompt = (
        "[Original Script]\n"
        f"{state.get('script', '')}\n\n"
        "[Rhythm And Atmosphere Guidance]\n"
        f"{state.get('atmosphere_strategy', '') or 'none'}\n\n"
        "[Aspect Ratio]\n"
        f"{state.get('aspect_ratio', '16:9')}\n\n"
        "[Required YAML Fields]\n"
        "film_tone: one concise sentence\n"
        "visual_style: one concise sentence\n"
        "emotional_curve: ordered list of 3-6 beats\n"
        "scene_goal: one sentence explaining what the audience must feel or understand\n"
        "shot_priority: ordered list of 3-5 priorities\n"
        "must_have: list of non-negotiable creative requirements\n"
        "never_do: list of forbidden choices that would break the scene\n"
        "handoff_notes: short notes for scene_analyst, story_planner, and shot_director\n\n"
        "[Decision Boundary]\n"
        "The brief may choose emphasis and taste, but it must not rewrite script facts.\n"
        "Prefer executable, continuity-safe choices over beautiful but unstable shots.\n"
    )

    started = time.perf_counter()
    try:
        output = dg.call_llm(system_prompt, user_prompt, agent_name="director_showrunner")
        output = (output or "").strip() or _fallback_director_brief(state, "empty_showrunner_output")
        runtime = {
            "agent_name": "director_showrunner",
            "mode": "direct",
            "status": "success",
            "output_chars": len(output),
        }
    except Exception as exc:
        output = _fallback_director_brief(state, f"{type(exc).__name__}: {exc}")
        runtime = {
            "agent_name": "director_showrunner",
            "mode": "direct",
            "status": "fallback",
            "output_chars": len(output),
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }

    outputs["director_showrunner"] = output
    knowledge_metadata = dg._record_knowledge_metadata(state, "director_showrunner", showrunner_hint, retrieval_meta)
    knowledge_metadata.setdefault("director_showrunner", {})["runtime"] = runtime
    return dg._persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_1_analyze",
            "message": "Director showrunner brief ready; scene analyst is running...",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "director_brief": output,
        },
    )


def scene_analyst_node(state: DirectorState) -> DirectorState:
    import agents.director_graph as dg

    outputs = dg._agent_outputs(state)
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
        knowledge_metadata = dg._record_knowledge_metadata(
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
        return dg._persist_update(
            state,
            {
                "status": "running_phase_1",
                "step": "step_2_plan",
                "message": "快速模式：已跳过场景分析LLM，结构规划师正在拆片...（3/6）",
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
            },
        )

    scene_hint = f"场景分析 剧本拆解 核心动作 炸点 约束 导演意图 {state['script'][:200]}"
    system_prompt, retrieval_meta = dg.build_system_prompt(
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
    knowledge_metadata = dg._record_knowledge_metadata(state, "scene_analyst", scene_hint, retrieval_meta)
    try:
        output = dg.call_llm(system_prompt, user_prompt, images_base64=ref_images, agent_name=agent_for_call)
    except Exception as exc:
        if ref_images:
            raise
        print(f"  [scene_analyst] primary text model failed, retrying via prompt_compiler channel: {exc}")
        output = dg.call_llm(system_prompt, user_prompt, images_base64=None, agent_name="prompt_compiler", max_retries=1)
    outputs["scene_analyst"] = output
    return dg._persist_update(
        state,
        {
            "status": "running_phase_1",
            "step": "step_2_plan",
            "message": "结构规划师正在拆片规划...（3/6）",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
        },
    )
