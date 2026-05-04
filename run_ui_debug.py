#!/usr/bin/env python3
import sys
import traceback

log_path = r"d:\AI_Director_Studio\native_ui_debug.log"

with open(log_path, "w", encoding="utf-8") as f:
    f.write("===== 开始运行 =====\n")
    f.flush()

    try:
        f.write("[1] 正在导入 tkinter...\n")
        f.flush()
        import tkinter as tk
        f.write("[1] tkinter 导入成功\n")
        f.flush()

        f.write("[2] 正在导入 director_native_cli...\n")
        f.flush()
        from tools import director_native_cli as cli
        f.write("[2] director_native_cli 导入成功\n")
        f.flush()

        f.write("[3] 正在创建 tkinter 窗口...\n")
        f.flush()
        root = tk.Tk()
        f.write("[3] tkinter 窗口创建成功\n")
        f.flush()

        f.write("[4] 正在导入 native_ui_app...\n")
        f.flush()
        import importlib.util
        spec = importlib.util.spec_from_file_location("native_ui_app", r"d:\AI_Director_Studio\native_ui_app.py")
        module = importlib.util.module_from_spec(spec)
        f.write("[4] native_ui_app 模块加载成功，准备执行...\n")
        f.flush()
        spec.loader.exec_module(module)
        f.write("[4] native_ui_app 执行成功\n")
        f.flush()

        f.write("[5] 正在调用 main()...\n")
        f.flush()
        module.main()
        f.write("[5] main() 执行完毕\n")
        f.flush()

    except Exception:
        f.write("!!!!! 出错了 !!!!!\n")
        f.write(traceback.format_exc())
        f.flush()
        sys.exit(1)

    f.write("===== 运行结束 =====\n")
    f.flush()

print("日志已写入：", log_path)
