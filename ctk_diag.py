import traceback
from pathlib import Path

log = Path(r"d:\AI_Director_Studio\ctk_diag.log")

with log.open("w", encoding="utf-8") as f:
    f.write("[1] 开始诊断\n")
    try:
        f.write("[2] 导入 customtkinter...\n")
        import customtkinter as ctk
        f.write(f"[OK] customtkinter imported: {getattr(ctk, '__version__', 'unknown')}\n")

        f.write("[3] 创建 CTk 窗口...\n")
        root = ctk.CTk()
        root.title("diag")
        root.geometry("300x120")
        f.write("[OK] 窗口已创建\n")

        f.write("[4] update_idletasks...\n")
        root.update_idletasks()
        f.write("[OK] update_idletasks 成功\n")

        f.write("[5] destroy...\n")
        root.destroy()
        f.write("[OK] destroy 成功\n")
    except Exception:
        f.write("[ERR] 诊断失败\n")
        f.write(traceback.format_exc())
