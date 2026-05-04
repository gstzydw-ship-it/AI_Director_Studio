#!/usr/bin/env python3
"""诊断脚本：测试 director_native_cli.py 各命令是否正常，结果写入文件"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "debug_cli_output.txt")
os.makedirs(os.path.dirname(output_path), exist_ok=True)

lines = []

def log(msg):
    lines.append(msg)
    print(msg)

log("=== 0. 基础环境检查 ===")
log(f"Python: {sys.executable}")
log(f"Version: {sys.version}")
log(f"CWD: {os.getcwd()}")
log(f"sys.path[0]: {sys.path[0]}")

try:
    import tools.director_native_cli as cli
    log("  [OK] import tools.director_native_cli")
except Exception as e:
    import traceback
    log(f"  [FAIL] import tools.director_native_cli: {type(e).__name__}: {e}")
    log(traceback.format_exc())
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    sys.exit(1)

log("\n=== 1. cmd_status ===")
try:
    r = cli.cmd_status("local")
    log(f"  [OK] cmd_status: {r}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n=== 2. cmd_model_profiles ===")
try:
    r = cli.cmd_model_profiles()
    log(f"  [OK] cmd_model_profiles: {r}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n=== 3. cmd_projects_recent ===")
try:
    r = cli.cmd_projects_recent(False)
    log(f"  [OK] cmd_projects_recent: {r}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n=== 4. cmd_assets_library ===")
try:
    r = cli.cmd_assets_library()
    log(f"  [OK] cmd_assets_library: {r}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n=== 5. cmd_run_pipeline (模拟前端调用) ===")
try:
    r = cli.cmd_run_pipeline(
        script="测试剧本：男人走进办公室，看到女人坐在椅子上。",
        aspect_ratio="9:16",
        session_id="local",
        model_profile_snapshot={},
        style_preset="modern_short_drama",
        reference_image_b64s=None,
        reference_image_manifest=None,
        asset_selection={},
        speed_mode=False
    )
    log(f"  [OK] cmd_run_pipeline: success={r.get('success')}, message={r.get('message')}, step={r.get('step')}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n=== 6. cmd_pipeline_progress ===")
try:
    r = cli.cmd_pipeline_progress("local")
    log(f"  [OK] progress: status={r.get('status')}, step={r.get('step')}, message={r.get('message')}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n=== 7. agents.director_graph 导入检查 ===")
try:
    from agents import director_graph
    log("  [OK] from agents import director_graph")
    log(f"       run_phase_1_planning 可用: {hasattr(director_graph, 'run_phase_1_planning')}")
except Exception as e:
    import traceback
    log(f"  [FAIL] {type(e).__name__}: {e}")
    log(traceback.format_exc())

log("\n诊断完成，结果已写入: " + output_path)
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
