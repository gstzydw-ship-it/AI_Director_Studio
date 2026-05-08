"""单次调用 shot_director 流水线单元测试 (精简 schema 版)。

用 monkeypatch stub 掉 call_llm，验证：
- 单次调用产出完整 lean YAML (subject/camera/size/action/dialogue/intent)
- agent_outputs["shot_director"] 包含所有 fragment
- knowledge_metadata 正确记录
- 从 story_plan 重启正确清理旧数据
"""
from __future__ import annotations

import os
import sys
import re
from pathlib import Path

import pytest

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.director_graph as dg
from agents.director_graph_package import legacy_impl, runners, shot_director_impl


# ── lean schema stub 输出 ──────────────────────────────────────────

LEAN_YAML = """\
- fragment_id: "F05"
  shots:
    - shot_id: "F05-S01"
      subject: "商北琛"
      camera: "正面平视 固定机位"
      size: "半身"
      action: "站在桌对面，目光扫向严飞"
      dialogue: "你没有资格。"
      intent: "建立施压入场"
    - shot_id: "F05-S02"
      type: "reaction"
      subject: "严飞"
      camera: "过肩(商北琛肩线前景) 眼平 固定机位"
      size: "中近景"
      action: "手中文件一顿，抬头"
      dialogue: "这不是你说了算的。"
      intent: "受击反应—��听到压制后反击"

- fragment_id: "F06"
  shots:
    - shot_id: "F06-S01"
      subject: "严飞"
      camera: "左侧 眼平 固定机位"
      size: "中景"
      action: "起身，身体前压"
      dialogue: "证据在我手里。"
      intent: "权力翻转——严飞反击"
    - shot_id: "F06-S02"
      type: "reaction"
      subject: "商北琛"
      camera: "正面平视 固定机位"
      size: "中近景"
      action: "后退半步，表情微僵"
      dialogue: ~
      intent: "受击——商北琛首次失势"
"""


# ── 辅助 ──────────────────────────────────────────────


def _make_state(script: str = "商北琛：你没有资格。\n严飞：这不是你说了算的。\n严飞：证据在我手里。"):
    return {
        "script": script,
        "aspect_ratio": "9:16",
        "reference_image_b64s": [],
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F05\n"
                "  duration_target: \"12秒\"\n"
                "  dramatic_unit: \"对峙升级\"\n"
                "  source_script_events:\n"
                "    - \"商北琛：你没有资格。\"\n"
                "    - \"严飞：这不是你说了算的。\"\n"
                "- fragment_id: F06\n"
                "  duration_target: \"10秒\"\n"
                "  dramatic_unit: \"权力翻转\"\n"
                "  source_script_events:\n"
                "    - \"严飞：证据在我手里。\"\n"
            ),
            "rhythm_rewrite_director": "氛围：高压权力博弈",
        },
        "knowledge_metadata": {},
        "speed_mode": False,
    }


def _fake_llm_factory():
    """Return a call_llm stub that always returns LEAN_YAML."""
    call_idx = {"n": 0}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        call_idx["n"] += 1
        return LEAN_YAML

    return fake_call_llm, call_idx


def _patch_fast_prompt_builder(monkeypatch):
    """Keep these tests offline."""
    def fake_build_system_prompt(base_system, agent_name, context_hint="", **_kwargs):
        return base_system, {
            "retrieval_mode": "stub",
            "used_full_fallback": False,
            "matched_sources": [f"{agent_name}.stub.md"],
            "context_hint": context_hint,
        }

    monkeypatch.setattr(dg, "build_system_prompt", fake_build_system_prompt)
    monkeypatch.setattr(dg, "_agent_configured", lambda agent_name: False)


# ── 测试 ──────────────────────────────────────────────

def test_single_pass_produces_complete_lean_output(monkeypatch):
    fake_llm, call_idx = _fake_llm_factory()
    monkeypatch.setattr(dg, "call_llm", fake_llm)
    _patch_fast_prompt_builder(monkeypatch)

    state = _make_state()
    result = dg.shot_director_node(state)

    final_output = result["agent_outputs"]["shot_director"]
    assert "F05" in final_output
    assert "F06" in final_output
    # lean schema 字段
    assert "subject:" in final_output
    assert "camera:" in final_output
    assert "size:" in final_output
    assert "action:" in final_output
    assert "intent:" in final_output

    # 单次调用 (primary) + 无 repair 情况下只有 1 ���
    assert call_idx["n"] >= 1


def test_single_pass_does_not_produce_old_stage_outputs(monkeypatch):
    fake_llm, _ = _fake_llm_factory()
    monkeypatch.setattr(dg, "call_llm", fake_llm)
    _patch_fast_prompt_builder(monkeypatch)

    state = _make_state()
    result = dg.shot_director_node(state)

    outputs = result["agent_outputs"]
    # 新架构不再产出 layout/blocking/guard 中间产物
    assert "shot_director" in outputs


def test_mcu_is_not_misclassified_as_closeup():
    assert not dg._is_closeup_shot_size("MCU")
    assert not dg._is_closeup_shot_size("medium close-up")
    assert not dg._is_closeup_shot_size("中近景")
    assert dg._is_closeup_shot_size("CU")
    assert dg._is_closeup_shot_size("ECU")
    assert dg._is_closeup_shot_size("脸部特写")


def test_single_pass_derives_missing_segment_names_from_planner(monkeypatch):
    fake_llm, _ = _fake_llm_factory()
    monkeypatch.setattr(dg, "call_llm", fake_llm)
    _patch_fast_prompt_builder(monkeypatch)

    state = _make_state()
    state.pop("segment_names", None)
    state.pop("total_segments", None)

    result = dg.shot_director_node(state)

    assert result["total_segments"] == 2
    assert result["segment_names"] == ["F05", "F06"]


def test_single_pass_runtime_metadata(monkeypatch):
    fake_llm, _ = _fake_llm_factory()
    monkeypatch.setattr(dg, "call_llm", fake_llm)
    _patch_fast_prompt_builder(monkeypatch)

    state = _make_state()
    result = dg.shot_director_node(state)

    km = result.get("knowledge_metadata", {})
    sd_meta = km.get("shot_director", {})

    # runtime 包含 final 阶段
    runtime = sd_meta.get("runtime", {})
    assert "path" in runtime
    assert runtime["path"] == "direct_llm_only"

    # stage_retrieval 包含 final
    stage_retrieval = sd_meta.get("stage_retrieval", {})
    assert "final" in stage_retrieval


def test_restart_shot_director_from_story_plan_clears_old_data(monkeypatch):
    state = _make_state()
    state["status"] = "idle"
    state["step"] = "step_3_direct"
    state["agent_outputs"]["shot_director"] = "stale output"
    state["agent_outputs"]["shot_director_final"] = "stale final"
    state["knowledge_metadata"] = {"shot_director": {"runtime": {"final": {"status": "error"}}}}

    saved_states: list[dict] = []
    captured_node_state: dict = {}

    monkeypatch.setattr(legacy_impl, "load_state", lambda: state)
    monkeypatch.setattr(legacy_impl, "save_state", lambda payload: saved_states.append(dict(payload)))

    def fake_shot_director_node(payload):
        captured_node_state.update(payload)
        result = dict(payload)
        result["status"] = "waiting_for_user_input"
        result["agent_outputs"] = {
            **payload["agent_outputs"],
            "shot_director": LEAN_YAML,
        }
        return result

    monkeypatch.setattr(shot_director_impl, "shot_director_node", fake_shot_director_node)

    result = runners.run_shot_director_restart_from_story_plan()

    node_outputs = captured_node_state["agent_outputs"]
    assert "story_planner" in node_outputs
    assert "shot_director" not in node_outputs
    assert "shot_director_final" not in node_outputs
    assert result["agent_outputs"]["shot_director"] == LEAN_YAML
