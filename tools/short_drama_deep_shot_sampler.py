"""Deep shot-director sampler for short-drama analysis.

Reads the full OpenCV analysis output, selects useful consecutive shot groups,
builds contact sheets, and optionally asks the configured vision model to label
shot-director knowledge: main-shot intent, sub-shot trigger, scale/angle/motion,
cut motivation, 9:16 discipline, and rule improvements.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
import yaml
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_DIR = PROJECT_ROOT / "output" / "short_drama_analysis_full_20260502_162409"
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


@dataclass
class Shot:
    episode: str
    shot_index: int
    start_s: float
    end_s: float
    duration_s: float
    keyframe: str
    mean_motion: float
    brightness: float
    face_count: int
    largest_face_ratio: float
    inferred_scale: str
    inferred_motion: str


@dataclass
class SequencePack:
    pack_id: str
    category: str
    episode: str
    shots: list[Shot]
    reason: str
    sheet_path: Path


def read_shots(path: Path) -> list[Shot]:
    shots: list[Shot] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            shots.append(
                Shot(
                    episode=row["episode"],
                    shot_index=int(row["shot_index"]),
                    start_s=float(row["start_s"]),
                    end_s=float(row["end_s"]),
                    duration_s=float(row["duration_s"]),
                    keyframe=row["keyframe"],
                    mean_motion=float(row["mean_motion"]),
                    brightness=float(row["brightness"]),
                    face_count=int(row["face_count"]),
                    largest_face_ratio=float(row["largest_face_ratio"]),
                    inferred_scale=row["inferred_scale"],
                    inferred_motion=row["inferred_motion"],
                )
            )
    return shots


def group_by_episode(shots: Iterable[Shot]) -> dict[str, list[Shot]]:
    grouped: dict[str, list[Shot]] = {}
    for shot in shots:
        grouped.setdefault(shot.episode, []).append(shot)
    for episode_shots in grouped.values():
        episode_shots.sort(key=lambda s: s.shot_index)
    return grouped


def pick_window(episode_shots: list[Shot], center_index: int, before: int = 2, after: int = 3) -> list[Shot]:
    pos = next((i for i, s in enumerate(episode_shots) if s.shot_index == center_index), 0)
    start = max(0, pos - before)
    end = min(len(episode_shots), pos + after + 1)
    return episode_shots[start:end]


def consecutive_clusters(episode_shots: list[Shot], predicate, min_len: int) -> list[list[Shot]]:
    clusters: list[list[Shot]] = []
    current: list[Shot] = []
    for shot in episode_shots:
        if predicate(shot):
            current.append(shot)
        else:
            if len(current) >= min_len:
                clusters.append(current)
            current = []
    if len(current) >= min_len:
        clusters.append(current)
    return clusters


def sequence_score(shots: list[Shot]) -> float:
    if not shots:
        return 0.0
    avg_motion = sum(s.mean_motion for s in shots) / len(shots)
    scale_variety = len({s.inferred_scale for s in shots})
    duration_variety = len({round(s.duration_s, 1) for s in shots})
    return avg_motion * 10 + scale_variety + duration_variety * 0.25


def build_sequence_candidates(grouped: dict[str, list[Shot]]) -> list[tuple[str, str, list[Shot], str, float]]:
    candidates: list[tuple[str, str, list[Shot], str, float]] = []

    for episode, episode_shots in grouped.items():
        for cluster in consecutive_clusters(episode_shots, lambda s: s.duration_s <= 1.2, 4):
            candidates.append(
                (
                    "short_cut_cluster",
                    episode,
                    cluster[:8],
                    "连续短切，用于分析短剧如何处理动作重音、受击反应或转场压缩。",
                    sequence_score(cluster),
                )
            )
        for cluster in consecutive_clusters(
            episode_shots,
            lambda s: s.inferred_motion == "high_cut_or_handheld_motion",
            4,
        ):
            candidates.append(
                (
                    "high_motion_cluster",
                    episode,
                    cluster[:8],
                    "高运动/高变化镜头组，用于分析动作调度、手持感或快速转场。",
                    sequence_score(cluster) + 1.0,
                )
            )

        long_dialogue_like = [
            s
            for s in episode_shots
            if s.duration_s >= 6.0 and s.inferred_scale in {"MS half-body", "MCU chest-up", "LS/MLS relation"}
        ]
        for shot in sorted(long_dialogue_like, key=lambda s: s.duration_s, reverse=True)[:2]:
            window = pick_window(episode_shots, shot.shot_index, before=2, after=3)
            candidates.append(
                (
                    "long_dialogue_or_relation_hold",
                    episode,
                    window,
                    "长持镜/关系镜头窗口，用于分析完整发言单元、关系景承载和切镜节制。",
                    sequence_score(window) + shot.duration_s * 0.08,
                )
            )

        cu_like = [s for s in episode_shots if s.inferred_scale in {"CU shoulder-up", "ECU/CU face-dominant"}]
        for shot in cu_like[:2]:
            window = pick_window(episode_shots, shot.shot_index, before=2, after=3)
            candidates.append(
                (
                    "cu_reaction_or_emphasis",
                    episode,
                    window,
                    "CU/ECU 邻近窗口，用于分析特写是否作为信息炸点、受击反应或动作重音。",
                    sequence_score(window) + 3.0,
                )
            )

    candidates.sort(key=lambda item: item[4], reverse=True)
    return candidates


def dedupe_candidates(candidates: list[tuple[str, str, list[Shot], str, float]], per_category: int) -> list[tuple[str, str, list[Shot], str, float]]:
    selected: list[tuple[str, str, list[Shot], str, float]] = []
    counts: dict[str, int] = {}
    used_keys: set[tuple[str, int, int]] = set()
    for category, episode, shots, reason, score in candidates:
        if counts.get(category, 0) >= per_category:
            continue
        if not shots:
            continue
        key = (episode, shots[0].shot_index, shots[-1].shot_index)
        if key in used_keys:
            continue
        selected.append((category, episode, shots, reason, score))
        counts[category] = counts.get(category, 0) + 1
        used_keys.add(key)
    return selected


def make_contact_sheet(analysis_dir: Path, pack_id: str, category: str, shots: list[Shot], output_dir: Path) -> Path:
    cell_w, cell_h = 220, 430
    cols = min(4, max(1, len(shots)))
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (238, 238, 238))

    for i, shot in enumerate(shots):
        key_path = analysis_dir / shot.keyframe
        if key_path.exists():
            frame = Image.open(key_path).convert("RGB")
        else:
            frame = Image.new("RGB", (160, 285), (220, 220, 220))
        frame.thumbnail((cell_w - 18, 310))
        cell = Image.new("RGB", (cell_w, cell_h), "white")
        x = (cell_w - frame.width) // 2
        cell.paste(frame, (x, 8))
        d = ImageDraw.Draw(cell)
        label = (
            f"{category}\n"
            f"E{shot.episode} S{shot.shot_index}\n"
            f"{shot.start_s:.2f}-{shot.end_s:.2f}s ({shot.duration_s:.2f}s)\n"
            f"{shot.inferred_scale}\n"
            f"{shot.inferred_motion}\n"
            f"motion={shot.mean_motion:.3f}"
        )
        d.text((8, 322), label, fill=(0, 0, 0))
        sheet.paste(cell, ((i % cols) * cell_w, (i // cols) * cell_h))

    sheet_dir = output_dir / "sequence_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    path = sheet_dir / f"{pack_id}_{category}_E{shots[0].episode}_S{shots[0].shot_index}-{shots[-1].shot_index}.jpg"
    sheet.save(path, quality=90)
    return path


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def image_to_data_url(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{data}"


def vision_prompt(pack: SequencePack) -> str:
    shot_lines = "\n".join(
        (
            f"- S{shot.shot_index}: {shot.start_s:.2f}-{shot.end_s:.2f}s, "
            f"duration={shot.duration_s:.2f}s, cv_scale={shot.inferred_scale}, cv_motion={shot.inferred_motion}"
        )
        for shot in pack.shots
    )
    return f"""你是短剧镜头导演规则分析师。下面是一组按时间顺序排列的短剧镜头关键帧 contact sheet。

请不要复述剧情，请专注分析镜头导演知识。OpenCV 粗标签仅供参考，可以推翻。

样本类别：{pack.category}
抽样原因：{pack.reason}
镜头列表：
{shot_lines}

请按以下结构输出中文 Markdown：

## 逐镜头标注
逐镜头给出：主体、景别（ELS/LS/MLS/MS/MCU/CU/ECU）、机位高度、拍摄角度、运镜/画面变化、构图关系、叙事功能。

## 切镜动机
逐个说明为什么从上一镜切到下一镜：主体关系变化、动作中间态、信息炸点、受击反应、空间复位、出画入画、还是无效切镜。

## 主分镜/子分镜判断
判断哪些应该是一号导演 main_shot，哪些只是二号导演 sub_shot。必须说明 parent_shot_id 或可挂靠的主镜头。

## 9:16 竖屏纪律
分析是否依赖半身/中景/关系镜头，CU/ECU 是否只是短重音，有没有大头滥用或空间丢失。

## 可沉淀规则
输出 3-6 条可直接写入 01/02/03/04/25/26 的规则，每条包含：
- 适用条件
- 执行指令
- 禁止项
"""


def call_vision_model(pack: SequencePack, config: dict, retries: int = 2) -> str:
    video_cfg = config.get("agent_models", {}).get("video_analyst", {})
    llm_cfg = config.get("llm", {})
    base_url = video_cfg.get("base_url") or llm_cfg.get("base_url")
    model = video_cfg.get("model") or llm_cfg.get("model")
    api_key = video_cfg.get("api_key") or llm_cfg.get("api_key")
    if not base_url or not model or not api_key:
        raise RuntimeError("Missing video_analyst/base_url/model/api_key config.")

    url = f"{str(base_url).rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": vision_prompt(pack)},
                    {"type": "image_url", "image_url": {"url": image_to_data_url(pack.sheet_path)}},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 5000,
    }
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=300)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"].get("content", "")
            last_error = f"HTTP {response.status_code}: {response.text[:500]}"
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
        time.sleep(8 * attempt)
    raise RuntimeError(last_error)


def write_pack_index(output_dir: Path, packs: list[SequencePack]) -> None:
    rows = []
    for pack in packs:
        rows.append(
            {
                "pack_id": pack.pack_id,
                "category": pack.category,
                "episode": pack.episode,
                "shot_start": pack.shots[0].shot_index,
                "shot_end": pack.shots[-1].shot_index,
                "time_start": pack.shots[0].start_s,
                "time_end": pack.shots[-1].end_s,
                "reason": pack.reason,
                "sheet_path": str(pack.sheet_path),
            }
        )
    with (output_dir / "deep_sequence_packs.json").open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    parser.add_argument("--output", default=None)
    parser.add_argument("--per-category", type=int, default=4)
    parser.add_argument("--max-vision", type=int, default=8)
    parser.add_argument("--call-vision", action="store_true")
    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir)
    output_dir = Path(args.output) if args.output else analysis_dir / "deep_shot_director"
    output_dir.mkdir(parents=True, exist_ok=True)

    shots = read_shots(analysis_dir / "shot_records.csv")
    grouped = group_by_episode(shots)
    candidates = build_sequence_candidates(grouped)
    selected = dedupe_candidates(candidates, args.per_category)

    packs: list[SequencePack] = []
    for i, (category, episode, pack_shots, reason, _score) in enumerate(selected, start=1):
        pack_id = f"pack_{i:03d}"
        sheet_path = make_contact_sheet(analysis_dir, pack_id, category, pack_shots, output_dir)
        packs.append(SequencePack(pack_id, category, episode, pack_shots, reason, sheet_path))

    write_pack_index(output_dir, packs)

    report_lines = [
        "# 短剧镜头导演深度样本报告",
        "",
        f"- 来源分析目录：`{analysis_dir}`",
        f"- 样本包数量：{len(packs)}",
        f"- 是否调用视觉模型：{bool(args.call_vision)}",
        "",
    ]

    config = load_config() if args.call_vision else {}
    for pack in packs[: args.max_vision if args.call_vision else len(packs)]:
        rel_sheet = pack.sheet_path.relative_to(output_dir)
        report_lines.extend(
            [
                f"## {pack.pack_id} | {pack.category} | E{pack.episode}",
                "",
                f"- 抽样原因：{pack.reason}",
                f"- 镜头范围：S{pack.shots[0].shot_index}-S{pack.shots[-1].shot_index}",
                f"- Contact sheet: `{rel_sheet}`",
                "",
            ]
        )
        if args.call_vision:
            print(f"[VISION] {pack.pack_id} {pack.category} E{pack.episode}")
            try:
                content = call_vision_model(pack, config)
            except Exception as exc:  # noqa: BLE001
                content = f"[VISION_ERROR] {exc}"
            (output_dir / f"{pack.pack_id}_vision.md").write_text(content, encoding="utf-8")
            report_lines.extend([content, ""])

    (output_dir / "deep_shot_director_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"[DONE] wrote deep samples to {output_dir}")


if __name__ == "__main__":
    main()
