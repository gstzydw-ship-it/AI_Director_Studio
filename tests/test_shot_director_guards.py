from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.knowledge_base import get_agent_knowledge_files  # noqa: E402
from agents.director_graph_package import legacy_impl, runners  # noqa: E402
from agents.director_graph_package.story_planner_impl import _script_emotional_attention_units  # noqa: E402
from agents.director_graph_package.shot_director_impl import (  # noqa: E402
    _clean_shot_director_output,
    _estimate_shot_director_coverage_plan,
    _hard_shot_director_issues,
    _shot_director_rhythm_match_rules,
    _shot_director_source_event_rules,
    _validate_shot_director_output,
    _validate_shot_director_source_event_coverage,
    _validate_shot_director_script_fidelity,
    _validate_shot_director_vertical_discipline,
)
from agents.director_graph_package import shot_director_impl  # noqa: E402


def _coverage_v3_output(shots: str, *, target_count: int = 1, max_count: int = 3) -> str:
    return f"""- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: test coverage
    rhythm_intent: controlled
    space_contract:
      location: test room
    shot_budget:
      target_count: {target_count}
      max_count: {max_count}
    required_beats:
      - establish_continuity
  template_plan:
    shots:
{shots}
  guard_result:
    status: pass
    final_shots: [F01-S01]
    repairs: []
"""


def test_clean_shot_director_output_strips_thinking_and_markdown():
    raw = """<thinking>
fragment_id: F04
draft notes without required fields
</thinking>

```yaml
fragment_id: F04
fragment_intent: "回到现实"
reaction_coverage: "乔熙反应在片段内承接"
continuity_anchor: "照片在桌上，书包在小豆丁身上"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "承接回神"
    dialogue_coverage: "乔熙OS"
```

解释文字。
"""

    cleaned = _clean_shot_director_output(raw)

    assert cleaned.startswith("fragment_id: F04")
    assert "<thinking>" not in cleaned
    assert "解释文字" not in cleaned
    assert "main_shots:" in cleaned


def test_segment_shot_director_reports_connection_failure_after_llm_failure(monkeypatch):
    def fail_three_stage(**_kwargs):
        raise RuntimeError("LLM network connection failed")

    monkeypatch.setattr(shot_director_impl, "_run_shot_director_three_stage", fail_three_stage)
    captured_update = {}

    def fake_persist(state, update):
        captured_update.update(update)
        return {**dict(state), **dict(update)}

    monkeypatch.setattr(shot_director_impl, "_persist_update", fake_persist)

    state = {
        "script": "Alex opens the door. Blair reacts and steps back.",
        "aspect_ratio": "9:16",
        "total_segments": 1,
        "segment_names": ["segment01"],
        "agent_outputs": {
            "story_planner": (
                "- fragment_id: F01\n"
                "  source_script_events:\n"
                "    - Alex opens the door.\n"
                "    - Blair reacts and steps back.\n"
            )
        },
    }

    with pytest.raises(RuntimeError, match="镜头导演大模型连接不成功"):
        shot_director_impl.run_shot_director_for_segment(state, 1)

    outputs = captured_update["agent_outputs"]
    runtime = captured_update["knowledge_metadata"]["shot_director"]["runtime"]

    assert captured_update["status"] == "error"
    assert captured_update["step"] == "error"
    assert "shot_director_segment_F01" not in outputs
    assert outputs["shot_director_error_fragment_F01"].startswith("镜头导演大模型连接不成功")
    assert "本地兜底" not in outputs["shot_director_error_fragment_F01"]
    assert runtime["local_fallback"] is False
    assert runtime["status"] == "connection_failed"
    assert runtime["final"]["status"] == "connection_failed"


def test_segment_shot_director_reports_connection_failure_after_logic_reviewer_failure(monkeypatch):
    def fake_three_stage(**_kwargs):
        output = (
            "- fragment_id: F01\n"
            "  fragment_intent: Door reaction\n"
            "  main_shots:\n"
            "    - shot_id: F01-S01\n"
            "      subject: Alex\n"
            "      shot_size: medium\n"
        )
        return output, {"final": {"status": "ok"}}, {"final": {"retrieval_mode": "stub"}}, {"final": output}

    def fail_review(**_kwargs):
        raise RuntimeError("镜头逻辑审查大模型连接不成功：offline")

    monkeypatch.setattr(shot_director_impl, "_run_shot_director_three_stage", fake_three_stage)
    monkeypatch.setattr(shot_director_impl, "_run_shot_director_review_board", fail_review)
    monkeypatch.setattr(shot_director_impl, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(shot_director_impl, "_hard_shot_director_issues", lambda issues: [])
    captured_update = {}

    def fake_persist(state, update):
        captured_update.update(update)
        return {**dict(state), **dict(update)}

    monkeypatch.setattr(shot_director_impl, "_persist_update", fake_persist)

    state = {
        "script": "Alex opens the door. Blair reacts.",
        "aspect_ratio": "9:16",
        "total_segments": 1,
        "segment_names": ["segment01"],
        "agent_outputs": {"story_planner": "- fragment_id: F01\n  source_script_events:\n    - Alex opens the door.\n"},
    }

    with pytest.raises(RuntimeError, match="镜头逻辑审查大模型连接不成功"):
        shot_director_impl.run_shot_director_for_segment(state, 1)

    outputs = captured_update["agent_outputs"]
    runtime = captured_update["knowledge_metadata"]["shot_director"]["runtime"]

    assert captured_update["status"] == "error"
    assert captured_update["step"] == "error"
    assert outputs["shot_director_error_fragment_F01"].startswith("镜头逻辑审查大模型连接不成功")
    assert runtime["status"] == "connection_failed"
    assert runtime["path"] == "logic_reviewer_connection_failed"
    assert runtime["review_board"]["status"] == "connection_failed"


def test_shot_director_fidelity_rejects_wake_up_reinterpretation():
    script = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。
▲小豆丁已经站在门口，单肩背着书包等她。
乔熙OS：It's been four years. He's married with a kid now. Sunny, wake up.
乔熙：Come on, baby, let's go. Gonna be late.
"""
    director_output = """fragment_id: F04
fragment_intent: "Sunny 睡醒"
reaction_coverage: "Sunny 睁眼"
continuity_anchor: "Sunny 仰卧在床上，伴侣站在床尾"
main_shots:
  - shot_id: "F04-S01"
    subject: "Sunny 睡颜"
    shot_size: "ECU"
    camera_height: "slightly_high"
    angle: "俯拍"
    movement: "static"
    lens: "85mm"
    depth: "shallow"
    shot_intent: "表现睡眠中的微表情"
    dialogue_coverage: "Sunny, wake up."
"""

    issues = _validate_shot_director_script_fidelity(director_output, script)

    assert any("剧本外前提" in issue for issue in issues)
    assert any("Sunny" in issue for issue in issues)


def test_shot_director_fidelity_rejects_photo_bag_state_drift():
    script = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。
▲小豆丁已经站在门口，单肩背着书包等她。
"""
    director_output = """fragment_id: F04
fragment_intent: "回到现实"
reaction_coverage: "乔熙把照片攥进掌心"
continuity_anchor: "照片被塞回书包"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "乔熙指尖压住照片"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_script_fidelity(director_output, script)

    assert any("照片/书包连续性" in issue for issue in issues)


def test_shot_director_fidelity_rejects_scene_space_drift():
    script = """1-3 晨/内/乔熙公寓（回到现实）
人物：乔熙、小豆丁
▲乔熙猛地回神，强压下心口闷痛，把照片放到桌上。
▲小豆丁已经站在门口，单肩背着书包等她。
"""
    director_output = """fragment_id: F04
fragment_intent: "乔熙独坐车内"
reaction_coverage: "乔熙在车窗边回神"
continuity_anchor: "乔熙已落座车内，车尚未起步"
main_shots:
  - shot_id: "F04-S01"
    subject: "乔熙"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "车内回神"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_script_fidelity(director_output, script)

    assert any("剧本外前提" in issue and "车内" in issue for issue in issues)


def test_shot_director_coverage_rejects_missing_source_event_terms():
    planner = """fragment_id: F04
cast:
  active:
    - 人物甲
    - 人物乙
source_script_events:
  - "▲人物甲猛地回神，强压下心口闷痛，把照片放到桌上。"
  - "▲人物乙已经站在门口，单肩背着背包等她。"
main_shots:
  - shot_id: "F04-S01"
reaction_plan: "片段内承接"
"""
    director_output = """fragment_id: F04
fragment_intent: "人物甲放下照片"
reaction_coverage: "人物甲反应"
continuity_anchor: "照片在桌上"
main_shots:
  - shot_id: "F04-S01"
    subject: "人物甲"
    shot_size: "medium"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "50mm"
    depth: "medium"
    shot_intent: "人物甲放下照片"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_source_event_coverage(director_output, planner)

    assert any("人物乙" in issue and "背包" in issue for issue in issues)


def test_shot_director_vertical_discipline_rejects_closeup_overuse_in_9x16():
    director_output = """fragment_id: F05
fragment_intent: "门口预压"
reaction_coverage: "人群反应"
continuity_anchor: "集团门口等待新老板"
main_shots:
  - shot_id: "F05-S01"
    subject: "乔熙"
    shot_size: "CU"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "85mm"
    depth: "shallow"
    shot_intent: "乔熙反应"
    dialogue_coverage: "none"
  - shot_id: "F05-S02"
    subject: "秘书"
    shot_size: "ECU"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "100mm"
    depth: "shallow"
    shot_intent: "秘书紧张"
    dialogue_coverage: "none"
"""

    issues = _validate_shot_director_vertical_discipline(director_output, "9:16")

    assert any("全部使用特写类景别" in issue for issue in issues)
    assert any("多次面部特写" in issue for issue in issues)


def test_validate_shot_director_output_rejects_invalid_transition_type_and_missing_tail_state_card():
    director_output = """fragment_id: F01
schema_version: shot_director_v2
fragment_intent: "门口压迫建立"
reaction_coverage: "听者受压后停住"
continuity_anchor: "两人站在门口对峙"
shots:
  - shot_id: "F01-S01"
    subject: "商北琛"
    shot_size: "中近景"
    camera_height: "平视"
    angle: "正面"
    movement: "固定"
    lens: "50mm"
    depth: "浅景深"
    coverage_role: "承载压迫发言"
    cut_reason: "台词前半句落下后切出"
    companion_visibility: "乔熙在过肩边缘"
    tailframe_role: "尾帧交给听者反应"
    dialogue_coverage: "前半句落在说话者，后半句切听者反应"
    transition_type: "同一机位继续"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("only schema_version: shot_director_coverage_v3 is supported." in issue for issue in issues)



def test_shot_director_vertical_discipline_rejects_micro_detail_shot_pileup():
    director_output = """fragment_id: F01
fragment_intent: "穿衣手忙脚乱"
reaction_coverage: "小豆丁不配合"
continuity_anchor: "乔熙在公寓给小豆丁穿衣"
main_shots:
  - shot_id: "F01-S01"
    subject: "掌心"
    shot_size: "CU"
    camera_height: "eye_level"
    angle: "front"
    movement: "static"
    lens: "85mm"
    depth: "shallow"
    shot_intent: "手忙脚乱"
    dialogue_coverage: "none"
sub_shots:
  - parent_shot_id: "F01-S01"
    trigger: "穿衣卡住"
    subject: "鞋尖"
    shot_size: "CU"
    beat_purpose: "细节强调"
    emotion_anchor: "慌乱"
  - parent_shot_id: "F01-S01"
    trigger: "衣服滑脱"
    subject: "袖口"
    shot_size: "CU"
    beat_purpose: "继续强调"
    emotion_anchor: "更乱"
"""

    issues = _validate_shot_director_vertical_discipline(director_output, "9:16")

    assert any("多个微细节局部" in issue for issue in issues)


def test_shot_director_allows_empty_sub_shots_array():
    director_output = _coverage_v3_output("""      - shot_id: F01-S01
        duration: 0-3s
        task: establish continuity
        subject: Actor
        shot: medium relation shot, eye-level
        action: Actor moves to exit.
        dialogue: none
        must_carry: continuity and position lock
        cut_point: scene exit
        continuity: Actor remains in same lobby state
        coverage_role: continuity
        cut_reason: actor leaves the room and moves to next area
        companion_visibility: Actor visible
        state_delta: stable
        tailframe_role: carry state
        template_id: COV-SD20-W1-ENTRY
        template_level: W1
        reference_need: identity_reference script_reference
        model_complexity_score: 1
        tail_state: Actor at lobby with stable position
""")

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert not any("sub_shots" in issue for issue in issues)


def test_shot_director_v1_uses_merged_shot_field():
    director_output = """- fragment_id: F01
  fragment_task: "legacy-shorthand"
  rhythm: "moderate"
  continuity_context: "legacy v1 layout should fail now"
  shots:
    - shot_id: F01-S01
      duration: 0-3s
      task: "legacy shot field test"
      subject: "Actor"
      shot: "wide"
      action: "Actor takes one step."
      dialogue: "~"
      must_carry: "legacy control"
      cut_point: "after line"
      continuity: "actor steps forward"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("only schema_version: shot_director_coverage_v3 is supported." in issue for issue in issues)


def test_shot_director_rejects_legacy_v2_schema():
    director_output = """- fragment_id: F01
  schema_version: shot_director_v2
  fragment_intent: "legacy coverage"
  reaction_coverage: "legacy coverage fields"
  continuity_anchor: "legacy continuity anchor"
  shots:
    - shot_id: F01-S01
      subject: "Actor"
      shot_size: "full shot"
      camera_height: "low"
      angle: "front"
      movement: "static"
      lens: "35mm"
      depth: "medium"
      coverage_role: "legacy"
      cut_reason: "legacy cut"
      companion_visibility: "both visible"
      tailframe_role: "carry state"
      dialogue_coverage: "none"
      transition_type: stay_on_A
      tail_state_card: "legacy actor state"
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("only schema_version: shot_director_coverage_v3 is supported." in issue for issue in issues)


def test_shot_director_rejects_vague_cut_point_in_coverage_v3():
    director_output = _coverage_v3_output("""      - shot_id: F01-S01
        duration: 0-3s
        task: establish continuity
        subject: Actor
        shot: medium relation shot
        action: Actor hesitates.
        dialogue: none
        must_carry: continuity carry
        cut_point: cinematic
        continuity: Actor stays in lobby
        coverage_role: continuity
        cut_reason: actor response unclear
        companion_visibility: actor visible
        state_delta: stable
        tailframe_role: carry state
        template_id: COV-SD20-W1-ENTRY
        template_level: W1
        reference_need: identity_reference script_reference
        model_complexity_score: 1
        tail_state: Actor in lobby
""")

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("cut_point must bind to action apex, dialogue break, readable information, reaction, or tailframe state." in issue for issue in issues)


def test_shot_director_restart_rerun_waits_for_per_segment_generation():
    state = {
        "agent_outputs": {"story_planner": "planner-output"},
        "knowledge_metadata": {"shot_director": {"old": True}},
    }
    saved_states = []

    previous_load_state = legacy_impl.load_state
    previous_save_state = legacy_impl.save_state

    def fake_load_state():
        return state

    def fake_save_state(updated_state):
        saved_states.append(dict(updated_state))

    legacy_impl.load_state = fake_load_state
    legacy_impl.save_state = fake_save_state
    try:
        result = runners.run_shot_director_restart_from_story_plan()
    finally:
        legacy_impl.load_state = previous_load_state
        legacy_impl.save_state = previous_save_state

    assert saved_states and saved_states[-1]["step"] == "step_3_direct"
    assert "shot_director" not in state["knowledge_metadata"]
    assert result["status"] == "waiting_for_user_input"
    assert result["current_segment_index"] == 1


def test_shot_director_closeup_density_is_soft_issue():
    issues = [
        "F02 在 9:16 里出现多次面部特写，特写使用过密。",
        "F04 的 main_shots 缺少字段 subject。",
    ]

    assert _hard_shot_director_issues(issues) == ["F04 的 main_shots 缺少字段 subject。"]


def test_shot_director_runtime_rules_and_rule_card_are_present():
    rules = _shot_director_source_event_rules()
    rhythm_rules = _shot_director_rhythm_match_rules()
    critical_files = get_agent_knowledge_files("shot_director", critical_only=True)

    assert "英文短语只按当前人物台词/画外音处理" in rules
    assert "不能联想成剧本外的新动作或新人物" in rules
    assert "公寓不能改成车内" in rules
    assert "subject 只能来自当前片段的人物行" in rules
    assert "一个片段的面部特写最多一次" in rules
    assert "没必要每个细节动作都给镜头" in rules
    assert "参考《AI 导演系统工程文档规范》" in rhythm_rules
    assert "镜头数量由节奏任务决定" in rhythm_rules
    assert "镜头数、镜头时长、景别、机位、运镜、反应覆盖和切镜点由 shot_director 决定" in rhythm_rules
    assert "5-6秒片段一般不超过3个有效镜头" in rhythm_rules
    assert "一号 layout 阶段先决定主镜头覆盖骨架和粗景别" in rhythm_rules
    assert "长对白必须根据情绪压力切听者反应" in rhythm_rules
    assert "9:16 竖屏下，半身/中景/双人关系镜头是主力" in rhythm_rules
    assert "rules/shot_director/SHOT-SOURCE-EVENT-FIDELITY-001.md" in critical_files
    assert "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md" not in critical_files


def test_shot_director_rhythm_compliance_rules_present():
    rules = _shot_director_source_event_rules()
    rhythm_rules = _shot_director_rhythm_match_rules()

    assert "不得重新判断整体节奏" in rules, "shot_director must not re-judge overall rhythm"
    assert "必须服从 atmosphere_strategy" in rules, "shot_director must obey atmosphere_strategy"
    assert "快慢" in rules, "rules must include tempo control"
    assert "停顿" in rules, "rules must include pause control"
    assert "卡断" in rules, "rules must include cut control"
    assert "反应归属" in rules, "rules must include reaction attribution"
    assert "尾帧承接" in rules, "rules must include tailframe continuity"
    assert "剧本事实" in rules, "rules must mention script facts"
    assert "台词原文" in rules, "rules must mention original dialogue"
    assert "动作道具连续性" in rules, "rules must mention action/prop continuity"
    assert "空间轴线安全" in rules, "rules must mention spatial axis safety"
    assert "后者优先" in rules, "rules must state script facts take priority over rhythm"
    assert "story_planner 给出的片段边界" in rhythm_rules, "rhythm rules must reference upstream instructions"
    assert "不得重新判断整体节奏" in rhythm_rules, "rhythm rules must not allow re-judging rhythm"


def test_shot_director_owns_shot_budget_after_story_planner_handoff():
    reveal_plan = _estimate_shot_director_coverage_plan(
        [
            "乔熙拿起书包，照片从夹层里掉出来。",
            "乔熙捡起照片，看清照片背后的日期。",
        ],
        planner_handoff="情绪曲线：忙乱后突然停住；必须保留照片看清和乔熙反应；弱拍可压缩。",
    )
    dialogue_plan = _estimate_shot_director_coverage_plan(
        [
            "商北琛让她解释昨晚的缺席。",
            "乔熙停住，低声说自己没有退路。",
        ],
        planner_handoff="高压对白后必须给听者受击反应，语义不能切断。",
    )
    action_plan = _estimate_shot_director_coverage_plan(
        [
            "闹钟响，乔熙一边接电话一边抓起小豆丁的外套。",
            "小豆丁在沙发上乱蹬腿，不肯把手伸进袖子。",
            "乔熙停住动作，蹲下哄她。",
        ],
        planner_handoff="前段急促动作叠压，后段短暂停住安抚。",
    )

    assert reveal_plan["effective_shots"] == "2-3"
    assert "信息可读" in reveal_plan["layout"]
    assert "不得早于文字/物件被看清" in reveal_plan["cut_timing"]
    assert dialogue_plan["effective_shots"] == "2-4"
    assert "听者反应" in dialogue_plan["layout"]
    assert "OS/J-cut/L-cut" in dialogue_plan["duration_logic"]
    assert action_plan["effective_shots"] == "2-4"
    assert "动作顶点" in action_plan["cut_timing"]


def test_story_planner_to_shot_director_twenty_episode_rhythm_coverage():
    cases = [
        ("晨间亲子", ["闹钟响，乔熙一边接电话一边抓起小豆丁的外套。", "小豆丁乱蹬腿，说不想上学。", "乔熙停住，蹲下哄她。", "照片从书包夹层掉出来。", "乔熙看清照片背后的日期。"]),
        ("办公室录音", ["乔熙推门进入办公室，所有人看向她。", "商北琛让她解释昨晚的缺席。", "乔熙把合同递到桌上。", "助理打开录音，昨晚的电话播放出来。", "会议室沉默。"]),
        ("医院诊断", ["母亲催乔熙别再查下去。", "诊断书从文件夹里露出来。", "乔熙看清诊断结果，手停住。", "手机震动打断沉默。", "陌生号码说已经知道真相。"]),
        ("校园欺负", ["小豆丁站在教室门口，不敢进去。", "同学把画本推到地上。", "乔熙蹲下捡画本，压住火气问老师。", "老师打开监控视频。", "班主任赶到，所有人安静。"]),
        ("婚礼闯入", ["婚礼交换戒指，宾客鼓掌。", "大门被推开，乔熙冲进来。", "她打开视频，昨晚的真相出现。", "新郎戒指掉在地上。", "女方父亲站起，现场沉默。"]),
        ("雨夜追逐", ["女主抱着包穿过巷子。", "追车灯光逼近，她躲进便利店后门。", "录音笔从包里滑出。", "嫌疑人推门进来，她把录音笔藏到货架后。", "警笛响起，店里所有人看向门口。"]),
        ("家宴亲鉴", ["父亲让乔熙给妹妹道歉。", "乔熙把亲子鉴定报告放到桌中央。", "众人看清报告，妹妹脸色变了。", "母亲突然倒下。", "救护车声音从窗外逼近。"]),
        ("电梯项链", ["商北琛挡在电梯门口，不让乔熙离开。", "乔熙低头避开他的视线。", "项链从她衣领里露出。", "回忆开始：他曾把同一条项链戴到她颈上。", "回到现实：乔熙后退半步。"]),
        ("餐厅误会", ["乔熙看到商北琛和陌生女人同桌。", "她忍着情绪转身要走。", "手机屏幕亮起，一张照片弹出来。", "她看见照片里的医院缴费单。", "新的短信解释对方只是医生。"]),
        ("奇幻钥匙", ["女孩在旧书店里找到锁住的门。", "门上的钥匙发光，书页自动翻开。", "回忆开始：她小时候听见母亲的声音。", "母亲把钥匙放进她掌心。", "回到现实：楼梯尽头传来脚步声。"]),
        ("长对白压迫", ["商北琛站在桌前说：你可以继续沉默，但董事会只看证据。", "乔熙握紧文件，没有立刻回答。", "他说：现在签字，至少还能保住孩子。", "乔熙抬头说：我不会再被你逼着选择。"]),
        ("母女和解", ["母亲把旧围巾放到乔熙面前。", "乔熙没有接，只问当年为什么离开。", "母亲沉默很久，说自己一直在医院门口。", "乔熙眼眶红了，慢慢坐下。"]),
        ("车祸目击", ["雨刷快速摆动，车灯照见路边的人影。", "乔熙猛踩刹车。", "手机从副驾滑落，通话还没挂断。", "她下车发现地上的项链。", "远处警笛逼近。"]),
        ("会议反转", ["董事宣布投票开始。", "乔熙拿出第二份合同。", "屏幕上出现真正签名时间。", "反对她的股东低头翻文件。", "商北琛没有说话。"]),
        ("直播翻车", ["主播对着镜头夸新品。", "弹幕突然刷出过敏照片。", "助理想关直播，乔熙按住他的手。", "乔熙对镜头承认问题并道歉。", "后台电话响个不停。"]),
        ("警局审讯", ["警察把录音笔放到桌上。", "嫌疑人笑着说那不是自己的声音。", "录音里传出他喊女主名字的片段。", "嫌疑人的笑僵住。", "门外有人敲门送来新证据。"]),
        ("产房门口", ["乔熙在产房门口来回走。", "护士冲出来问谁是家属。", "商北琛赶到，却被乔熙挡住。", "护士递出一张病危通知。", "商北琛终于停下。"]),
        ("楼梯对峙", ["乔熙抱着文件上楼。", "妹妹从楼梯口拦住她。", "两人拉扯时文件散落。", "亲子鉴定页滑到父亲脚边。", "父亲弯腰捡起文件。"]),
        ("葬礼真相", ["葬礼上所有人低头默哀。", "乔熙把录音放到遗像前。", "录音里死者说出遗嘱被改。", "亲属们纷纷抬头。", "律师从后排站起来。"]),
        ("海边告别", ["天快亮时，乔熙站在海边。", "商北琛把车钥匙递给她。", "乔熙没有接，只说孩子在等我。", "他收回手，点头。", "乔熙转身沿海堤离开。"]),
    ]

    rhythm_tasks: set[str] = set()
    for _title, lines in cases:
        units = _script_emotional_attention_units("\n".join(lines))
        assert units
        for start, end, reason in units:
            plan = _estimate_shot_director_coverage_plan(lines[start : end + 1], planner_handoff=reason)
            rhythm_tasks.add(plan["rhythm_task"])
            assert int(plan["effective_shots"].split("-")[-1]) <= 4
            assert plan["layout"]
            assert plan["cut_timing"]
            assert plan["duration_logic"]
            assert plan["action_direction"]

    assert "信息揭示/关键物件" in rhythm_tasks
    assert "高压对白/情绪反应" in rhythm_tasks
    assert "急促动作/压力上升" in rhythm_tasks
    assert "回忆/时空切层" in rhythm_tasks
