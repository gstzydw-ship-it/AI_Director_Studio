from __future__ import annotations

from pathlib import Path

from agents.director_graph_package import nodes
from agents.director_graph_package import prompt_compiler_impl
from agents.director_graph_package import state_store


def test_prompt_compiler_uses_package_state_store_helpers() -> None:
    assert prompt_compiler_impl._agent_outputs is state_store._agent_outputs
    assert prompt_compiler_impl._persist_update is state_store._persist_update


def test_prompt_compiler_has_no_director_graph_reverse_import() -> None:
    source = Path(prompt_compiler_impl.__file__).read_text(encoding="utf-8")
    assert "agents.director_graph" not in source


def test_nodes_prompt_compiler_node_delegates_to_package_impl(monkeypatch) -> None:
    sentinel_state = {"step": "compile"}
    sentinel_result = {"step": "inspect"}

    def fake_prompt_compiler_node(state):
        assert state is sentinel_state
        return sentinel_result

    monkeypatch.setattr(
        nodes._prompt_compiler_impl,
        "prompt_compiler_node",
        fake_prompt_compiler_node,
    )

    assert nodes.prompt_compiler_node(sentinel_state) is sentinel_result
