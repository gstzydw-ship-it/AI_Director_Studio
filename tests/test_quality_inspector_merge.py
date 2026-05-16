from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph_package import quality_inspector_impl as qi
from agents.director_graph_package.prompt_compiler_impl import _compiler_guard_report
from agents.director_graph_package.quality_inspector_impl import (
    quality_inspector_node,
)


def test_qc_router_delegates_retry_instruction_to_package_state_store(monkeypatch):
    captured = {}

    def fake_persist_update(state, update):
        captured["state"] = state
        captured["update"] = update
        return update

    monkeypatch.setattr(qi, "_persist_update", fake_persist_update)
    state = {
        "last_qc_status": "fail",
        "qc_retry_count": 0,
        "agent_outputs": {"quality_inspector": "retry this segment"},
    }

    update = qi.qc_router_node(state)

    assert update["qc_retry_count"] == 1
    assert update["revision_instruction"] == "retry this segment"
    assert update["step"] == "step_2_compile"
    assert captured["state"] is state


def test_route_after_qc_keeps_revision_compatibility_path_clear():
    assert qi.route_after_qc({"revision_instruction": "fix prompt"}) == "prompt_compiler"
    assert qi.route_after_qc({"revision_instruction": ""}) == "segment_complete"
    assert qi.route_after_qc({}) == "segment_complete"


def test_quality_inspector_flags_same_camera_continue_and_abstract_jargon(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    state = {
        "active_segment_index": 1,
        "agent_outputs": {
            "compiled_segment_1": """片段1｜办公室｜压迫对峙｜~8秒
【风格锚点】
冷硬现实。
【画幅锚点】
9:16竖屏。
【空间与首帧总控】
办公室内，桌面与门口可见。
【人物】
- 商北琛：总裁。
- 乔熙：助理。
【镜头序列】
0-4秒：商北琛胸部以上中近景，摄影机位于商北琛右前方30度、固定机位。商北琛说完后空气收紧，句尾仍坐在桌后。
4-8秒：同一机位继续，乔熙胸部以上中近景，摄影机位于乔熙左前方30度。乔熙低头，肩膀收紧，停在桌前。
【约束】
禁止字幕。""",
            "story_planner": "fragment_id: F01\nreaction_plan: 片段内承接受击反应",
            "shot_director": """fragment_id: F01
schema_version: shot_director_v2
fragment_intent: office pressure
reaction_coverage: listener reaction
continuity_anchor: office desk
shots:
  - shot_id: F01-S01
    coverage_role: speaker_start
    cut_reason: pressure_line
    companion_visibility: 乔熙画外
    tailframe_role: none
    dialogue_coverage: 商北琛起句，切乔熙听者反应
""",
        },
    }

    update = quality_inspector_node(state)
    report = update["agent_outputs"]["quality_inspector"]

    assert "PROMPT-NO-SAME-CAMERA-ABUSE-001" in report
    assert "PROMPT-VISIBLE-BODY-LANGUAGE-001" in report


def test_quality_inspector_rejects_local_fallback_v1_shot_contract(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    state = {
        "active_segment_index": 1,
        "agent_outputs": {
            "compiled_segment_1": "",
            "story_planner": "fragment_id: F01\nreaction_plan: none\nsource_script_events:\n  - Alex opens the door.\n",
            "shot_director": """fragment_id: F01
schema_version: shot_director_local_fallback_v1
fragment_task: local fallback beat
rhythm: readable action
shots:
  - shot_id: F01-S01
    duration: "0-3s"
    task: carry the door beat
    subject: Alex
    shot: stable medium shot
    action: Alex opens the door.
    dialogue: ""
    dialogue_coverage: none
    must_carry: Alex opens the door.
    cut_point: after the door opens
    continuity: keep screen direction
""",
        },
    }

    update = quality_inspector_node(state)
    report = update["agent_outputs"]["quality_inspector"]

    assert "输出来自旧本地兜底" in report
    assert "缺少 v1 字段 duration" not in report
    assert "缺少 v1 字段 camera" not in report
    assert "缺少 v1 字段 size" not in report
    assert "残留 v2 字段 dialogue_coverage" not in report


def test_quality_inspector_accepts_chinese_contract_and_compact_seedance_prompt(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    prompt = """片段1｜乔熙公寓客厅｜赶时间+安抚｜约5秒｜9:16

【画面基底】
风格锚点：真人短剧，清晨自然光。连续性状态契约：乔熙和小豆丁在沙发与茶几之间，手机和闹钟停在茶几上。参考素材只锁人物身份和客厅空间。

【镜头序列】
镜头1【2.5秒】【乔熙、小豆丁】双人半身关系景，茶几侧面固定视角。乔熙按停闹钟，把手机放回茶几边缘，转向小豆丁和衣服。（切镜时机：手机落稳后切至镜头2）
镜头2【2.5秒】【乔熙、小豆丁】中近景，从乔熙肩后看向小豆丁。乔熙蹲近小豆丁，说出"Sweetie. I'll get you some strawberry cake later, okay?"，小豆丁表情从抗拒变软，停顿后伸脚配合，反应落稳。

尾帧：乔熙蹲在沙发边，小豆丁伸脚配合，表情已经缓和，手机仍在茶几边缘。

【约束】
禁止字幕、屏幕文字、英文字幕、文字浮层、水印、logo、可读标牌、手机屏幕文字、文件可读字；Kiki不出镜。
"""
    planner = """- fragment_id: F01
  generation_unit_id: GU-F01-01
  source_script_events:
    - 乔熙按停闹钟，把手机放回茶几。
    - "乔熙：Sweetie. I'll get you some strawberry cake later, okay?"
    - 小豆丁伸脚配合。
  event_atom: 乔熙安抚小豆丁并让她伸脚配合。
  duration_target: 5s
  model_complexity_score: 1
  reference_needs: [identity_reference, scene_reference]
  tail_state_required: 乔熙蹲在沙发边，小豆丁伸脚配合，手机仍在茶几边缘。
  rhythm_operation_sheet_ref: F01
  shot_director_handoff: 孩子拒绝上学的反应在本段闭合。
"""
    director = """fragment_id: F01
schema_version: shot_director_coverage_v3
coverage_plan:
  template_id: COV-SD20-W1-RELATION-HOLD
  template_level: W1
  reference_need: identity_reference + scene_reference
template_plan:
  shots:
    - shot_id: F01-S01
      duration: 2.5秒
      coverage_role: relation_setup
      task: 建立手机、闹钟和亲子穿衣关系。
      subject: 乔熙、小豆丁
      shot: 双人半身关系景，茶几侧面固定视角
      action: 乔熙按停闹钟，把手机放回茶几边缘，转向小豆丁。
      dialogue: ''
      must_carry: 手机和闹钟停在茶几上。
      cut_reason: 手机状态落稳
      cut_point: 手机落稳后切出。
      continuity: 手机仍在茶几边缘，小豆丁仍在沙发边。
      tailframe_role: setup
      template_id: COV-SD20-W1-RELATION-HOLD
      template_level: W1
      model_complexity_score: 1
      reference_need: identity_reference + scene_reference
      tail_state: 手机仍在茶几边缘，小豆丁仍在沙发边。
    - shot_id: F01-S02
      duration: 2.5秒
      coverage_role: reaction_landing
      task: 完成草莓蛋糕安抚。
      subject: 乔熙、小豆丁
      shot: 中近景，从乔熙肩后看向小豆丁
      action: 乔熙蹲近小豆丁，小豆丁伸脚配合。
      dialogue: "Sweetie. I'll get you some strawberry cake later, okay?"
      must_carry: 小豆丁从拒绝转为配合。
      cut_reason: 反应闭合
      cut_point: 小豆丁伸脚后收束。
      continuity: 两人仍在沙发边，手机仍在茶几上。
      tailframe_role: bridge
      template_id: COV-SD20-W1-RELATION-HOLD
      template_level: W1
      model_complexity_score: 1
      reference_need: identity_reference + scene_reference
      tail_state: 乔熙蹲在沙发边，小豆丁伸脚配合，手机仍在茶几边缘。
guard_result: pass
tail_state: 乔熙蹲在沙发边，小豆丁伸脚配合，手机仍在茶几边缘。
"""

    update = quality_inspector_node(
        {
            "active_segment_index": 1,
            "segment_names": ["F01"],
            "agent_outputs": {
                "compiled_segment_1": prompt,
                "story_planner": planner,
                "shot_director": director,
            },
            "system_guard_report": "",
        }
    )

    assert "总体评级：pass" in update["agent_outputs"]["quality_inspector"]


def test_compiler_guard_accepts_compact_prompt_with_chinese_shot_assets():
    prompt = """片段1｜乔熙公寓客厅｜赶时间+安抚｜约5秒｜9:16

【画面基底】
风格锚点：真人短剧，清晨自然光。连续性状态契约：乔熙和小豆丁在沙发与茶几之间，手机和闹钟停在茶几上。参考素材只锁人物身份和客厅空间。

【镜头序列】
镜头1【2.5秒】【乔熙、小豆丁】双人半身关系景，茶几侧面固定视角。乔熙按停闹钟，把手机放回茶几边缘，转向小豆丁和衣服。（切镜时机：手机落稳后切至镜头2）
镜头2【2.5秒】【乔熙、小豆丁】中近景，从乔熙肩后看向小豆丁。乔熙蹲近小豆丁，说出"Sweetie. I'll get you some strawberry cake later, okay?"，小豆丁伸脚配合，画面停住。

尾帧：乔熙蹲在沙发边，小豆丁伸脚配合，手机仍在茶几边缘。

【约束】
禁止字幕、屏幕文字、英文字幕、文字浮层、水印、logo、可读标牌、手机屏幕文字、文件可读字；Kiki不出镜。
"""
    planner = """- fragment_id: F01
  generation_unit_id: GU-F01-01
  source_script_events:
    - "乔熙：Sweetie. I'll get you some strawberry cake later, okay?"
  event_atom: 乔熙安抚小豆丁。
  duration_target: 5s
  model_complexity_score: 1
  reference_needs: [identity_reference, scene_reference]
  tail_state_required: 小豆丁伸脚配合。
  rhythm_operation_sheet_ref: F01
  shot_director_handoff: 孩子拒绝上学的反应在本段闭合。
"""
    director = """fragment_id: F01
schema_version: shot_director_coverage_v3
coverage_plan:
  template_id: COV-SD20-W1-RELATION-HOLD
  template_level: W1
  reference_need: identity_reference + scene_reference
template_plan:
  shots:
    - shot_id: F01-S01
      duration: 2.5秒
      coverage_role: relation_setup
      task: 建立手机、闹钟和亲子穿衣关系。
      subject: 乔熙、小豆丁
      shot: 双人半身关系景，茶几侧面固定视角
      action: 乔熙按停闹钟，把手机放回茶几边缘，转向小豆丁。
      dialogue: ''
      must_carry: 手机和闹钟停在茶几上。
      cut_reason: 手机状态落稳
      cut_point: 手机落稳后切出。
      continuity: 手机仍在茶几边缘，小豆丁仍在沙发边。
      tailframe_role: bridge
      template_id: COV-SD20-W1-RELATION-HOLD
      template_level: W1
      model_complexity_score: 1
      reference_need: identity_reference + scene_reference
      tail_state: 手机仍在茶几边缘，小豆丁仍在沙发边。
guard_result: pass
tail_state: 手机仍在茶几边缘，小豆丁仍在沙发边。
"""

    assert _compiler_guard_report(prompt, planner, planner, director) == ""


def test_compiler_guard_rejects_overfragmented_life_pressure_prompt():
    prompt = """片段1｜乔熙公寓客厅｜赶时间+穿衣受阻｜约11秒｜9:16

【画面基底】
清晨公寓客厅，乔熙和小豆丁在沙发与茶几之间，手机和闹钟在茶几上，书包在右侧地面。

【镜头序列】
镜头1【2.2秒】【乔熙、小豆丁】双人半身关系景，茶几侧面固定视角。乔熙按停闹钟，把手机放回茶几边缘，转向沙发前的衣服。（切镜时机：乔熙转向小豆丁时切至镜头2）
镜头2【0.7秒】【乔熙的手、手机】局部近景，茶几侧面固定视角。手机停在茶几边缘，乔熙的手离开画面。（切镜时机：手机落稳后切至镜头3）
镜头3【2.0秒】【乔熙、小豆丁】半身关系景，从乔熙肩后看向小豆丁。乔熙扶住小豆丁套衣服，说出"Kiki, cover for me. I'll be right there!"，小豆丁缩回胳膊。（切镜时机：小豆丁缩手时切至镜头4）
镜头4【1.8秒】【小豆丁】中近景，同侧固定视角。小豆丁缩在沙发边，说出"I don't want to go to school!"。（切镜时机：拒绝台词落下后切至镜头5）
镜头5【2.6秒】【乔熙、小豆丁】双人半身关系景，沙发前略高视角。乔熙蹲近小豆丁，说出"Sweetie. I'll get you some strawberry cake later, okay?"，小豆丁停住。（切镜时机：小豆丁伸脚时切至镜头6）
镜头6【0.8秒】【小豆丁伸出的脚、衣服】膝下局部近景，沙发侧面固定视角。小豆丁把脚伸向衣服位置，乔熙的手停住接应。（切镜时机：小豆丁脚停到衣服旁后切至镜头7）
镜头7【2.0秒】【乔熙、书包、小豆丁】中景，沙发前同侧关系视角。乔熙转向右侧地面提起书包，小豆丁留在沙发边，尾帧停在乔熙手中书包。

【约束】
禁止字幕、水印、屏幕文字；Kiki不出镜。
"""
    script = """乔熙：Kiki, cover for me. I'll be right there!
小豆丁：I don't want to go to school!
乔熙：Sweetie. I'll get you some strawberry cake later, okay?
"""
    planner = """- 片段编号: F01
  片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
  承接要求: 孩子拒绝上学的反应在本段闭合。
"""
    director = """片段编号: F01
片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
节奏: 紧凑生活动作压力
"""

    report = _compiler_guard_report(prompt, script, planner, director)

    assert "镜头切分过碎" in report
    assert "1秒以下碎镜过多" in report


def test_compiler_guard_rejects_untested_seedance_coverage_template():
    prompt = """片段1｜办公室｜压迫｜约5秒｜9:16

【画面基底】
办公室内，A和B面对面站定。

【镜头序列】
镜头1【5秒】【A、B】双人半身关系景，固定机位。A停住看向B，B没有移动。

尾帧：两人仍面对面站定。

【约束】
禁止字幕。
"""
    planner = """- fragment_id: F01
  generation_unit: "core_visible_event=A confronts B; reaction_bridge=B holds; emotion_landing=B remains silent"
  model_complexity_score: 2
  required_reference_role: "identity_reference + scene_reference"
"""
    director = """fragment_id: F01
schema_version: shot_director_coverage_v3
coverage_plan:
  dramatic_task: pressure
template_plan:
  shots:
    - shot_id: F01-S01
      template_id: COV-CANDIDATE-001
      template_status: candidate
      duration: "5秒"
      task: pressure beat
      subject: A, B
      shot: 双人半身关系景
      action: A looks at B.
      dialogue: ""
      must_carry: pressure
      cut_point: tail state holds
      continuity: same room
"""

    report = _compiler_guard_report(prompt, "", planner, director)

    assert "SEEDANCE-COVERAGE-TEMPLATE-GATE-001" in report
    assert "candidate/untested" in report


def test_quality_inspector_rejects_r1_template_without_reference(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    prompt = """片段1｜走廊｜追逐｜约6秒｜9:16

【画面基底】
走廊内，A在画面中央。

【镜头序列】
镜头1【6秒】【A】单人中景，固定机位。A向前快步停住。

尾帧：A停在走廊中。

【约束】
禁止字幕。
"""
    planner = """- fragment_id: F01
  generation_unit: "core_visible_event=A moves fast; reaction_bridge=A stops; emotion_landing=A looks ahead"
  model_complexity_score: 3
  required_reference_role: "identity_reference + scene_reference"
"""
    director = """fragment_id: F01
schema_version: shot_director_coverage_v3
template_plan:
  shots:
    - shot_id: F01-S01
      template_id: COV-SD20-R1-FAST-CHASE
      template_status: R1
      duration: "6秒"
      task: fast chase
      subject: A
      shot: 单人中景
      action: A moves fast.
      dialogue: ""
      must_carry: fast movement
      cut_point: A stops
      continuity: same hallway
"""

    update = quality_inspector_node(
        {
            "active_segment_index": 1,
            "agent_outputs": {
                "compiled_segment_1": prompt,
                "story_planner": planner,
                "shot_director": director,
            },
        }
    )

    report = update["agent_outputs"]["quality_inspector"]
    assert "总体评级：fail" in report
    assert "R1 模板缺少视频参考" in report


def test_quality_inspector_rejects_overfragmented_life_pressure_prompt(monkeypatch):
    monkeypatch.setattr(qi, "_persist_update", lambda state, update: update)

    prompt = """片段1｜乔熙公寓客厅｜赶时间+穿衣受阻｜约11秒｜9:16

【画面基底】
清晨公寓客厅，乔熙和小豆丁在沙发与茶几之间，手机和闹钟在茶几上。

【镜头序列】
镜头1【2.2秒】【乔熙、小豆丁】双人半身关系景，茶几侧面固定视角。乔熙按停闹钟，把手机放回茶几边缘，转向沙发前的衣服。（切镜时机：乔熙转向小豆丁时切至镜头2）
镜头2【0.7秒】【乔熙的手、手机】局部近景，茶几侧面固定视角。手机停在茶几边缘，乔熙的手离开画面。（切镜时机：手机落稳后切至镜头3）
镜头3【2.0秒】【乔熙、小豆丁】半身关系景，从乔熙肩后看向小豆丁。乔熙扶住小豆丁套衣服，小豆丁缩回胳膊。（切镜时机：小豆丁缩手时切至镜头4）
镜头4【1.8秒】【小豆丁】中近景，同侧固定视角。小豆丁缩在沙发边，说出"I don't want to go to school!"。（切镜时机：拒绝台词落下后切至镜头5）
镜头5【2.6秒】【乔熙、小豆丁】双人半身关系景，沙发前略高视角。乔熙蹲近小豆丁，说出"Sweetie. I'll get you some strawberry cake later, okay?"，小豆丁停住。（切镜时机：小豆丁伸脚时切至镜头6）
镜头6【0.8秒】【小豆丁伸出的脚、衣服】膝下局部近景，沙发侧面固定视角。小豆丁把脚伸向衣服位置，乔熙的手停住接应。（切镜时机：小豆丁脚停到衣服旁后切至镜头7）
镜头7【2.0秒】【乔熙、书包、小豆丁】中景，沙发前同侧关系视角。乔熙转向右侧地面提起书包，小豆丁留在沙发边，尾帧停在乔熙手中书包。

【约束】
禁止字幕、水印、屏幕文字；Kiki不出镜。
"""
    planner = """- 片段编号: F01
  片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
  承接要求: 孩子拒绝上学的反应在本段闭合。
"""
    director = """片段编号: F01
片段任务: 清晨赶时间给小豆丁穿衣并安抚她上学。
节奏: 紧凑生活动作压力
镜头列表:
  - 镜头编号: F01-S01
    时长: 2秒
    镜头任务: 建立关系
    拍摄主体: 乔熙、小豆丁
    镜头: 双人半身关系景，茶几侧面固定视角
    画面动作: 乔熙按停闹钟，把手机放回茶几边缘。
    台词: ~
    必须承载: 手机和闹钟停在茶几上。
    切镜点: 手机落稳后切出。
    连续性: 两人仍在沙发与茶几之间。
"""

    update = quality_inspector_node(
        {
            "active_segment_index": 1,
            "segment_names": ["F01"],
            "agent_outputs": {
                "compiled_segment_1": prompt,
                "story_planner": planner,
                "shot_director": director,
            },
            "system_guard_report": "",
        }
    )

    report = update["agent_outputs"]["quality_inspector"]

    assert "总体评级：fail" in report
    assert "镜头切分过碎" in report
    assert "1秒以下碎镜过多" in report
