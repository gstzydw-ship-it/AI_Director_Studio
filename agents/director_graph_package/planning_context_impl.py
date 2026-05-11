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
    filename_scene_items: list[dict[str, Any]] = []
    metadata_scene_items: list[dict[str, Any]] = []
    for index, item in enumerate(manifest):
        if index >= len(images):
            break
        if _is_generated_scene_card_item(item):
            continue
        filename_text = " ".join(
            str(item.get(key) or "")
            for key in ("filename", "name", "label")
        ).lower()
        metadata_text = " ".join(
            str(item.get(key) or "")
            for key in ("purpose", "type", "role")
        ).lower()
        scene_item = {
            "source_index": index,
            "image": images[index],
            "manifest": dict(item),
        }
        if any(marker in filename_text for marker in _SCENE_REFERENCE_MARKERS):
            filename_scene_items.append(scene_item)
            continue
        if any(marker in metadata_text for marker in _SCENE_REFERENCE_MARKERS):
            metadata_scene_items.append(scene_item)

    # Prefer filenames/names that explicitly look like locations. This prevents
    # auto-inferred or stale metadata from turning character portraits into scenes.
    if filename_scene_items:
        return filename_scene_items
    if metadata_scene_items:
        return metadata_scene_items

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


_SCENE_CARD_TEXT_OMIT_KEYS = (
    "reference_bindings",
    "九层输入卡",
    "本场景在场人物",
    "禁止加入人物",
    "戏剧动作关系",
    "人物站位",
    "人物占位",
    "站位姿势",
    "增强约束",
)


def _scene_card_reference_context(
    state: DirectorState,
    scene_item: dict[str, Any] | None,
) -> str:
    """Return only the active scene reference metadata to avoid cross-scene bleed."""
    if scene_item:
        manifest = dict(scene_item.get("manifest") or {})
        label = str(manifest.get("label") or f"@图片{int(scene_item.get('source_index') or 0) + 1}").strip()
        filename = str(manifest.get("filename") or "").strip()
        purpose = str(manifest.get("purpose") or manifest.get("name") or "当前场景空间参考图").strip()
        parts = [part for part in (label, filename, purpose) if part]
        if parts:
            return "当前随请求发送的唯一参考图：" + "｜".join(parts)
    return _reference_context(state) or "当前随请求发送的唯一参考图。"


def _scene_card_spatial_summary(scene_output: str, limit: int = 900) -> str:
    """Keep scene-card prompts spatial-only; remove all people/position marker content."""
    text = (scene_output or "").strip()
    if not text:
        return "无"

    selected: list[str] = []
    skipping_section = False
    key_pattern = "|".join(re.escape(key) for key in _SCENE_CARD_TEXT_OMIT_KEYS)
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if not skipping_section:
                selected.append(line)
            continue

        is_top_level_field = bool(re.match(r"^[^\s#][^:：]{0,40}\s*[:：]", line))
        if re.match(rf"^\s*(?:{key_pattern})\s*[:：]", line):
            skipping_section = True
            continue
        if skipping_section and is_top_level_field:
            skipping_section = False
        if skipping_section:
            continue

        marker_terms = ("人物点位", "人物站位", "站位标记", "彩色圆点", "位置标点", "相机标记")
        if any(term in stripped for term in marker_terms):
            continue
        selected.append(line)

    summary = "\n".join(selected).strip() or "无"
    if len(summary) > limit:
        summary = summary[:limit].rstrip() + "\n...[已截断]..."
    return summary


def _build_scene_card_image_prompt(
    state: DirectorState,
    scene_output: str,
    scene_item: dict[str, Any] | None = None,
    scene_number: int = 1,
    total_scenes: int = 1,
) -> str:
    """Build the second-step prompt for a standalone 3x3 scene view grid."""
    return (
        "基于随请求上传的两张参考图，生成一张独立的 3x3 多机位参考图 / cinematic camera-angle coverage sheet。\n\n"
        "参考图用途：\n"
        "- 参考图1：只用于锁定真实场景的材质、家具外观、色彩、光线、氛围和渲染风格。\n"
        "- 参考图2：只用于锁定新场景开局空间定盘：初始站位可参照的空间边界、基础轴线、方向、门窗、入口、通道、家具和固定物体位置。\n"
        "- 两张参考图都只是参考，不得被复制、裁切、拼贴或直接画进最终图。\n\n"
        "最终输出：\n"
        "- 只输出一张完整图片。\n"
        "- 3列 x 3行九宫格，16:9 横版。\n"
        "- 九个格子铺满整张画布，只保留极细分隔线。\n"
        "- 禁止出现俯视图、说明卡、十格布局、海报拼贴、白边、留白、背景底色、标题栏或未绘制区域。\n\n"
        "空间规则：\n"
        "- 以参考图2为唯一布局依据，图上方=北，右侧=东，下方=南，左侧=西。\n"
        "- 九个视图必须来自同一个空间、同一布局、同一材质、同一光线方向和同一视觉风格。\n"
        "- 不得重新设计房间，不得移动、增删、旋转或替换门窗、入口、通道、沙发、茶几、电视墙、柜体和其他固定物体。\n"
        "- 所有透视画面都必须由俯视布局反推真实相机位置生成，而不是复制、镜像、裁切同一张画面。\n\n"
        "九宫格固定排列：\n"
        "左上：北侧平视，看南。\n"
        "上中：高位看全场。\n"
        "右上：东侧平视，看西。\n"
        "左中：西侧平视，看东。\n"
        "中间：正对主墙看。\n"
        "右中：南侧平视，看北。\n"
        "左下：入口看里面。\n"
        "下中：道具近景。\n"
        "右下：里面看入口。\n\n"
        "四个正向平视机位：\n"
        "- 北侧平视：相机贴近俯视图北边界，眼平高度，水平看南。\n"
        "- 东侧平视：相机贴近俯视图东边界，眼平高度，水平看西。\n"
        "- 南侧平视：相机贴近俯视图南边界，眼平高度，水平看北。\n"
        "- 西侧平视：相机贴近俯视图西边界，眼平高度，水平看东。\n\n"
        "四个方向必须明显不同：\n"
        "- 北、东、南、西四格必须呈现不同的背景面、侧墙、通道、门窗组合、家具侧面或空间边界。\n"
        "- 东侧和西侧必须有清晰的侧墙、侧立面或侧向通道透视，不能仍然正对主入口或主墙。\n"
        "- 如果某方向没有完整墙面，也要画出该方向对应的入口、走廊、窗边、柜体侧面、外部道路或相邻空间边界。\n"
        "- 禁止用同一个入口、主墙、窗墙、沙发、电视墙、门头或主立面画面冒充多个方向。\n\n"
        "其余五个机位：\n"
        "- 高位看全场：空间一角稍高机位，轻微俯视，展示整体空间关系。\n"
        "- 正对主墙看：水平正对最重要的墙面、电视墙、柜体、门头或主背景面。\n"
        "- 入口看里面：位于入口、门口或通道口，水平看向空间内部。\n"
        "- 道具近景：靠近原图已有固定道具，如茶几、沙发、柜体、门把手、标志、台阶或水景边缘，近景中仍能看出周围空间。\n"
        "- 里面看入口：位于空间内部、靠近核心家具或主活动区，水平看向入口、门、通道或来向，只画空景。\n\n"
        "禁止内容：\n"
        "不要人物、人物肩背、视线轴线、箭头、点位标记、运动线、图例、新家具、新装饰、复制画面、镜像画面、鱼眼、超广角畸变或夸张透视。\n\n"
        "标签：\n"
        "每格角落用小号清晰文字标注：\n"
        "北侧平视、高位看全场、东侧平视、西侧平视、正对主墙、南侧平视、入口看里面、道具近景、里面看入口。"
    )


def _build_scene_card_overhead_prompt(
    state: DirectorState,
    scene_output: str,
    scene_item: dict[str, Any] | None = None,
    scene_number: int = 1,
    total_scenes: int = 1,
) -> str:
    """Build the first-step prompt that extracts only the overhead layout."""
    reference_context = _scene_card_reference_context(state, scene_item)
    scene_title = _scene_reference_title(scene_item or {}, scene_number)
    scene_summary = _scene_card_spatial_summary(scene_output)

    return (
        "第一步：只根据随请求发送的这一张场景参考图，生成一张独立的俯视布局图，用于新场景开局空间定盘。\n"
        f"场景 {scene_number}/{total_scenes}: {scene_title}\n"
        "输出只允许是一张俯视布局图，不要九宫格、不要透视内景、不要场景卡、不要拼贴。\n"
        "这张俯视图必须严格依据当前随请求发送的唯一场景参考图推导；不要引用文字摘要里出现的其他图片、其他场景名、人物图或通用豪宅/大堂模板。\n"
        "如果参考图不是俯视角，只能从可见空间关系谨慎推导平面布局：保留参考图里的真实入口、窗、墙面、通道、家具/固定物体、道路/水景/台阶/门头等相对位置；不可凭空新增对称大厅、停车区、水池、柱廊、沙发区、雕塑或绿化。\n"
        "必须清楚画出场景开局可继承的空间边界、基础轴线、墙体/外立面、门窗、入口出口、主要通道、固定家具、固定道具和它们的相对位置；看不见的区域可以简化或留作边界推断，但不能换成另一个场景。\n"
        "固定家具和空间锚点必须继承参考图，不能移动、替换或重排；材质和光线只作为辅助，不要盖过布局表达。\n"
        "俯视图必须铺满整张画布，房间/场地边界尽量贴近画布四边，禁止白边、留白、底板、图例、编号、箭头、机位点、站位点和人物。\n\n"
        f"【当前参考图】\n{reference_context}\n\n"
        f"【仅供锁定空间的文字摘要】\n{scene_summary}"
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
    """Generate the standalone 3x3 scene view grid with the image model."""
    system_prompt = (
        "你是多机位场景参考图生成模型。严格按用户提示生成一张独立 3x3 九宫格图。"
        "输入图片顺序固定：参考图1为原始场景图，参考图2为俯视布局图。"
        "不得复制、裁切、拼贴或直接画入任何参考图；不得输出俯视图、十格布局、说明卡或海报拼贴。"
        "只输出同一空间的九个透视机位空景，必须依据参考图2反推相机位置。"
    )
    result = call_llm(
        system_prompt=system_prompt,
        user_prompt=prompt,
        images_base64=images_base64,
        temperature=0.2,
        agent_name="scene_card_designer",
    )
    return _extract_image_result(result)


def _call_scene_card_overhead_api(prompt: str, images_base64: list[str]) -> str:
    """Generate the first-step overhead layout image."""
    system_prompt = (
        "你是场景俯视布局生成模型。只生成一张独立俯视图，用于下一步九宫格机位推导。"
        "必须从原始场景参考图提取真实空间边界、门窗入口、通道、固定家具和固定道具的相对位置。"
        "不要生成九宫格、不要内景透视、不要人物、不要站位点、不要相机点、不要箭头或图例。"
        "输出要清晰、铺满画布、空间比例稳定，便于下一步严格参考。"
    )
    result = call_llm(
        system_prompt=system_prompt,
        user_prompt=prompt,
        images_base64=images_base64,
        temperature=0.15,
        agent_name="scene_card_designer",
    )
    return _extract_image_result(result)


def _generate_scene_card_with_overhead(
    overhead_prompt: str,
    card_prompt: str,
    scene_image: str,
    session_id: str,
    scene_number: int,
) -> tuple[str, str]:
    """Generate overhead first, then generate a standalone 3x3 view grid from that layout."""
    overhead_result = _call_scene_card_overhead_api(overhead_prompt, [scene_image])
    overhead_path = _save_scene_card_layout_image(overhead_result, session_id, scene_number)
    overhead_image = _file_to_image_data_uri(overhead_path)
    card_result = _call_scene_card_image_api(card_prompt, [scene_image, overhead_image])
    return card_result, overhead_path


def _save_generated_scene_image(data: str, filepath: str) -> str:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

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

    raise RuntimeError("场景参考图接口没有返回可保存的图片。")


def _save_scene_card_image(data: str, session_id: str, scene_number: int = 1) -> str:
    """Save a generated 3x3 scene view grid image and return its local path."""
    output_dir = os.path.join(OUTPUT_DIR, "sessions", session_id, "scene_cards")
    filepath = os.path.join(output_dir, f"scene_grid_{scene_number:02d}.png")
    return _save_generated_scene_image(data, filepath)


def _save_scene_card_layout_image(data: str, session_id: str, scene_number: int = 1) -> str:
    """Save the generated overhead layout used to drive the scene card."""
    output_dir = os.path.join(OUTPUT_DIR, "sessions", session_id, "scene_cards")
    filepath = os.path.join(output_dir, f"scene_layout_{scene_number:02d}.png")
    return _save_generated_scene_image(data, filepath)


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
        if "场景母版图" in role_text or "scene_card" in role_text or "scene_layout" in role_text:
            continue
        kept_images.append(image)
        kept_manifest.append(item)

    for scene_card in scene_cards:
        scene_title = scene_card.get("scene_title") or f"场景{scene_card.get('scene_number') or ''}".strip()
        generated_refs = [
            (
                scene_card.get("layout_path") or "",
                "scene_layout",
                (
                    f"{scene_title}场景俯视布局图：用于新场景开局空间定盘，只锁场景开局初始站位参考、"
                    "固定物、基础轴线、空间边界和入口通道；后续片段不要求逐段标点，"
                    "运动过程由片段出入场状态和视频尾帧承接"
                ),
            ),
            (
                scene_card.get("grid_path") or scene_card.get("image_path") or "",
                "scene_card",
                (
                    f"{scene_title}场景九宫格机位图：与同批俯视布局图配套，"
                    "用于按场景开局空间定盘推导同一空间的基础机位参考"
                ),
            ),
        ]
        for image_path, role, purpose in generated_refs:
            if not image_path:
                continue
            label = f"@图片{len(kept_images) + 1}"
            kept_images.append(_file_to_image_data_uri(image_path))
            kept_manifest.append(
                {
                    "label": label,
                    "filename": os.path.basename(image_path),
                    "purpose": purpose,
                    "type": role,
                    "role": role,
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


_SHOWRUNNER_SCENE_KEEP_FIELDS = (
    "场景信息",
    "道具锚点",
    "固定物体锁定",
    "增强约束",
    "与剧本冲突点",
    "冲突点",
)

_SHOWRUNNER_SCENE_SKIP_FIELDS = (
    "场景参考图需求",
    "光线与材质",
    "reference_bindings",
    "九层输入卡",
    "本场景在场人物",
    "禁止加入人物",
    "戏剧动作关系",
    "人物站位",
    "人物占位",
    "站位姿势",
    "行动路径",
    "运动轨迹",
)

_SHOWRUNNER_SCENE_FORBIDDEN_TERMS = (
    "人物站位",
    "人物占位",
    "站位姿势",
    "行动路径",
    "运动轨迹",
    "人物点位",
    "标点",
    "俯视图上手动",
)


def _compact_scene_context_for_showrunner(scene_context: str, max_chars: int = 700) -> str:
    """Keep only short spatial constraints that the story enhancer can safely use."""
    text = (scene_context or "").strip()
    if not text:
        return ""

    kept: dict[str, list[str]] = {field: [] for field in _SHOWRUNNER_SCENE_KEEP_FIELDS}
    current_field = ""
    field_pattern = re.compile(r"^\s*([^:：\n]{1,32})\s*[:：]\s*(.*)$")

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        match = field_pattern.match(raw_line)
        if match and not raw_line.startswith((" ", "\t", "-", "  -")):
            field = match.group(1).strip()
            value = match.group(2).strip()
            if field in _SHOWRUNNER_SCENE_SKIP_FIELDS:
                current_field = ""
                continue
            if field in _SHOWRUNNER_SCENE_KEEP_FIELDS:
                current_field = field
                if value:
                    kept[field].append(value)
                continue
            current_field = ""
            continue

        if current_field:
            kept[current_field].append(stripped.lstrip("- ").strip())

    lines: list[str] = []
    for field in _SHOWRUNNER_SCENE_KEEP_FIELDS:
        values = [value for value in kept[field] if value]
        if not values:
            continue
        safe_values = [
            value
            for value in values
            if not any(term in value for term in _SHOWRUNNER_SCENE_FORBIDDEN_TERMS)
        ]
        if not safe_values:
            continue
        compact_value = "；".join(safe_values[:2])
        if len(compact_value) > 180:
            compact_value = compact_value[:180].rstrip() + "..."
        lines.append(f"{field}: {compact_value}")

    if not lines:
        return ""

    compact = "\n".join(lines)
    if len(compact) > max_chars:
        compact = compact[:max_chars].rstrip() + "..."
    return compact


def director_showrunner_node(state: DirectorState) -> DirectorState:
    import time

    outputs = _agent_outputs(state)
    source_script = str(state.get("script") or "")
    original_script = str(state.get("original_script") or source_script)
    scene_context_brief = str(state.get("scene_context_brief") or outputs.get("scene_analyst") or "").strip()
    showrunner_scene_context = _compact_scene_context_for_showrunner(scene_context_brief)

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
        "抽象动作因果 相对互动 主线保护 禁止新增台词 禁止改主线 "
        f"画幅 {state.get('aspect_ratio', '16:9')}"
    )
    system_prompt, retrieval_meta = build_system_prompt(
        "你是 AI 短剧流水线里的剧情冲突增强导演。\n"
        "你的职责是在不改变主线剧情的前提下，把原剧本里偏弱、偏概括、偏静态的冲突增强成可拍内容。\n"
        "你不做拆片、不做具体镜头设计、不输出 shot 建议；你只交付增强版剧本和增强依据。\n"
        "你的增强必须是清晰的动作剧本，不是文学化润色；少用形容和比喻，只写观众能看见、演员能执行的动作。\n"
        "禁止输出状态合同、入场状态、出场状态、道具状态变化、禁止连续性等制作合同块；这些只可内化为判断，不能写进增强版剧本。\n"
        "允许增强 L1 动作层和笼统相对互动：动作密度、时间压力、声音压力、已有道具阻碍、靠近、停住、避让、拦住、转身等可见动作。\n"
        "不要写精确站位、具体方位、距离、行走路线、运动轨迹或镜头调度；这些留给用户标注后的镜头导演处理。\n"
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
        f"{showrunner_scene_context or '无参考图/场景预分析；只能根据原始剧本文字增强。'}\n\n"
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
        "2. 可以把静态说明改成笼统可见动作，例如已有角色出现、停住、靠近、避让、拦住、转身、递出或收回道具；不要写具体站位、方位、距离或路线。\n"
        "3. 可以使用原剧本已有道具和环境强化阻力，例如闹钟、电话、水杯、书包、咖啡、公司大门、车辆声音。\n"
        "4. 每两句原台词之间最多补 1-2 个动作节拍；优先写因果动作，不写情绪散文，不把简单动作拆成过多微动作。\n"
        "5. 手机/电话规则：只有原文台词、动作或上下文明示通话时才可使用手机；如果写手机夹在肩上、握在手里或放在一旁，后续动作必须符合单手/双手可执行逻辑。\n"
        "6. 增强版剧本只写场景标题、人物、动作、原台词和必要转场；不要写“状态合同/入场状态/出场状态/道具状态变化/禁止连续性/特写/音效”等合同式或镜头式小标题，除非原文已有。\n"
        "7. 只遵守上方简表里的物理空间硬约束：入口、通道、固定物体和可见道具不能改乱；不要推导或锁定人物站位、行动路径、运动轨迹。\n"
        "8. 没有明确空间信息时，使用“靠近、停下、退开、挡住、绕开、转身看向”等笼统关系词，不写“左侧/右侧/北侧/几米/从A点到B点”等精确调度。\n"
        "9. 不得改变主线剧情：人物关系、公司易主、新老板到达、前夫揭示等核心事实不能变。\n"
        "10. 不得新增台词；原台词必须原样保留。\n"
        "11. 除原剧本台词或专有名词外，不要输出英文标签、英文小标题或英文字段名。\n"
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
        "场景预分析 场景母版图 参考图分析 俯视布局 九宫格机位 空间锚点 固定家具 门窗通道 可见道具 "
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
        "输出必须简短，只分析：场景空间、固定家具、门窗入口、通道、可见道具、光线方向、与剧本冲突点。"
        "不要输出逐段运动标点或完整运动路线；这里只做新场景开局空间定盘：场景开局的初始站位参考、固定物和基础轴线。"
        "后续片段不要求逐段标点，运动过程由片段出入场状态和视频尾帧承接。"
        "不要把参考图里的真人位置、姿态、距离或视线当作固定站位。"
        "凡参考图中可见的固定家具和空间锚点，都要作为不可移动的场景母版规则。",
        "scene_analyst",
        context_hint=scene_hint,
    )
    user_prompt = (
        f"{director_brief_block}\n"
        f"请生成简短场景预分析卡：只给剧情增强导演物理空间边界，并给后续场景生图锁定空间锚点。\n\n"
        f"【剧本】\n{state['script']}\n\n"
        f"【画幅】{state.get('aspect_ratio', '16:9')}\n\n"
        f"【参考图清单】\n{_reference_context(state)}\n\n"
        "【参考图使用边界】\n"
        "1. 参考图只用于提取空间、环境、固定家具、门窗入口、通道、光线方向和关键场景锚点。\n"
        "2. 不从参考图固定人物姿势、人物朝向、人物间距离或视线轴线；参考图里的真人只当作可忽略干扰。\n"
        "3. 场景参考资产只服务新场景开局空间定盘：锁场景开局初始站位参考、固定物、基础轴线和入口通道；后续片段不要求逐段标点，运动过程由片段出入场状态和视频尾帧承接。\n"
        "4. 场景分析必须把可见空间翻译成可继承的文字锚点：入口/电梯/门/走廊/前台/窗/桌椅等物体的相对方位。\n"
        "5. 固定家具和空间锚点必须作为场景母版锁定：茶几、沙发、窗户、门、地毯、床、柜子、台面等一旦在参考图中可见，后续不得移动、替换或重排。\n"
        "6. 如果参考图与剧本文字冲突，不得新增剧情，只能把参考图作为空间和环境基底说明。\n\n"
        f"{_script_fidelity_rules()}\n"
        "【输出 YAML 字段】\n"
        "场景信息: 列出空间类型、入口、主要家具/门/走廊/公司门口等锚点。\n"
        "调度待定: 固定写“场景开局初始站位、固定物和基础轴线可由俯视图/标注锁定；后续片段不要求逐段标点，运动过程由片段出入场状态和视频尾帧承接；场景预分析不推导完整运动路线”。\n"
        "道具锚点: 只列原剧本或参考图可见的关键道具及位置；不新增手机、照片、咖啡等未确认道具。\n"
        "光线与材质: 列出参考图里的主光方向、材质气质和空间尺度。\n"
        "场景参考图需求: 一句话说明需要输出两张独立图片：第一张是俯视布局图，只锁定新场景开局初始站位参考、空间边界、固定物和基础轴线；第二张是 16:9 的 3x3 九宫格机位图，严格依据俯视图生成东西南北四个正向平视图，并补充高位看全场、正对主墙、入口看里面、道具近景、里面看入口。不要要求生成左侧俯视图+右侧九宫格的十格场景卡。\n"
        "固定物体锁定: 列出参考图中不可移动的固定家具和空间锚点，强调后续只能换机位或裁切，不能移动物体。\n"
        "增强约束: 给剧情增强导演的简短物理空间边界，只提醒场景开局空间、固定家具、门窗通道、基础轴线和道具不能改乱；不要写逐段动作路线。\n"
    )
    scene_ref_items = _scene_reference_items(state)
    ref_images = [item["image"] for item in scene_ref_items] or None
    agent_for_call = "scene_vision_analyst" if ref_images else "scene_analyst"
    knowledge_metadata = _record_knowledge_metadata(state, "scene_analyst", scene_hint, retrieval_meta)
    try:
        output = call_llm(system_prompt, user_prompt, images_base64=ref_images, agent_name=agent_for_call)
    except Exception as exc:
        if ref_images:
            print(f"  [scene_analyst] vision model failed, retrying text-only scene analysis: {exc}")
            fallback_prompt = (
                f"{user_prompt}\n\n"
                "【降级说明】参考图网关连接失败，本次不要编造图像细节；"
                "只基于剧本文字和参考图清单中已有的名称、用途、顺序信息生成场景预分析。"
            )
            try:
                output = call_llm(system_prompt, fallback_prompt, images_base64=None, agent_name="scene_analyst", max_retries=1)
            except Exception as fallback_exc:
                print(f"  [scene_analyst] text fallback failed, using local scene card: {fallback_exc}")
                output = (
                    "mode: degraded_local_scene_card\n"
                    f"aspect_ratio: {state.get('aspect_ratio', '16:9')}\n"
                    "source: original_script_and_reference_manifest_only\n"
                    "scene_info: |\n"
                    "  LLM vision gateway failed, so only script text and reference-image manifest were used.\n"
                    "schedule_pending: 场景开局初始站位、固定物和基础轴线可由俯视图/标注锁定；后续片段不要求逐段标点，运动过程由片段出入场状态和视频尾帧承接；场景预分析不推导完整运动路线。\n"
                    "reference_manifest: |\n"
                    f"{_reference_context(state) or '  none'}\n"
                    "notes:\n"
                    "  - Do not invent visual details from unavailable images.\n"
                    "  - Downstream agents must keep to the original script and explicit reference-image labels only.\n"
                )
        else:
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
            overhead_prompt = _build_scene_card_overhead_prompt(
                state,
                output,
                scene_item=scene_item,
                scene_number=scene_number,
                total_scenes=total_scenes,
            )
            scene_card_prompt = _build_scene_card_image_prompt(
                state,
                output,
                scene_item=scene_item,
                scene_number=scene_number,
                total_scenes=total_scenes,
            )
            image_result, overhead_path = _generate_scene_card_with_overhead(
                overhead_prompt,
                scene_card_prompt,
                scene_item["image"],
                session_id,
                scene_number,
            )
            scene_card_image = _save_scene_card_image(image_result, session_id, scene_number)
            scene_cards.append(
                {
                    "scene_number": str(scene_number),
                    "scene_title": scene_title,
                    "image_path": scene_card_image,
                    "grid_path": scene_card_image,
                    "layout_path": overhead_path,
                    "layout_prompt": overhead_prompt,
                    "prompt": scene_card_prompt,
                    "grid_prompt": scene_card_prompt,
                }
            )

        updated_reference_images, updated_reference_manifest = _append_scene_card_references(
            state,
            scene_cards,
        )
        scene_card_lines = "\n".join(
            f"  - 场景{card['scene_number']}：{card['scene_title']}\n"
            f"    俯视图 → {card['layout_path']}\n"
            f"    九宫格 → {card['grid_path']}"
            for card in scene_cards
        )
        output = (
            f"{output.rstrip()}\n\n"
            "场景参考图: |\n"
            f"{scene_card_lines}\n"
            "  流程：每个场景输出两张独立图片：一张俯视布局图，一张 3x3 九宫格机位图。\n"
            "  用途：俯视图只锁新场景开局初始站位参考、固定物、基础轴线和空间结构；后续片段不要求逐段标点，运动过程由片段出入场状态和视频尾帧承接。\n"
        )
        outputs["scene_card_prompt"] = scene_cards[0]["prompt"]
        outputs["scene_card_image"] = scene_cards[0]["image_path"]
        outputs["scene_card_images"] = json.dumps(scene_cards, ensure_ascii=False)
        outputs["scene_layout_prompt"] = scene_cards[0]["layout_prompt"]
        outputs["scene_layout_image"] = scene_cards[0]["layout_path"]
        outputs["scene_grid_prompt"] = scene_cards[0]["grid_prompt"]
        outputs["scene_grid_image"] = scene_cards[0]["grid_path"]

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
        update_payload["message"] = f"场景预分析和 {len(scene_cards)} 组俯视图/九宫格图已完成，剧情增强导演正在按场景约束增强剧本...（2/8）"
        update_payload["scene_card_image"] = scene_cards[0]["image_path"]
        update_payload["scene_card_prompt"] = scene_cards[0]["prompt"]
        update_payload["scene_card_images"] = scene_cards
        update_payload["scene_layout_image"] = scene_cards[0]["layout_path"]
        update_payload["scene_layout_prompt"] = scene_cards[0]["layout_prompt"]
        update_payload["scene_grid_image"] = scene_cards[0]["grid_path"]
        update_payload["scene_grid_prompt"] = scene_cards[0]["grid_prompt"]
    if updated_reference_images is not None and updated_reference_manifest is not None:
        update_payload["reference_image_b64s"] = updated_reference_images
        update_payload["reference_image_manifest"] = updated_reference_manifest
        update_payload["reference_image_count"] = len(updated_reference_images)

    return _persist_update(state, update_payload)
