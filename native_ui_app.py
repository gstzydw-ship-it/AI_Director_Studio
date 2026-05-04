"""兼容入口：保留旧文件名，但启动原来的 Web UI。"""

from ui.app import start_ui


def main():
    """Start the legacy FastAPI Web UI."""
    start_ui()


if __name__ == "__main__":
    main()
