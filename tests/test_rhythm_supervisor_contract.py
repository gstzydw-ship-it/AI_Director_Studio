from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_rhythm_supervisor_does_not_replace_source_script(monkeypatch):
    from agents.director_graph_package import helpers, legacy_impl, nodes

    original_script = "乔熙：Wait a second!\n商北琛扶住她。"

    monkeypatch.setattr(
        helpers,
        "build_system_prompt",
        lambda prompt, agent_name, context_hint="", **kwargs: (prompt, {"retrieval_mode": "test"}),
    )
    monkeypatch.setattr(
        legacy_impl,
        "call_llm",
        lambda *args, **kwargs: "rhythm_diagnosis: F01 保持快速进入；construction_notes: 普通反应留在片段内部。",
    )
    monkeypatch.setattr(legacy_impl, "_record_knowledge_metadata", lambda *args, **kwargs: {})

    def fake_persist(state, payload):
        merged = dict(state)
        merged.update(payload)
        return merged

    monkeypatch.setattr(legacy_impl, "_persist_update", fake_persist)

    result = nodes.rhythm_rewrite_director_node(
        {
            "script": original_script,
            "aspect_ratio": "9:16",
            "speed_mode": False,
            "agent_outputs": {},
        }
    )

    assert result["script"] == original_script
    assert "普通反应留在片段内部" in result["atmosphere_strategy"]
    assert "改写后剧本" not in result["agent_outputs"]["rhythm_rewrite_director"]


def test_rhythm_supervisor_requires_conflict_and_speed_curve(monkeypatch):
    from agents.director_graph_package import helpers, legacy_impl, nodes

    captured: dict[str, object] = {}

    def fake_build_system_prompt(
        role_description,
        agent_name,
        context_hint="",
        retrieval_profile=None,
        **kwargs,
    ):
        captured["role_description"] = role_description
        captured["agent_name"] = agent_name
        captured["context_hint"] = context_hint
        captured["retrieval_profile"] = retrieval_profile
        captured["build_kwargs"] = kwargs
        return role_description, {"retrieval_mode": "test"}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["call_kwargs"] = kwargs
        return (
            "conflict_diagnosis: 目标是赶到公司，阻力是迟到和突发易主消息。\n"
            "conflict_enhancement_plan: L1_动作层增强加入动作密度；L2_调度层增强加入人群快速列队；"
            "L3_剧情层增强无，需用户确认才可新增事件。\n"
            "speed_curve: 起速、加速动作、刹车点、再启动点、钩子落点必须明确。\n"
            "rhythm_diagnosis: 快段不能拍慢，照片处才慢。\n"
            "construction_notes: 普通停顿留在片段内部。\n"
            "shot_director_notes: 公司门口人员快速跑出，车急停，乔熙反应停半拍。"
        )

    monkeypatch.setattr(helpers, "build_system_prompt", fake_build_system_prompt)
    monkeypatch.setattr(legacy_impl, "call_llm", fake_call_llm)
    monkeypatch.setattr(legacy_impl, "_record_knowledge_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr(legacy_impl, "_persist_update", lambda state, payload: {**state, **payload})

    result = nodes.rhythm_rewrite_director_node(
        {
            "script": "▲乔熙急匆匆赶到公司门口。\n苏小可：New boss is coming!",
            "director_notes": "人群要快速跑出，车要急停，不要慢速走。",
            "aspect_ratio": "9:16",
            "speed_mode": False,
            "agent_outputs": {},
        }
    )

    assert captured["agent_name"] == "rhythm_rewrite_director"
    assert captured["call_kwargs"]["agent_name"] == "rhythm_rewrite_director"
    assert "冲突诊断" in captured["system_prompt"]
    assert "冲突增强方案" in captured["system_prompt"]
    assert "速度曲线" in captured["system_prompt"]
    assert "L1_动作层增强" in captured["system_prompt"]
    assert "L2_调度层增强" in captured["system_prompt"]
    assert "L3_剧情层增强" in captured["system_prompt"]
    assert "director_notes: 人群要快速跑出，车要急停，不要慢速走。" in captured["user_prompt"]
    assert captured["retrieval_profile"]["rule_type"][-2:] == ["conflict_diagnosis", "speed_curve"]
    assert "conflict_diagnosis" in result["atmosphere_strategy"]
    assert "speed_curve" in result["atmosphere_strategy"]
    assert "shot_director_notes" in result["atmosphere_strategy"]
