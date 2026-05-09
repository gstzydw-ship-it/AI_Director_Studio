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
            "节奏总合同:\n"
            "  - 原文锚点: ▲乔熙急匆匆赶到公司门口。\n"
            "    时间分配指令: 快推\n"
            "    建议时长: 4-6秒\n"
            "拆片边界建议:\n"
            "  - 边界锚点: 苏小可：New boss is coming!\n"
            "    拆分决定: 不拆\n"
            "反应归属: []\n"
            "尾帧承接: []\n"
            "结构规划施工指令: 普通停顿留在片段内部。\n"
            "镜头导演节奏执行约束:\n"
            "  - 原文锚点: ▲乔熙急匆匆赶到公司门口。\n"
            "    执行约束: 已有赶到动作快速承接，不新增人群反应。\n"
            "    停顿要求: 乔熙反应停半拍。\n"
            "    切镜预算:\n"
            "      覆盖时长: 4-6秒\n"
            "      主镜头上限: 2\n"
            "      辅助插入镜头上限: 0\n"
            "      单个主镜头最短时长: 2\n"
            "      最低停顿时长: 0.8\n"
            "      禁止切走区间: 无\n"
            "    无效过渡压缩:\n"
            "      压缩决定: 压缩\n"
            "      必须保留: 乔熙已到公司门口\n"
            "      可省略或桥接: 赶路全过程\n"
            "      允许桥接到: 下一个画面直接接公司门口\n"
            "      过渡最长时长: 2\n"
            "      安全规则: 若出现台词、关键道具或认出反应则禁止省略。\n"
            "    反应主体: 乔熙\n"
            "    尾帧要求: 保留乔熙停住听到新老板消息的状态。\n"
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
    assert "节奏总合同" in captured["system_prompt"]
    assert "拆片边界建议" in captured["system_prompt"]
    assert "反应归属" in captured["system_prompt"]
    assert "尾帧承接" in captured["system_prompt"]
    assert "切镜预算" in captured["system_prompt"]
    assert "无效过渡压缩" in captured["system_prompt"]
    assert "主镜头上限" in captured["system_prompt"]
    assert "辅助插入镜头上限" in captured["system_prompt"]
    assert "过渡最长时长" in captured["system_prompt"]
    assert "rhythm_contract" not in captured["system_prompt"]
    assert "source_anchor" not in captured["system_prompt"]
    assert "shot_director_notes" not in captured["system_prompt"]
    assert "不要只写高/中/低切镜密度" in captured["user_prompt"]
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
    assert "节奏总合同" in result["atmosphere_strategy"]
    assert "拆片边界建议" in result["atmosphere_strategy"]
    assert "镜头导演节奏执行约束" in result["atmosphere_strategy"]
    assert "主镜头上限" in result["atmosphere_strategy"]
    assert "无效过渡压缩" in result["atmosphere_strategy"]


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
            "director_brief": "节奏总控交接: 照片出现后必须刹车。",
            "scene_context_brief": "道具锚点: 照片在书包内。",
            "aspect_ratio": "9:16",
            "speed_mode": False,
            "agent_outputs": {},
        }
    )

    assert "【当前施工剧本（已由剧情增强导演处理）】" in captured["user_prompt"]
    assert "【剧情增强导演契约】" in captured["user_prompt"]
    assert "照片出现后必须刹车" in captured["user_prompt"]
    assert "【场景预分析约束】" in captured["user_prompt"]
    assert "照片在书包内" in captured["user_prompt"]
