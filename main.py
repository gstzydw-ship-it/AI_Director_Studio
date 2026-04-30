"""
智能导演多Agent团队 — 主入口
"""

import base64
import mimetypes
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="🎬 智能导演多Agent团队")
    parser.add_argument("command", nargs="?", default="ui", choices=["ui", "build-db", "run"],
                        help="执行命令：ui=启动Web界面（默认）, build-db=构建向量库, run=命令行执行")
    parser.add_argument("--script", type=str, help="剧本文件路径（run模式）")
    parser.add_argument("--aspect-ratio", type=str, default="16:9", help="画幅（16:9 或 9:16）")
    parser.add_argument("--reference-image", action="append", default=[], help="参考图路径，可重复传入，run模式至少3张")
    parser.add_argument("--reference-note", type=str, default="", help="参考图说明（run模式）")
    parser.add_argument("--rebuild", action="store_true", help="强制重建向量库")

    args = parser.parse_args()

    # 临时全局配置本地代理端口，确保可以连通外部模型 API
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
    os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1,localhost"

    if args.command == "ui":
        from ui.app import start_ui
        start_ui()

    elif args.command == "build-db":
        from agents.knowledge_base import build_vectordb
        build_vectordb(force_rebuild=True)

    elif args.command == "run":
        if not args.script:
            print("❌ 请使用 --script 指定剧本文件")
            sys.exit(1)

        with open(args.script, "r", encoding="utf-8") as f:
            script = f.read()

        if len(args.reference_image) < 3:
            print("❌ run 模式请至少传入3张参考图：--reference-image 主角图 --reference-image 对手图 --reference-image 场景图")
            sys.exit(1)

        reference_image_b64s = []
        reference_image_manifest = []
        for index, image_path in enumerate(args.reference_image, start=1):
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            reference_image_b64s.append(f"data:{mime_type};base64,{encoded}")
            reference_image_manifest.append(
                {
                    "label": f"@图片{index}",
                    "filename": os.path.basename(image_path),
                    "purpose": "人物/场景/位置关系参考图，按用户传入顺序与说明限定用途",
                }
            )

        from agents.director_graph import run_full_pipeline
        result = run_full_pipeline(
            script=script,
            aspect_ratio=args.aspect_ratio,
            reference_images=args.reference_note or None,
            reference_image_b64s=reference_image_b64s,
            reference_image_manifest=reference_image_manifest,
        )

        print("\n" + "=" * 60)
        print("🎬 导演流水线执行完成")
        print("=" * 60)
        print(result)


if __name__ == "__main__":
    main()
