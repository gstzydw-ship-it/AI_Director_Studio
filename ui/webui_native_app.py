from __future__ import annotations

import socket
import threading
import time
import webbrowser
from dataclasses import dataclass
from typing import Any

import uvicorn

try:
    import customtkinter as ctk
except Exception as exc:  # pragma: no cover - shown only in fallback UI
    ctk = None
    CTK_IMPORT_ERROR = exc
else:
    CTK_IMPORT_ERROR = None

try:
    import webview
except Exception as exc:  # pragma: no cover - optional desktop shell
    webview = None
    WEBVIEW_IMPORT_ERROR = exc
else:
    WEBVIEW_IMPORT_ERROR = None

from agents.knowledge_base import load_config
from ui.app import app as fastapi_app


UI_MODE = "python-hosted-full-webui"
CLI_ERROR = None
cli = None


@dataclass
class WebUIServer:
    host: str
    port: int
    server: uvicorn.Server
    thread: threading.Thread

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def stop(self) -> None:
        self.server.should_exit = True
        if self.thread.is_alive():
            self.thread.join(timeout=3)


def _configured_host_port() -> tuple[str, int]:
    config = load_config()
    ui_config = config.get("ui", {}) if isinstance(config, dict) else {}
    host = str(ui_config.get("host") or "127.0.0.1")
    port = int(ui_config.get("port") or 8686)
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    return host, port


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) != 0


def _find_available_port(host: str, preferred_port: int) -> int:
    for port in [preferred_port, *range(preferred_port + 1, preferred_port + 50)]:
        if _is_port_available(host, port):
            return port
    raise RuntimeError(f"No available local port near {preferred_port}")


def _wait_until_ready(host: str, port: int, timeout: float = 12.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.12)
    raise RuntimeError(f"WebUI server did not start on {host}:{port}") from last_error


def start_webui_server() -> WebUIServer:
    host, configured_port = _configured_host_port()
    port = _find_available_port(host, configured_port)
    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="ads-webui-server", daemon=True)
    thread.start()
    _wait_until_ready(host, port)
    return WebUIServer(host=host, port=port, server=server, thread=thread)


class DirectorStudioApp:
    """Compatibility wrapper that launches the complete Web UI as the Python UI."""

    def __init__(self) -> None:
        self.server: WebUIServer | None = None

    def mainloop(self) -> None:
        self.server = start_webui_server()
        try:
            _open_full_webui(self.server)
        finally:
            self.server.stop()


def _open_full_webui(server: WebUIServer) -> None:
    title = "AI Director Studio - Python WebUI"
    if webview is not None:
        webview.create_window(title, server.url, width=1680, height=960, min_size=(1280, 760))
        webview.start()
        return
    _open_browser_fallback(server, title)


def _open_browser_fallback(server: WebUIServer, title: str) -> None:
    webbrowser.open(server.url)
    if ctk is None:
        print(f"{title}: {server.url}")
        print("Press Ctrl+C to stop the local WebUI server.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title(title)
    root.geometry("560x220")
    root.resizable(False, False)

    label = ctk.CTkLabel(
        root,
        text="完整 WebUI 已在浏览器打开。\n安装 pywebview 后会直接嵌入到 Python 桌面窗口。",
        font=ctk.CTkFont(family="Microsoft YaHei UI", size=15),
        justify="left",
    )
    label.pack(anchor="w", padx=24, pady=(24, 12))

    url_box = ctk.CTkEntry(root, width=500)
    url_box.pack(fill="x", padx=24)
    url_box.insert(0, server.url)

    buttons = ctk.CTkFrame(root, fg_color="transparent")
    buttons.pack(fill="x", padx=24, pady=20)
    ctk.CTkButton(buttons, text="打开 WebUI", command=lambda: webbrowser.open(server.url)).pack(side="left")
    ctk.CTkButton(buttons, text="关闭", fg_color="#374151", command=root.destroy).pack(side="right")
    root.mainloop()


def main() -> None:
    DirectorStudioApp().mainloop()


if __name__ == "__main__":
    main()
