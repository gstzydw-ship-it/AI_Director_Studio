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
        lambda *args, **kwargs: "节奏总合同: F01 保持快速进入；结构规划施工指令: 普通反应留在片段内部。",
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


def test_rhythm_supervisor_outputs_time_and_segment_contract(monkeypatch):
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
            "节奏诊断:\n"
            "  - ▲乔熙急匆匆赶到公司门口是过渡动作，需要压缩赶路过程。\n"
            "给结构规划师:\n"
            "  - 原文锚点: ▲乔熙急匆匆赶到公司门口。\n"
            "    分段决定: 与后面合并\n"
            "    必须包含的原文事件:\n"
            "      - ▲乔熙急匆匆赶到公司门口。\n"
            "      - 苏小可：New boss is coming!\n"
            "    不能包含的后续事件: []\n"
            "    建议时长: 4-6秒\n"
            "    可以压缩:\n"
            "      - 赶路全过程\n"
            "    不能省略:\n"
            "      - 乔熙已到公司门口\n"
            "    结尾必须停在: 乔熙听到新老板消息后停住。\n"
            "    承接提醒: 普通停顿留在片段内部。\n"
            "给镜头导演:\n"
            "  - 原文锚点: ▲乔熙急匆匆赶到公司门口。\n"
            "    本段必须拍完整:\n"
            "      - 乔熙已到公司门口\n"
            "      - 乔熙听到通知\n"
            "    可以省略:\n"
            "      - 完整赶路过程\n"
            "    不能省略:\n"
            "      - 到达公司门口这个结果\n"
            "    最少停留时间:\n"
            "      人物反应: 0.8秒\n"
            "    最多镜头数:\n"
            "      主镜头: 2\n"
            "      辅助插入镜头: 0\n"
            "    禁止新增:\n"
            "      - 人群反应\n"
            "    结尾画面必须是: 乔熙停住听到新老板消息的状态。\n"
            "风险提醒: 不得新增人群反应。"
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
    assert "时间与段落合同" in captured["system_prompt"]
    assert "不得新增动作" in captured["system_prompt"]
    assert "节奏诊断" in captured["system_prompt"]
    assert "给结构规划师" in captured["system_prompt"]
    assert "给镜头导演" in captured["system_prompt"]
    assert "必须包含的原文事件" in captured["system_prompt"]
    assert "不能包含的后续事件" in captured["system_prompt"]
    assert "最多镜头数" in captured["system_prompt"]
    assert "最少停留时间" in captured["system_prompt"]
    assert "结尾画面必须是" in captured["system_prompt"]
    assert "rhythm_contract" not in captured["system_prompt"]
    assert "source_anchor" not in captured["system_prompt"]
    assert "shot_director_notes" not in captured["system_prompt"]
    assert "最多镜头数和最少停留时间必须给具体数量" in captured["user_prompt"]
    assert "走向电梯、按按钮、门打开" in captured["user_prompt"]
    assert "conflict_enhancement_plan" not in captured["system_prompt"]
    assert "L1_动作层增强" not in captured["system_prompt"]
    assert "L2_调度层增强" not in captured["system_prompt"]
    assert "导演备注: 人群要快速跑出，车要急停，不要慢速走。" in captured["user_prompt"]
    assert captured["retrieval_profile"]["rule_type"][-3:] == [
        "segment_boundary",
        "tailframe_handoff",
        "reaction_ownership",
    ]
    assert "cut_budget" in captured["retrieval_profile"]["signals"]
    assert "transition_trim" in captured["retrieval_profile"]["signals"]
    assert "reference_images" not in captured["user_prompt"]
    assert "给结构规划师" in result["atmosphere_strategy"]
    assert "给镜头导演" in result["atmosphere_strategy"]
    assert "最多镜头数" in result["atmosphere_strategy"]
    assert "可以省略" in result["atmosphere_strategy"]


def test_rhythm_supervisor_receives_enhancement_contract(monkeypatch):
    from agents.director_graph_package import helpers, legacy_impl, nodes

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        helpers,
        "build_system_prompt",
        lambda prompt, agent_name, context_hint="", **kwargs: (prompt, {"retrieval_mode": "test"}),
    )

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["user_prompt"] = user_prompt
        return (
            "节奏总合同: []\n"
            "拆片边界建议: []\n"
            "反应归属: []\n"
            "尾帧承接: []\n"
            "结构规划施工指令: 无\n"
            "镜头导演节奏执行约束: 无\n"
            "风险提醒: 无"
        )

    monkeypatch.setattr(legacy_impl, "call_llm", fake_call_llm)
    monkeypatch.setattr(legacy_impl, "_record_knowledge_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr(legacy_impl, "_persist_update", lambda state, payload: {**state, **payload})

    nodes.rhythm_rewrite_director_node(
        {
            "script": "增强后剧本",
            "enhanced_script": "增强后剧本",
            "director_brief": "节奏总控交接: 照片出现后必须保护人物反应。",
            "scene_context_brief": "道具锚点: 照片在书包内。",
            "aspect_ratio": "9:16",
            "speed_mode": False,
            "agent_outputs": {},
        }
    )

    assert "【当前施工剧本（已由剧情增强导演处理）】" in captured["user_prompt"]
    assert "【剧情增强导演契约】" in captured["user_prompt"]
    assert "照片出现后必须保护人物反应" in captured["user_prompt"]
    assert "【场景预分析约束】" in captured["user_prompt"]
    assert "照片在书包内" in captured["user_prompt"]
