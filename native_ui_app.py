"""Compatibility entrypoint for the Python UI.

The Python UI now hosts the full FastAPI/Web frontend so the desktop entrypoint
and browser UI share the same screens, actions, and backend API surface.
"""

from ui.webui_native_app import (
    CLI_ERROR,
    UI_MODE,
    DirectorStudioApp,
    cli,
    ctk,
    main,
)


if __name__ == "__main__":
    main()
