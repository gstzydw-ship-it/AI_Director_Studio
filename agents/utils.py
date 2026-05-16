import os
import re
import sys
import shutil
from typing import Any

import yaml

COMFLY_BASE_URL = "https://ai.comfly.chat/v1"
_UNRESOLVED_ENV_REF_RE = re.compile(r"^(?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|%[A-Za-z_][A-Za-z0-9_]*%)$")


def _drop_unresolved_env_refs(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_unresolved_env_refs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_drop_unresolved_env_refs(item) for item in value]
    if isinstance(value, str) and _UNRESOLVED_ENV_REF_RE.fullmatch(value.strip()):
        return ""
    return value


def load_yaml_config(path: str) -> dict[str, Any]:
    """Load YAML config with environment-variable expansion.

    Unset placeholders such as ${DIRECTOR_LLM_API_KEY} are normalized to an
    empty string so they do not behave like literal API keys.
    """
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        expanded = os.path.expandvars(f.read())
    data = yaml.safe_load(expanded) or {}
    data = _drop_unresolved_env_refs(data)
    return data if isinstance(data, dict) else {}


def get_base_dir():
    """Get absolute path to bundled resources. Works for dev and PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return sys._MEIPASS
    except Exception:
        # Normal execution: return project root (parent of agents/)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _settings_path_for_knowledge_dir() -> str:
    """Return settings.yaml path without calling get_config_path()."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        external_config = os.path.join(exe_dir, "config", "settings.yaml")
        if os.path.exists(external_config):
            return external_config
        return os.path.join(get_base_dir(), "config", "settings.yaml")
    return os.path.join(get_base_dir(), "config", "settings.yaml")


def _configured_knowledge_directory(settings_path: str) -> str:
    if not settings_path or not os.path.exists(settings_path):
        return ""
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            expanded = os.path.expandvars(f.read())
        data = yaml.safe_load(expanded) or {}
    except (OSError, yaml.YAMLError):
        return ""
    data = _drop_unresolved_env_refs(data)
    if not isinstance(data, dict):
        return ""
    knowledge = data.get("knowledge") or {}
    if not isinstance(knowledge, dict):
        return ""
    directory = knowledge.get("directory")
    return str(directory).strip() if directory else ""


def _project_root_for_settings(settings_path: str) -> str:
    if not getattr(sys, "frozen", False):
        return get_base_dir()
    exe_dir = os.path.dirname(sys.executable)
    external_config_dir = os.path.normcase(os.path.abspath(os.path.join(exe_dir, "config")))
    settings_dir = os.path.normcase(os.path.abspath(os.path.dirname(settings_path)))
    return exe_dir if settings_dir == external_config_dir else get_base_dir()


def get_knowledge_dir():
    """Return the configured knowledge directory.

    Relative paths are resolved from the project root. In PyInstaller builds,
    an external config next to the executable resolves from the executable
    directory, with a bundled fallback for the default ./knowledge path.
    """
    settings_path = _settings_path_for_knowledge_dir()
    configured_dir = _configured_knowledge_directory(settings_path)
    if configured_dir:
        if os.path.isabs(configured_dir):
            return os.path.normpath(configured_dir)

        root = _project_root_for_settings(settings_path)
        candidate = os.path.normpath(os.path.join(root, configured_dir))
        if getattr(sys, "frozen", False) and not os.path.exists(candidate):
            bundled_candidate = os.path.normpath(os.path.join(get_base_dir(), configured_dir))
            if os.path.exists(bundled_candidate):
                return bundled_candidate
        return candidate

    return os.path.join(get_base_dir(), "knowledge")


def get_config_path():
    """
    Returns the active settings path.
    If frozen (PyInstaller .exe), keeps settings.yaml NEXT to the executable so it persists.
    Copies default from bundled data if it doesn't exist.
    The web UI is the single source of truth for runtime model configuration,
    so the active path is always config/settings.yaml.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        config_dir = os.path.join(exe_dir, "config")
        config_file = os.path.join(config_dir, "settings.yaml")
        
        if not os.path.exists(config_file):
            meipass_config = os.path.join(sys._MEIPASS, "config", "settings.yaml")
            if os.path.exists(meipass_config):
                os.makedirs(config_dir, exist_ok=True)
                shutil.copy2(meipass_config, config_file)
        return config_file
    else:
        config_dir = os.path.join(get_base_dir(), "config")
        return os.path.join(config_dir, "settings.yaml")

def get_public_config_path():
    """Return the shareable config/settings.yaml path."""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "config", "settings.yaml")
    return os.path.join(get_base_dir(), "config", "settings.yaml")

def get_cache_dir():
    """
    Returns the cache directory (.bm25_cache) path.
    If frozen, create it next to the executable so we don't rebuild every time we launch the exe.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, ".bm25_cache")
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bm25_cache")

def get_output_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        out_dir = os.path.join(exe_dir, "output")
    else:
        out_dir = os.path.join(get_base_dir(), "output")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir
