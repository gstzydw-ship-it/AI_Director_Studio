from __future__ import annotations

from pathlib import Path

from agents.director_graph_package import nodes
from agents.director_graph_package import helpers
from agents.director_graph_package import legacy_impl
from agents.director_graph_package import prompt_compiler_impl
from agents.director_graph_package import state_store


def test_prompt_compiler_uses_package_state_store_helpers() -> None:
    assert prompt_compiler_impl._agent_outputs is state_store._agent_outputs
    assert prompt_compiler_impl._persist_update is state_store._persist_update


def test_prompt_compiler_has_no_director_graph_reverse_import() -> None:
    source = Path(prompt_compiler_impl.__file__).read_text(encoding="utf-8")
    assert "agents.director_graph" not in source


def test_prompt_compiler_owns_segment_block_extraction() -> None:
    assert prompt_compiler_impl._segment_block is not legacy_impl._segment_block

    text = (
        "fragment_id: F01\n"
        "fragment_task: first\n"
        "shots:\n"
        "  - shot_id: S01\n"
        "fragment_id: F02\n"
        "fragment_task: second\n"
    )

    block = prompt_compiler_impl._segment_block(text, 1)

    assert "fragment_id: F01" in block
    assert "fragment_task: first" in block
    assert "fragment_id: F02" not in block


def test_segment_block_can_use_actual_fragment_id() -> None:
    text = (
        "fragment_id: F05\n"
        "fragment_task: selected\n"
        "shots:\n"
        "  - shot_id: F05-S01\n"
        "fragment_id: F06\n"
        "fragment_task: next\n"
    )

    assert helpers._fragment_id_for_segment_index(["F05"], 1) == "F05"
    assert helpers._fragment_id_for_segment_index(["Test"], 1) == "F01"
    block = prompt_compiler_impl._segment_block(text, 1, "F05")

    assert "fragment_id: F05" in block
    assert "fragment_task: selected" in block
    assert "fragment_id: F06" not in block


def test_segment_block_accepts_chinese_shot_director_fields() -> None:
    text = (
        "- 片段编号: F01\n"
        "  片段任务: 第一段\n"
        "  镜头列表:\n"
        "    - 镜头编号: F01-S01\n"
        "- 片段编号: F02\n"
        "  片段任务: 第二段\n"
    )

    block = prompt_compiler_impl._segment_block(text, 1, "F01")

    assert "片段编号: F01" in block
    assert "片段任务: 第一段" in block
    assert "片段编号: F02" not in block


def test_prompt_compiler_uses_segment_names_for_non_f01_fragment(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_build_system_prompt(base_system, _agent_name, context_hint="", **_kwargs):
        captured["context_hint"] = context_hint
        return base_system, {"retrieval_mode": "stub"}

    def fake_call_llm_with_mcp(_system_prompt, user_prompt, **_kwargs):
        captured["user_prompt"] = user_prompt
        return "片段 1｜测试 Prompt\n\n【镜头序列】\n镜头1【3秒】【商北琛】中景，正面固定机位，说出台词。\n\n【约束】\n保持办公室空间。"

    monkeypatch.setattr(prompt_compiler_impl, "build_system_prompt", fake_build_system_prompt)
    monkeypatch.setattr(prompt_compiler_impl, "call_llm_with_mcp", fake_call_llm_with_mcp)

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "segment_names": ["F05"],
        "script": "商北琛：你没有资格。\n严飞：这不是你说了算的。",
        "aspect_ratio": "16:9",
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F05\n"
                "  source_script_events:\n"
                "    - \"商北琛：你没有资格。\"\n"
                "    - \"严飞：这不是你说了算的。\"\n"
            ),
            "shot_director": (
                "- fragment_id: F05\n"
                "  fragment_task: 对峙升级\n"
                "  rhythm: 台词压迫后给听者反应\n"
                "  shots:\n"
                "    - shot_id: F05-S01\n"
                "      duration: 0-3秒\n"
                "      task: 承载对白\n"
                "      subject: 商北琛\n"
                "      shot: 正面中景固定机位\n"
                "      action: 商北琛站在桌边看向严飞\n"
                "      dialogue: \"你没有资格。\"\n"
                "      must_carry: 商北琛施压\n"
                "      cut_point: 台词说完切至严飞反应\n"
                "      continuity: 保持桌边对峙轴线\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)

    assert "compiled_segment_1" in result["agent_outputs"]
    assert "fragment_id: F05" in captured["user_prompt"]
    assert "F05-S01" in captured["user_prompt"]
    assert "fragment_id: F01" not in captured["user_prompt"]


def test_prompt_compiler_uses_local_fallback_after_llm_failure(monkeypatch) -> None:
    def fail_call_llm_with_mcp(*_args, **_kwargs):
        raise RuntimeError("LLM gateway failed")

    monkeypatch.setattr(prompt_compiler_impl, "call_llm_with_mcp", fail_call_llm_with_mcp)
    monkeypatch.setattr(
        prompt_compiler_impl,
        "_persist_update",
        lambda state, update: {**dict(state), **dict(update)},
    )

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 2,
        "segment_names": ["F01"],
        "script": "Alex: Stay here.\nBlair steps back.",
        "aspect_ratio": "9:16",
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Alex says stay here.\n"
                "    - Blair steps back.\n"
            ),
            "shot_director": (
                "- fragment_id: F01\n"
                "  fragment_task: pressure beat\n"
                "  rhythm: dialogue then reaction\n"
                "  shots:\n"
                "    - shot_id: F01-S01\n"
                "      duration: 0-3s\n"
                "      task: carry the command beat\n"
                "      subject: Alex\n"
                "      shot: stable medium shot\n"
                "      action: Alex looks at Blair and gives the order.\n"
                "      dialogue: Stay here.\n"
                "      must_carry: Alex gives the order.\n"
                "      cut_point: after the order lands\n"
                "      continuity: keep the same eyeline\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)
    outputs = result["agent_outputs"]

    assert "compiled_segment_1" in outputs
    assert "Alex looks at Blair" in outputs["compiled_segment_1"]
    assert "local fallback reason" in outputs["compiled_segment_1"]
    assert "prompt_compiler_fallback_seg01" in outputs
    assert "LLM gateway failed" in outputs["prompt_compiler_fallback_seg01"]
    assert result["step"] == "step_5_inspect"


def test_prompt_compiler_accepts_legacy_local_shot_fallback_marker(monkeypatch) -> None:
    def fail_call_llm_with_mcp(*_args, **_kwargs):
        raise RuntimeError("LLM gateway failed")

    monkeypatch.setattr(prompt_compiler_impl, "call_llm_with_mcp", fail_call_llm_with_mcp)
    monkeypatch.setattr(
        prompt_compiler_impl,
        "_persist_update",
        lambda state, update: {**dict(state), **dict(update)},
    )

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "segment_names": ["F01"],
        "script": "Alex opens the door. Blair steps back.",
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Alex opens the door.\n"
            ),
            "shot_director": (
                "- fragment_id: F01\n"
                "  schema_version: shot_director_local_fallback_v1\n"
                "  fragment_task: local fallback beat\n"
                "  rhythm: readable action\n"
                "  shots:\n"
                "    - shot_id: F01-S01\n"
                "      duration: 0-3s\n"
                "      task: carry the door beat\n"
                "      subject: Alex\n"
                "      shot: stable medium shot\n"
                "      action: Alex opens the door.\n"
                "      dialogue: \"\"\n"
                "      must_carry: Alex opens the door.\n"
                "      cut_point: after the door opens\n"
                "      continuity: keep screen direction\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)

    assert result["step"] == "step_5_inspect"
    assert "compiled_segment_1" in result["agent_outputs"]


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
