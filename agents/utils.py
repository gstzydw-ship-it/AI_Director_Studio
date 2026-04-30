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

def get_knowledge_dir():
    """Return the path to the knowledge/ directory (bundled)."""
    return os.path.join(get_base_dir(), "knowledge")

def get_config_path():
    """
    Returns the active settings path.
    If frozen (PyInstaller .exe), keeps settings.yaml NEXT to the executable so it persists.
    Copies default from bundled data if it doesn't exist.
    A private settings.local.yaml takes precedence when present so local owners
    can keep API credentials out of the shareable settings.yaml.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        config_dir = os.path.join(exe_dir, "config")
        config_file = os.path.join(config_dir, "settings.yaml")
        private_config_file = os.path.join(config_dir, "private", "settings.local.yaml")
        
        if not os.path.exists(config_file):
            meipass_config = os.path.join(sys._MEIPASS, "config", "settings.yaml")
            if os.path.exists(meipass_config):
                os.makedirs(config_dir, exist_ok=True)
                shutil.copy2(meipass_config, config_file)
        if os.path.exists(private_config_file):
            return private_config_file
        return config_file
    else:
        config_dir = os.path.join(get_base_dir(), "config")
        private_config_file = os.path.join(config_dir, "private", "settings.local.yaml")
        if os.path.exists(private_config_file):
            return private_config_file
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
