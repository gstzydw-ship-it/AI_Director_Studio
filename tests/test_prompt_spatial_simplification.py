import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.director_graph import _compiler_guard_report, _compress_director_for_compiler, prompt_compiler_node


def test_compiler_guard_flags_overloaded_space_control():
    prompt = """片段1｜集团大堂电梯口｜入场｜~14秒

【风格锚点】
冷峻商务现实风。

【画幅锚点】
9:16竖屏。

【空间与首帧总控】
首帧是集团大堂中轴通向尽头电梯，众员工分布在中轴两侧，严飞位于电梯前侧，商北琛仍在南侧入口画外。
轴线固定为大堂入口到电梯的纵深方向，左侧员工、右侧员工、前景肩线、后景电梯、远端门框都必须清楚。
光线保持明亮冷调自然光与顶光。
门框边缘、近侧侧边、远端尽头、画面左侧和画面右侧都要解释清楚。

【时间轴】
0-3秒：众员工群体中景，正面眼平，固定机位。员工先后停步，看向入口方向，到结束时中间通道让空。

【约束】
禁止字幕。
"""

    report = _compiler_guard_report(prompt, "", "", "")

    assert "空间与首帧总控过载" in report


def test_compiler_guard_flags_timeline_spatial_direction_overload():
    prompt = """片段1｜集团大堂电梯口｜入场｜~14秒

【风格锚点】
冷峻商务现实风。

【画幅锚点】
9:16竖屏。

【空间与首帧总控】
集团大堂通向电梯，众员工分列通道两侧，冷调办公光。

【时间轴】
0-3秒：众员工群体中景，正面眼平，固定机位。前景员工、中景员工、后景电梯、画面左侧队列、画面右侧队列、远端门框同时交代，员工先后停步并看向入口方向，到结束时中间通道让空。

【约束】
禁止字幕。
"""

    report = _compiler_guard_report(prompt, "", "", "")

    assert "空间方位词过载" in report


def test_director_context_compresses_six_spatial_fields_into_one_geom_line():
    fragment = """- fragment_id: F01
  main_shots:
    - shot_id: F01-S01
      subject: 商北琛
      shot_size: 半身中景
      camera_basis: scene_fixed
      camera_scene_position: lobby_axis
      camera_looks_toward: toward_elevator
      subject_position: before_elevator
      subject_facing: toward_elevator
      visible_landmarks: elevator_door
      dialogue_coverage: none
"""

    compressed = _compress_director_for_compiler(fragment)

    assert "geom: 机位:scene_fixed lobby_axis →toward_elevator | 主体:before_elevator 朝toward_elevator | 锚点:elevator_door" in compressed
    assert "camera_basis:" not in compressed
    assert "camera_scene_position:" not in compressed
    assert "camera_looks_toward:" not in compressed
    assert "subject_position:" not in compressed
    assert "subject_facing:" not in compressed
    assert "visible_landmarks:" not in compressed


def test_prompt_compiler_prompt_teaches_successful_shot_chain(monkeypatch):
    captured = {}

    def fake_build_system_prompt(role_description, agent_name, context_hint=""):
        captured["role_description"] = role_description
        return role_description, {}

    def fake_call_llm_with_mcp(system_prompt, user_prompt, **_kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return """片段1｜天御集团大堂｜权威入场｜~14秒

【风格锚点】
都市职场冷感现实风。

【画幅锚点】
9:16竖屏。

【空间与首帧总控】
集团大堂通向电梯，员工分列通道两侧，冷白商务光。

【时间轴】
0-4秒：商北琛皮鞋局部特写，低机位贴地轻跟。皮鞋踩实地面后，镜头上摇到商北琛半身中景，正面眼平跟拍，他目光扫过两侧人群。
4-7秒：镜头切至商北琛过肩半身景，严飞肩线轻虚，说出“Welcome, Mr. Pierce.” 商北琛眉头微皱，不接话，视线掠过严飞。

【约束】
禁止字幕。

片段1 prompt 已输出。
请生成视频后，上传：

片段1的尾帧截图
当前人物位置关系（若有变化）

我将基于实际尾帧继续输出片段2。
"""

    monkeypatch.setattr("agents.director_graph.build_system_prompt", fake_build_system_prompt)
    monkeypatch.setattr("agents.director_graph.call_llm_with_mcp", fake_call_llm_with_mcp)
    monkeypatch.setattr("agents.director_graph._record_knowledge_metadata", lambda state, *_args, **_kwargs: state.get("knowledge_metadata", {}))
    monkeypatch.setattr("agents.director_graph._persist_update", lambda state, update: {**state, **update})

    state = {
        "aspect_ratio": "9:16",
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "script": "商北琛进入大堂。严飞：Welcome, Mr. Pierce.",
        "agent_outputs": {
            "story_planner": "fragment_id: F01\nsource_script_events:\n- 商北琛进入大堂。\n- 严飞：Welcome, Mr. Pierce.\nreaction_plan: 冷处理问候。",
            "shot_director": "fragment_id: F01\nmain_shots:\n- shot_id: F01-S01\n  subject: 商北琛\n  camera_basis: subject_relative\n  camera_scene_position: lobby_axis\n  camera_looks_toward: elevator\n  subject_position: lobby_axis\n  subject_facing: toward_elevator\n  visible_landmarks: employee_lines\n  dialogue_coverage: none",
        },
    }

    prompt_compiler_node(state)

    assert "成功案例镜头链条" in captured["system_prompt"]
    assert "局部动作或人物半身建立节奏" in captured["system_prompt"]
    assert "过肩或双人关系景" in captured["system_prompt"]
    assert "命令句用半身景承载" in captured["system_prompt"]
    assert "镜头机位切换 + 人物动作表情 + 台词落点" in captured["system_prompt"]
    assert "单段内禁止写“反打至/反打镜头”" in captured["system_prompt"]
    assert "同侧听者反应" in captured["system_prompt"]
