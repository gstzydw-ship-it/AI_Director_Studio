from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"

RULE_FIELDS = [
    "rule_id",
    "title",
    "doc_type",
    "rule_type",
    "agent_scope",
    "priority",
    "status",
    "runtime_retrieval",
    "retrieval_key",
    "applies_when",
    "avoid_when",
    "signals",
    "scene_types",
    "events",
    "risks",
    "dialogue_types",
    "aspect_ratios",
    "applies_to",
    "source_files",
    "conflicts_with",
    "supersedes",
]

CASE_FIELDS = [
    "case_title",
    "doc_type",
    "served_agents",
    "scene_types",
    "events",
    "dialogue_types",
    "visual_constraints",
    "risks",
    "reusable_pattern",
    "aspect_ratio",
    "runtime_retrieval",
    "source_files",
]

PRIORITY_ALIASES = {
    "hard": "P0",
    "critical": "P0",
    "must": "P0",
    "high": "P1",
    "medium": "P3",
    "normal": "P3",
    "low": "P5",
}

AGENT_DEFAULTS = {
    "action": ["shot_director", "shot_director_blocking", "quality_inspector"],
    "continuity": ["story_planner", "shot_director", "prompt_compiler", "quality_inspector"],
    "prompt_compiler": ["prompt_compiler", "quality_inspector"],
    "quality_inspector": ["quality_inspector"],
    "rhythm_rewrite_director": ["rhythm_rewrite_director", "story_planner", "quality_inspector"],
    "scene_analyst": ["scene_analyst", "story_planner"],
    "shared": ["shared"],
    "shot_director": ["shot_director", "prompt_compiler", "quality_inspector"],
    "shot_director_blocking": ["shot_director_blocking", "quality_inspector"],
    "shot_director_guard": ["shot_director_guard", "quality_inspector"],
    "shot_director_layout": ["shot_director_layout", "quality_inspector"],
    "story_planner": ["story_planner", "shot_director", "quality_inspector"],
}

RULE_TYPE_DEFAULTS = {
    "action": "action_coverage",
    "continuity": "continuity",
    "prompt_compiler": "prompt_compilation",
    "quality_inspector": "quality_control",
    "rhythm_rewrite_director": "rhythm_rewrite",
    "scene_analyst": "scene_analysis",
    "shared": "global_policy",
    "shot_director": "shot_calling",
    "shot_director_blocking": "blocking",
    "shot_director_guard": "guard",
    "shot_director_layout": "layout",
    "story_planner": "segment_planning",
}

TAG_RULES = [
    ("aspect_ratios", "9:16", ["9:16", "竖屏", "vertical"]),
    ("aspect_ratios", "16:9", ["16:9", "横屏"]),
    ("scene_types", "elevator", ["电梯", "门缝"]),
    ("scene_types", "dialogue", ["对白", "台词", "对话", "正反打", "过肩"]),
    ("scene_types", "action", ["动作", "受击", "碰撞", "追逐", "冲入"]),
    ("scene_types", "suspense", ["悬念", "未知", "探索", "揭示"]),
    ("scene_types", "intimacy_privacy", ["换衣", "身体", "亲密", "隐私"]),
    ("events", "rush_in", ["冲入", "闯入", "挤入"]),
    ("events", "collision", ["碰撞", "撞", "受击", "压住"]),
    ("events", "waist_support", ["扶腰", "腰侧", "搂住", "托住"]),
    ("events", "door_state", ["电梯门", "门缝", "开门", "关门", "门状态"]),
    ("events", "reaction", ["反应", "停顿", "沉默", "愣住"]),
    ("events", "cut", ["切镜", "切点", "cut_point", "cut"]),
    ("events", "tailframe", ["尾帧", "首帧", "first_frame", "tailframe"]),
    ("events", "reference_binding", ["参考图", "reference", "绑定"]),
    ("dialogue_types", "teasing", ["调侃", "打趣", "玩笑"]),
    ("dialogue_types", "argument_escalation", ["争吵", "质问", "爆发", "冲突"]),
    ("dialogue_types", "long_dialogue_compression", ["长对白", "访谈", "解释"]),
    ("dialogue_types", "reaction_beat", ["听者", "反应镜头", "停顿"]),
    ("risks", "door_state_jump", ["门又开", "重新打开", "电梯门", "门缝"]),
    ("risks", "romanticize_collision", ["碰撞", "扶腰", "亲密", "暧昧"]),
    ("risks", "axis_confusion", ["越轴", "轴线", "左右关系"]),
    ("risks", "vertical_closeup_overuse", ["竖屏", "特写限频", "近景过密"]),
    ("risks", "script_invention_risk", ["剧本外", "新增", "不得发明", "忠实"]),
    ("risks", "reference_misuse", ["参考图", "首帧", "尾帧", "绑定"]),
    ("risks", "privacy_body", ["身体", "换衣", "隐私"]),
    ("risks", "blood_avoidance", ["暴力", "血", "受击"]),
    ("signals", "vertical_framing", ["9:16", "竖屏", "画幅"]),
    ("signals", "tailframe_lock", ["尾帧", "首帧", "first_frame", "tailframe"]),
    ("signals", "dialogue_coverage", ["对白", "台词", "听者", "反应镜头"]),
    ("signals", "action_coverage", ["动作", "受击", "碰撞"]),
    ("signals", "continuity_lock", ["连续性", "承接", "状态"]),
    ("signals", "reference_binding", ["参考图", "reference", "绑定"]),
]

VISUAL_RULES = [
    ("visual_constraints", "wide_shot", ["全景", "远景"]),
    ("visual_constraints", "medium_shot", ["中景", "半身"]),
    ("visual_constraints", "closeup", ["近景", "特写"]),
    ("visual_constraints", "over_shoulder", ["过肩", "OTS"]),
    ("visual_constraints", "shot_reverse_shot", ["正反打", "反打"]),
    ("visual_constraints", "reaction_shot", ["反应镜头", "听者反应"]),
    ("visual_constraints", "handheld", ["手持", "晃动"]),
    ("visual_constraints", "focus_pull", ["焦点转移", "浅焦", "虚焦"]),
    ("visual_constraints", "offscreen_space", ["画外", "省略"]),
]

CASE_OVERRIDES = {
    "动作转场": {"events": ["match_action", "scene_change"], "served_agents": ["story_planner", "shot_director"]},
    "双人对话": {"dialogue_types": ["argument_escalation"], "served_agents": ["shot_director", "shot_director_blocking"]},
    "访谈": {"dialogue_types": ["long_dialogue_compression"], "visual_constraints": ["cutaway_reaction"]},
    "角度": {"risks": ["power_angle_mismatch"], "visual_constraints": ["high_angle", "low_angle"]},
    "浅焦": {"scene_types": ["psychology_fantasy"], "visual_constraints": ["focus_pull", "shallow_focus"]},
    "情绪升级": {"events": ["violence", "reaction"], "risks": ["blood_avoidance"]},
    "换衣": {"risks": ["privacy_body"], "visual_constraints": ["offscreen_space"]},
    "追逐": {"scene_types": ["pursuit"], "visual_constraints": ["handheld"]},
    "越轴": {"risks": ["axis_confusion"], "scene_types": ["psychology_fantasy"]},
    "进门": {"events": ["enter_unknown_space"], "scene_types": ["suspense"]},
}


def _read_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    text = text.lstrip("\ufeff")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, flags=re.S)
    if not match:
        return {}, text
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        metadata = {}
    return (metadata if isinstance(metadata, dict) else {}), text[match.end():]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_as_list(item))
        return result
    if isinstance(value, dict):
        return [f"{key}:{val}" for key, val in value.items()]
    return [item.strip() for item in re.split(r"[,，;；\n]+", str(value)) if item.strip()]


def _merge_list(existing: Any, additions: list[str]) -> list[str]:
    seen = set()
    merged: list[str] = []
    for item in _as_list(existing) + additions:
        item = str(item).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _title_from_body(path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    return path.stem


def _match_tags(text: str, rules: list[tuple[str, str, list[str]]]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    lowered = text.lower()
    for field, tag, needles in rules:
        if any(needle.lower() in lowered for needle in needles):
            found.setdefault(field, []).append(tag)
    return found


def _retrieval_keys(metadata: dict[str, Any], path: Path) -> list[str]:
    base = path.stem.lower().replace("_", "-")
    keys = [base]
    for field in ("signals", "events", "risks", "dialogue_types", "scene_types"):
        for tag in _as_list(metadata.get(field)):
            keys.append(f"{field}.{tag}")
    return keys


def _ordered(metadata: dict[str, Any], order: list[str]) -> dict[str, Any]:
    ordered = {field: metadata[field] for field in order if field in metadata}
    for key, value in metadata.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _dump(metadata: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False, width=1000).strip()
    return f"---\n{dumped}\n---\n\n{body.lstrip()}"


def tag_rule(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    metadata, body = _read_frontmatter(text)
    folder = path.parent.name
    metadata.setdefault("rule_id", path.stem)
    metadata.setdefault("title", _title_from_body(path, body))
    metadata["doc_type"] = "rule_card"
    metadata.setdefault("rule_type", RULE_TYPE_DEFAULTS.get(folder, folder))
    metadata["agent_scope"] = _merge_list(metadata.get("agent_scope"), AGENT_DEFAULTS.get(folder, [folder]))
    metadata["priority"] = PRIORITY_ALIASES.get(str(metadata.get("priority", "P3")).lower(), metadata.get("priority", "P3"))
    metadata.setdefault("status", "active")
    metadata["runtime_retrieval"] = metadata.get("runtime_retrieval") is not False

    tag_text = f"{path.stem}\n{metadata.get('title', '')}\n{body}"
    matched = _match_tags(tag_text, TAG_RULES)
    for field, values in matched.items():
        metadata[field] = _merge_list(metadata.get(field), values)

    metadata["retrieval_key"] = _merge_list(metadata.get("retrieval_key"), _retrieval_keys(metadata, path))
    metadata.setdefault("applies_when", _as_list(metadata.get("applies_to"))[:3])
    metadata.setdefault("avoid_when", [])
    metadata.setdefault("conflicts_with", [])
    metadata.setdefault("supersedes", [])

    new_text = _dump(_ordered(metadata, RULE_FIELDS), body)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def tag_case(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    metadata, body = _read_frontmatter(text)
    title = metadata.get("case_title") or metadata.get("title") or _title_from_body(path, body)
    metadata["case_title"] = str(title)
    metadata["doc_type"] = "case_card"
    metadata["served_agents"] = _merge_list(
        metadata.get("served_agents"),
        ["scene_analyst", "story_planner", "shot_director", "shot_director_blocking", "quality_inspector"],
    )
    metadata["aspect_ratio"] = metadata.get("aspect_ratio") or "unspecified"
    metadata["runtime_retrieval"] = metadata.get("runtime_retrieval") is not False

    tag_text = f"{path.stem}\n{metadata.get('case_title', '')}\n{body}"
    for rules in (TAG_RULES, VISUAL_RULES):
        matched = _match_tags(tag_text, rules)
        for field, values in matched.items():
            metadata[field] = _merge_list(metadata.get(field), values)

    for needle, override in CASE_OVERRIDES.items():
        if needle in path.stem or needle in str(metadata.get("case_title", "")):
            for field, values in override.items():
                metadata[field] = _merge_list(metadata.get(field), values)

    metadata.setdefault("scene_types", ["general_scene"])
    metadata.setdefault("events", ["story_beat"])
    metadata.setdefault("dialogue_types", [])
    metadata.setdefault("visual_constraints", [])
    metadata.setdefault("risks", [])
    metadata.setdefault("reusable_pattern", path.stem)
    metadata.setdefault("source_files", [])

    new_text = _dump(_ordered(metadata, CASE_FIELDS), body)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Report files that would change without writing.")
    args = parser.parse_args()

    changed: list[Path] = []
    for path in sorted((KNOWLEDGE_DIR / "rules").rglob("*.md")):
        if args.check:
            continue
        if tag_rule(path):
            changed.append(path)

    for path in sorted((KNOWLEDGE_DIR / "cases").rglob("*.md")):
        if path.name.startswith("_"):
            continue
        if args.check:
            continue
        if tag_case(path):
            changed.append(path)

    print(f"knowledge profile tags updated: {len(changed)} files")
    for path in changed[:20]:
        print(f"  - {path.relative_to(ROOT)}")
    if len(changed) > 20:
        print(f"  ... {len(changed) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
