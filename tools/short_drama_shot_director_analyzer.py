"""Short drama shot-director analyzer.

This tool performs a local OpenCV pass over vertical short-drama episodes and
produces shot-boundary statistics, representative keyframes, and a director-rule
oriented Markdown report. It avoids ffmpeg so it can run in the current Windows
workspace with only cv2/numpy available.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median

import cv2
import numpy as np


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


@dataclass
class VideoMeta:
    episode: str
    path: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration_s: float
    aspect: str


@dataclass
class ShotRecord:
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


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.stem)
    return [int(part) if part.isdigit() else part for part in parts]


def list_videos(input_dir: Path, limit: int | None = None) -> list[Path]:
    videos = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    videos.sort(key=natural_key)
    return videos[:limit] if limit else videos


def safe_name(path: Path) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", path.stem)


def load_face_cascade() -> cv2.CascadeClassifier | None:
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if not cascade_path.exists():
        return None
    cascade = cv2.CascadeClassifier(str(cascade_path))
    return cascade if not cascade.empty() else None


def resize_for_analysis(frame: np.ndarray, max_side: int = 360) -> np.ndarray:
    h, w = frame.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return frame
    return cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))))


def frame_hist(frame: np.ndarray) -> np.ndarray:
    small = resize_for_analysis(frame, 240)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def frame_diff_score(prev: np.ndarray, frame: np.ndarray, prev_hist: np.ndarray) -> tuple[float, np.ndarray]:
    hist = frame_hist(frame)
    hist_dist = cv2.compareHist(prev_hist.astype("float32"), hist.astype("float32"), cv2.HISTCMP_BHATTACHARYYA)
    prev_small = resize_for_analysis(prev, 240)
    frame_small = resize_for_analysis(frame, 240)
    if prev_small.shape != frame_small.shape:
        frame_small = cv2.resize(frame_small, (prev_small.shape[1], prev_small.shape[0]))
    pixel = float(np.mean(cv2.absdiff(prev_small, frame_small))) / 255.0
    return 0.72 * float(hist_dist) + 0.28 * pixel, hist


def infer_aspect(width: int, height: int) -> str:
    if height <= 0:
        return "unknown"
    ratio = width / height
    if ratio < 0.7:
        return "9:16 vertical"
    if ratio > 1.3:
        return "16:9 horizontal"
    return "square/other"


def detect_faces(frame: np.ndarray, cascade: cv2.CascadeClassifier | None) -> tuple[int, float]:
    if cascade is None:
        return 0, 0.0
    small = resize_for_analysis(frame, 640)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(28, 28))
    if len(faces) == 0:
        return 0, 0.0
    h = small.shape[0]
    largest = max(face[3] for face in faces)
    return int(len(faces)), float(largest / max(1, h))


def infer_scale(face_count: int, largest_face_ratio: float) -> str:
    if face_count == 0:
        return "relation_or_environment_unknown"
    if largest_face_ratio >= 0.48:
        return "ECU/CU face-dominant"
    if largest_face_ratio >= 0.34:
        return "CU shoulder-up"
    if largest_face_ratio >= 0.23:
        return "MCU chest-up"
    if largest_face_ratio >= 0.14:
        return "MS half-body"
    return "LS/MLS relation"


def infer_motion(mean_motion: float) -> str:
    if mean_motion >= 0.22:
        return "high_cut_or_handheld_motion"
    if mean_motion >= 0.12:
        return "active_motion_or_reframe"
    if mean_motion >= 0.06:
        return "gentle_motion"
    return "mostly_static"


def write_keyframe(frame: np.ndarray, out_path: Path, max_side: int = 720) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = frame.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 86])


def analyze_video(
    video_path: Path,
    output_dir: Path,
    cascade: cv2.CascadeClassifier | None,
    sample_fps: float,
    cut_threshold: float,
    min_shot_s: float,
    save_keyframes: bool,
) -> tuple[VideoMeta, list[ShotRecord]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_s = frame_count / fps if fps > 0 else 0.0
    meta = VideoMeta(
        episode=video_path.stem,
        path=str(video_path),
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_s=duration_s,
        aspect=infer_aspect(width, height),
    )

    step = max(1, int(round(fps / sample_fps))) if fps > 0 else 12
    min_gap_frames = max(1, int(round(min_shot_s * fps))) if fps > 0 else 10

    ret, prev = cap.read()
    if not ret:
        cap.release()
        return meta, []
    prev_hist = frame_hist(prev)
    last_cut = 0
    shot_starts = [0]
    diffs_since_cut: list[float] = []
    shot_motion: dict[int, list[float]] = {0: []}
    sampled_frames: dict[int, np.ndarray] = {0: prev.copy()}

    idx = 0
    while True:
        idx += step
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        score, hist = frame_diff_score(prev, frame, prev_hist)
        diffs_since_cut.append(score)
        current_shot_start = shot_starts[-1]
        shot_motion.setdefault(current_shot_start, []).append(score)
        if score >= cut_threshold and (idx - last_cut) >= min_gap_frames:
            shot_starts.append(idx)
            sampled_frames[idx] = frame.copy()
            last_cut = idx
            diffs_since_cut = []
            shot_motion.setdefault(idx, [])
        prev = frame
        prev_hist = hist

    cap.release()
    if frame_count > 0 and (frame_count - 1) not in shot_starts:
        shot_starts.append(frame_count - 1)

    records: list[ShotRecord] = []
    episode_name = safe_name(video_path)
    keyframe_dir = output_dir / "keyframes" / episode_name
    for shot_no, start in enumerate(shot_starts[:-1], start=1):
        end = shot_starts[shot_no]
        if fps <= 0:
            start_s = float(start)
            end_s = float(end)
        else:
            start_s = start / fps
            end_s = end / fps
        duration = max(0.0, end_s - start_s)
        key = sampled_frames.get(start)
        if key is None:
            continue

        face_count, face_ratio = detect_faces(key, cascade)
        gray = cv2.cvtColor(resize_for_analysis(key, 320), cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray)) / 255.0
        motion_values = shot_motion.get(start, [])
        mean_motion = float(mean(motion_values)) if motion_values else 0.0

        key_rel = ""
        if save_keyframes:
            key_path = keyframe_dir / f"shot_{shot_no:03d}_{start_s:06.2f}s.jpg"
            write_keyframe(key, key_path)
            key_rel = str(key_path.relative_to(output_dir)).replace("\\", "/")

        records.append(
            ShotRecord(
                episode=video_path.stem,
                shot_index=shot_no,
                start_s=round(start_s, 3),
                end_s=round(end_s, 3),
                duration_s=round(duration, 3),
                keyframe=key_rel,
                mean_motion=round(mean_motion, 4),
                brightness=round(brightness, 4),
                face_count=face_count,
                largest_face_ratio=round(face_ratio, 4),
                inferred_scale=infer_scale(face_count, face_ratio),
                inferred_motion=infer_motion(mean_motion),
            )
        )

    return meta, records


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    return values[f] * (c - k) + values[c] * (k - f)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(output_dir: Path, metas: list[VideoMeta], shots: list[ShotRecord]) -> None:
    durations = [shot.duration_s for shot in shots if shot.duration_s > 0]
    scale_counts: dict[str, int] = {}
    motion_counts: dict[str, int] = {}
    for shot in shots:
        scale_counts[shot.inferred_scale] = scale_counts.get(shot.inferred_scale, 0) + 1
        motion_counts[shot.inferred_motion] = motion_counts.get(shot.inferred_motion, 0) + 1

    short = len([d for d in durations if d <= 1.2])
    medium = len([d for d in durations if 1.2 < d <= 3.0])
    long = len([d for d in durations if d > 3.0])
    vertical = len([m for m in metas if m.aspect == "9:16 vertical"])

    def pct(n: int, total: int) -> str:
        return f"{(n / total * 100):.1f}%" if total else "0.0%"

    top_fast = sorted(shots, key=lambda s: s.mean_motion, reverse=True)[:20]
    face_heavy = [s for s in shots if s.inferred_scale in {"ECU/CU face-dominant", "CU shoulder-up"}]
    relation = [s for s in shots if s.inferred_scale in {"MS half-body", "LS/MLS relation", "relation_or_environment_unknown"}]

    report = [
        "# 短剧样片镜头导演分析报告",
        "",
        f"- 样片目录视频数：{len(metas)}",
        f"- 竖屏视频数：{vertical}/{len(metas)}",
        f"- 检测镜头数：{len(shots)}",
        f"- 平均镜头时长：{mean(durations):.2f}s" if durations else "- 平均镜头时长：0s",
        f"- 中位镜头时长：{median(durations):.2f}s" if durations else "- 中位镜头时长：0s",
        f"- P25/P75 镜头时长：{percentile(durations, 0.25):.2f}s / {percentile(durations, 0.75):.2f}s" if durations else "- P25/P75 镜头时长：0s / 0s",
        "",
        "## 镜头时长分布",
        "",
        f"- <=1.2s 短切：{short} ({pct(short, len(durations))})",
        f"- 1.2-3.0s 常规镜头：{medium} ({pct(medium, len(durations))})",
        f"- >3.0s 长镜头：{long} ({pct(long, len(durations))})",
        "",
        "## 疑似景别分布（基于人脸占画面高度的粗估）",
        "",
    ]
    for key, count in sorted(scale_counts.items(), key=lambda item: item[1], reverse=True):
        report.append(f"- {key}: {count} ({pct(count, len(shots))})")
    report.extend(["", "## 运镜/画面变化强度分布", ""])
    for key, count in sorted(motion_counts.items(), key=lambda item: item[1], reverse=True):
        report.append(f"- {key}: {count} ({pct(count, len(shots))})")

    report.extend(
        [
            "",
            "## 对镜头导演规则的初步启发",
            "",
            f"- 关系/环境/半身类镜头约 {len(relation)} 个，说明短剧并不是只靠大头特写推进；一号镜头摆位仍应优先给空间关系和人物站位。",
            f"- CU/ECU 类镜头约 {len(face_heavy)} 个，应主要挂在信息炸点、受击反应、情绪顶点，不应机械覆盖完整对白。",
            "- 快速变化镜头应作为动作、受击或转场重音；若连续出现，二号动作调度需要检查是否有动作锚点、视线锚点或信息锚点。",
            "- 该报告的人脸景别是粗估，后续应抽取典型关键帧交给视觉模型做人工可读的镜头语言标注，再沉淀成 25/26 号规则案例。",
            "",
            "## 高运动/疑似动作或切换重音样本",
            "",
        ]
    )
    for shot in top_fast[:12]:
        report.append(
            f"- {shot.episode} shot {shot.shot_index}: {shot.start_s:.2f}-{shot.end_s:.2f}s, "
            f"{shot.inferred_motion}, {shot.inferred_scale}, keyframe={shot.keyframe}"
        )

    (output_dir / "short_drama_shot_director_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=r"H:\样片", help="Input directory containing short-drama videos.")
    parser.add_argument("--output", default=r"output\short_drama_analysis", help="Output directory.")
    parser.add_argument("--limit", type=int, default=None, help="Optional video limit for smoke tests.")
    parser.add_argument("--sample-fps", type=float, default=4.0, help="Frame sampling rate for cut detection.")
    parser.add_argument("--cut-threshold", type=float, default=0.46, help="Shot cut threshold.")
    parser.add_argument("--min-shot-s", type=float, default=0.45, help="Minimum shot duration.")
    parser.add_argument("--no-keyframes", action="store_true", help="Skip representative keyframe writes.")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    videos = list_videos(input_dir, args.limit)
    if not videos:
        raise SystemExit(f"No videos found in {input_dir}")

    cascade = load_face_cascade()
    metas: list[VideoMeta] = []
    all_shots: list[ShotRecord] = []
    errors: list[dict[str, str]] = []

    for index, video in enumerate(videos, start=1):
        print(f"[{index}/{len(videos)}] analyzing {video.name}")
        try:
            meta, records = analyze_video(
                video,
                output_dir,
                cascade,
                sample_fps=args.sample_fps,
                cut_threshold=args.cut_threshold,
                min_shot_s=args.min_shot_s,
                save_keyframes=not args.no_keyframes,
            )
            metas.append(meta)
            all_shots.extend(records)
            print(f"  duration={meta.duration_s:.1f}s shots={len(records)} aspect={meta.aspect}")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors.append({"path": str(video), "error": str(exc)})

    write_csv(output_dir / "episode_meta.csv", [asdict(m) for m in metas], list(asdict(metas[0]).keys()) if metas else [])
    if all_shots:
        write_csv(output_dir / "shot_records.csv", [asdict(s) for s in all_shots], list(asdict(all_shots[0]).keys()))

    summary = {
        "input_dir": str(input_dir),
        "video_count": len(metas),
        "shot_count": len(all_shots),
        "errors": errors,
        "metas": [asdict(m) for m in metas],
        "shots": [asdict(s) for s in all_shots],
    }
    (output_dir / "analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(output_dir, metas, all_shots)
    print(f"[DONE] wrote analysis to {output_dir}")


if __name__ == "__main__":
    main()
