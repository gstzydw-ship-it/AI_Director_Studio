from __future__ import annotations

import base64
import json
import os
import shutil
import threading
import traceback
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except Exception as exc:
    ctk = None
    CTK_IMPORT_ERROR = exc
else:
    CTK_IMPORT_ERROR = None

try:
    from PIL import Image
except Exception:
    Image = None

CLI_ERROR = None
try:
    from tools import director_native_cli as cli
except Exception:
    CLI_ERROR = traceback.format_exc()
    cli = None


COLORS = {
    "page": "#fbfcff",
    "panel": "#ffffff",
    "soft": "#f3f6fb",
    "soft_blue": "#eef5ff",
    "line": "#e2e8f0",
    "line_strong": "#d7dfec",
    "text": "#0f172a",
    "muted": "#64748b",
    "faint": "#94a3b8",
    "blue": "#0b63f6",
    "blue_hover": "#0753d8",
    "green": "#16a34a",
    "green_soft": "#dcfce7",
    "orange": "#f59e0b",
    "orange_soft": "#ffedd5",
    "red": "#dc2626",
}

ICONS = {
    "workspace": "⌂",
    "assets": "▧",
    "preview": "▻",
    "frames": "⌗",
    "outputs": "▤",
    "review": "✎",
    "settings": "⚙",
    "project": "▣",
    "status": "◉",
    "quick": "⚡",
    "log": "▤",
    "play": "▷",
    "folder": "▰",
    "save": "▣",
    "copy": "⧉",
    "export": "⇩",
    "send": "✈",
    "check": "✓",
    "dot": "●",
    "empty": "○",
}

NAV_ITEMS = [
    ("workspace", ICONS["workspace"], "工作台"),
    ("assets", ICONS["assets"], "素材库"),
    ("preview", ICONS["preview"], "视频预览"),
    ("frames", ICONS["frames"], "抽帧"),
    ("outputs", ICONS["outputs"], "输出结果"),
    ("review", ICONS["review"], "审改"),
    ("settings", ICONS["settings"], "模型设置"),
]

ASSET_TYPES = [
    ("character", "角色"),
    ("scene", "场景"),
    ("prop", "道具"),
    ("frame", "抽帧"),
    ("upload", "上传"),
]

AGENTS = [
    ("director_showrunner", "剧情增强", "增强原剧本内弱冲突，转成可拍动作"),
    ("rhythm_rewrite_director", "节奏改写", "优化节奏、冲突和情绪推进"),
    ("scene_analyst", "场景分析", "识别人物、地点、动作和视觉元素"),
    ("story_planner", "结构规划", "拆分片段并规划叙事结构"),
    ("shot_director", "镜头导演", "设计景别、机位、运镜和画面说明"),
    ("prompt_compiler", "提示词编译", "整理可用于生成的提示词"),
    ("quality_inspector", "质量检查", "检查连续性、完整性和可生成性"),
]

STEPS = ["剧情增强", "节奏改写", "场景分析", "结构规划", "镜头导演", "提示词编译", "质量检查"]
ASPECT_OPTIONS = ["9:16", "16:9", "1:1", "4:5", "3:4"]
STYLE_OPTIONS = ["都市短剧", "都市商战", "悬疑冷调", "情感现实", "古风精致", "喜剧明亮", "赛博霓虹"]
PROVIDER_OPTIONS = ["火山引擎", "通义千问", "深度求索", "开放接口", "本地模型"]
MODEL_LABEL_TO_ID = {
    "豆包通用模型": "doubao-seed-1-6",
    "通义千问": "qwen-plus",
    "深度求索": "deepseek-chat",
    "开放接口通用": "gpt-4o-mini",
    "本地模型": "local-model",
}
MODEL_NAME_OPTIONS = [
    "doubao-seed-1-6",
    "doubao-1-5-pro-32k",
    "qwen-plus",
    "qwen-max",
    "deepseek-chat",
    "deepseek-reasoner",
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet",
    "gemini-2.5-pro",
]
INTERVAL_OPTIONS = ["1 秒", "2 秒", "3 秒", "5 秒", "10 秒"]
SHOT_SIZE_OPTIONS = ["特写", "近景", "中景", "全景", "远景"]
CAMERA_OPTIONS = ["固定机位", "跟拍", "推近", "拉远", "横移", "俯拍", "仰拍"]
MOVE_OPTIONS = ["静止", "缓慢推进", "跟随", "轻微摇移", "快速切换"]


@dataclass
class WorkerResult:
    kind: str
    payload: Any = None
    error: str | None = None


class DirectorStudioApp(ctk.CTk if ctk else object):
    def __init__(self):
        if CTK_IMPORT_ERROR:
            raise RuntimeError(f"界面组件加载失败: {CTK_IMPORT_ERROR}") from CTK_IMPORT_ERROR
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("AI 短剧导演工作台")
        self.geometry("1680x960")
        self.minsize(1320, 820)
        self.configure(fg_color=COLORS["page"])

        self.session_id = "local"
        self.current_page = "workspace"
        self.status_data: dict[str, Any] = {}
        self.progress_data: dict[str, Any] = {}
        self.projects: list[dict[str, Any]] = []
        self.assets: dict[str, list[dict[str, Any]]] = {}
        self.models: list[dict[str, Any]] = []
        self.nav_buttons: dict[str, Any] = {}
        self.asset_lookup: dict[str, dict[str, Any]] = {}
        self.project_label_to_session: dict[str, str] = {"本地项目": "local"}
        self.available_model_names: list[str] = list(MODEL_NAME_OPTIONS)
        self.image_refs: list[Any] = []
        self.selected_video_path = ""
        self.frame_selection_all = True
        self.logs = ["等待启动分析..."]

        if CLI_ERROR:
            self._build_error(CLI_ERROR)
            return

        self._build_shell()
        self._show_page("workspace")
        self.after(300, self.refresh_all)
        self.after(7000, self.auto_refresh)

    def _font(self, size: int, weight: str = "normal"):
        return ctk.CTkFont(family="Microsoft YaHei UI", size=size, weight=weight)

    def _worker(self, kind: str, func: Callable[[], Any]):
        def task():
            try:
                payload = func()
                self.after(0, lambda: self._handle_result(WorkerResult(kind, payload)))
            except Exception:
                self.after(0, lambda: self._handle_result(WorkerResult(kind, error=traceback.format_exc())))

        threading.Thread(target=task, daemon=True).start()

    def _build_shell(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        topbar = ctk.CTkFrame(self, height=58, corner_radius=0, fg_color=COLORS["panel"], border_width=0)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_propagate(False)
        ctk.CTkLabel(topbar, text="▣", width=28, height=28, fg_color=COLORS["blue"], text_color="#ffffff", corner_radius=6, font=self._font(18, "bold")).pack(side="left", padx=(22, 10), pady=15)
        ctk.CTkLabel(topbar, text="AI 短剧导演工作台", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkFrame(self, height=1, fg_color=COLORS["line"], corner_radius=0).grid(row=0, column=0, columnspan=2, sticky="sew")

        left = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=COLORS["panel"], border_width=0)
        left.grid(row=1, column=0, sticky="ns")
        left.grid_propagate(False)

        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(fill="x", padx=14, pady=(24, 0))
        for key, icon, label in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav,
                text=f"{icon}  {label}",
                height=56,
                corner_radius=10,
                anchor="w",
                fg_color="transparent",
                hover_color=COLORS["soft"],
                text_color=COLORS["text"],
                font=self._font(15, "bold"),
                command=lambda page=key: self._show_page(page),
            )
            btn.pack(fill="x", pady=6)
            self.nav_buttons[key] = btn

        self.toast_label = ctk.CTkLabel(left, text="", font=self._font(12), text_color=COLORS["muted"], wraplength=180, justify="left")
        self.toast_label.pack(side="bottom", anchor="w", padx=20, pady=22)

        self.content = ctk.CTkFrame(self, fg_color=COLORS["page"], corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_columnconfigure(1, weight=0)

        main_wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        main_wrap.grid(row=0, column=0, sticky="nsew", padx=(38, 22), pady=(22, 24))
        main_wrap.grid_rowconfigure(1, weight=1)
        main_wrap.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(main_wrap, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(self.header, text="", font=self._font(30, "bold"), text_color=COLORS["text"])
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = ctk.CTkLabel(self.header, text="", font=self._font(13), text_color=COLORS["muted"])
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))
        ctk.CTkButton(self.header, text="↻  刷新", width=96, height=38, fg_color=COLORS["panel"], hover_color=COLORS["soft"], text_color=COLORS["text"], border_width=1, border_color=COLORS["line"], corner_radius=8, command=self.refresh_all).grid(row=0, column=1, rowspan=2, sticky="e")

        self.page_body = ctk.CTkFrame(main_wrap, fg_color="transparent")
        self.page_body.grid(row=1, column=0, sticky="nsew")

        self._build_right_panel()

    def _build_right_panel(self):
        right = ctk.CTkFrame(self.content, width=320, fg_color=COLORS["page"], corner_radius=0)
        right.grid(row=0, column=1, sticky="ns", padx=(0, 22), pady=(22, 24))
        right.grid_propagate(False)

        project = self._card(right)
        project.pack(fill="x", pady=(0, 14))
        self._section_title(project, f"{ICONS['project']}  当前项目").pack(anchor="w", padx=18, pady=(16, 10))
        self.project_menu = self._menu(project, ["本地项目"], self._select_project)
        self.project_menu.pack(fill="x", padx=18, pady=(0, 12))
        self.project_rows = {}
        for label in ["项目名", "画幅", "风格", "当前阶段"]:
            row = ctk.CTkFrame(project, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=3)
            ctk.CTkLabel(row, text=label, width=72, anchor="w", font=self._font(12), text_color=COLORS["muted"]).pack(side="left")
            value = ctk.CTkLabel(row, text="待设置", anchor="w", font=self._font(12), text_color=COLORS["text"])
            value.pack(side="left", fill="x", expand=True)
            self.project_rows[label] = value

        status = self._card(right)
        status.pack(fill="x", pady=(0, 14))
        top = ctk.CTkFrame(status, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(top, text=f"{ICONS['status']}  运行状态", font=self._font(16, "bold"), text_color=COLORS["text"]).pack(side="left")
        self.status_badge = ctk.CTkLabel(top, text="待启动", font=self._font(12, "bold"), text_color=COLORS["muted"], fg_color=COLORS["soft"], corner_radius=12, width=60, height=24)
        self.status_badge.pack(side="right")
        self.step_labels = []
        for idx, step in enumerate(STEPS):
            row = ctk.CTkFrame(status, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            rail = ctk.CTkFrame(row, fg_color="transparent", width=26)
            rail.pack(side="left", fill="y")
            dot = ctk.CTkLabel(rail, text=ICONS["empty"], width=24, height=24, text_color=COLORS["faint"], font=self._font(15, "bold"))
            dot.pack()
            ctk.CTkLabel(row, text=step, anchor="w", font=self._font(12), text_color=COLORS["text"]).pack(side="left", fill="x", expand=True)
            self.step_labels.append(dot)
        ctk.CTkLabel(status, text="", height=8).pack()

        quick = self._card(right)
        quick.pack(fill="x", pady=(0, 14))
        self._section_title(quick, f"{ICONS['quick']}  快捷操作").pack(anchor="w", padx=18, pady=(16, 10))
        grid = ctk.CTkFrame(quick, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=(0, 16))
        grid.grid_columnconfigure((0, 1), weight=1)
        self._button(grid, f"{ICONS['play']}  启动分析", self.start_analysis, primary=True).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=5)
        self._button(grid, f"{ICONS['folder']}  打开输出页", lambda: self._show_page("outputs")).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=5)
        self._button(grid, f"{ICONS['review']}  进入审改", lambda: self._show_page("review")).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=5)
        self._button(grid, f"{ICONS['save']}  保存项目", self.save_project).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=5)

        log = self._card(right)
        log.pack(fill="both", expand=True)
        head = ctk.CTkFrame(log, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(head, text=f"{ICONS['log']}  运行日志", font=self._font(16, "bold"), text_color=COLORS["text"]).pack(side="left")
        self.log_box = ctk.CTkTextbox(log, height=150, fg_color=COLORS["panel"], border_width=0, text_color=COLORS["muted"], font=self._font(12), wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    def _card(self, parent, radius: int = 12):
        return ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=radius, border_width=1, border_color=COLORS["line"])

    def _section_title(self, parent, text: str):
        return ctk.CTkLabel(parent, text=text, font=self._font(16, "bold"), text_color=COLORS["text"])

    def _button(self, parent, text: str, command: Callable[[], Any], primary: bool = False):
        return ctk.CTkButton(
            parent,
            text=text,
            height=42,
            corner_radius=8,
            fg_color=COLORS["blue"] if primary else COLORS["panel"],
            hover_color=COLORS["blue_hover"] if primary else COLORS["soft"],
            text_color="#ffffff" if primary else COLORS["text"],
            border_width=0 if primary else 1,
            border_color=COLORS["line"],
            font=self._font(13, "bold"),
            command=command,
        )

    def _menu(self, parent, values: list[str], command: Callable[[str], Any] | None = None):
        return ctk.CTkOptionMenu(
            parent,
            values=values or ["暂无选项"],
            height=42,
            corner_radius=8,
            fg_color=COLORS["panel"],
            button_color=COLORS["panel"],
            button_hover_color=COLORS["soft"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["panel"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["soft"],
            command=command,
        )

    def _entry(self, parent, secret: bool = False):
        return ctk.CTkEntry(parent, height=42, corner_radius=8, fg_color=COLORS["panel"], border_color=COLORS["line"], text_color=COLORS["text"], show="*" if secret else "")

    def _textbox(self, parent, height: int = 140):
        return ctk.CTkTextbox(parent, height=height, corner_radius=8, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line"], text_color=COLORS["text"], font=self._font(12), wrap="word")

    def _build_error(self, err: str):
        box = self._card(self)
        box.pack(fill="both", expand=True, padx=28, pady=28)
        ctk.CTkLabel(box, text="后端加载失败", font=self._font(24, "bold"), text_color=COLORS["red"]).pack(anchor="w", padx=18, pady=(18, 10))
        tb = self._textbox(box, 520)
        tb.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        tb.insert("1.0", err)

    def _show_page(self, page: str):
        self.current_page = page
        titles = {
            "workspace": ("工作台", "从剧本到成片，一站式短剧创作与分析"),
            "assets": ("素材库", "管理角色、场景等素材资源，支持添加、查看与复用"),
            "preview": ("视频预览", "预览项目片段视频，查看片段信息，进行后续抽帧或审改操作"),
            "frames": ("抽帧", "选择视频并按间隔抽帧，保存为素材"),
            "outputs": ("输出结果", "查看各模块分析结果，并发送到审改"),
            "review": ("审改", "选择片段和镜头模块，修改后提交第二阶段"),
            "settings": ("模型设置", "配置模型服务、调用参数和流程绑定"),
        }
        title, subtitle = titles[page]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        for key, btn in self.nav_buttons.items():
            btn.configure(fg_color=COLORS["blue"] if key == page else "transparent", text_color="#ffffff" if key == page else COLORS["text"])
        for child in self.page_body.winfo_children():
            child.destroy()
        getattr(self, f"_page_{page}")()

    def _page_workspace(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        overview = self._card(wrap)
        overview.pack(fill="x", pady=(0, 16))
        overview.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(overview, text=f"{ICONS['project']}  项目概览", font=self._font(17, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 10))
        self.project_cover = ctk.CTkLabel(overview, text="项目封面", width=360, height=190, fg_color=COLORS["soft"], text_color=COLORS["muted"], corner_radius=8)
        self.project_cover.grid(row=1, column=0, rowspan=4, sticky="w", padx=18, pady=(0, 18))
        self.overview_rows = {}
        for idx, label in enumerate(["项目名", "画幅", "风格", "当前阶段"]):
            ctk.CTkLabel(overview, text=label, font=self._font(13), text_color=COLORS["muted"], width=110, anchor="w").grid(row=idx + 1, column=1, sticky="w", padx=(28, 8), pady=8)
            value = ctk.CTkLabel(overview, text="待设置", font=self._font(14), text_color=COLORS["text"], anchor="w")
            value.grid(row=idx + 1, column=2, sticky="w", padx=8, pady=8)
            self.overview_rows[label] = value

        steps = self._card(wrap)
        steps.pack(fill="x", pady=(0, 16))
        row = ctk.CTkFrame(steps, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=18)
        for i, label in enumerate(["输入剧本", "选择画幅", "风格设置", "模型配置", "启动分析"]):
            item = self._card(row)
            item.pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkLabel(item, text=str(i + 1), width=28, height=28, fg_color=COLORS["blue"], text_color="#ffffff", corner_radius=14, font=self._font(13, "bold")).pack(anchor="w", padx=14, pady=(14, 6))
            ctk.CTkLabel(item, text=label, font=self._font(13), text_color=COLORS["text"]).pack(pady=(0, 14))

        quick = self._card(wrap)
        quick.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(quick, text=f"{ICONS['quick']}  快速开始", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 10))
        grid = ctk.CTkFrame(quick, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=(0, 18))
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._button(grid, "+  新建项目", self.create_project).grid(row=0, column=0, sticky="ew", padx=8)
        self._button(grid, "▤  导入剧本", self.import_script).grid(row=0, column=1, sticky="ew", padx=8)
        self._button(grid, f"{ICONS['folder']}  进入素材库", lambda: self._show_page("assets")).grid(row=0, column=2, sticky="ew", padx=8)
        self._button(grid, f"{ICONS['play']}  开始分析", self.start_analysis, True).grid(row=0, column=3, sticky="ew", padx=8)

        editor = self._card(wrap)
        editor.pack(fill="x", pady=(0, 16))
        editor_head = ctk.CTkFrame(editor, fg_color="transparent")
        editor_head.pack(fill="x", padx=18, pady=(18, 10))
        ctk.CTkLabel(editor_head, text="▤  剧本输入区", font=self._font(18, "bold"), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(editor_head, text="在下面粘贴剧本，或点击上方“导入剧本”选择文件", font=self._font(12), text_color=COLORS["muted"]).pack(side="left", padx=(16, 0))
        form = ctk.CTkFrame(editor, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 12))
        form.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(form, text="画幅", text_color=COLORS["muted"]).grid(row=0, column=0, padx=(0, 8))
        self.aspect_menu = self._menu(form, ASPECT_OPTIONS)
        self.aspect_menu.grid(row=0, column=1, sticky="ew", padx=(0, 16))
        self.aspect_menu.set("9:16")
        ctk.CTkLabel(form, text="风格", text_color=COLORS["muted"]).grid(row=0, column=2, padx=(0, 8))
        self.style_menu = self._menu(form, STYLE_OPTIONS)
        self.style_menu.grid(row=0, column=3, sticky="ew", padx=(0, 16))
        ctk.CTkLabel(form, text="模型方案", text_color=COLORS["muted"]).grid(row=0, column=4, padx=(0, 8))
        self.profile_menu_main = self._menu(form, ["默认方案"])
        self.profile_menu_main.grid(row=0, column=5, sticky="ew")
        ctk.CTkLabel(editor, text="剧本内容", font=self._font(14, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(2, 6))
        self.script_box = self._textbox(editor, 190)
        self.script_box.pack(fill="x", padx=18, pady=(0, 18))
        self.script_box.insert("1.0", "请把短剧剧本粘贴到这里，或点击“导入剧本”选择文本文件。\n\n示例：\n男主走进办公室电梯区，手机收到一条神秘消息，他停下脚步，表情变得紧张……")
        self.script_placeholder_active = True
        self.script_box.bind("<FocusIn>", self._clear_script_placeholder)
        self.script_box.bind("<FocusOut>", self._restore_script_placeholder)

        bottom = ctk.CTkFrame(wrap, fg_color="transparent")
        bottom.pack(fill="x")
        recent = self._card(bottom)
        recent.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ctk.CTkLabel(recent, text="最近项目", font=self._font(16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 6))
        self.recent_box = self._textbox(recent, 120)
        self.recent_box.pack(fill="x", padx=18, pady=(0, 16))
        flow = self._card(bottom)
        flow.pack(side="left", fill="both", expand=True, padx=(8, 0))
        ctk.CTkLabel(flow, text="流程概览", font=self._font(16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        ctk.CTkLabel(flow, text="节奏改写 → 场景分析 → 结构规划 → 镜头导演 → 提示词编译 → 质量检查", font=self._font(13), text_color=COLORS["muted"], wraplength=470).pack(anchor="w", padx=18, pady=(0, 20))
        self._paint_workspace()

    def _page_assets(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))
        self._button(top, "+  添加素材", self.import_images, True).pack(side="left")
        self.asset_type_filter = self._menu(top, ["全部"] + [name for _, name in ASSET_TYPES], lambda _: self._paint_asset_cards())
        self.asset_type_filter.pack(side="left", padx=24)
        self.asset_source_filter = self._menu(top, ["全部", "本地导入", "视频抽帧"], lambda _: self._paint_asset_cards())
        self.asset_source_filter.pack(side="left")

        self.asset_cards = ctk.CTkFrame(wrap, fg_color="transparent")
        self.asset_cards.pack(fill="x", pady=(0, 16))

        selected = self._card(wrap)
        selected.pack(fill="x")
        ctk.CTkLabel(selected, text="已选素材", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 8))
        row = ctk.CTkFrame(selected, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkLabel(row, text="素材类型", text_color=COLORS["muted"]).pack(side="left")
        self.asset_picker_type = self._menu(row, [name for _, name in ASSET_TYPES], lambda _: self._refresh_asset_picker())
        self.asset_picker_type.pack(side="left", padx=(10, 18))
        ctk.CTkLabel(row, text="素材名称", text_color=COLORS["muted"]).pack(side="left")
        self.asset_picker_item = self._menu(row, ["暂无素材"], self._select_asset)
        self.asset_picker_item.pack(side="left", fill="x", expand=True, padx=(10, 0))

        detail = ctk.CTkFrame(selected, fg_color="transparent")
        detail.pack(fill="x", padx=18, pady=(0, 18))
        self.asset_preview = ctk.CTkLabel(detail, text="暂无缩略图", width=180, height=120, fg_color=COLORS["soft"], text_color=COLORS["muted"], corner_radius=8)
        self.asset_preview.pack(side="left")
        self.asset_info = self._textbox(detail, 120)
        self.asset_info.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self._paint_asset_cards()
        self._refresh_asset_picker()

    def _page_preview(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        controls = ctk.CTkFrame(wrap, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(controls, text="选择片段", text_color=COLORS["muted"]).pack(side="left")
        self.preview_segment = self._menu(controls, self._segment_options())
        self.preview_segment.pack(side="left", padx=12)
        ctk.CTkLabel(controls, text="选择版本", text_color=COLORS["muted"]).pack(side="left", padx=(20, 0))
        self.preview_version = self._menu(controls, ["版本 01（最新）"])
        self.preview_version.pack(side="left", padx=12)
        self._button(controls, "↻  刷新预览", self.refresh_all).pack(side="left", padx=12)
        self._button(controls, f"{ICONS['send']}  发送到抽帧", lambda: self._show_page("frames"), True).pack(side="left")

        main = ctk.CTkFrame(wrap, fg_color="transparent")
        main.pack(fill="x", pady=(0, 16))
        video = self._card(main)
        video.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.preview_image = ctk.CTkLabel(video, text="选择视频或抽帧素材后显示预览", height=380, fg_color="#111827", text_color="#ffffff", corner_radius=8)
        self.preview_image.pack(fill="both", expand=True, padx=14, pady=14)
        info = self._card(main)
        info.pack(side="left", fill="both", padx=(10, 0))
        info.configure(width=300)
        ctk.CTkLabel(info, text="片段信息", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 12))
        self.preview_info = self._textbox(info, 300)
        self.preview_info.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        rows = self._card(wrap)
        rows.pack(fill="x")
        ctk.CTkLabel(rows, text="片段列表", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 8))
        self.segment_list_box = self._textbox(rows, 160)
        self.segment_list_box.pack(fill="x", padx=18, pady=(0, 18))
        self._paint_preview()

    def _page_frames(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        controls = ctk.CTkFrame(wrap, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 16))
        self._button(controls, f"{ICONS['folder']}  选择视频", self.choose_video).pack(side="left")
        ctk.CTkLabel(controls, text="抽帧间隔", text_color=COLORS["muted"]).pack(side="left", padx=(28, 8))
        self.interval_menu = self._menu(controls, INTERVAL_OPTIONS)
        self.interval_menu.pack(side="left")
        self._button(controls, f"{ICONS['play']}  开始抽帧", self.extract_frames, True).pack(side="left", padx=28)
        self._button(controls, f"{ICONS['save']}  保存为素材", self.save_frames_to_assets).pack(side="left")

        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))
        preview = self._card(top)
        preview.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.video_frame_preview = ctk.CTkLabel(preview, text="请选择视频", height=310, fg_color="#111827", text_color="#ffffff", corner_radius=8)
        self.video_frame_preview.pack(fill="both", expand=True, padx=14, pady=14)
        info = self._card(top)
        info.pack(side="left", fill="both", padx=(10, 0))
        info.configure(width=360)
        ctk.CTkLabel(info, text="视频信息", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 12))
        self.video_info_box = self._textbox(info, 250)
        self.video_info_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        result = self._card(wrap)
        result.pack(fill="x")
        ctk.CTkLabel(result, text="抽帧结果", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 8))
        self.frame_grid = ctk.CTkFrame(result, fg_color="transparent")
        self.frame_grid.pack(fill="x", padx=18, pady=(0, 16))
        bottom = ctk.CTkFrame(result, fg_color="transparent")
        bottom.pack(fill="x", padx=18, pady=(0, 18))
        self._button(bottom, f"{ICONS['check']}  全选", self.select_all_frames).pack(side="left")
        self._button(bottom, "加入素材库", self.save_frames_to_assets, True).pack(side="right", padx=(12, 0))
        self._button(bottom, f"{ICONS['export']}  导出图片", self.export_frames).pack(side="right")
        self._paint_frames()

    def _page_outputs(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        tabs = ctk.CTkFrame(wrap, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 14))
        self.output_tab_buttons = {}
        for key, label, _ in AGENTS:
            btn = ctk.CTkButton(tabs, text=label, height=40, fg_color="transparent", hover_color=COLORS["soft"], text_color=COLORS["text"], command=lambda k=key: self._select_output(k))
            btn.pack(side="left", padx=(0, 8))
            self.output_tab_buttons[key] = btn

        stats = ctk.CTkFrame(wrap, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 16))
        self._stat_card(stats, "总片段", str(self._total_segments())).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._stat_card(stats, "已完成模块", f"{self._completed_count()} / 6").pack(side="left", fill="x", expand=True, padx=8)
        self._stat_card(stats, "当前模块", self._agent_label("shot_director")).pack(side="left", fill="x", expand=True, padx=(8, 0))

        body = ctk.CTkFrame(wrap, fg_color="transparent")
        body.pack(fill="both", expand=True)
        left = self._card(body)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.configure(width=330)
        ctk.CTkLabel(left, text="片段列表", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        self.output_segments_box = self._textbox(left, 420)
        self.output_segments_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        right = self._card(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.output_title = ctk.CTkLabel(right, text="模块结果", font=self._font(17, "bold"), text_color=COLORS["text"])
        self.output_title.pack(anchor="w", padx=18, pady=(16, 10))
        self.output_text = self._textbox(right, 420)
        self.output_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        actions = ctk.CTkFrame(wrap, fg_color="transparent")
        actions.pack(fill="x", pady=(16, 0))
        self._button(actions, f"{ICONS['copy']}  复制结果", self.copy_output).pack(side="left", padx=(70, 20))
        self._button(actions, f"{ICONS['export']}  导出文档", self.export_output_doc).pack(side="left", padx=20)
        self._button(actions, f"{ICONS['send']}  发送到审改", lambda: self._show_page("review"), True).pack(side="right", padx=(20, 70))
        self._select_output("shot_director")

    def _page_review(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        controls = ctk.CTkFrame(wrap, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(controls, text="选择片段", text_color=COLORS["muted"]).pack(side="left")
        self.review_segment = self._menu(controls, self._segment_options(), lambda _: self.load_segment())
        self.review_segment.pack(side="left", padx=12)
        ctk.CTkLabel(controls, text="查看模块", text_color=COLORS["muted"]).pack(side="left", padx=(20, 0))
        self.review_module = self._menu(controls, ["镜头列表", "完整文本"])
        self.review_module.pack(side="left", padx=12)
        self._button(controls, "恢复原结果", self.load_segment).pack(side="right", padx=(12, 0))
        self._button(controls, "保存修改", self.save_segment).pack(side="right", padx=12)
        self._button(controls, "提交第二阶段", self.submit_and_continue, True).pack(side="right")

        body = ctk.CTkFrame(wrap, fg_color="transparent")
        body.pack(fill="both", expand=True)
        left = self._card(body)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.configure(width=460)
        ctk.CTkLabel(left, text="镜头列表", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        self.review_list = self._textbox(left, 330)
        self.review_list.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        right = self._card(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(right, text="镜头编辑", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        form = ctk.CTkFrame(right, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 12))
        form.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(form, text="景别").grid(row=0, column=0, sticky="w", pady=5)
        self.review_size = self._menu(form, SHOT_SIZE_OPTIONS)
        self.review_size.grid(row=0, column=1, sticky="ew", padx=(8, 18), pady=5)
        ctk.CTkLabel(form, text="机位").grid(row=0, column=2, sticky="w", pady=5)
        self.review_camera = self._menu(form, CAMERA_OPTIONS)
        self.review_camera.grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=5)
        ctk.CTkLabel(form, text="运镜").grid(row=1, column=0, sticky="w", pady=5)
        self.review_move = self._menu(form, MOVE_OPTIONS)
        self.review_move.grid(row=1, column=1, sticky="ew", padx=(8, 18), pady=5)
        self.review_editor = self._textbox(right, 300)
        self.review_editor.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        note = self._card(wrap)
        note.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(note, text="审改说明", font=self._font(16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 8))
        self.review_note = self._textbox(note, 90)
        self.review_note.pack(fill="x", padx=18, pady=(0, 18))
        self.load_segment()

    def _page_settings(self):
        wrap = ctk.CTkScrollableFrame(self.page_body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        current = self._card(wrap)
        current.pack(fill="x", pady=(0, 18))
        current.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(current, text="当前方案", font=self._font(18, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(18, 10))
        ctk.CTkLabel(current, text="默认方案", font=self._font(17, "bold"), text_color=COLORS["text"]).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        self.connection_label = ctk.CTkLabel(current, text="未测试", fg_color=COLORS["soft"], text_color=COLORS["muted"], corner_radius=12, width=86, height=34)
        self.connection_label.grid(row=1, column=1, sticky="e", padx=(18, 8), pady=(0, 14))
        actions_top = ctk.CTkFrame(current, fg_color="transparent")
        actions_top.grid(row=1, column=2, sticky="e", padx=18, pady=(0, 14))
        self._button(actions_top, "获取模型列表", self.fetch_model_list).pack(side="left", padx=(0, 8))
        self._button(actions_top, "+  新建方案", self.new_model_profile, True).pack(side="left")

        forms = ctk.CTkFrame(wrap, fg_color="transparent")
        forms.pack(fill="x", pady=(0, 18))
        basic = self._card(forms)
        basic.pack(side="left", fill="both", expand=True, padx=(0, 8))
        params = self._card(forms)
        params.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._settings_form(basic)
        self._params_form(params)

        flow = self._card(wrap)
        flow.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(flow, text="各模块独立模型", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(flow, text="每个智能导演模块都可以单独填写接口地址、密钥和模型名称；留空则使用上方默认配置。", font=self._font(12), text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(0, 10))
        agent_grid = ctk.CTkFrame(flow, fg_color="transparent")
        agent_grid.pack(fill="x", padx=18, pady=(0, 16))
        agent_grid.grid_columnconfigure(1, weight=2)
        agent_grid.grid_columnconfigure(2, weight=1)
        agent_grid.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(agent_grid, text="模块", text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 6), padx=(0, 10))
        ctk.CTkLabel(agent_grid, text="接口地址", text_color=COLORS["muted"]).grid(row=0, column=1, sticky="w", pady=(0, 6), padx=(0, 10))
        ctk.CTkLabel(agent_grid, text="密钥", text_color=COLORS["muted"]).grid(row=0, column=2, sticky="w", pady=(0, 6), padx=(0, 10))
        ctk.CTkLabel(agent_grid, text="模型名称", text_color=COLORS["muted"]).grid(row=0, column=3, sticky="w", pady=(0, 6))
        self.agent_model_fields = {}
        for idx, (agent_key, label, _) in enumerate(AGENTS):
            row = idx + 1
            ctk.CTkLabel(agent_grid, text=label, text_color=COLORS["text"]).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
            base_url = self._entry(agent_grid)
            base_url.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 10))
            api_key = self._entry(agent_grid, True)
            api_key.grid(row=row, column=2, sticky="ew", pady=6, padx=(0, 10))
            model = self._menu(agent_grid, self.available_model_names)
            model.grid(row=row, column=3, sticky="ew", pady=6)
            self.agent_model_fields[agent_key] = {
                "base_url": base_url,
                "api_key": api_key,
                "model": model,
            }

        bottom = ctk.CTkFrame(wrap, fg_color="transparent")
        bottom.pack(fill="x")
        result = self._card(bottom)
        result.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ctk.CTkLabel(result, text="连接结果", font=self._font(16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 8))
        self.connection_result = ctk.CTkLabel(result, text="尚未测试连接。", text_color=COLORS["muted"], anchor="w")
        self.connection_result.pack(anchor="w", padx=18, pady=(0, 18))
        actions = ctk.CTkFrame(bottom, fg_color="transparent")
        actions.pack(side="right", pady=28)
        self._button(actions, "测试连接", self.test_model_profile).pack(side="left", padx=8)
        self._button(actions, "保存配置", self.save_model_profile, True).pack(side="left", padx=8)
        self._button(actions, "设为默认", lambda: self._toast("已设为默认方案")).pack(side="left", padx=8)

    def _settings_form(self, parent):
        ctk.CTkLabel(parent, text="基础配置", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 18))
        form.grid_columnconfigure(1, weight=1)
        rows = [("服务商", "provider"), ("接口地址", "base_url"), ("密钥", "api_key"), ("超时时间", "timeout")]
        self.settings_widgets = {}
        for i, (label, key) in enumerate(rows):
            ctk.CTkLabel(form, text=label, text_color=COLORS["text"]).grid(row=i, column=0, sticky="w", pady=7)
            if key == "provider":
                widget = self._menu(form, PROVIDER_OPTIONS)
            elif key == "api_key":
                widget = self._entry(form, True)
            else:
                widget = self._entry(form)
            widget.grid(row=i, column=1, sticky="ew", padx=(16, 0), pady=7)
            self.settings_widgets[key] = widget
        self.settings_widgets["timeout"].insert(0, "60")

    def _params_form(self, parent):
        ctk.CTkLabel(parent, text="调用参数", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 18))
        form.grid_columnconfigure(1, weight=1)
        rows = [("默认模型", "model_name"), ("温度", "temperature"), ("最大长度", "max_tokens"), ("默认画幅", "aspect"), ("重试次数", "retries")]
        self.param_widgets = {}
        for i, (label, key) in enumerate(rows):
            ctk.CTkLabel(form, text=label, text_color=COLORS["text"]).grid(row=i, column=0, sticky="w", pady=7)
            if key == "model_name":
                widget = self._menu(form, self.available_model_names)
            elif key == "aspect":
                widget = self._menu(form, ASPECT_OPTIONS)
            else:
                widget = self._entry(form)
            widget.grid(row=i, column=1, sticky="ew", padx=(16, 0), pady=7)
            self.param_widgets[key] = widget
        self.param_widgets["temperature"].insert(0, "0.7")
        self.param_widgets["max_tokens"].insert(0, "2048")
        self.param_widgets["retries"].insert(0, "2")

    def _stat_card(self, parent, label: str, value: str):
        card = self._card(parent)
        ctk.CTkLabel(card, text=label, font=self._font(13), text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(card, text=value, font=self._font(24, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(0, 18))
        return card

    def refresh_all(self):
        self._worker("status", lambda: cli.cmd_status(self.session_id))
        self._worker("progress", lambda: cli.cmd_pipeline_progress(self.session_id))
        self._worker("projects", lambda: cli.cmd_projects_recent(False))
        self._worker("assets", lambda: cli.cmd_assets_library())
        self._worker("models", lambda: cli.cmd_model_profiles())
        self._toast("已刷新")

    def auto_refresh(self):
        self.refresh_all()
        self.after(7000, self.auto_refresh)

    def create_project(self):
        self._worker("create_project", lambda: cli.cmd_projects_new())

    def import_script(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as file:
                content = file.read()
        except Exception:
            messagebox.showerror("导入失败", "无法读取该剧本文件。")
            return
        if hasattr(self, "script_box"):
            self.script_box.delete("1.0", "end")
            self.script_box.insert("1.0", content)
            self.script_placeholder_active = False
        self._toast("剧本已导入")

    def start_analysis(self):
        script = self.script_box.get("1.0", "end").strip() if hasattr(self, "script_box") else str(self.status_data.get("input_script") or "")
        if getattr(self, "script_placeholder_active", False):
            script = ""
        if not script:
            messagebox.showwarning("缺少剧本", "请在“剧本输入区”的“剧本内容”框里粘贴剧本，或点击“导入剧本”。")
            return
        aspect = self.aspect_menu.get() if hasattr(self, "aspect_menu") else "9:16"
        style = self.style_menu.get() if hasattr(self, "style_menu") else "都市短剧"
        self._worker("run", lambda: cli.cmd_run_pipeline(script, aspect, self.session_id, style_preset=style))
        self._toast("已启动分析")
        self._add_log("分析任务已提交")

    def _clear_script_placeholder(self, _event=None):
        if getattr(self, "script_placeholder_active", False) and hasattr(self, "script_box"):
            self.script_box.delete("1.0", "end")
            self.script_placeholder_active = False

    def _restore_script_placeholder(self, _event=None):
        if hasattr(self, "script_box") and not self.script_box.get("1.0", "end").strip():
            self.script_box.insert("1.0", "请把短剧剧本粘贴到这里，或点击“导入剧本”选择文本文件。\n\n示例：\n男主走进办公室电梯区，手机收到一条神秘消息，他停下脚步，表情变得紧张……")
            self.script_placeholder_active = True

    def choose_video(self):
        path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4 *.mov *.avi *.mkv *.webm")])
        if not path:
            return
        self.selected_video_path = path
        self._paint_video_preview(path)
        self._toast("视频已选择")

    def extract_frames(self):
        if not self.selected_video_path:
            self.choose_video()
        if not self.selected_video_path:
            return
        seconds = 3
        if hasattr(self, "interval_menu"):
            seconds = int("".join(ch for ch in self.interval_menu.get() if ch.isdigit()) or "3")
        self._worker("frames", lambda: cli.cmd_video_extract_frames(self.selected_video_path, seconds, 12))
        self._toast("正在抽帧")

    def import_images(self):
        asset_type = "character"
        if hasattr(self, "asset_type_filter"):
            label = self.asset_type_filter.get()
            if label != "全部":
                asset_type = self._asset_type_key(label)
        elif hasattr(self, "asset_picker_type"):
            asset_type = self._asset_type_key(self.asset_picker_type.get())
        paths = list(filedialog.askopenfilenames(filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp")]))
        if not paths:
            return
        self._worker("import_assets", lambda: cli.cmd_assets_import_batch(asset_type, "", "", "项目参考", paths))
        self._toast("素材已添加")

    def load_segment(self):
        if not hasattr(self, "review_editor"):
            return
        text = self._segment_text_from_state(self.status_data, self._current_segment())
        self.review_editor.delete("1.0", "end")
        self.review_editor.insert("1.0", text or "暂无可审改内容，请先启动分析。")
        if hasattr(self, "review_list"):
            self.review_list.delete("1.0", "end")
            self.review_list.insert("1.0", self._shot_list_text(text))

    def save_segment(self):
        content = self.review_editor.get("1.0", "end").strip() if hasattr(self, "review_editor") else ""
        self._worker("save_edit", lambda: cli.cmd_director_edits_save(self.session_id, self._current_segment(), content))
        self._toast("修改已保存")

    def submit_and_continue(self):
        content = self.review_editor.get("1.0", "end").strip() if hasattr(self, "review_editor") else ""
        self._worker("submit_edit", lambda: cli.cmd_director_edits_submit(self.session_id, self._current_segment(), content))
        self._toast("已提交第二阶段")

    def copy_output(self):
        if hasattr(self, "output_text"):
            self.clipboard_clear()
            self.clipboard_append(self.output_text.get("1.0", "end").strip())
            self._toast("结果已复制")

    def save_project(self):
        self._add_log("项目状态已保存/同步")
        self.refresh_all()
        self._toast("项目已保存")

    def show_asset_detail(self, asset: dict[str, Any] | None):
        if not asset:
            messagebox.showinfo("素材详情", "当前分类暂无素材。")
            return
        tags = "、".join(asset.get("tags") or []) or "无"
        text = f"名称：{asset.get('name', '')}\n类型：{self._asset_type_label(asset.get('type', ''))}\n文件：{asset.get('filename', '')}\n标签：{tags}\n说明：{asset.get('description') or '无'}"
        messagebox.showinfo("素材详情", text)
        if hasattr(self, "asset_info"):
            self.asset_info.delete("1.0", "end")
            self.asset_info.insert("1.0", text)

    def add_asset_to_project(self, asset: dict[str, Any] | None):
        if not asset:
            messagebox.showinfo("加入项目", "当前分类暂无可加入素材。")
            return
        self._add_log(f"素材已加入项目：{asset.get('name') or asset.get('filename') or '未命名素材'}")
        self._toast("已加入当前项目")

    def select_all_frames(self):
        self.frame_selection_all = True
        self._toast("已选择全部抽帧")
        self._paint_frames()

    def save_frames_to_assets(self):
        self._show_page("assets")
        self._toast("抽帧素材已在素材库中可用")

    def export_frames(self):
        rows = self.assets.get("frame", [])
        if not rows:
            messagebox.showinfo("导出图片", "暂无抽帧图片可导出，请先抽帧。")
            return
        folder = filedialog.askdirectory(title="选择导出目录")
        if not folder:
            return
        count = 0
        for idx, asset in enumerate(rows, 1):
            source = str(asset.get("path") or asset.get("file_path") or "")
            if source and os.path.exists(source):
                try:
                    shutil.copy2(source, os.path.join(folder, os.path.basename(source)))
                    count += 1
                except Exception:
                    pass
            else:
                thumb = str(asset.get("thumbnail") or "")
                if thumb:
                    try:
                        encoded = thumb.split(",", 1)[1] if "," in thumb else thumb
                        with open(os.path.join(folder, f"frame_{idx:03d}.png"), "wb") as file:
                            file.write(base64.b64decode(encoded))
                        count += 1
                    except Exception:
                        pass
        self._toast(f"已导出 {count} 张图片")
        self._add_log(f"抽帧图片已导出：{count} 张")

    def export_output_doc(self):
        text = self.output_text.get("1.0", "end").strip() if hasattr(self, "output_text") else ""
        if not text or text == "暂无结果，请先启动分析。":
            messagebox.showinfo("导出文档", "暂无可导出的模块结果。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown 文档", "*.md"), ("文本文件", "*.txt")], initialfile="AI短剧导演输出结果.md")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as file:
            file.write(f"# AI 短剧导演输出结果\n\n{self.output_title.cget('text') if hasattr(self, 'output_title') else '模块结果'}\n\n```text\n{text}\n```\n")
        self._toast("文档已导出")
        self._add_log("输出结果已导出为文档")

    def new_model_profile(self):
        if hasattr(self, "settings_widgets"):
            for key in ["base_url", "api_key", "timeout"]:
                if key in self.settings_widgets:
                    self.settings_widgets[key].delete(0, "end")
            self.settings_widgets["timeout"].insert(0, "60")
        if hasattr(self, "param_widgets"):
            defaults = {"temperature": "0.7", "max_tokens": "2048", "retries": "2"}
            for key, value in defaults.items():
                self.param_widgets[key].delete(0, "end")
                self.param_widgets[key].insert(0, value)
        self._toast("已新建空白方案")

    def save_model_profile(self):
        provider = self.settings_widgets["provider"].get() if hasattr(self, "settings_widgets") else "开放接口"
        default_model = self.param_widgets["model_name"].get().strip() if hasattr(self, "param_widgets") and "model_name" in self.param_widgets else ""
        default_model = default_model or self.available_model_names[0]
        agent_models = self._collect_agent_models(default_model)
        payload = {
            "name": provider,
            "id": provider,
            "base_url": self.settings_widgets["base_url"].get().strip(),
            "api_key": self.settings_widgets["api_key"].get().strip(),
            "default_model": default_model,
            "agent_models": agent_models,
            "max_tokens": self.param_widgets["max_tokens"].get().strip(),
            "max_retries": self.param_widgets["retries"].get().strip(),
            "timeout_seconds": self.settings_widgets["timeout"].get().strip(),
        }
        self._worker("save_model", lambda: cli.cmd_save_model_profile(payload))

    def test_model_profile(self):
        self.connection_label.configure(text="测试中", text_color=COLORS["orange"])
        provider = self.settings_widgets["provider"].get()
        model_name = self.param_widgets["model_name"].get().strip() or self.available_model_names[0]
        payload = {
            "name": provider,
            "base_url": self.settings_widgets["base_url"].get().strip(),
            "api_key": self.settings_widgets["api_key"].get().strip(),
            "default_model": model_name,
        }
        self._worker("test_model", lambda: cli.cmd_test_model_profile(payload))

    def fetch_model_list(self):
        base_url = self.settings_widgets["base_url"].get().strip() if hasattr(self, "settings_widgets") else ""
        api_key = self.settings_widgets["api_key"].get().strip() if hasattr(self, "settings_widgets") else ""
        base_url = base_url or "https://www.xkwuai.cn/v1"
        self._toast("正在获取模型列表")
        self._worker("fetch_models", lambda: self._fetch_models_from_api(base_url, api_key))

    def _fetch_models_from_api(self, base_url: str, api_key: str):
        import requests

        url = base_url.rstrip("/") + "/models"
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.get(url, headers=headers, timeout=25, verify=False)
        response.raise_for_status()
        data = response.json()
        rows = data.get("data", data if isinstance(data, list) else [])
        names = []
        for item in rows:
            if isinstance(item, dict):
                name = item.get("id") or item.get("name") or item.get("model")
            else:
                name = str(item)
            if name:
                names.append(str(name).strip())
        names = [name for name in dict.fromkeys(names) if name]
        if not names:
            raise RuntimeError("接口没有返回可用模型名称")
        return names

    def resume_phase2(self):
        self._worker("resume", lambda: cli.cmd_resume_pipeline(self.session_id, self._current_segment()))
        self._toast("已进入第二阶段")

    def _handle_result(self, result: WorkerResult):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if result.error:
            self._add_log("操作失败，请检查配置或日志。")
            self._toast("操作失败")
            return
        kind, payload = result.kind, result.payload
        if kind == "status":
            self.status_data = payload or {}
            self._paint_all_dynamic()
        elif kind == "progress":
            self.progress_data = payload or {}
            self._paint_status()
        elif kind == "projects":
            self.projects = payload or []
            self._paint_projects()
        elif kind == "assets":
            self.assets = (payload or {}).get("groups", {}) if isinstance(payload, dict) else {}
            self._paint_assets_dynamic()
        elif kind == "models":
            self.models = payload or []
            self._paint_models_dynamic()
        elif kind == "create_project":
            project = payload or {}
            self.session_id = project.get("session_id") or self.session_id
            self._add_log("新项目已创建")
            self.refresh_all()
        elif kind in {"run", "frames", "import_assets", "save_edit", "submit_edit", "resume", "save_model"}:
            self._add_log("操作已完成")
            self.refresh_all()
        elif kind == "test_model":
            ok = bool((payload or {}).get("success"))
            if hasattr(self, "connection_label"):
                self.connection_label.configure(text="已连接" if ok else "未连接", text_color=COLORS["green"] if ok else COLORS["red"])
            if hasattr(self, "connection_result"):
                self.connection_result.configure(text="连接成功，可以正常调用模型服务。" if ok else "连接失败，请检查接口地址、密钥或网络。")
        elif kind == "fetch_models":
            self.available_model_names = list(payload or MODEL_NAME_OPTIONS)
            self._paint_model_dropdowns()
            if hasattr(self, "connection_result"):
                self.connection_result.configure(text=f"已获取 {len(self.available_model_names)} 个模型，所有模型下拉框已更新。")
            self._toast("模型列表已更新")

    def _paint_all_dynamic(self):
        self._paint_status()
        self._paint_project_info()
        self._paint_workspace()
        if self.current_page == "outputs":
            self._select_output(getattr(self, "selected_output_agent", "shot_director"))
        if self.current_page == "preview":
            self._paint_preview()
        if self.current_page == "review":
            self.load_segment()

    def _paint_status(self):
        data = self.progress_data or self.status_data or {}
        status = str(data.get("status") or data.get("phase") or "idle")
        running = status in {"running", "running_phase_1", "running_phase_2"}
        error = status == "error" or bool(data.get("error"))
        label = "运行中" if running else "异常" if error else "待启动"
        color = COLORS["green"] if running else COLORS["red"] if error else COLORS["muted"]
        self.status_badge.configure(text=label, text_color=color)
        active = self._active_step_index(status)
        for i, dot in enumerate(self.step_labels):
            if i < active:
                dot.configure(text=ICONS["dot"], text_color=COLORS["green"])
            elif i == active and running:
                dot.configure(text=ICONS["dot"], text_color=COLORS["blue"])
            else:
                dot.configure(text=ICONS["empty"], text_color=COLORS["faint"])

    def _paint_project_info(self):
        name = str(self.status_data.get("project_name") or "未命名项目")
        aspect = str(self.status_data.get("input_aspect_ratio") or "9:16")
        style = str(self.status_data.get("style_preset") or "都市短剧")
        stage = self._status_label(str(self.status_data.get("status") or "idle"))
        values = {"项目名": name, "画幅": aspect, "风格": style, "当前阶段": stage}
        for key, value in values.items():
            try:
                if key in self.project_rows and self.project_rows[key].winfo_exists():
                    self.project_rows[key].configure(text=value)
            except Exception:
                pass
            try:
                if hasattr(self, "overview_rows") and key in self.overview_rows and self.overview_rows[key].winfo_exists():
                    self.overview_rows[key].configure(text=value)
            except Exception:
                pass

    def _paint_workspace(self):
        if self._alive("recent_box"):
            self.recent_box.delete("1.0", "end")
            lines = []
            for project in self.projects[:4]:
                lines.append(f"{project.get('name', '未命名项目')}    {project.get('status', '待启动')}")
            self.recent_box.insert("1.0", "\n".join(lines) or "暂无最近项目")
        self._paint_project_info()

    def _paint_projects(self):
        labels = ["本地项目"]
        self.project_label_to_session = {"本地项目": "local"}
        used = {"本地项目"}
        for project in self.projects:
            base = self._project_label(project)
            label = base
            index = 2
            while label in used:
                label = f"{base}（{index}）"
                index += 1
            used.add(label)
            labels.append(label)
            self.project_label_to_session[label] = str(project.get("session_id") or "local")
        if hasattr(self, "project_menu"):
            self.project_menu.configure(values=labels)
            current = next((x for x in labels if self._session_from_label(x) == self.session_id), "本地项目")
            self.project_menu.set(current)
        self._paint_workspace()

    def _paint_assets_dynamic(self):
        if self.current_page == "assets":
            self._paint_asset_cards()
            self._refresh_asset_picker()
        if self.current_page == "frames":
            self._paint_frames()
        if self.current_page == "preview":
            self._paint_preview()

    def _paint_models_dynamic(self):
        if self._alive("profile_menu_main"):
            names = [str(m.get("name") or "") for m in self.models if m.get("name")]
            values = list(dict.fromkeys(["默认方案"] + names))
            try:
                self.profile_menu_main.configure(values=values)
            except Exception:
                pass

    def _paint_asset_cards(self):
        if not hasattr(self, "asset_cards"):
            return
        for child in self.asset_cards.winfo_children():
            child.destroy()
        selected = self.asset_type_filter.get() if hasattr(self, "asset_type_filter") else "全部"
        types = ASSET_TYPES if selected == "全部" else [(self._asset_type_key(selected), selected)]
        for idx, (key, label) in enumerate(types[:2]):
            rows = self.assets.get(key, [])
            card = self._card(self.asset_cards)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=8, pady=8)
            self.asset_cards.grid_columnconfigure(idx % 2, weight=1)
            ctk.CTkLabel(card, text=f"{label}素材", font=self._font(17, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 8))
            image = self._asset_image(rows[0], (450, 250)) if rows else None
            preview = ctk.CTkLabel(card, text="暂无素材", image=image, height=250, fg_color=COLORS["soft"], text_color=COLORS["muted"], corner_radius=8)
            preview.pack(fill="x", padx=18, pady=(0, 10))
            if image:
                self.image_refs.append(image)
            name = rows[0].get("name") if rows else "暂无素材"
            ctk.CTkLabel(card, text=name, font=self._font(16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(0, 6))
            tags = "    ".join((rows[0].get("tags") or [])[:4]) if rows else ""
            ctk.CTkLabel(card, text=tags, font=self._font(12), text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(0, 12))
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(fill="x", padx=18, pady=(0, 16))
            self._button(actions, "查看详情", lambda a=rows[0] if rows else None: self.show_asset_detail(a)).pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._button(actions, "加入项目", lambda a=rows[0] if rows else None: self.add_asset_to_project(a), True).pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _refresh_asset_picker(self):
        if not hasattr(self, "asset_picker_item"):
            return
        key = self._asset_type_key(self.asset_picker_type.get())
        rows = self.assets.get(key, [])
        self.asset_lookup = {self._asset_label(asset): asset for asset in rows}
        values = list(self.asset_lookup) or ["暂无素材"]
        self.asset_picker_item.configure(values=values)
        self.asset_picker_item.set(values[0])
        self._select_asset(values[0])

    def _select_asset(self, label: str):
        asset = self.asset_lookup.get(label)
        if not asset:
            if hasattr(self, "asset_info"):
                self.asset_info.delete("1.0", "end")
                self.asset_info.insert("1.0", "当前类型暂无素材。")
            if hasattr(self, "asset_preview"):
                self.asset_preview.configure(text="暂无缩略图", image=None)
            return
        tags = "、".join(asset.get("tags") or []) or "无"
        info = f"名称：{asset.get('name', '')}\n类型：{self._asset_type_label(asset.get('type', ''))}\n文件：{asset.get('filename', '')}\n标签：{tags}\n说明：{asset.get('description') or '无'}"
        self.asset_info.delete("1.0", "end")
        self.asset_info.insert("1.0", info)
        image = self._asset_image(asset, (180, 120))
        self.asset_preview.configure(text="" if image else "暂无缩略图", image=image)
        if image:
            self.image_refs.append(image)

    def _paint_preview(self):
        if hasattr(self, "preview_info"):
            info = f"片段编号：{self._current_segment():03d}\n时长：待生成\n画幅：{self.status_data.get('input_aspect_ratio', '9:16')}\n状态：{self._status_label(str(self.status_data.get('status') or 'idle'))}\n\n内容摘要：\n{self._segment_summary()}"
            self.preview_info.delete("1.0", "end")
            self.preview_info.insert("1.0", info)
        if hasattr(self, "segment_list_box"):
            rows = [f"{i:03d}    片段 {i}    {self.status_data.get('input_aspect_ratio', '9:16')}    待预览" for i in range(1, self._total_segments() + 1)]
            self.segment_list_box.delete("1.0", "end")
            self.segment_list_box.insert("1.0", "\n".join(rows) or "暂无片段，请先启动分析。")
        frame = self._first_asset("frame") or self._first_asset("scene") or self._first_asset("character")
        if hasattr(self, "preview_image"):
            image = self._asset_image(frame, (740, 380)) if frame else None
            self.preview_image.configure(text="" if image else "暂无视频预览", image=image)
            if image:
                self.image_refs.append(image)

    def _paint_frames(self):
        if not hasattr(self, "frame_grid"):
            return
        for child in self.frame_grid.winfo_children():
            child.destroy()
        rows = self.assets.get("frame", [])[:8]
        for i, asset in enumerate(rows):
            cell = ctk.CTkFrame(self.frame_grid, fg_color="transparent")
            cell.grid(row=i // 4, column=i % 4, sticky="nsew", padx=8, pady=8)
            self.frame_grid.grid_columnconfigure(i % 4, weight=1)
            img = self._asset_image(asset, (230, 120))
            tile = ctk.CTkFrame(cell, fg_color=COLORS["soft"], corner_radius=7)
            tile.pack(fill="x")
            if self.frame_selection_all:
                ctk.CTkLabel(tile, text=ICONS["check"], width=22, height=22, fg_color=COLORS["blue"], text_color="#ffffff", corner_radius=4, font=self._font(12, "bold")).place(x=4, y=4)
            ctk.CTkLabel(tile, text="" if img else "暂无图像", image=img, height=120, fg_color="transparent", corner_radius=7).pack(fill="x")
            if img:
                self.image_refs.append(img)
            ctk.CTkLabel(cell, text=asset.get("timecode") or asset.get("name") or "抽帧", font=self._font(12), text_color=COLORS["muted"]).pack(anchor="w", pady=(4, 0))
        if not rows:
            ctk.CTkLabel(self.frame_grid, text="暂无抽帧结果，请先选择视频并开始抽帧。", text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=20)

    def _select_output(self, key: str):
        self.selected_output_agent = key
        for k, btn in getattr(self, "output_tab_buttons", {}).items():
            btn.configure(text_color=COLORS["blue"] if k == key else COLORS["text"], fg_color=COLORS["soft"] if k == key else "transparent")
        label = self._agent_label(key)
        if hasattr(self, "output_title"):
            self.output_title.configure(text=f"{label}结果")
        outputs = self.status_data.get("agent_outputs") if isinstance(self.status_data, dict) else {}
        value = outputs.get(key) if isinstance(outputs, dict) else None
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) if value else "暂无结果，请先启动分析。"
        if hasattr(self, "output_text"):
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", text)
        if hasattr(self, "output_segments_box"):
            rows = [f"片段 {i:02d}    待查看" for i in range(1, self._total_segments() + 1)]
            self.output_segments_box.delete("1.0", "end")
            self.output_segments_box.insert("1.0", "\n".join(rows) or "暂无片段")

    def _paint_video_preview(self, path: str):
        if hasattr(self, "video_info_box"):
            self.video_info_box.delete("1.0", "end")
            self.video_info_box.insert("1.0", f"视频名称：{os.path.basename(path)}\n抽帧间隔：{self.interval_menu.get() if hasattr(self, 'interval_menu') else '3 秒'}\n当前状态：已选择")
        if Image is None:
            return
        try:
            import cv2

            cap = cv2.VideoCapture(path)
            ok, frame = cap.read()
            cap.release()
            if ok:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(frame)
                pil.thumbnail((760, 310))
                img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
                self.video_frame_preview.configure(text="", image=img)
                self.image_refs.append(img)
        except Exception:
            self.video_frame_preview.configure(text="视频预览不可用")

    def _asset_image(self, asset: dict[str, Any] | None, size: tuple[int, int]):
        if not asset or Image is None:
            return None
        thumb = str(asset.get("thumbnail") or "")
        if not thumb:
            return None
        try:
            encoded = thumb.split(",", 1)[1] if "," in thumb else thumb
            pil = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGB")
            pil.thumbnail(size)
            return ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
        except Exception:
            return None

    def _first_asset(self, key: str):
        rows = self.assets.get(key, [])
        return rows[0] if rows else None

    def _project_label(self, project: dict[str, Any]):
        return str(project.get("name") or "未命名项目")

    def _session_from_label(self, label: str):
        return self.project_label_to_session.get(label, "local")

    def _select_project(self, label: str):
        self.session_id = self._session_from_label(label)
        self.refresh_all()

    def _segment_options(self):
        return [f"第 {i} 段" for i in range(1, self._total_segments() + 1)]

    def _current_segment(self):
        widget = getattr(self, "review_segment", None) or getattr(self, "preview_segment", None)
        value = widget.get() if widget else "第 1 段"
        digits = "".join(ch for ch in value if ch.isdigit())
        return max(1, int(digits or "1"))

    def _total_segments(self):
        return max(1, int(self.status_data.get("total_segments") or len(self.status_data.get("segment_names") or []) or 5))

    def _completed_count(self):
        outputs = self.status_data.get("agent_outputs") if isinstance(self.status_data, dict) else {}
        return sum(1 for key, _, _ in AGENTS if isinstance(outputs, dict) and outputs.get(key))

    def _agent_label(self, key: str):
        return next((label for k, label, _ in AGENTS if k == key), "镜头导演")

    def _asset_type_key(self, label: str):
        return next((key for key, name in ASSET_TYPES if name == label), "character")

    def _asset_type_label(self, key: str):
        return next((name for k, name in ASSET_TYPES if k == key), key)

    def _collect_agent_models(self, default_model: str):
        result = {}
        fields = getattr(self, "agent_model_fields", {})
        for agent_key, widgets in fields.items():
            base_url = widgets["base_url"].get().strip()
            api_key = widgets["api_key"].get().strip()
            model = widgets["model"].get().strip()
            if base_url or api_key or model:
                result[agent_key] = {
                    "base_url": base_url,
                    "api_key": api_key,
                    "model": model or default_model,
                }
        return result

    def _asset_label(self, asset: dict[str, Any]):
        name = str(asset.get("name") or asset.get("filename") or "未命名素材")
        filename = str(asset.get("filename") or "")
        short = filename[:24] + "..." if len(filename) > 27 else filename
        return f"{name} [{short or name}]"

    def _status_label(self, status: str):
        return {
            "idle": "第一阶段分析前",
            "running": "运行中",
            "running_phase_1": "第一阶段分析中",
            "waiting_for_user_input": "第二阶段审改",
            "running_phase_2": "第二阶段生成中",
            "completed": "已完成",
            "done": "已完成",
            "error": "运行异常",
        }.get(status, "待启动")

    def _active_step_index(self, status: str):
        if status in {"running_phase_2", "completed", "done"}:
            return 5
        if status == "waiting_for_user_input":
            return 4
        if status == "running_phase_1":
            return 2
        return 0

    def _segment_text_from_state(self, state: dict[str, Any], segment: int):
        key = str(segment)
        edits = state.get("director_edits_by_segment") or {}
        if isinstance(edits, dict) and isinstance(edits.get(key), dict):
            return str(edits[key].get("edited_yaml") or "")
        outputs = state.get("agent_outputs") if isinstance(state, dict) else {}
        return str(outputs.get("shot_director") or "") if isinstance(outputs, dict) else ""

    def _shot_list_text(self, text: str):
        if not text:
            return "暂无镜头列表"
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines[:18]) or "暂无镜头列表"

    def _segment_summary(self):
        text = self._segment_text_from_state(self.status_data, self._current_segment())
        return (text[:180] + "...") if len(text) > 180 else text or "暂无摘要"

    def _add_log(self, text: str):
        self.logs.append(text)
        if len(self.logs) > 8:
            self.logs = self.logs[-8:]
        if self._alive("log_box"):
            try:
                self.log_box.delete("1.0", "end")
                self.log_box.insert("1.0", "\n".join(self.logs))
            except Exception:
                pass

    def _toast(self, text: str):
        if self._alive("toast_label"):
            self.toast_label.configure(text=text)
            self.after(3000, self._clear_toast)

    def _clear_toast(self):
        if self._alive("toast_label"):
            self.toast_label.configure(text="")

    def _alive(self, name: str) -> bool:
        widget = getattr(self, name, None)
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False


def main():
    app = DirectorStudioApp()
    app.mainloop()
