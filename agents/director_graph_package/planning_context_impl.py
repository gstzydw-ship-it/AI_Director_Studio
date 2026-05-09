"""Package-local planning context nodes (showrunner + scene analyst) extracted from legacy_impl."""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import yaml

from .helpers import build_system_prompt
from .llm import _get_llm_settings, call_llm
from .state_store import _agent_outputs, _persist_update
from .types import DirectorState, OUTPUT_DIR

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


_SCENE_REFERENCE_MARKERS = (
    "scene",
    "space",
    "location",
    "environment",
    "set",
    "场景",
    "空间",
    "环境",
    "地点",
    "场地",
    "公寓",
    "客厅",
    "卧室",
    "厨房",
    "餐厅",
    "门口",
    "大堂",
    "公司",
    "集团",
    "办公室",
    "会议室",
    "小区",
    "街道",
    "走廊",
    "电梯",
    "酒店",
    "医院",
    "学校",
    "房间",
    "庭院",
    "车库",
    "停车场",
)


def _is_generated_scene_card_item(item: dict[str, Any]) -> bool:
    role_text = " ".join(
        str(item.get(key) or "")
        for key in ("role", "type", "purpose", "name", "filename")
    ).lower()
    return "scene_card" in role_text or "场景母版图" in role_text


def _scene_reference_items(state: DirectorState) -> list[dict[str, Any]]:
    """Return all original scene reference images, excluding generated cards."""
    images = list(state.get("reference_image_b64s") or [])
    if not images:
        return []

    manifest = list(state.get("reference_image_manifest") or [])
    items: list[dict[str, Any]] = []
    for index, item in enumerate(manifest):
        if index >= len(images):
            break
        if _is_generated_scene_card_item(item):
            continue
        haystack = " ".join(
            str(item.get(key) or "")
            for key in ("label", "filename", "purpose", "type", "role", "name")
        ).lower()
        if any(marker in haystack for marker in _SCENE_REFERENCE_MARKERS):
            items.append(
                {
                    "source_index": index,
                    "image": images[index],
                    "manifest": dict(item),
                }
            )

    if items:
        return items

    fallback_manifest = dict(manifest[0]) if manifest else {}
    if _is_generated_scene_card_item(fallback_manifest):
        return []
    return [{"source_index": 0, "image": images[0], "manifest": fallback_manifest}]


def _scene_reference_images(state: DirectorState) -> list[str]:
    return [item["image"] for item in _scene_reference_items(state)]


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


def _scene_reference_title(scene_item: dict[str, Any], scene_number: int) -> str:
    manifest = dict(scene_item.get("manifest") or {})
    label = str(manifest.get("label") or f"@图片{int(scene_item.get('source_index') or 0) + 1}").strip()
    filename = str(manifest.get("filename") or "").strip()
    purpose = str(manifest.get("purpose") or manifest.get("name") or "").strip()
    title_bits = [bit for bit in (label, filename, purpose) if bit]
    return "｜".join(title_bits) if title_bits else f"场景{scene_number}"


def _build_scene_card_image_prompt(
    state: DirectorState,
    scene_output: str,
    scene_item: dict[str, Any] | None = None,
    scene_number: int = 1,
    total_scenes: int = 1,
) -> str:
    """Build the image prompt for a reusable visual scene master card."""
    aspect_ratio = str(state.get("aspect_ratio") or "9:16")
    reference_context = _reference_context(state) or "未提供文字清单；以随请求发送的场景参考图为准。"
    scene_title = _scene_reference_title(scene_item or {}, scene_number)
    scene_summary = (scene_output or "").strip()
    if len(scene_summary) > 1800:
        scene_summary = scene_summary[:1800].rstrip() + "\n...[已截断]..."

    return (
        "请根据随请求发送的场景参考图，生成一张“场景母版参考图”。\n"
        f"当前要生成的是第 {scene_number}/{total_scenes} 个场景母版：{scene_title}。\n"
        "只分析并重建当前这一个场景；不要把其他场景参考图、人物参考图或上一张场景母版混入本图。\n"
        f"整张图片使用 {aspect_ratio} 画幅，适合后续作为分镜流程图和 Seedance 2.0 的场景参考。\n\n"
        "画面结构：\n"
        "1. 图片必须包含五个清晰分区：一个俯视布局图，四个同一场景的固定视角参考图。\n"
        "2. 俯视布局图展示房间/空间边界、入口、窗、门、沙发、茶几、地毯、床、柜子、通道等固定物体的相对位置。\n"
        "3. 四个固定视角参考图必须是从房间四面墙壁位置看向房间内景象的正面内景视角：入口墙向内、入口对面墙向内、左侧墙向内、右侧墙向内。\n"
        "4. 五个分区必须来自同一个场景，不允许变成五个不同房间或不同装修版本。\n\n"
        "空间锁定硬规则：\n"
        "1. 固定家具和空间锚点必须继承参考图，不能移动、替换、重新摆放或新增同类替代物。\n"
        "2. 如果参考图中有茶几、沙发、窗户、门、地毯、床头、柜子、台面，它们的相对位置必须一致。\n"
        "3. 视角变化只能改变摄影机所在墙面位置，不能改变场景结构；四个视角看到的是同一套空间，镜头均朝向房间中心。\n"
        "4. 不生成剧情动作、台词、字幕、对白气泡、人物运动线、箭头说明或夸张漫画符号。\n"
        "5. 可以保留极淡人物比例剪影作为尺度参考，但不要画具体表演动作；如果无法确定人物，保持无人场景。\n\n"
        "视觉要求：写实影视场景参考图，干净、明亮、空间关系清楚，家具轮廓稳定，适合后续镜头导演和分镜生图继承。\n"
        "分区标题可以放在每个分区外缘的小标签中，只能写中文：俯视布局、入口墙向内、对面墙向内、左侧墙向内、右侧墙向内；"
        "不要把文字写在家具、墙面或道具表面。\n\n"
        f"【参考图清单】\n{reference_context}\n\n"
        f"【场景预分析文字卡】\n{scene_summary or '无'}"
    )


def _extract_image_result(result: str) -> str:
    """Return URL/data URI/raw base64 from an image API text response."""
    text = (result or "").strip()
    url_match = re.search(r"https?://\S+\.(?:png|jpg|jpeg|webp|gif)", text, re.IGNORECASE)
    if url_match:
        return url_match.group(0)

    data_uri_match = re.search(r"data:image/\w+;base64,[A-Za-z0-9+/=]+", text)
    if data_uri_match:
        return data_uri_match.group(0)

    if re.fullmatch(r"[A-Za-z0-9+/=]+", text):
        return f"data:image/png;base64,{text}"

    return text


def _call_scene_card_image_api(prompt: str, images_base64: list[str]) -> str:
    """Generate the visual scene master card with the image model."""
    system_prompt = (
        "你是场景母版图生成模型。请根据参考图生成一张可复用的场景参考卡："
        "必须包含一个俯视布局图和四个同一场景的固定视角图；四个视角要从房间四面墙壁位置看向房间内部。"
        "重点是锁定固定家具、门窗、通道、光线和空间轴线；不得移动或重排固定物体。"
    )
    result = call_llm(
        system_prompt=system_prompt,
        user_prompt=prompt,
        images_base64=images_base64,
        temperature=0.25,
        agent_name="scene_card_designer",
    )
    return _extract_image_result(result)


def _save_scene_card_image(data: str, session_id: str, scene_number: int = 1) -> str:
    """Save a generated scene master card image and return its local path."""
    output_dir = os.path.join(OUTPUT_DIR, "sessions", session_id, "scene_cards")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"scene_card_{scene_number:02d}.png")

    if os.path.exists(data):
        return data

    if data.startswith("data:"):
        _header, _sep, b64 = data.partition(",")
        raw = base64.b64decode(b64)
        with open(filepath, "wb") as f:
            f.write(raw)
        return filepath

    if data.startswith("http"):
        import httpx

        with httpx.Client(timeout=60.0) as client:
            resp = client.get(data)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
        return filepath

    raise RuntimeError("场景母版图接口没有返回可保存的图片。")


def _file_to_image_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _append_scene_card_references(
    state: DirectorState,
    scene_cards: list[dict[str, str]],
) -> tuple[list[str], list[dict[str, str]]]:
    """Append generated scene cards to the reference image set."""
    images = list(state.get("reference_image_b64s") or [])
    manifest = [dict(item) for item in list(state.get("reference_image_manifest") or [])]
    while len(manifest) < len(images):
        manifest.append({})

    kept_images: list[str] = []
    kept_manifest: list[dict[str, str]] = []
    for index, image in enumerate(images):
        item = manifest[index] if index < len(manifest) else {}
        role_text = " ".join(str(item.get(key) or "") for key in ("role", "type", "purpose", "name"))
        if "场景母版图" in role_text or "scene_card" in role_text:
            continue
        kept_images.append(image)
        kept_manifest.append(item)

    for scene_card in scene_cards:
        image_path = scene_card.get("image_path") or ""
        if not image_path:
            continue
        label = f"@图片{len(kept_images) + 1}"
        scene_title = scene_card.get("scene_title") or f"场景{scene_card.get('scene_number') or ''}".strip()
        kept_images.append(_file_to_image_data_uri(image_path))
        kept_manifest.append(
            {
                "label": label,
                "filename": os.path.basename(image_path),
                "purpose": (
                    f"{scene_title}场景母版图：俯视布局和四个固定视角，"
                    "用于后续分镜流程图与 Seedance 2.0 场景参考"
                ),
                "type": "scene_card",
                "role": "scene_card",
                "name": scene_title,
            }
        )
    return kept_images, kept_manifest


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
    scene_context_brief = str(state.get("scene_context_brief") or outputs.get("scene_analyst") or "").strip()

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
        "你的增强必须是清晰的动作剧本，不是文学化润色；少用形容和比喻，只写观众能看见、演员能执行的动作。\n"
        "禁止输出状态合同、入场状态、出场状态、道具状态变化、禁止连续性等制作合同块；这些只可内化为判断，不能写进增强版剧本。\n"
        "允许增强 L1 动作层与 L2 调度层：动作密度、时间压力、声音压力、已有道具阻碍、已有角色进入/拦住/停住/转身等可见调度。\n"
        "禁止直接改动主线剧情、人物关系、剧情结果和原台词；禁止新增未确认的新人物、新台词、新关键道具、新误会或新反转。\n"
        "道具处理必须保持因果清晰：只使用原剧本已经出现或由原台词明确暗示的道具；每个道具只在必要时变化一次，不要为了细节堆动作。\n"
        "手机/电话尤其要谨慎：如果原台词暗示正在通话，可以写乔熙拿着或放下手机；通话结束后必须写清手机去向，不能让手机持续占手却又同时完成双手动作。\n"
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
        "【场景预分析约束】\n"
        f"{scene_context_brief or '无参考图/场景预分析；只能根据原始剧本文字增强。'}\n\n"
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
        "4. 每两句原台词之间最多补 1-2 个动作节拍；优先写因果动作，不写情绪散文，不把简单动作拆成过多微动作。\n"
        "5. 手机/电话规则：只有原文台词、动作或上下文明示通话时才可使用手机；如果写手机夹在肩上、握在手里或放在一旁，后续动作必须符合单手/双手可执行逻辑。\n"
        "6. 增强版剧本只写场景标题、人物、动作、原台词和必要转场；不要写“状态合同/入场状态/出场状态/道具状态变化/禁止连续性/特写/音效”等合同式或镜头式小标题，除非原文已有。\n"
        "7. 必须遵守场景预分析约束：人物站位、姿势、朝向、空间锚点、可见道具和参考图基底不能被剧情增强改乱。\n"
        "8. 不得改变主线剧情：人物关系、公司易主、新老板到达、前夫揭示等核心事实不能变。\n"
        "9. 不得新增台词；原台词必须原样保留。\n"
        "10. 除原剧本台词或专有名词外，不要输出英文标签、英文小标题或英文字段名。\n"
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
                "message": "剧情增强完成，节奏总控导演正在分析增强版剧本...（3/8）",
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
                "step": "step_0_enhance",
                "message": "快速模式：已生成本地场景预分析，剧情增强导演正在运行...（2/8）",
                "agent_outputs": outputs,
                "scene_context_brief": output,
                "knowledge_metadata": knowledge_metadata,
            },
        )

    scene_hint = (
        "场景预分析 场景母版图 参考图分析 俯视布局 四视角 人物站位 姿势 朝向 空间锚点 可见道具 "
        f"aspect_ratio {state.get('aspect_ratio', '16:9')}"
    )
    system_prompt, retrieval_meta = build_system_prompt(
        "你是一位短剧场景预分析师，运行在剧情增强导演之前。\n"
        "你的任务不是拆片、不是增强剧情、不是写镜头方案，而是把参考图和原剧本中的场景信息转成文字场景卡，"
        "并配合生成一张可被后续分镜流程图和 Seedance 2.0 继承的场景母版图。\n\n"
        "【绝对禁令】你只能提取剧本原文中明确存在的信息。\n"
        "禁止推测、补充或扩展剧本中没有出现的内容。\n"
        "禁止新增剧本中没有的员工反应、旁白、低声议论、表情反应或任何解释性信息。\n"
        "如果原剧本没有写员工说话，分析卡中不得出现员工对白或低语。\n"
        "如果原剧本没有写某个动作，分析卡中不得出现该动作。\n"
        "输出必须简短，只分析：人物形象占位、人物站位/姿势/朝向、场景空间、固定家具、可见道具、与剧本冲突点。"
        "凡参考图中可见的固定家具和空间锚点，都要作为不可移动的场景母版规则。",
        "scene_analyst",
        context_hint=scene_hint,
    )
    user_prompt = (
        f"{director_brief_block}\n"
        f"请为剧情增强导演和后续场景母版生图生成场景预分析卡。\n\n"
        f"【剧本】\n{state['script']}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n\n"
        f"【参考图清单】\n{_reference_context(state)}\n\n"
        "【参考图使用边界】\n"
        "1. 参考图只用于提取空间、环境、人物站位、人物姿势、人物朝向、人物间距离、视线轴线和关键场景锚点。\n"
        "2. 人物形象只做占位描述，例如“女主/孩子/西装男/秘书群体”；不要展开五官、发型、服装纹理。\n"
        "3. 场景分析必须把可见空间翻译成可继承的文字锚点：入口/电梯/门/走廊/前台/窗/桌椅等物体的相对方位，以及人物与这些锚点的关系。\n"
        "4. 固定家具和空间锚点必须作为场景母版锁定：茶几、沙发、窗户、门、地毯、床、柜子、台面等一旦在参考图中可见，后续不得移动、替换或重排。\n"
        "5. 如果参考图与剧本文字冲突，不得新增剧情，只能把参考图作为空间和环境基底说明。\n\n"
        f"{_script_fidelity_rules()}\n"
        "【输出 YAML 字段】\n"
        "人物占位: 每个可见人物/群体一句话，写身份占位和可见姿态。\n"
        "站位姿势: 列出人物相对位置、朝向、距离、是否坐/站/移动。\n"
        "场景信息: 列出空间类型、入口、主要家具/门/走廊/公司门口等锚点。\n"
        "道具锚点: 只列原剧本或参考图可见的关键道具及位置；不新增手机、照片、咖啡等未确认道具。\n"
        "场景母版图需求: 一句话说明需要生成俯视布局图，以及从入口墙、入口对面墙、左侧墙、右侧墙位置看向房间内景象的四个正面内景固定视角，全部继承同一场景结构。\n"
        "固定物体锁定: 列出参考图中不可移动的固定家具和空间锚点，强调后续只能换机位或裁切，不能移动物体。\n"
        "增强约束: 给剧情增强导演的简短边界，提醒哪些空间/站位/道具不能改乱。\n"
    )
    scene_ref_items = _scene_reference_items(state)
    ref_images = [item["image"] for item in scene_ref_items] or None
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
    scene_cards: list[dict[str, str]] = []
    updated_reference_images: list[str] | None = None
    updated_reference_manifest: list[dict[str, str]] | None = None
    if scene_ref_items:
        from ..request_context import request_session_id

        session_id = request_session_id.get("local")
        total_scenes = len(scene_ref_items)
        for scene_number, scene_item in enumerate(scene_ref_items, start=1):
            scene_title = _scene_reference_title(scene_item, scene_number)
            scene_card_prompt = _build_scene_card_image_prompt(
                state,
                output,
                scene_item=scene_item,
                scene_number=scene_number,
                total_scenes=total_scenes,
            )
            image_result = _call_scene_card_image_api(scene_card_prompt, [scene_item["image"]])
            scene_card_image = _save_scene_card_image(image_result, session_id, scene_number)
            scene_cards.append(
                {
                    "scene_number": str(scene_number),
                    "scene_title": scene_title,
                    "image_path": scene_card_image,
                    "prompt": scene_card_prompt,
                }
            )

        updated_reference_images, updated_reference_manifest = _append_scene_card_references(
            state,
            scene_cards,
        )
        scene_card_lines = "\n".join(
            f"  - 场景{card['scene_number']}：{card['scene_title']} → {card['image_path']}"
            for card in scene_cards
        )
        output = (
            f"{output.rstrip()}\n\n"
            "场景母版图: |\n"
            f"{scene_card_lines}\n"
            "  用途：每个场景单独作为后续分镜流程图与 Seedance 2.0 场景参考；每张图包含俯视布局和四个固定视角。\n"
        )
        outputs["scene_card_prompt"] = scene_cards[0]["prompt"]
        outputs["scene_card_image"] = scene_cards[0]["image_path"]
        outputs["scene_card_images"] = json.dumps(scene_cards, ensure_ascii=False)

    outputs["scene_analyst"] = output
    update_payload: dict[str, Any] = {
        "status": "running_phase_1",
        "step": "step_0_enhance",
        "message": "场景预分析完成，剧情增强导演正在按场景约束增强剧本...（2/8）",
        "agent_outputs": outputs,
        "scene_context_brief": output,
        "knowledge_metadata": knowledge_metadata,
    }
    if scene_cards:
        update_payload["message"] = f"场景预分析和 {len(scene_cards)} 张场景母版图已完成，剧情增强导演正在按场景约束增强剧本...（2/8）"
        update_payload["scene_card_image"] = scene_cards[0]["image_path"]
        update_payload["scene_card_prompt"] = scene_cards[0]["prompt"]
        update_payload["scene_card_images"] = scene_cards
    if updated_reference_images is not None and updated_reference_manifest is not None:
        update_payload["reference_image_b64s"] = updated_reference_images
        update_payload["reference_image_manifest"] = updated_reference_manifest
        update_payload["reference_image_count"] = len(updated_reference_images)

    return _persist_update(state, update_payload)
