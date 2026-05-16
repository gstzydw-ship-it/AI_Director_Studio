"""Build Seedance-aligned learning packs from short-drama frame analysis.

The existing OpenCV pass extracts one keyframe per detected shot. This script
adds the production-learning layer we need for agent refactoring:

- maps real short-drama shots into W1/W2/R1/X Seedance candidate buckets
- builds category contact sheets for visual review
- builds neighboring sequence packs so rhythm and cut motivation can be studied
- writes machine-readable CSV/JSON/YAML artifacts for later rule-card upgrades

It does not call external APIs and does not promote any sample to runtime rules.
Everything emitted here is still "candidate" until reviewed and tested.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

import yaml
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_DIR = PROJECT_ROOT / "output" / "short_drama_analysis_full_20260516_105744"
DEFAULT_OUTPUT_PARENT = PROJECT_ROOT / "output"


@dataclass(frozen=True)
class ShotRow:
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


@dataclass(frozen=True)
class Candidate:
    category: str
    seedance_level: str
    template_hint: str
    learning_goal: str
    episode: str
    shot_index: int
    start_s: float
    end_s: float
    duration_s: float
    keyframe: str
    inferred_scale: str
    inferred_motion: str
    mean_motion: float
    model_complexity_score: int
    reason: str


def natural_key(value: str) -> list[object]:
    parts = re.split(r"(\d+)", value)
    return [int(part) if part.isdigit() else part for part in parts]


def timestamped_output_dir(parent: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"seedance_sample_learning_{stamp}"


def read_shots(path: Path) -> list[ShotRow]:
    shots: list[ShotRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            shots.append(
                ShotRow(
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
    shots.sort(key=lambda s: (natural_key(s.episode), s.shot_index))
    return shots


def group_by_episode(shots: list[ShotRow]) -> dict[str, list[ShotRow]]:
    grouped: dict[str, list[ShotRow]] = {}
    for shot in shots:
        grouped.setdefault(shot.episode, []).append(shot)
    return grouped


def complexity_score(shot: ShotRow) -> int:
    score = 0
    if shot.duration_s > 8:
        score += 1
    if shot.inferred_motion == "high_cut_or_handheld_motion":
        score += 1
    if shot.inferred_motion == "active_motion_or_reframe":
        score += 1
    if shot.face_count >= 3:
        score += 1
    if shot.largest_face_ratio >= 0.48:
        score += 1
    if shot.duration_s <= 1.2 and shot.mean_motion >= 0.20:
        score += 1
    return score


def candidate_for(shot: ShotRow) -> Candidate | None:
    score = complexity_score(shot)
    scale = shot.inferred_scale
    motion = shot.inferred_motion
    duration = shot.duration_s

    if duration > 8.0:
        return Candidate(
            category="x_long_overpacked_or_slow_burn_review",
            seedance_level="X",
            template_hint="split_or_manual_review",
            learning_goal="Find when long real-drama holds should be split for Seedance.",
            episode=shot.episode,
            shot_index=shot.shot_index,
            start_s=shot.start_s,
            end_s=shot.end_s,
            duration_s=duration,
            keyframe=shot.keyframe,
            inferred_scale=scale,
            inferred_motion=motion,
            mean_motion=shot.mean_motion,
            model_complexity_score=score,
            reason="duration_gt_8s",
        )

    if motion == "high_cut_or_handheld_motion" or duration <= 1.2:
        return Candidate(
            category="r1_fast_motion_or_short_cut",
            seedance_level="R1",
            template_hint="motion_reference_or_degrade_to_w1",
            learning_goal="Study fast-cut emphasis, then degrade into explicit W1/W2 action beats.",
            episode=shot.episode,
            shot_index=shot.shot_index,
            start_s=shot.start_s,
            end_s=shot.end_s,
            duration_s=duration,
            keyframe=shot.keyframe,
            inferred_scale=scale,
            inferred_motion=motion,
            mean_motion=shot.mean_motion,
            model_complexity_score=score,
            reason="high_motion_or_short_duration",
        )

    if scale in {"LS/MLS relation", "MS half-body"} and 1.4 <= duration <= 5.5:
        return Candidate(
            category="w1_relation_or_half_body_coverage",
            seedance_level="W1",
            template_hint="COV-SD20-W1-TWO-SHOT-PRESSURE",
            learning_goal="Learn relation-first coverage, spatial anchors, and readable blocking.",
            episode=shot.episode,
            shot_index=shot.shot_index,
            start_s=shot.start_s,
            end_s=shot.end_s,
            duration_s=duration,
            keyframe=shot.keyframe,
            inferred_scale=scale,
            inferred_motion=motion,
            mean_motion=shot.mean_motion,
            model_complexity_score=score,
            reason="relation_or_half_body_stable_duration",
        )

    if scale in {"MCU chest-up", "CU shoulder-up", "ECU/CU face-dominant"} and 1.3 <= duration <= 5.0:
        return Candidate(
            category="w1_reaction_or_dialogue_hold",
            seedance_level="W1",
            template_hint="COV-SD20-W1-REACTION-HOLD",
            learning_goal="Learn how short dramas hold readable reaction without over-cutting.",
            episode=shot.episode,
            shot_index=shot.shot_index,
            start_s=shot.start_s,
            end_s=shot.end_s,
            duration_s=duration,
            keyframe=shot.keyframe,
            inferred_scale=scale,
            inferred_motion=motion,
            mean_motion=shot.mean_motion,
            model_complexity_score=score,
            reason="chest_or_close_reaction_duration",
        )

    if scale == "relation_or_environment_unknown" and 0.8 <= duration <= 3.5:
        return Candidate(
            category="w1_prop_or_information_insert_proxy",
            seedance_level="W1",
            template_hint="COV-SD20-W1-PROP-INSERT",
            learning_goal="Review possible prop/information inserts; promote only if visual object is clear.",
            episode=shot.episode,
            shot_index=shot.shot_index,
            start_s=shot.start_s,
            end_s=shot.end_s,
            duration_s=duration,
            keyframe=shot.keyframe,
            inferred_scale=scale,
            inferred_motion=motion,
            mean_motion=shot.mean_motion,
            model_complexity_score=score,
            reason="no_face_short_insert_proxy",
        )

    if scale in {"LS/MLS relation", "MS half-body", "MCU chest-up"} and 5.5 < duration <= 8.0:
        return Candidate(
            category="w2_long_relation_or_dialogue_hold",
            seedance_level="W2",
            template_hint="low_complexity_long_hold",
            learning_goal="Learn when a longer hold is still simple enough for Seedance.",
            episode=shot.episode,
            shot_index=shot.shot_index,
            start_s=shot.start_s,
            end_s=shot.end_s,
            duration_s=duration,
            keyframe=shot.keyframe,
            inferred_scale=scale,
            inferred_motion=motion,
            mean_motion=shot.mean_motion,
            model_complexity_score=score,
            reason="long_but_readable_human_hold",
        )

    return None


def select_candidates(shots: list[ShotRow], per_category: int) -> list[Candidate]:
    buckets: dict[str, list[Candidate]] = {}
    for shot in shots:
        candidate = candidate_for(shot)
        if candidate is None:
            continue
        buckets.setdefault(candidate.category, []).append(candidate)

    selected: list[Candidate] = []
    for category, items in buckets.items():
        items.sort(
            key=lambda c: (
                c.model_complexity_score,
                -abs(c.duration_s - 3.0),
                -c.mean_motion,
                natural_key(c.episode),
                c.shot_index,
            )
        )
        if category.startswith(("r1_", "x_")):
            items.sort(
                key=lambda c: (
                    -c.model_complexity_score,
                    -c.mean_motion,
                    -c.duration_s,
                    natural_key(c.episode),
                    c.shot_index,
                )
            )
        selected.extend(items[:per_category])
    selected.sort(key=lambda c: (c.category, natural_key(c.episode), c.shot_index))
    return selected


def load_frame(analysis_dir: Path, keyframe: str, max_h: int = 360) -> Image.Image:
    path = analysis_dir / keyframe
    if not path.exists():
        return Image.new("RGB", (202, max_h), (230, 230, 230))
    image = Image.open(path).convert("RGB")
    scale = min(1.0, max_h / max(1, image.height))
    if scale < 1:
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))))
    return image


def make_contact_sheet(
    analysis_dir: Path,
    output_dir: Path,
    title: str,
    candidates: list[Candidate],
    cols: int = 5,
) -> Path:
    sheet_dir = output_dir / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    cell_w, cell_h = 220, 455
    rows = max(1, (len(candidates) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (244, 244, 244))

    for i, candidate in enumerate(candidates):
        frame = load_frame(analysis_dir, candidate.keyframe)
        cell = Image.new("RGB", (cell_w, cell_h), "white")
        x = (cell_w - frame.width) // 2
        cell.paste(frame, (x, 8))
        draw = ImageDraw.Draw(cell)
        label = (
            f"{candidate.seedance_level} {candidate.template_hint}\n"
            f"E{candidate.episode} S{candidate.shot_index}\n"
            f"{candidate.start_s:.2f}-{candidate.end_s:.2f}s\n"
            f"dur={candidate.duration_s:.2f}s score={candidate.model_complexity_score}\n"
            f"{candidate.inferred_scale}\n"
            f"{candidate.inferred_motion}\n"
            f"motion={candidate.mean_motion:.3f}"
        )
        draw.text((8, 322), label, fill=(0, 0, 0))
        sheet.paste(cell, ((i % cols) * cell_w, (i // cols) * cell_h))

    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_")
    path = sheet_dir / f"{safe_title}.jpg"
    sheet.save(path, quality=90)
    return path


def write_candidates_csv(path: Path, candidates: list[Candidate]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(candidates[0]).keys()) if candidates else [])
        if candidates:
            writer.writeheader()
            for candidate in candidates:
                writer.writerow(asdict(candidate))


def window_around(grouped: dict[str, list[ShotRow]], candidate: Candidate, before: int = 2, after: int = 3) -> list[ShotRow]:
    episode_shots = grouped[candidate.episode]
    pos = next((i for i, shot in enumerate(episode_shots) if shot.shot_index == candidate.shot_index), 0)
    return episode_shots[max(0, pos - before) : min(len(episode_shots), pos + after + 1)]


def make_sequence_sheet(analysis_dir: Path, output_dir: Path, pack_id: str, shots: list[ShotRow]) -> Path:
    sheet_dir = output_dir / "sequence_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    cell_w, cell_h = 205, 430
    cols = min(6, max(1, len(shots)))
    rows = max(1, (len(shots) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (238, 238, 238))

    for i, shot in enumerate(shots):
        frame = load_frame(analysis_dir, shot.keyframe, max_h=315)
        cell = Image.new("RGB", (cell_w, cell_h), "white")
        x = (cell_w - frame.width) // 2
        cell.paste(frame, (x, 8))
        draw = ImageDraw.Draw(cell)
        label = (
            f"E{shot.episode} S{shot.shot_index}\n"
            f"{shot.start_s:.2f}-{shot.end_s:.2f}s ({shot.duration_s:.2f})\n"
            f"{shot.inferred_scale}\n"
            f"{shot.inferred_motion}"
        )
        draw.text((8, 330), label, fill=(0, 0, 0))
        sheet.paste(cell, ((i % cols) * cell_w, (i // cols) * cell_h))

    episode = shots[0].episode if shots else "unknown"
    first = shots[0].shot_index if shots else 0
    last = shots[-1].shot_index if shots else 0
    path = sheet_dir / f"{pack_id}_E{episode}_S{first:03d}-{last:03d}.jpg"
    sheet.save(path, quality=90)
    return path


def build_sequence_packs(
    analysis_dir: Path,
    output_dir: Path,
    grouped: dict[str, list[ShotRow]],
    candidates: list[Candidate],
    per_level: int,
) -> list[dict[str, object]]:
    packs: list[dict[str, object]] = []
    by_level: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        by_level.setdefault(candidate.seedance_level, []).append(candidate)

    pack_no = 1
    used: set[tuple[str, int]] = set()
    for level in ("W1", "W2", "R1", "X"):
        for candidate in by_level.get(level, [])[:per_level]:
            key = (candidate.episode, candidate.shot_index)
            if key in used:
                continue
            used.add(key)
            shots = window_around(grouped, candidate)
            pack_id = f"seq_{pack_no:03d}_{level.lower()}"
            sheet_path = make_sequence_sheet(analysis_dir, output_dir, pack_id, shots)
            packs.append(
                {
                    "pack_id": pack_id,
                    "seedance_level": level,
                    "center_category": candidate.category,
                    "template_hint": candidate.template_hint,
                    "episode": candidate.episode,
                    "center_shot_index": candidate.shot_index,
                    "time_start": shots[0].start_s if shots else candidate.start_s,
                    "time_end": shots[-1].end_s if shots else candidate.end_s,
                    "sheet_path": str(sheet_path.relative_to(output_dir)).replace("\\", "/"),
                    "learning_goal": candidate.learning_goal,
                    "shots": [asdict(shot) for shot in shots],
                }
            )
            pack_no += 1
    return packs


def write_manifest(
    output_dir: Path,
    analysis_dir: Path,
    shots: list[ShotRow],
    candidates: list[Candidate],
    contact_sheets: dict[str, str],
    sequence_packs: list[dict[str, object]],
) -> None:
    counts: dict[str, int] = {}
    level_counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.category] = counts.get(candidate.category, 0) + 1
        level_counts[candidate.seedance_level] = level_counts.get(candidate.seedance_level, 0) + 1

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_dir": str(analysis_dir),
        "source_shot_count": len(shots),
        "candidate_count": len(candidates),
        "category_counts": counts,
        "seedance_level_counts": level_counts,
        "contact_sheets": contact_sheets,
        "sequence_pack_count": len(sequence_packs),
        "status": "candidate_only_not_runtime_rule",
        "seedance_gate": {
            "W1": "default production candidate after visual review",
            "W2": "cautious candidate; keep low complexity",
            "R1": "requires reference asset or downgrade",
            "X": "do not compile; split or manual review",
        },
    }
    (output_dir / "seedance_learning_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_template_yaml(output_dir: Path, candidates: list[Candidate]) -> None:
    groups: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.category, []).append(candidate)
    payload = {
        "source": "94 short-drama sample keyframes",
        "status": "candidate_only",
        "promotion_rule": "candidate -> visual review -> Seedance test -> whitelist -> runtime rule",
        "categories": {},
    }
    for category, items in sorted(groups.items()):
        payload["categories"][category] = {
            "seedance_level": items[0].seedance_level,
            "template_hint": items[0].template_hint,
            "learning_goal": items[0].learning_goal,
            "sample_count": len(items),
            "avg_duration_s": round(mean(item.duration_s for item in items), 3),
            "avg_complexity_score": round(mean(item.model_complexity_score for item in items), 3),
            "example_shots": [
                {
                    "episode": item.episode,
                    "shot_index": item.shot_index,
                    "duration_s": item.duration_s,
                    "keyframe": item.keyframe,
                    "reason": item.reason,
                }
                for item in items[:8]
            ],
        }
    (output_dir / "candidate_templates_seedance.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_learning_plan(output_dir: Path) -> None:
    text = """# Seedance-Aligned Sample Learning Plan

## Goal

Use the 94 live-action short-drama samples to mine candidate rhythm, coverage,
tail-frame, and negative-QC rules. Do not copy real-drama complexity directly
into runtime prompts.

## Seedance Gate

- W1: safe default candidates, usually relation shots, reaction holds, and clear prop inserts.
- W2: usable only when duration and action count stay low.
- R1: reference-driven candidates; require motion/video reference or downgrade.
- X: prohibited for direct generation; split, simplify, or keep for manual review only.

## Learning Passes

1. Frame candidate pass: classify keyframes by shot task and Seedance level.
2. Sequence pass: inspect neighboring shots around each candidate to learn cut motivation.
3. Human/vision review: label actual subject, action, reaction owner, and tail state.
4. Rule extraction: write candidate rule cards, not active runtime rules.
5. Seedance test pass: promote only tested stable candidates to whitelist.
6. Agent refactor: inject approved rules into rhythm, planner, shot, compiler, and QC contracts.

## Agent Targets

- rhythm_rewrite_director: learn pressure curves, beat budgets, pause points, and shot-density hints.
- story_planner: learn which beats should be one generation unit versus split.
- shot_director: learn coverage-role selection and natural viewpoint language.
- storyboard_designer: learn first-frame, key-frame, and tail-frame continuity contracts.
- prompt_compiler: learn how to down-translate live-action coverage into executable prompt text.
- quality_inspector: learn failure patterns: over-cutting, unsupported motion, text dependency, and tail-frame loss.
"""
    (output_dir / "LEARNING_PLAN.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Seedance-aligned learning packs from sample keyframes.")
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    parser.add_argument("--output", default=None)
    parser.add_argument("--per-category", type=int, default=24)
    parser.add_argument("--sequence-per-level", type=int, default=6)
    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir)
    output_dir = Path(args.output) if args.output else timestamped_output_dir(DEFAULT_OUTPUT_PARENT)
    output_dir = output_dir if output_dir.is_absolute() else PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    shot_csv = analysis_dir / "shot_records.csv"
    if not shot_csv.exists():
        raise SystemExit(f"Missing shot_records.csv: {shot_csv}")

    shots = read_shots(shot_csv)
    grouped = group_by_episode(shots)
    candidates = select_candidates(shots, per_category=args.per_category)
    if not candidates:
        raise SystemExit("No candidates selected.")

    write_candidates_csv(output_dir / "frame_candidates.csv", candidates)

    contact_sheets: dict[str, str] = {}
    by_category: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        by_category.setdefault(candidate.category, []).append(candidate)
    for category, items in sorted(by_category.items()):
        sheet_path = make_contact_sheet(analysis_dir, output_dir, category, items)
        contact_sheets[category] = str(sheet_path.relative_to(output_dir)).replace("\\", "/")

    sequence_packs = build_sequence_packs(
        analysis_dir,
        output_dir,
        grouped,
        candidates,
        per_level=args.sequence_per_level,
    )
    (output_dir / "sequence_packs.json").write_text(
        json.dumps(sequence_packs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_template_yaml(output_dir, candidates)
    write_manifest(output_dir, analysis_dir, shots, candidates, contact_sheets, sequence_packs)
    write_learning_plan(output_dir)

    print(f"[DONE] Seedance learning pack: {output_dir}")
    print(f"[DONE] candidates: {len(candidates)}")
    print(f"[DONE] sequence packs: {len(sequence_packs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
