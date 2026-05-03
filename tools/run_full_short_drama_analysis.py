"""Run the full short-drama shot-director analysis task.

This is a small orchestration wrapper around
tools/short_drama_shot_director_analyzer.py. It fixes the project-local paths,
creates a timestamped output folder, writes a manifest and a live log, then
runs the OpenCV analyzer over the complete sample directory.

Examples:
  py tools/run_full_short_drama_analysis.py
  py tools/run_full_short_drama_analysis.py --dry-run
  py tools/run_full_short_drama_analysis.py --limit 3 --sample-fps 2
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = Path(r"H:\样片")
DEFAULT_OUTPUT_PARENT = PROJECT_ROOT / "output"
ANALYZER = PROJECT_ROOT / "tools" / "short_drama_shot_director_analyzer.py"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def natural_key(path: Path) -> list[object]:
    import re

    parts = re.split(r"(\d+)", path.stem)
    return [int(part) if part.isdigit() else part for part in parts]


def list_videos(input_dir: Path) -> list[Path]:
    videos = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    videos.sort(key=natural_key)
    return videos


def timestamped_output_dir(output_parent: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_parent / f"short_drama_analysis_full_{stamp}"


def write_manifest(
    output_dir: Path,
    input_dir: Path,
    videos: list[Path],
    args: argparse.Namespace,
    command: list[str],
) -> None:
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "video_count": len(videos),
        "videos": [str(p) for p in videos],
        "analyzer": str(ANALYZER),
        "sample_fps": args.sample_fps,
        "cut_threshold": args.cut_threshold,
        "min_shot_s": args.min_shot_s,
        "limit": args.limit,
        "no_keyframes": args.no_keyframes,
        "command": command,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "full_run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_next_steps(output_dir: Path) -> None:
    text = f"""# 全量短剧镜头导演分析任务

## 输出文件

- `episode_meta.csv`: 每集元数据。
- `shot_records.csv`: 每个镜头的起止、时长、关键帧、粗略景别和运动强度。
- `analysis_summary.json`: 全量结构化结果。
- `short_drama_shot_director_report.md`: 面向镜头导演规则的统计报告。
- `keyframes/`: 每个镜头的代表帧。
- `run.log`: 本次运行日志。

## 后续规则优化建议

1. 从 `short_drama_shot_director_report.md` 里挑高运动、短切、长镜头样本。
2. 打开 contact sheet 或关键帧，人工/视觉模型复核真实景别、角度、运镜。
3. 把稳定结论沉淀到 `01/02/03/04/25/26`，尤其是主分镜职责、子分镜触发、9:16 景别纪律。
4. 再把典型镜头序列写入 `knowledge/cases/`，供 shot_director 检索。

## 本次输出目录

`{output_dir}`
"""
    (output_dir / "NEXT_STEPS.md").write_text(text, encoding="utf-8")


def run_and_log(command: list[str], log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8", newline="") as log:
        log.write("COMMAND:\n")
        log.write(" ".join(command))
        log.write("\n\nOUTPUT:\n")
        log.flush()

        process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
            log.flush()
        return process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full short-drama shot-director analysis.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_DIR), help="Sample video directory.")
    parser.add_argument("--output", default=None, help="Output directory. Defaults to timestamped output folder.")
    parser.add_argument("--limit", type=int, default=None, help="Optional video limit for pilot runs.")
    parser.add_argument("--sample-fps", type=float, default=2.0, help="Frame sampling rate for cut detection.")
    parser.add_argument("--cut-threshold", type=float, default=0.46, help="Shot cut threshold.")
    parser.add_argument("--min-shot-s", type=float, default=0.45, help="Minimum shot duration.")
    parser.add_argument("--no-keyframes", action="store_true", help="Skip keyframe image output.")
    parser.add_argument("--dry-run", action="store_true", help="Print and write manifest without running analysis.")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {input_dir}")
    if not ANALYZER.exists():
        raise SystemExit(f"Analyzer script does not exist: {ANALYZER}")

    videos = list_videos(input_dir)
    selected_count = min(len(videos), args.limit) if args.limit else len(videos)
    output_dir = Path(args.output) if args.output else timestamped_output_dir(DEFAULT_OUTPUT_PARENT)
    output_dir = output_dir if output_dir.is_absolute() else PROJECT_ROOT / output_dir

    command = [
        sys.executable,
        str(ANALYZER),
        "--input",
        str(input_dir),
        "--output",
        str(output_dir),
        "--sample-fps",
        str(args.sample_fps),
        "--cut-threshold",
        str(args.cut_threshold),
        "--min-shot-s",
        str(args.min_shot_s),
    ]
    if args.limit:
        command.extend(["--limit", str(args.limit)])
    if args.no_keyframes:
        command.append("--no-keyframes")

    write_manifest(output_dir, input_dir, videos[:selected_count], args, command)
    write_next_steps(output_dir)

    print(f"[PLAN] input: {input_dir}")
    print(f"[PLAN] videos: {selected_count}/{len(videos)}")
    print(f"[PLAN] output: {output_dir}")
    print(f"[PLAN] sample_fps={args.sample_fps} cut_threshold={args.cut_threshold} min_shot_s={args.min_shot_s}")

    if args.dry_run:
        print("[DRY-RUN] Manifest and NEXT_STEPS written. Analysis not started.")
        return 0

    code = run_and_log(command, output_dir / "run.log")
    if code != 0:
        print(f"[ERROR] Analyzer exited with code {code}. See {output_dir / 'run.log'}")
        return code

    required = [
        output_dir / "episode_meta.csv",
        output_dir / "shot_records.csv",
        output_dir / "analysis_summary.json",
        output_dir / "short_drama_shot_director_report.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("[WARN] Analysis finished but some expected files are missing:")
        for path in missing:
            print(f"  - {path}")
        return 2

    print("[DONE] Full short-drama analysis completed.")
    print(f"[DONE] Report: {output_dir / 'short_drama_shot_director_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
