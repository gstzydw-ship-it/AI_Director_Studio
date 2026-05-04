"""主题配色与样式配置 — 参考 VS Code Dark+ / Open WebUI"""
from __future__ import annotations
import tkinter as tk

try:
    import customtkinter as ctk
    HAS_CTK = True
except Exception:
    HAS_CTK = False

# ── 配色方案 ──────────────────────────────────────────────
COLORS = {
    "bg_primary":   "#0d1117",   # 主背景（VS Code 标题栏）
    "bg_secondary": "#161b22",   # 次级背景（侧边栏）
    "bg_card":      "#1c2128",   # 卡片背景
    "bg_input":     "#21262d",   # 输入框背景
    "border":       "#30363d",   # 边框
    "border_light": "#484f58",   # 亮色边框
    "text_primary": "#e6edf3",   # 主文字
    "text_secondary":"#8b949e",  # 次文字
    "text_muted":   "#6e7681",   # 暗淡文字
    "accent":       "#58a6ff",   # 强调蓝
    "accent_hover": "#79c0ff",   # 强调蓝 hover
    "success":      "#238636",   # 成功绿
    "success_light":"#3fb950",
    "warning":      "#d29922",   # 警告黄
    "error":        "#f85149",   # 错误红
    "info":         "#58a6ff",   # 信息蓝
}

STEP_COLORS = {
    "done":    COLORS["success_light"],
    "active":  COLORS["warning"],
    "pending": COLORS["text_muted"],
}

AGENT_COLORS = {
    "rhythm_rewrite_director": "#a371f7",
    "scene_analyst":           "#58a6ff",
    "story_planner":           "#3fb950",
    "shot_director":           "#d29922",
    "prompt_compiler":         "#f0883e",
    "quality_inspector":       "#f85149",
}

# ── 字体 ──────────────────────────────────────────────────
def get_font(size: int = 12, weight: str = "normal"):
    if HAS_CTK:
        return ctk.CTkFont(family="Microsoft YaHei", size=size, weight=weight)
    return ("Microsoft YaHei", size, weight)

FONTS = {
    "title":       get_font(22, "bold"),
    "subtitle":    get_font(14, "normal"),
    "heading":     get_font(16, "bold"),
    "body":        get_font(12, "normal"),
    "body_bold":   get_font(12, "bold"),
    "small":       get_font(10, "normal"),
    "small_bold":  get_font(10, "bold"),
    "mono":        get_font(11, "normal"),
    "badge":       get_font(10, "bold"),
}

# ── Widget 封装 ───────────────────────────────────────────
if HAS_CTK:
    Win   = ctk.CTk
    Fr    = ctk.CTkFrame
    Lb    = ctk.CTkLabel
    Btn   = ctk.CTkButton
    Ent   = ctk.CTkEntry
    Tx    = ctk.CTkTextbox
    Scr   = ctk.CTkScrollableFrame
    PB    = ctk.CTkProgressBar
    Seg   = ctk.CTkSegmentedButton
    
    def make_card(parent, title: str = ""):
        c = Fr(parent, corner_radius=8, fg_color=COLORS["bg_card"],
               border_width=1, border_color=COLORS["border"])
        if title:
            Lb(c, text=title, font=FONTS["heading"], text_color=COLORS["text_primary"]
              ).pack(anchor="w", padx=16, pady=(14, 10))
        return c
    
    def make_badge(parent, text: str, color: str):
        return Lb(parent, text=text, font=FONTS["badge"],
                  text_color=COLORS["bg_primary"], fg_color=color,
                  corner_radius=12, width=60, height=22)

else:
    # 纯 tkinter fallback
    class _Fr(tk.Frame):
        def __init__(self, master=None, **kw):
            for k in ("fg_color","corner_radius","border_width","border_color"): kw.pop(k,None)
            bg = kw.pop("bg", COLORS["bg_card"])
            super().__init__(master, bg=bg, **kw)
    class _Lb(tk.Label):
        def __init__(self, master=None, **kw):
            kw.pop("text_color", None); kw.pop("font", None); kw.pop("corner_radius", None)
            kw.pop("fg_color", None); kw.pop("width", None); kw.pop("height", None)
            super().__init__(master, bg=COLORS["bg_card"], fg=COLORS["text_primary"], **kw)
    class _Btn(tk.Button):
        def __init__(self, master=None, **kw):
            for k in ("corner_radius","fg_color","hover_color","border_width","width","height",
                      "text_color","border_color"): kw.pop(k,None)
            super().__init__(master, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"], **kw)
    class _Ent(tk.Entry):
        def __init__(self, master=None, **kw):
            kw.pop("placeholder_text", None); kw.pop("font", None); kw.pop("corner_radius", None)
            kw.pop("fg_color", None); kw.pop("border_color", None); kw.pop("text_color", None)
            super().__init__(master, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                            insertbackground=COLORS["text_primary"], **kw)
    class _Tx(tk.Text):
        def __init__(self, master=None, **kw):
            kw.pop("corner_radius", None); kw.pop("font", None); kw.pop("fg_color", None)
            kw.pop("border_color", None); kw.pop("text_color", None)
            super().__init__(master, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                            insertbackground=COLORS["text_primary"], **kw)
    class _Scr(tk.Frame):
        def __init__(self, master=None, **kw):
            kw.pop("fg_color", None); kw.pop("corner_radius", None)
            super().__init__(master, bg=COLORS["bg_primary"], **kw)
    
    Win = tk.Tk
    Fr  = _Fr
    Lb  = _Lb
    Btn = _Btn
    Ent = _Ent
    Tx  = _Tx
    Scr = _Scr
    PB  = None
    Seg = None
    
    def make_card(parent, title: str = ""):
        c = Fr(parent, bg=COLORS["bg_card"])
        if title:
            tk.Label(c, text=title, font=get_font(16, "bold"), bg=COLORS["bg_card"],
                    fg=COLORS["text_primary"]).pack(anchor="w", padx=12, pady=(10, 8))
        return c
    
    def make_badge(parent, text: str, color: str):
        return tk.Label(parent, text=text, font=get_font(10, "bold"),
                       bg=color, fg=COLORS["bg_primary"])

def cset(widget, **kw):
    """安全 configure"""
    try:
        if hasattr(widget, "configure"): widget.configure(**kw)
        else: widget.config(**kw)
    except Exception:
        pass
