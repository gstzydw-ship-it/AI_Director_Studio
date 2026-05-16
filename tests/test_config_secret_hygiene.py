from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.utils import load_yaml_config


def test_shareable_config_files_do_not_contain_literal_api_keys():
    shareable_paths = [
        ROOT / "config" / "settings.yaml",
        ROOT / "fix.py",
        ROOT / "test_connectivity.py",
    ]

    for path in shareable_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "sk-" not in text


def test_load_yaml_config_expands_and_cleans_env_placeholders(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "llm:\n"
        "  api_key: ${DIRECTOR_LLM_API_KEY}\n"
        "  model: gpt-5.4\n"
        "vectordb:\n"
        "  api_key: ${DIRECTOR_EMBEDDING_API_KEY}\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("DIRECTOR_LLM_API_KEY", raising=False)
    monkeypatch.setenv("DIRECTOR_EMBEDDING_API_KEY", "embedding-key")

    config = load_yaml_config(str(config_path))

    assert config["llm"]["api_key"] == ""
    assert config["llm"]["model"] == "gpt-5.4"
    assert config["vectordb"]["api_key"] == "embedding-key"
