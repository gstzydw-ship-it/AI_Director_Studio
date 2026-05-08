"""Package-local planning context nodes (showrunner + scene analyst) extracted from legacy_impl."""
from __future__ import annotations

import re
from typing import Any

import yaml

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
    "enhanced_script": "增强版剧本",
    "enhancement_basis": "增强依据",
    "mainline_protection": "主线保护",
    "rhythm_supervisor_handoff": "节奏总控交接",
    "needs_user_confirmation": "需用户确认",
    "forbidden_changes": "禁止改动",
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


def _strip_yaml_fence(text: str) -> str:
    text = (text or "").strip()
    fence_match = re.search(r"(?is)```(?:yaml|yml)?\s*(.*?)\s*```", text)
    return fence_match.group(1).strip() if fence_match else text


def _parse_director_showrunner_yaml(output: str) -> dict[str, Any]:
    text = _strip_yaml_fence(output)
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_enhanced_script(output: str, fallback_script: str) -> str:
    payload = _parse_director_showrunner_yaml(output)
    for key in ("增强版剧本", "enhanced_script"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    match = re.search(
        r"(?ms)^\s*(?:增强版剧本|enhanced_script)\s*[：:]\s*(?:\|\s*)?\n?(.*?)(?=^\S[^：:\n]{0,40}[：:]|\Z)",
        _strip_yaml_fence(output),
    )
    if match and match.group(1).strip():
        return match.group(1).strip()
    return (fallback_script or "").strip()


def _director_enhancement_contract(output: str, enhanced_script: str, max_chars: int = 1800) -> str:
    payload = _parse_director_showrunner_yaml(output)
    if payload:
        compact_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"增强版剧本", "enhanced_script"} and value not in (None, "", [], {})
        }
        if compact_payload:
            contract = yaml.safe_dump(compact_payload, allow_unicode=True, sort_keys=False).strip()
            return contract[:max_chars].strip()

    text = _strip_yaml_fence(output)
    text = re.sub(
        r"(?ms)^\s*(?:增强版剧本|enhanced_script)\s*[：:]\s*(?:\|\s*)?\n?.*?(?=^\S[^：:\n]{0,40}[：:]|\Z)",
        "",
        text,
    ).strip()
    if text:
        return text[:max_chars].strip()
    return (
        "增强原则:\n"
        "  - 使用增强版剧本作为后续施工文本\n"
        "  - 只增强原剧本内已有冲突，不改变主线剧情\n"
        "节奏总控交接:\n"
        "  - 基于增强版剧本重新判断快慢、停顿、卡断和反应归属"
    )


def _director_showrunner_user_intent(state: DirectorState) -> str:
    candidate_keys = (
        "director_intent",
        "user_director_intent",
        "user_notes",
        "director_notes",
        "creative_brief",
        "requirements",
        "visual_requirements",
        "reference_images",
    )
    lines: list[str] = []
    for key in candidate_keys:
        value = state.get(key)
        if not value:
            continue
        text = value if isinstance(value, str) else str(value)
        text = text.strip()
        if text:
            lines.append(f"{key}: {text}")
    return "\n".join(lines)


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
        "【剧情增强契约】\n"
        "这是剧情增强导演给下游 agent 的施工边界。当前输入剧本可能已经做过冲突增强；"
        "下游必须以当前剧本为施工文本，同时保护原始主线剧情，不得新增未确认的核心事件、人物关系或台词。\n"
        f"{director_brief}\n"
    )


def _fallback_director_brief(state: DirectorState | dict[str, object], reason: str = "") -> str:
    reason_line = f"兜底原因: {reason[:180]}\n" if reason else ""
    return (
        "主线保护:\n"
        "  - 使用当前剧本继续施工，但不得改变人物关系、核心事件、台词和剧情结果\n"
        "  - 只允许把原文已有的概括动作、静态说明和弱冲突转成可拍动作\n"
        "可执行增强:\n"
        "  - 动作密度、时间压力、声音压力、已有道具使用、已有角色调度可以增强\n"
        "  - 新人物、新台词、新关键道具、新误会或新反转必须先进入需用户确认\n"
        "节奏总控交接:\n"
        "  - 基于增强后的当前剧本重新判断快慢、停顿、卡断、反应归属和尾帧承接\n"
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
    source_script = str(state.get("script") or "")
    original_script = str(state.get("original_script") or source_script)

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
                "step": "step_0_rhythm",
                "message": "快速模式：已跳过剧情增强，节奏总控导演正在运行...",
                "agent_outputs": outputs,
                "knowledge_metadata": knowledge_metadata,
                "director_brief": output,
                "enhanced_script": source_script,
                "original_script": original_script,
            },
        )

    showrunner_hint = (
        "剧情增强 冲突强化 弱冲突 可拍动作 动作密度 时间压力 声音压力 "
        "人物调度 主线保护 禁止新增台词 禁止改主线 "
        f"画幅 {state.get('aspect_ratio', '16:9')}"
    )
    system_prompt, retrieval_meta = build_system_prompt(
        "你是 AI 短剧流水线里的剧情冲突增强导演。\n"
        "你的职责是在不改变主线剧情的前提下，把原剧本里偏弱、偏概括、偏静态的冲突增强成可拍内容。\n"
        "你不做拆片、不做具体镜头设计、不输出 shot 建议；你只交付增强版剧本和增强依据。\n"
        "允许增强 L1 动作层与 L2 调度层：动作密度、时间压力、声音压力、已有道具阻碍、已有角色进入/拦住/停住/转身等可见调度。\n"
        "禁止直接改动主线剧情、人物关系、剧情结果和原台词；禁止新增未确认的新人物、新台词、新关键道具、新误会或新反转。\n"
        "如果某个想法属于剧情层新增，必须放入“需用户确认”，不能写进增强版剧本。\n"
        "输出必须是 YAML，字段名和说明内容全部使用中文；只有原剧本台词或专有名词可以保留原文。",
        "director_showrunner",
        context_hint=showrunner_hint,
    )
    user_prompt = (
        "【原始剧本】\n"
        f"{source_script}\n\n"
        "【用户导演意图/补充要求】\n"
        f"{_director_showrunner_user_intent(state) or '无'}\n\n"
        "【画幅】\n"
        f"{state.get('aspect_ratio', '16:9')}\n\n"
        "【必须输出的 YAML 字段】\n"
        "增强版剧本: 使用 YAML 多行文本，输出完整可施工剧本；保留原台词原文，不翻译、不改写台词。\n"
        "增强依据: 列表；每条包含 原文锚点 / 增强方式 / 权限级别 / 是否改动主线。\n"
        "主线保护: 列出本次增强没有改变的核心剧情事实。\n"
        "节奏总控交接: 给下一步节奏总控导演的简短说明，只写节奏关注点，不写拆片和镜头方案。\n"
        "需用户确认: 只列 L3 剧情层新增想法；没有就写 无。\n\n"
        "【决策边界】\n"
        "1. 可以把“忙乱、急匆匆、气氛紧张、愣住、等待、列队”等概括词展开成连续可见动作。\n"
        "2. 可以把静态说明改成动态调度，例如已有主管/秘书从门内快速出来列队，已有朋友迎面拦住女主提醒。\n"
        "3. 可以使用原剧本已有道具和环境强化阻力，例如闹钟、电话、水杯、书包、咖啡、公司大门、车辆声音。\n"
        "4. 不得改变主线剧情：人物关系、公司易主、新老板到达、前夫揭示等核心事实不能变。\n"
        "5. 不得新增台词；原台词必须原样保留。\n"
        "6. 除原剧本台词或专有名词外，不要输出英文标签、英文小标题或英文字段名。\n"
    )

    started = time.perf_counter()
    try:
        output = call_llm(system_prompt, user_prompt, agent_name="director_showrunner")
        output = (output or "").strip() or _fallback_director_brief(state, "empty_showrunner_output")
        output = _localize_director_showrunner_output(output)
        enhanced_script = _extract_enhanced_script(output, source_script)
        director_brief = _director_enhancement_contract(output, enhanced_script)
        runtime = {
            "agent_name": "director_showrunner",
            "mode": "direct",
            "status": "success",
            "output_chars": len(output),
            "enhanced_script_chars": len(enhanced_script),
        }
    except Exception as exc:
        output = _fallback_director_brief(state, f"{type(exc).__name__}: {exc}")
        output = _localize_director_showrunner_output(output)
        enhanced_script = source_script
        director_brief = output
        runtime = {
            "agent_name": "director_showrunner",
            "mode": "direct",
            "status": "fallback",
            "output_chars": len(output),
            "enhanced_script_chars": len(enhanced_script),
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
            "step": "step_0_rhythm",
            "message": "剧情增强完成，节奏总控导演正在分析增强版剧本...（2/6）",
            "script": enhanced_script,
            "original_script": original_script,
            "enhanced_script": enhanced_script,
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
            "director_brief": director_brief,
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
                "message": "快速模式：已跳过场景分析LLM，结构规划师正在拆片...（4/6）",
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
            "message": "结构规划师正在拆片规划...（4/6）",
            "agent_outputs": outputs,
            "knowledge_metadata": knowledge_metadata,
        },
    )
