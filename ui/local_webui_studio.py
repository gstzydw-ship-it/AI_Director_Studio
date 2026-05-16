from __future__ import annotations

import base64
import json
import os
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except Exception as exc:  # pragma: no cover - shown in the UI at runtime
    ctk = None
    CTK_IMPORT_ERROR = exc
else:
    CTK_IMPORT_ERROR = None

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover - thumbnails are optional
    Image = None
    ImageOps = None

CLI_ERROR = None
try:
    from tools import director_native_cli as cli
except Exception:  # pragma: no cover - shown in the UI at runtime
    CLI_ERROR = traceback.format_exc()
    cli = None


UI_MODE = "customtkinter-webui-layout"

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "output"

COLORS = {
    "bg": "#0b0f17",
    "sidebar": "#111827",
    "panel": "#171c25",
    "panel_2": "#1e2530",
    "panel_3": "#11151d",
    "line": "#2d3748",
    "line_soft": "#263142",
    "text": "#f5f7fb",
    "muted": "#98a2b3",
    "faint": "#667085",
    "gold": "#f6b73c",
    "gold_hover": "#ffd166",
    "cyan": "#4cc9d8",
    "green": "#35c486",
    "red": "#ef615f",
    "input": "#0f141d",
}

NAV_ITEMS = [
    ("workspace", "01", "导演工作台"),
    ("config", "02", "模型配置"),
    ("knowledge", "03", "知识库"),
]

STEPS = [
    ("analyze", "01", "场景预分析", "参考图 / 站位 / 空间"),
    ("enhance", "02", "剧情增强", "弱冲突可拍化"),
    ("plan", "03", "节奏拆片导演", "快慢 / 时长 / 动作节奏 / 交接"),
    ("direct", "04", "三段镜头导演", "摆位 / 调度 / 守门"),
    ("storyboard", "05", "分镜流程图", "可视化设计"),
    ("compile", "06", "Seedance 编译", "单段 Prompt"),
    ("inspect", "07", "质检导演", "判例 / 返修"),
]

STEP_ALIASES = {
    "scene": 0,
    "analyze": 0,
    "enhance": 1,
    "showrunner": 1,
    "rhythm": 2,
    "plan": 2,
    "planner": 2,
    "direct": 3,
    "shot": 3,
    "storyboard": 4,
    "compile": 5,
    "prompt": 5,
    "inspect": 6,
    "quality": 6,
}

AGENT_TABS = [
    ("scene_analyst", "场景预分析"),
    ("director_showrunner", "剧情增强"),
    ("story_planner", "节奏拆片导演"),
    ("shot_director", "镜头导演"),
    ("storyboard_designer", "分镜设计"),
    ("prompt_compiler", "Seedance Prompt"),
    ("quality_inspector", "质检报告"),
]

ASPECT_OPTIONS = ["9:16", "16:9", "1:1", "4:5", "3:4"]
STYLE_OPTIONS = ["都市短剧", "都市商战", "悬疑冷调", "情感现实", "古风精致", "喜剧明亮"]


@dataclass
class WorkerResult:
    kind: str
    payload: Any = None
    error: str | None = None


def _status_label(status: str) -> str:
    return {
        "idle": "就绪",
        "running": "运行中",
        "running_phase_1": "第一阶段运行中",
        "waiting_for_user_input": "等待审改",
        "running_phase_2": "第二阶段运行中",
        "completed": "已完成",
        "done": "已完成",
        "error": "异常",
    }.get(status or "", status or "就绪")


def _short_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


class DirectorStudioApp(ctk.CTk if ctk else object):
    def __init__(self) -> None:
        if CTK_IMPORT_ERROR:
            raise RuntimeError(f"CustomTkinter 加载失败: {CTK_IMPORT_ERROR}") from CTK_IMPORT_ERROR
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AI Director Studio - 本地工作台")
        self.geometry("1680x960")
        self.minsize(1280, 760)
        self.configure(fg_color=COLORS["bg"])

        self.session_id = "local"
        self.current_tab = "workspace"
        self.current_agent = "prompt_compiler"
        self.status_data: dict[str, Any] = {}
        self.progress_data: dict[str, Any] = {}
        self.projects: list[dict[str, Any]] = []
        self.model_profiles: list[dict[str, Any]] = []
        self.active_profile_payload: dict[str, Any] | None = None
        self.reference_paths: list[str] = []
        self.thumbnail_refs: list[Any] = []

        self.nav_buttons: dict[str, Any] = {}
        self.step_cards: list[Any] = []
        self.result_tab_buttons: dict[str, Any] = {}

        if CLI_ERROR:
            self._build_error(CLI_ERROR)
            return

        self._build_shell()
        self._show_tab("workspace")
        self.after(250, self.refresh_all)
        self.after(3000, self._auto_refresh)

    def _font(self, size: int, weight: str = "normal") -> Any:
        return ctk.CTkFont(family="Microsoft YaHei UI", size=size, weight=weight)

    def _run_worker(self, kind: str, func: Callable[[], Any]) -> None:
        def task() -> None:
            try:
                payload = func()
                result = WorkerResult(kind, payload)
            except Exception:
                result = WorkerResult(kind, error=traceback.format_exc())
            self.after(0, lambda: self._handle_worker_result(result))

        threading.Thread(target=task, daemon=True).start()

    def _build_error(self, detail: str) -> None:
        box = self._card(self)
        box.pack(fill="both", expand=True, padx=28, pady=28)
        self._label(box, "本地 UI 后端加载失败", 24, "bold", COLORS["red"]).pack(anchor="w", padx=20, pady=(20, 10))
        text = self._textbox(box, height=560)
        text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        text.insert("1.0", detail)

    def _build_shell(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        sidebar = ctk.CTkFrame(self, width=244, corner_radius=0, fg_color=COLORS["sidebar"])
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(24, 20))
        ctk.CTkLabel(
            brand,
            text="ADS",
            width=48,
            height=48,
            corner_radius=8,
            fg_color=COLORS["gold"],
            text_color="#111112",
            font=self._font(16, "bold"),
        ).pack(side="left", padx=(0, 12))
        title_box = ctk.CTkFrame(brand, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        self._label(title_box, "AI Director Studio", 16, "bold").pack(anchor="w")
        self._label(title_box, "Native v0.1", 11, "normal", COLORS["muted"]).pack(anchor="w", pady=(3, 0))

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=(4, 0))
        for key, icon, label in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav,
                text=f"{icon}   {label}",
                height=46,
                corner_radius=8,
                anchor="w",
                fg_color="transparent",
                hover_color=COLORS["panel_2"],
                text_color=COLORS["muted"],
                font=self._font(14, "bold"),
                command=lambda tab=key: self._show_tab(tab),
            )
            btn.pack(fill="x", pady=4)
            self.nav_buttons[key] = btn

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=20, pady=18)
        self._label(footer, "本地会话", 11, "bold", COLORS["faint"]).pack(anchor="w", pady=(0, 8))
        self.sidebar_status = self._label(footer, "● Agent 就绪", 12, "normal", COLORS["green"])
        self.sidebar_status.pack(anchor="w")

        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self.main, height=96, corner_radius=0, fg_color=COLORS["bg"])
        self.header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 4))
        self.header.grid_columnconfigure(0, weight=1)
        self.eyebrow = self._label(self.header, "Director Console", 12, "bold", COLORS["gold"])
        self.eyebrow.grid(row=0, column=0, sticky="w")
        self.page_title = self._label(self.header, "", 28, "bold")
        self.page_title.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.page_subtitle = self._label(self.header, "", 13, "normal", COLORS["muted"])
        self.page_subtitle.grid(row=2, column=0, sticky="w", pady=(5, 0))
        self._button(self.header, "刷新", self.refresh_all).grid(row=1, column=1, rowspan=2, sticky="e")

        self.body = ctk.CTkFrame(self.main, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))

    def _show_tab(self, tab: str) -> None:
        self.current_tab = tab
        labels = {
            "workspace": ("导演工作台", "剧本、参考图、流水线状态和最终 Prompt 集中在一个本地窗口里。"),
            "config": ("模型配置", "保存本地模型方案，供后台流水线调用。"),
            "knowledge": ("知识库", "查看知识库与素材库状态，触发本地刷新。"),
        }
        title, subtitle = labels[tab]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        for key, btn in self.nav_buttons.items():
            active = key == tab
            btn.configure(
                fg_color=COLORS["panel_2"] if active else "transparent",
                text_color=COLORS["gold"] if active else COLORS["muted"],
            )
        for child in self.body.winfo_children():
            child.destroy()
        getattr(self, f"_page_{tab}")()

    def _page_workspace(self) -> None:
        self.body.grid_rowconfigure(1, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        summary = ctk.CTkFrame(self.body, fg_color="transparent")
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        summary.grid_columnconfigure((0, 1, 2), weight=1)
        self.summary_status = self._summary_card(summary, "当前状态", "就绪", 0)
        self.summary_refs = self._summary_card(summary, "参考素材", "0 张", 1)
        self.summary_target = self._summary_card(summary, "输出目标", "Seedance Prompt", 2)

        grid = ctk.CTkFrame(self.body, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="nsew")
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_columnconfigure(0, weight=42)
        grid.grid_columnconfigure(1, weight=58)

        left_scroll = ctk.CTkScrollableFrame(grid, fg_color="transparent")
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right_scroll = ctk.CTkScrollableFrame(grid, fg_color="transparent")
        right_scroll.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self._build_script_card(left_scroll)
        self._build_controls_card(left_scroll)
        self._build_pipeline_card(right_scroll)
        self._build_result_card(right_scroll)
        self._paint_dynamic()

    def _build_script_card(self, parent: Any) -> None:
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 12))
        self._card_title(card, "Source", "剧本输入")
        self.script_input = self._textbox(card, height=270)
        self.script_input.pack(fill="x", padx=14, pady=(0, 14))
        script = self.status_data.get("input_script") or ""
        if script:
            self.script_input.insert("1.0", script)
        else:
            self.script_input.insert("1.0", "粘贴你的剧本片段...")

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 12))
        actions.grid_columnconfigure((0, 1, 2), weight=1)
        self.run_button = self._button(actions, "启动导演流水线", self.start_pipeline, primary=True)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._button(actions, "新建空白任务", self.create_blank_project).grid(row=0, column=1, sticky="ew", padx=8)
        self._button(actions, "恢复最近任务", self.refresh_all).grid(row=0, column=2, sticky="ew", padx=(8, 0))

    def _build_controls_card(self, parent: Any) -> None:
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 12))
        self._card_title(card, "Controls", "运行设置")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))
        row.grid_columnconfigure((0, 1), weight=1)
        self.aspect_menu = self._option(row, ASPECT_OPTIONS)
        self.aspect_menu.set(str(self.status_data.get("input_aspect_ratio") or "9:16"))
        self._field(row, "画幅", self.aspect_menu, 0, 0)
        self.style_menu = self._option(row, STYLE_OPTIONS)
        self.style_menu.set(str(self.status_data.get("style_preset") or STYLE_OPTIONS[0]))
        self._field(row, "风格", self.style_menu, 0, 1)

        self.speed_mode = ctk.BooleanVar(value=False)
        speed = ctk.CTkSwitch(
            card,
            text="快速模式",
            variable=self.speed_mode,
            progress_color=COLORS["gold"],
            button_color=COLORS["text"],
            text_color=COLORS["text"],
            font=self._font(13, "bold"),
        )
        speed.pack(anchor="w", padx=14, pady=(0, 12))

        ref_head = ctk.CTkFrame(card, fg_color="transparent")
        ref_head.pack(fill="x", padx=14, pady=(4, 8))
        self._label(ref_head, "参考图", 13, "bold").pack(side="left")
        self._button(ref_head, "添加", self.add_reference_images, small=True).pack(side="right", padx=(8, 0))
        self._button(ref_head, "清空", self.clear_reference_images, small=True).pack(side="right")

        self.ref_grid = ctk.CTkFrame(card, fg_color=COLORS["panel_3"], corner_radius=8)
        self.ref_grid.pack(fill="x", padx=14, pady=(0, 12))
        self.ref_note = self._textbox(card, height=86)
        self.ref_note.pack(fill="x", padx=14, pady=(0, 14))
        self.ref_note.insert("1.0", "可写 @图片1、@图片2 的说明，例如人物造型、空间关系、服装、道具。")
        self._paint_references()

    def _build_pipeline_card(self, parent: Any) -> None:
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 12))
        self._card_title(card, "Pipeline", "Agent 流水线")
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 12))
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.step_cards = []
        for idx, (_, number, title, desc) in enumerate(STEPS):
            step = ctk.CTkFrame(grid, fg_color=COLORS["panel_3"], border_width=1, border_color=COLORS["line"], corner_radius=8)
            step.grid(row=idx // 4, column=idx % 4, sticky="nsew", padx=4, pady=4)
            ctk.CTkLabel(step, text=number, width=34, height=26, corner_radius=6, fg_color=COLORS["panel_2"], text_color=COLORS["muted"], font=self._font(11, "bold")).pack(pady=(10, 6))
            self._label(step, title, 12, "bold").pack()
            self._label(step, desc, 10, "normal", COLORS["muted"]).pack(pady=(3, 8))
            badge = ctk.CTkLabel(step, text="等待", height=20, corner_radius=10, fg_color=COLORS["panel_2"], text_color=COLORS["faint"], font=self._font(10))
            badge.pack(pady=(0, 10))
            step.status_badge = badge
            self.step_cards.append(step)
        self.pipeline_msg = self._label(card, "", 12, "normal", COLORS["cyan"])
        self.pipeline_msg.pack(fill="x", padx=14, pady=(0, 14))

    def _build_result_card(self, parent: Any) -> None:
        card = self._card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 10))
        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        self._label(left, "Output", 11, "bold", COLORS["gold"]).pack(anchor="w")
        self._label(left, "执行结果", 16, "bold").pack(anchor="w", pady=(2, 0))
        self._button(head, "复制当前", self.copy_current_output, small=True).pack(side="right")

        shell = ctk.CTkFrame(card, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        rail = ctk.CTkScrollableFrame(shell, width=220, fg_color=COLORS["panel_3"], corner_radius=8)
        rail.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        self.result_tab_buttons = {}
        for key, label in AGENT_TABS:
            btn = ctk.CTkButton(
                rail,
                text=label,
                height=42,
                corner_radius=7,
                anchor="w",
                fg_color="transparent",
                hover_color=COLORS["panel_2"],
                text_color=COLORS["muted"],
                font=self._font(12, "bold"),
                command=lambda agent=key: self.select_result_agent(agent),
            )
            btn.pack(fill="x", padx=6, pady=4)
            self.result_tab_buttons[key] = btn

        panel = ctk.CTkFrame(shell, fg_color=COLORS["panel_3"], corner_radius=8)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        self.result_title = self._label(panel, "", 16, "bold")
        self.result_title.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self.result_output = self._textbox(panel, height=420)
        self.result_output.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.select_result_agent(self.current_agent)

    def _page_config(self) -> None:
        wrap = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        card = self._card(wrap)
        card.pack(fill="x", pady=(0, 12))
        self._card_title(card, "Model Profiles", "模型服务方案")
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=14, pady=(0, 14))
        form.grid_columnconfigure((0, 1), weight=1)

        self.profile_menu = self._option(form, ["新建方案"])
        self.profile_menu.configure(command=self._select_profile)
        self._field(form, "已有方案", self.profile_menu, 0, 0)

        self.profile_name = self._entry(form)
        self._field(form, "方案名称", self.profile_name, 0, 1)
        self.base_url = self._entry(form)
        self._field(form, "Base URL", self.base_url, 1, 0)
        self.api_key = self._entry(form, secret=True)
        self._field(form, "API Key", self.api_key, 1, 1)
        self.default_model = self._entry(form)
        self._field(form, "默认模型", self.default_model, 2, 0)
        self.embedding_model = self._entry(form)
        self._field(form, "Embedding 模型", self.embedding_model, 2, 1)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        self._button(actions, "保存模型方案", self.save_model_profile, primary=True).pack(side="left", padx=(0, 8))
        self._button(actions, "测试连接", self.test_model_profile).pack(side="left")
        self.config_status = self._label(actions, "", 12, "normal", COLORS["muted"])
        self.config_status.pack(side="left", padx=14)

        self.agent_hint = self._label(
            card,
            "提示：如果 API Key 留空，保存同名方案时会保留原密钥；新方案需要填写密钥。",
            12,
            "normal",
            COLORS["muted"],
        )
        self.agent_hint.pack(anchor="w", padx=14, pady=(0, 14))
        self._paint_profiles()

    def _page_knowledge(self) -> None:
        wrap = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        card = self._card(wrap)
        card.pack(fill="x", pady=(0, 12))
        self._card_title(card, "Knowledge", "本地知识库与素材索引")
        self.knowledge_text = self._textbox(card, height=260)
        self.knowledge_text.pack(fill="x", padx=14, pady=(0, 14))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        self._button(actions, "刷新状态", self.refresh_all, primary=True).pack(side="left", padx=(0, 8))
        self._button(actions, "打开输出目录", self.open_output_dir).pack(side="left")
        self._paint_knowledge()

    def _summary_card(self, parent: Any, label: str, value: str, column: int) -> Any:
        card = self._card(parent)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 7, 0 if column == 2 else 7))
        self._label(card, label, 12, "normal", COLORS["muted"]).pack(anchor="w", padx=14, pady=(13, 2))
        value_label = self._label(card, value, 18, "bold")
        value_label.pack(anchor="w", padx=14, pady=(0, 13))
        return value_label

    def _card(self, parent: Any) -> Any:
        return ctk.CTkFrame(parent, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line_soft"], corner_radius=8)

    def _mini_panel(self, parent: Any, title: str, subtitle: str) -> Any:
        panel = ctk.CTkFrame(parent, fg_color=COLORS["panel_3"], border_width=1, border_color=COLORS["line"], corner_radius=8)
        self._label(panel, title, 13, "bold").pack(anchor="w", padx=12, pady=(12, 2))
        self._label(panel, subtitle, 11, "normal", COLORS["muted"]).pack(anchor="w", padx=12, pady=(0, 12))
        return panel

    def _card_title(self, parent: Any, kicker: str, title: str) -> None:
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 10))
        self._label(head, kicker, 11, "bold", COLORS["gold"]).pack(anchor="w")
        self._label(head, title, 16, "bold").pack(anchor="w", pady=(2, 0))

    def _label(self, parent: Any, text: str, size: int, weight: str = "normal", color: str | None = None) -> Any:
        return ctk.CTkLabel(parent, text=text, text_color=color or COLORS["text"], font=self._font(size, weight), justify="left")

    def _button(self, parent: Any, text: str, command: Callable[[], Any], primary: bool = False, small: bool = False) -> Any:
        return ctk.CTkButton(
            parent,
            text=text,
            height=32 if small else 40,
            corner_radius=8,
            fg_color=COLORS["gold"] if primary else COLORS["panel_2"],
            hover_color=COLORS["gold_hover"] if primary else COLORS["panel_3"],
            text_color="#111112" if primary else COLORS["text"],
            border_width=0 if primary else 1,
            border_color=COLORS["line"],
            font=self._font(12 if small else 13, "bold"),
            command=command,
        )

    def _entry(self, parent: Any, secret: bool = False) -> Any:
        return ctk.CTkEntry(
            parent,
            height=40,
            corner_radius=8,
            fg_color=COLORS["input"],
            border_color=COLORS["line"],
            text_color=COLORS["text"],
            show="*" if secret else "",
            font=self._font(12),
        )

    def _textbox(self, parent: Any, height: int = 160) -> Any:
        return ctk.CTkTextbox(
            parent,
            height=height,
            corner_radius=8,
            fg_color=COLORS["input"],
            border_width=1,
            border_color=COLORS["line"],
            text_color=COLORS["text"],
            font=self._font(13),
            wrap="word",
        )

    def _option(self, parent: Any, values: list[str]) -> Any:
        return ctk.CTkOptionMenu(
            parent,
            values=values or ["暂无选项"],
            height=40,
            corner_radius=8,
            fg_color=COLORS["input"],
            button_color=COLORS["panel_2"],
            button_hover_color=COLORS["panel_3"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["panel"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["panel_2"],
            font=self._font(12),
        )

    def _field(self, parent: Any, label: str, widget: Any, row: int, col: int) -> None:
        padx = (0 if col == 0 else 8, 8 if col == 0 else 0)
        self._label(parent, label, 12, "bold", COLORS["muted"]).grid(
            row=row * 2,
            column=col,
            sticky="w",
            padx=padx,
            pady=(0, 6),
        )
        widget.grid(
            row=row * 2 + 1,
            column=col,
            sticky="ew",
            padx=padx,
            pady=(0, 12),
        )

    def refresh_all(self) -> None:
        if cli is None:
            return
        self._run_worker("refresh", self._fetch_state)

    def _fetch_state(self) -> dict[str, Any]:
        status = cli.cmd_status(self.session_id)
        progress = cli.cmd_pipeline_progress(self.session_id)
        projects = cli.cmd_projects_recent(False)
        profiles = cli.cmd_model_profiles()
        assets = cli.cmd_assets_library()
        return {
            "status": status if isinstance(status, dict) else {},
            "progress": progress if isinstance(progress, dict) else {},
            "projects": projects if isinstance(projects, list) else [],
            "profiles": profiles if isinstance(profiles, list) else [],
            "assets": assets if isinstance(assets, dict) else {},
        }

    def _auto_refresh(self) -> None:
        try:
            self.refresh_all()
        finally:
            self.after(3000, self._auto_refresh)

    def _handle_worker_result(self, result: WorkerResult) -> None:
        if result.error:
            self._toast("操作失败")
            messagebox.showerror("操作失败", result.error)
            return
        if result.kind == "refresh":
            payload = result.payload or {}
            self.status_data = payload.get("status") or {}
            self.progress_data = payload.get("progress") or {}
            self.projects = payload.get("projects") or []
            self.model_profiles = payload.get("profiles") or []
            self.assets_data = payload.get("assets") or {}
            self._paint_dynamic()
            if self.current_tab == "config":
                self._paint_profiles()
            if self.current_tab == "knowledge":
                self._paint_knowledge()
        elif result.kind == "start_pipeline":
            self._toast("导演流水线已提交")
            self.refresh_all()
        elif result.kind == "new_project":
            project = (result.payload or {}).get("project", {})
            self.session_id = str(project.get("session_id") or self.session_id)
            self._toast("新任务已创建")
            self.refresh_all()
        elif result.kind == "save_profile":
            self._toast("模型方案已保存")
            if self.current_tab == "config" and hasattr(self, "config_status"):
                self.config_status.configure(text="已保存", text_color=COLORS["green"])
            self.refresh_all()
        elif result.kind == "test_profile":
            ok = bool((result.payload or {}).get("success"))
            text = "连接成功" if ok else f"连接失败: {(result.payload or {}).get('error') or '请检查配置'}"
            if hasattr(self, "config_status"):
                self.config_status.configure(text=text, text_color=COLORS["green"] if ok else COLORS["red"])

    def _paint_dynamic(self) -> None:
        state = self.progress_data or self.status_data or {}
        status = str(state.get("status") or self.status_data.get("status") or "idle")
        label = _status_label(status)
        color = COLORS["red"] if status == "error" else COLORS["gold"] if status.startswith("running") else COLORS["green"]
        if hasattr(self, "sidebar_status"):
            self.sidebar_status.configure(text=f"● Agent {label}", text_color=color)
        if hasattr(self, "summary_status"):
            self.summary_status.configure(text=label)
        if hasattr(self, "summary_refs"):
            count = len(self.reference_paths) or len(self.status_data.get("input_ref_manifest") or [])
            self.summary_refs.configure(text=f"{count} 张")
        if hasattr(self, "pipeline_msg"):
            self.pipeline_msg.configure(text=_short_text(state.get("message"), "等待启动流水线。"))
        self._paint_steps(status, str(state.get("step") or ""))
        self._paint_result_output()

    def _paint_steps(self, status: str, step_name: str) -> None:
        active_index = self._active_step_index(status, step_name)
        done_until = -1
        if status in {"completed", "done"}:
            done_until = len(STEPS) - 1
        elif status.startswith("running") or status == "waiting_for_user_input":
            done_until = max(-1, active_index - 1)

        for index, frame in enumerate(getattr(self, "step_cards", [])):
            if index <= done_until:
                border = COLORS["green"]
                badge_text = "完成"
                badge_color = COLORS["green"]
            elif index == active_index and status.startswith("running"):
                border = COLORS["gold"]
                badge_text = "运行中"
                badge_color = COLORS["gold"]
            elif status == "error" and index == active_index:
                border = COLORS["red"]
                badge_text = "异常"
                badge_color = COLORS["red"]
            else:
                border = COLORS["line"]
                badge_text = "等待"
                badge_color = COLORS["faint"]
            frame.configure(border_color=border)
            frame.status_badge.configure(text=badge_text, text_color=badge_color)

    def _active_step_index(self, status: str, step_name: str) -> int:
        lower = f"{status} {step_name}".lower()
        for key, idx in STEP_ALIASES.items():
            if key in lower:
                return idx
        if status == "running_phase_2":
            return 6
        if status == "waiting_for_user_input":
            return 4
        return 0

    def select_result_agent(self, agent: str) -> None:
        self.current_agent = agent
        for key, btn in getattr(self, "result_tab_buttons", {}).items():
            active = key == agent
            btn.configure(fg_color=COLORS["panel_2"] if active else "transparent", text_color=COLORS["gold"] if active else COLORS["muted"])
        if hasattr(self, "result_title"):
            self.result_title.configure(text=next((label for key, label in AGENT_TABS if key == agent), agent))
        self._paint_result_output()

    def _paint_result_output(self) -> None:
        if not hasattr(self, "result_output"):
            return
        outputs = self.status_data.get("agent_outputs") or self.progress_data.get("agent_outputs") or {}
        text = ""
        if isinstance(outputs, dict):
            value = outputs.get(self.current_agent)
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) if value else ""
            if self.current_agent == "prompt_compiler" and not text:
                compiled = [
                    str(v)
                    for k, v in sorted(outputs.items())
                    if str(k).startswith("compiled_segment_") and v
                ]
                text = "\n\n".join(compiled)
        if not text:
            text = "暂无输出。启动流水线后，这里会按 Agent 展示结果。"
        self.result_output.delete("1.0", "end")
        self.result_output.insert("1.0", text)

    def _paint_references(self) -> None:
        if not hasattr(self, "ref_grid"):
            return
        for child in self.ref_grid.winfo_children():
            child.destroy()
        self.thumbnail_refs = []
        if not self.reference_paths:
            self._label(self.ref_grid, "还没有参考图。可分批添加，后添加的不会覆盖前面。", 12, "normal", COLORS["muted"]).pack(padx=12, pady=16)
            return
        for idx, path in enumerate(self.reference_paths[:12]):
            item = ctk.CTkFrame(self.ref_grid, fg_color="transparent")
            item.grid(row=idx // 3, column=idx % 3, sticky="ew", padx=8, pady=8)
            preview = self._thumbnail(path, (96, 72))
            ctk.CTkLabel(item, text=f"图片{idx + 1}" if preview is None else "", image=preview, width=96, height=72, fg_color=COLORS["input"], corner_radius=7).pack(side="left")
            if preview is not None:
                self.thumbnail_refs.append(preview)
            name = os.path.basename(path)
            self._label(item, name[:20], 11, "normal", COLORS["muted"]).pack(side="left", padx=8)
        for col in range(3):
            self.ref_grid.grid_columnconfigure(col, weight=1)

    def _thumbnail(self, path: str, size: tuple[int, int]) -> Any:
        if Image is None or ImageOps is None:
            return None
        try:
            image = Image.open(path)
            image = ImageOps.exif_transpose(image)
            image.thumbnail(size)
            return ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        except Exception:
            return None

    def add_reference_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择参考图",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")],
        )
        for path in paths:
            if path and path not in self.reference_paths:
                self.reference_paths.append(path)
        self.reference_paths = self.reference_paths[:12]
        self._paint_references()
        self._paint_dynamic()

    def clear_reference_images(self) -> None:
        self.reference_paths = []
        self._paint_references()
        self._paint_dynamic()

    def start_pipeline(self) -> None:
        if cli is None:
            return
        script = self.script_input.get("1.0", "end").strip() if hasattr(self, "script_input") else ""
        if script == "粘贴你的剧本片段...":
            script = ""
        if not script:
            messagebox.showwarning("缺少剧本", "请先粘贴剧本片段。")
            return
        payload = {
            "script": script,
            "aspect_ratio": self.aspect_menu.get() if hasattr(self, "aspect_menu") else "9:16",
            "style_preset": self.style_menu.get() if hasattr(self, "style_menu") else "",
            "reference_image_b64s": self._reference_b64s(),
            "reference_image_manifest": self._reference_manifest(),
            "model_profile_snapshot": self.active_profile_payload or {},
            "speed_mode": bool(self.speed_mode.get()) if hasattr(self, "speed_mode") else False,
        }
        self._run_worker("start_pipeline", lambda: cli.cmd_run_pipeline(session_id=self.session_id, **payload))

    def _reference_b64s(self) -> list[str]:
        encoded: list[str] = []
        for path in self.reference_paths[:12]:
            try:
                with open(path, "rb") as file:
                    encoded.append(base64.b64encode(file.read()).decode("ascii"))
            except OSError:
                continue
        return encoded

    def _reference_manifest(self) -> list[dict[str, Any]]:
        notes = self.ref_note.get("1.0", "end").strip() if hasattr(self, "ref_note") else ""
        return [
            {
                "index": idx + 1,
                "name": os.path.basename(path),
                "path": path,
                "role": "reference",
                "description": notes,
            }
            for idx, path in enumerate(self.reference_paths[:12])
        ]

    def create_blank_project(self) -> None:
        if cli is None:
            return
        self._run_worker("new_project", lambda: {"project": cli.cmd_projects_new("本地导演任务")})

    def _paint_profiles(self) -> None:
        if not hasattr(self, "profile_menu"):
            return
        labels = ["新建方案"] + [str(p.get("name") or p.get("id") or "未命名方案") for p in self.model_profiles]
        self.profile_menu.configure(values=labels)
        current = self.profile_menu.get()
        if current not in labels:
            self.profile_menu.set(labels[0])

    def _select_profile(self, label: str) -> None:
        profile = next((p for p in self.model_profiles if str(p.get("name") or p.get("id")) == label), None)
        for widget, value in [
            (getattr(self, "profile_name", None), profile.get("name") if profile else ""),
            (getattr(self, "base_url", None), profile.get("base_url") if profile else ""),
            (getattr(self, "api_key", None), "" if profile else ""),
            (getattr(self, "default_model", None), profile.get("default_model") if profile else ""),
            (getattr(self, "embedding_model", None), profile.get("embedding_model") if profile else ""),
        ]:
            if widget is None:
                continue
            widget.delete(0, "end")
            widget.insert(0, str(value or ""))

    def _profile_payload_from_form(self) -> dict[str, Any]:
        label = self.profile_menu.get() if hasattr(self, "profile_menu") else ""
        existing = next((p for p in self.model_profiles if str(p.get("name") or p.get("id")) == label), None) or {}
        return {
            "id": existing.get("id") or "",
            "name": self.profile_name.get().strip() or label or "Local Model Profile",
            "base_url": self.base_url.get().strip(),
            "api_key": self.api_key.get().strip(),
            "default_model": self.default_model.get().strip(),
            "embedding_model": self.embedding_model.get().strip(),
        }

    def save_model_profile(self) -> None:
        if cli is None:
            return
        payload = self._profile_payload_from_form()
        if not payload.get("base_url"):
            messagebox.showwarning("缺少 Base URL", "请填写模型服务 Base URL。")
            return
        self.active_profile_payload = dict(payload)
        self._run_worker("save_profile", lambda: cli.cmd_save_model_profile(payload))

    def test_model_profile(self) -> None:
        if cli is None:
            return
        payload = self._profile_payload_from_form()
        self._run_worker("test_profile", lambda: cli.cmd_test_model_profile(payload))

    def _paint_knowledge(self) -> None:
        if not hasattr(self, "knowledge_text"):
            return
        assets = getattr(self, "assets_data", {}) or {}
        groups = assets.get("groups") if isinstance(assets, dict) else {}
        lines = [
            f"当前会话: {self.session_id}",
            f"项目数: {len(self.projects)}",
            "",
            "素材库:",
        ]
        if isinstance(groups, dict):
            for key in ["character", "scene", "prop", "frame", "upload"]:
                lines.append(f"- {key}: {len(groups.get(key) or [])}")
        else:
            lines.append("- 暂无素材索引")
        lines.extend([
            "",
            f"输出目录: {OUTPUT_DIR}",
            "",
            "知识库重建仍沿用 Web UI / 后端命令；本地窗口先提供状态查看和输出目录入口。",
        ])
        self.knowledge_text.delete("1.0", "end")
        self.knowledge_text.insert("1.0", "\n".join(lines))

    def open_output_dir(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(OUTPUT_DIR))

    def copy_current_output(self) -> None:
        if not hasattr(self, "result_output"):
            return
        text = self.result_output.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self._toast("已复制当前输出")

    def _toast(self, text: str) -> None:
        if hasattr(self, "sidebar_status"):
            self.sidebar_status.configure(text=text, text_color=COLORS["cyan"])


def main() -> None:
    app = DirectorStudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
