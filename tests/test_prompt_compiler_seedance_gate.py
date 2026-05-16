from __future__ import annotations

from agents.director_graph_package import prompt_compiler_impl
from agents.director_graph_package.prompt_compiler_impl import _compiler_guard_report


def _valid_prompt() -> str:
    return """片段1｜客厅｜对峙｜约6秒｜9:16竖屏

【画面基底】
客厅侧面固定观察视角，乔熙和小豆丁在沙发旁，晨光稳定。

【镜头序列】
镜头1【3秒】【乔熙】中景，客厅侧面平视。乔熙看向小豆丁，停住半步。（切镜时机：乔熙停住后切至镜头2）
镜头2【3秒】【小豆丁】半身景，沙发旁固定半身景。小豆丁低头不动，尾帧：仍坐在沙发边，视线避开乔熙，书包留在脚边。

【约束】
严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌。人物、空间、道具和尾帧状态连续。
"""


def test_seedance_contract_guard_flags_x_template_tail_state_and_text_dependency() -> None:
    planner = """fragment_id: F01
generation_unit_id: GU01
source_script_events:
  - 乔熙发现手机屏幕文字。
model_complexity_score: 2
reference_needs: [identity_reference, scene_reference]
"""
    director = """fragment_id: F01
fragment_task: 手机文字揭示误会
rhythm: 信息揭示
template_id: COV-SD20-X-TEXT-REVEAL
template_level: X
reference_need: identity_reference + scene_reference
tail_state: 不清
shots:
  - shot_id: F01-S01
    duration: 3秒
    task: 揭示手机屏幕文字
    subject: 乔熙
    shot: 手机特写
    action: 乔熙通过手机屏幕文字发现真相
    dialogue: ''
    must_carry: 依赖屏幕文字传达剧情
    cut_point: 文字看清后
    continuity: 手机仍在手里
"""

    report = _compiler_guard_report(_valid_prompt(), "", planner, director)

    assert "SEEDANCE-COVERAGE-TEMPLATE-GATE-001" in report
    assert "X 禁用 coverage 模板" in report
    assert "SEEDANCE-TAIL-STATE-GATE-001" in report
    assert "SEEDANCE-NO-TEXT-DEPENDENCY-001" in report


def test_seedance_contract_guard_flags_r1_without_reference_and_complexity_over_limit() -> None:
    planner = """fragment_id: F01
source_script_events:
  - 两人争抢手机。
model_complexity_score: 5
reference_needs: [identity_reference, scene_reference]
"""
    director = """fragment_id: F01
fragment_task: 争抢手机
rhythm: 冲突
template_id: COV-SD20-R1-FIGHT-BEAT
template_level: R1
reference_need: identity_reference + scene_reference
tail_state: 乔熙站在沙发旁，手机仍在她手里，小豆丁退开半步看向手机。
shots:
  - shot_id: F01-S01
    duration: 5秒
    task: 争抢手机
    subject: 乔熙
    shot: 双人中景
    action: 两人争抢手机后停住
    dialogue: ''
    must_carry: 手机归属变化
    cut_point: 手机被拉住时
    continuity: 两人仍在沙发旁
"""

    report = _compiler_guard_report(_valid_prompt(), "", planner, director)

    assert "SEEDANCE-COMPLEXITY-GATE-001" in report
    assert "model_complexity_score=5" in report
    assert "R1 参考驱动模板缺少视频参考/关键帧/动作参考绑定" in report


def test_prompt_compiler_injects_seedance_contract_card_and_gate_rules(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_build_system_prompt(base_system, _agent_name, context_hint="", **_kwargs):
        captured["system_prompt"] = base_system
        captured["context_hint"] = context_hint
        return base_system, {"retrieval_mode": "stub"}

    def fake_call_llm(system_prompt, user_prompt, images_base64=None, agent_name=""):
        captured["llm_system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["agent_name"] = agent_name
        assert images_base64 is None
        return _valid_prompt()

    monkeypatch.setattr(prompt_compiler_impl, "build_system_prompt", fake_build_system_prompt)
    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fake_call_llm)
    monkeypatch.setattr(prompt_compiler_impl, "_record_knowledge_metadata", lambda state, *_args, **_kwargs: state.get("knowledge_metadata", {}))
    monkeypatch.setattr(prompt_compiler_impl, "_persist_update", lambda state, update: {**dict(state), **dict(update)})

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "segment_names": ["F01"],
        "script": "乔熙看向小豆丁。",
        "aspect_ratio": "9:16",
        "agent_outputs": {
            "story_planner": (
                "fragment_id: F01\n"
                "source_script_events:\n"
                "  - 乔熙看向小豆丁。\n"
                "model_complexity_score: 2\n"
                "reference_needs: [identity_reference, scene_reference]\n"
            ),
            "shot_director": (
                "fragment_id: F01\n"
                "fragment_task: 亲子对峙停顿\n"
                "rhythm: 停顿\n"
                "template_id: COV-SD20-W1-REACTION-HOLD\n"
                "template_level: W1\n"
                "reference_need: identity_reference + scene_reference\n"
                "tail_state: 乔熙站在沙发旁看向小豆丁，小豆丁坐在沙发边，书包留在脚边。\n"
                "shots:\n"
                "  - shot_id: F01-S01\n"
                "    duration: 3秒\n"
                "    task: 乔熙停住\n"
                "    subject: 乔熙\n"
                "    shot: 中景，客厅侧面平视\n"
                "    action: 乔熙看向小豆丁后停住\n"
                "    dialogue: ''\n"
                "    must_carry: 亲子距离和停顿\n"
                "    cut_point: 乔熙停住后\n"
                "    continuity: 两人仍在沙发旁\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)

    assert result["agent_outputs"]["compiled_segment_1"].startswith("片段1｜客厅")
    assert "【Seedance 2.0 合同编译 gate】" in captured["system_prompt"]
    assert "【Seedance 2.0 合同字段卡" in captured["user_prompt"]
    assert "template_id: COV-SD20-W1-REACTION-HOLD" in captured["user_prompt"]
    assert "template_level: W1" in captured["user_prompt"]
    assert "reference_need: identity_reference + scene_reference" in captured["user_prompt"]
    assert "tail_state: 乔熙站在沙发旁看向小豆丁" in captured["user_prompt"]
    assert "model_complexity_score: 2" in captured["user_prompt"]
    assert captured["agent_name"] == "prompt_compiler"
