from __future__ import annotations

from pathlib import Path

from agents.director_graph_package import nodes
from agents.director_graph_package import helpers
from agents.director_graph_package import legacy_impl
from agents.director_graph_package import prompt_compiler_impl
from agents.director_graph_package import shot_director_impl
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

    monkeypatch.setattr(prompt_compiler_impl, "build_system_prompt", fake_build_system_prompt)

    state = {
        "active_segment_index": 1,
        "current_segment_index": 1,
        "total_segments": 1,
        "segment_names": ["F05"],
        "script": "商北琛：你没有资格。\n严飞：这不是你说了算的。",
        "aspect_ratio": "16:9",
        "reference_image_manifest": [
            {
                "label": "@图片1",
                "filename": "shangbeichen.png",
                "role": "character",
                "purpose": "商北琛人物参考图",
            },
            {
                "label": "@图片2",
                "filename": "office.png",
                "role": "scene",
                "purpose": "办公室场景参考图",
            },
            {
                "label": "@图片3",
                "filename": "seg00_tail.jpg",
                "role": "previous_segment_tail_frame",
                "purpose": "上一段实际尾帧",
            },
        ],
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
                "  continuity_context: 本片段是一段对峙升级；商北琛、严飞在同一办公室空间内；单人镜只改变拍摄主体，不代表另一人离开。\n"
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
                "      coverage_role: 承载商北琛压迫发言\n"
                "      cut_reason: 台词落点后切到听者受击反应\n"
                "      companion_visibility: 严飞保持在办公桌对面画外右侧\n"
                "      state_delta: 商北琛完成施压，严飞进入受击状态\n"
                "      tailframe_role: 交给严飞反应镜头承接\n"
            ),
        },
    }

    result = prompt_compiler_impl.prompt_compiler_node(state)
    compiled = result["agent_outputs"]["compiled_segment_1"]

    assert "compiled_segment_1" in result["agent_outputs"]
    assert "【风格锚点】" in compiled
    assert "【画幅锚点】" in compiled
    assert "【空间与首帧总控】" in compiled
    assert "【人物】" in compiled
    assert "【镜头序列】" in compiled
    assert "【约束】" in compiled
    assert "商北琛、严飞在同一办公室空间内" in compiled
    assert "单人镜只改变拍摄主体" in compiled
    assert "镜头1【0-3秒】【商北琛】" in compiled
    assert "承载商北琛压迫发言" in compiled
    assert "严飞保持在办公桌对面画外右侧" in compiled
    assert "交给严飞反应镜头承接" in compiled
    assert "【参考图说明】" not in compiled
    assert "@图片" not in compiled
    assert "严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌" in compiled
    assert "fragment_id: F01" not in compiled


def test_prompt_compiler_uses_deterministic_shot_director_handoff(monkeypatch) -> None:
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
    assert "local fallback reason" not in outputs["compiled_segment_1"]
    assert "prompt_compiler_fallback_seg01" not in outputs
    assert result["step"] == "step_5_inspect"


def test_prompt_compiler_local_fallback_scrubs_internal_english_terms() -> None:
    compiled = prompt_compiler_impl._build_local_compiled_prompt(
        segment_index=1,
        total_segments=2,
        aspect_label="9:16竖屏",
        planner_segment=(
            "- fragment_id: F01\n"
            "  source_script_events:\n"
            "    - 乔熙按掉闹钟，把手机按成免提放在玻璃茶几边。\n"
            "    - 小豆丁扯住乔熙衣角。\n"
        ),
        director_segment=(
            "- fragment_id: F01\n"
            "  shots:\n"
            "    - shot_id: F01-S01\n"
            "      duration: 0-3s\n"
            "      task: 建立闹钟被按掉、电话免提和两人位置关系\n"
            "      subject: 乔熙、小豆丁\n"
            "      shot: vertical medium relationship shot, stable camera, clear blocking\n"
            "      action: 乔熙按掉闹钟，把手机按成免提放在玻璃茶几边。\n"
            "      dialogue: \"Sunny, wake up.\"\n"
            "      must_carry: 闹钟停下，手机免提放在玻璃茶几边，小豆丁在乔熙身旁。\n"
            "      cut_point: after the first readable action lands\n"
            "      continuity: preserve established positions, props and eye-lines from the approved upstream plan\n"
            "      coverage_role: 建立闹钟、免提电话和两人位置关系\n"
            "      cut_reason: 闹钟停下且手机放稳后切到孩子动作\n"
            "      companion_visibility: 小豆丁始终在乔熙身旁画面边缘\n"
            "      state_delta: 手机从闹钟状态变为免提通话状态\n"
            "      tailframe_role: 把乔熙和小豆丁同处茶几旁的位置交给下一镜\n"
            "    - shot_id: F01-S02\n"
            "      duration: 3-6s\n"
            "      task: 承接孩子拉衣角动作\n"
            "      subject: 乔熙、小豆丁\n"
            "      shot: medium close relationship shot, stable camera, same screen direction\n"
            "      action: 小豆丁扯住乔熙衣角。\n"
            "      dialogue: \"Come on, baby.\"\n"
            "      must_carry: 小豆丁动作落点清楚，乔熙和孩子仍在同一侧轴线内。\n"
            "      cut_point: after the reaction or information beat is visible\n"
            "      continuity: end on a readable tail frame for the next segment handoff\n"
        ),
        script_context="乔熙按掉闹钟，把手机按成免提放在玻璃茶几边。",
        tail_frame_memory=(
            "bridge_available: false\n"
            "reason: \"No visual bridge is available; compile the next segment from its own scene and shot assets.\"\n"
            "bridge_strategy: direct_cut\n"
        ),
        reference_context="@图片1 集团门口.png：自动匹配场景参考图；补充说明：auto: 集团门口",
        failure=RuntimeError("LLM gateway failed"),
    )

    assert "竖屏中景双人关系镜头" in compiled
    assert "固定机位" in compiled
    assert "【镜头序列】" in compiled
    assert "【参考图说明】" not in compiled
    assert "【风格锚点】" in compiled
    assert "参考图只作为隐性约束" in compiled
    assert "镜头1【0-3秒】【乔熙、小豆丁】" in compiled
    assert "建立闹钟被按掉、电话免提和两人位置关系" in compiled
    assert "Sunny, wake up." in compiled
    assert "闹钟停下，手机免提放在玻璃茶几边，小豆丁在乔熙身旁" in compiled
    assert "本镜负责：建立闹钟、免提电话和两人位置关系" in compiled
    assert "同场关系保持：小豆丁始终在乔熙身旁画面边缘" in compiled
    assert "本镜新增变化：手机从闹钟状态变为免提通话状态" in compiled
    assert "尾帧交给：把乔熙和小豆丁同处茶几旁的位置交给下一镜" in compiled
    assert "闹钟停下且手机放稳后切到孩子动作" in compiled
    assert "切至镜头2" in compiled
    assert "无可用上一段尾帧" in compiled
    assert "relationship shot" not in compiled
    assert "stable camera" not in compiled
    assert "No visual bridge" not in compiled
    assert "approved upstream" not in compiled
    assert "local fallback reason" not in compiled
    assert "task:" not in compiled
    assert "must_carry:" not in compiled
    assert "coverage_role:" not in compiled
    assert "tailframe_role:" not in compiled
    assert "严禁出现任何文字、字幕、水印、logo、屏幕文字或可读标牌" in compiled


def test_prompt_compiler_local_fallback_uses_planner_target_duration() -> None:
    compiled = prompt_compiler_impl._build_local_compiled_prompt(
        segment_index=1,
        total_segments=1,
        aspect_label="9:16竖屏",
        planner_segment=(
            "- 片段编号: F01\n"
            "  目标时长: 5-6秒\n"
            "  施工剧本原文事件:\n"
            "    - 闹钟响，乔熙一把按掉。\n"
            "    - 乔熙把手机夹在肩与耳之间，腾出双手去够小豆丁的外套。\n"
        ),
        director_segment=(
            "片段编号: F01\n"
            "镜头列表:\n"
            "  - 镜头编号: F01-S01\n"
            "    时长: 2秒\n"
            "    镜头任务: 承载闹钟和手机动作\n"
            "    拍摄主体: 乔熙\n"
            "    镜头: 中景固定机位\n"
            "    画面动作: 乔熙一把按掉闹钟并夹住手机。\n"
            "  - 镜头编号: F01-S02\n"
            "    时长: 3.5秒\n"
            "    镜头任务: 承载外套和小豆丁抗拒\n"
            "    拍摄主体: 乔熙、小豆丁\n"
            "    镜头: 双人关系景\n"
            "    画面动作: 乔熙急忙够外套，小豆丁乱蹬。\n"
        ),
        script_context="闹钟响，乔熙一把按掉。",
        tail_frame_memory="",
        reference_context="",
        failure=RuntimeError("LLM gateway failed"),
    )

    assert compiled.startswith("片段1｜本地兜底编译｜已确认事件｜5-6秒")
    assert "｜~9秒" not in compiled


def test_seedance_reference_prompt_block_labels_reference_roles() -> None:
    block = prompt_compiler_impl._seedance_reference_prompt_block(
        {
            "reference_image_manifest": [
                {"label": "@图片1", "filename": "hero.png", "role": "character", "purpose": "乔熙人物参考"},
                {"label": "@图片2", "filename": "car.jpg", "role": "scene", "purpose": "车后排场景"},
                {
                    "label": "@图片3",
                    "filename": "tail.jpg",
                    "role": "previous_segment_tail_frame",
                    "purpose": "上一段尾帧",
                },
            ]
        }
    )

    assert "@图片1 是人物参考图" in block
    assert "面部形象、发型、服装" in block
    assert "@图片2 是场景参考图" in block
    assert "空间结构、固定家具/道具、光线方向" in block
    assert "@图片3 是上一段实际尾帧/抽帧参考图" in block
    assert "本段首帧承接" in block


def test_seedance_reference_prompt_block_does_not_treat_scene_layout_as_tail_frame() -> None:
    block = prompt_compiler_impl._seedance_reference_prompt_block(
        {
            "reference_image_manifest": [
                {
                    "label": "@图片12",
                    "filename": "scene_layout_01.png",
                    "role": "scene_layout",
                    "type": "scene_layout",
                    "purpose": "集团门口场景俯视布局图；运动过程由片段出入场状态和视频尾帧承接",
                },
            ]
        }
    )

    assert "@图片12 是场景参考图" in block
    assert "上一段实际尾帧/抽帧参考图" not in block


def test_seedance_reference_prompt_block_filters_to_current_segment_context() -> None:
    state = {
        "reference_image_manifest": [
            {"label": "@图片1", "filename": "集团门口.png", "role": "scene", "purpose": "自动匹配场景参考图：集团门口"},
            {"label": "@图片2", "filename": "乔熙公寓-客厅.png", "role": "scene", "purpose": "自动匹配场景参考图：乔熙公寓-客厅"},
            {"label": "@图片3", "filename": "商北琛.png", "role": "character", "purpose": "商北琛人物参考"},
            {
                "label": "@图片4",
                "filename": "scene_layout_02.png",
                "role": "scene_layout",
                "type": "scene_layout",
                "name": "@图片2｜乔熙公寓-客厅.png｜自动匹配场景参考图：乔熙公寓-客厅",
                "purpose": "乔熙公寓-客厅场景俯视布局图；运动过程由片段出入场状态和视频尾帧承接",
            },
            {
                "label": "@图片5",
                "filename": "seg01_tail.jpg",
                "role": "previous_segment_tail_frame",
                "purpose": "上一段尾帧",
            },
        ]
    }

    block = prompt_compiler_impl._seedance_reference_prompt_block(
        state,
        segment_index=1,
        current_context="片段1｜乔熙公寓｜闹钟铃响。场景：乔熙公寓-客厅。主体：闹钟。",
    )

    assert "@图片2 是场景参考图" in block
    assert "@图片4 是场景参考图" in block
    assert "集团门口" not in block
    assert "商北琛" not in block
    assert "上一段实际尾帧/抽帧参考图" not in block


def test_shot_director_local_fallback_uses_chinese_director_language() -> None:
    fallback = shot_director_impl._build_local_shot_director_fallback(
        fragment_id="F01",
        fragment_planner_output=(
            "- fragment_id: F01\n"
            "  source_script_events:\n"
            "    - 乔熙按掉闹钟。\n"
            "    - 小豆丁扯住乔熙衣角。\n"
        ),
        script="乔熙按掉闹钟。小豆丁扯住乔熙衣角。",
        aspect_ratio="9:16",
        failure=RuntimeError("shot director failed"),
    )

    assert "竖屏中景双人关系镜头" in fallback
    assert "固定机位" in fallback
    assert "第一个可读动作落点后" in fallback
    assert "relationship shot" not in fallback
    assert "stable camera" not in fallback
    assert "approved upstream" not in fallback


def test_shot_director_local_fallback_skips_planner_metadata_events() -> None:
    fallback = shot_director_impl._build_local_shot_director_fallback(
        fragment_id="F01",
        fragment_planner_output=(
            "- fragment_id: F01\n"
            "  source_script_events:\n"
            "    - 1-1 晨/内/乔熙公寓\n"
            "    - 人物：乔熙、小豆丁\n"
            "    - 【特写-闹钟：7:30】\n"
            "    - 【音效：闹钟铃响】\n"
            "    - ▲闹钟响了三声，乔熙一巴掌拍灭。\n"
            "    - 乔熙：Kiki, cover for me. I'll be right there!\n"
            "    - ▲小豆丁整个身子一扭，从半套上的校服里滑出去，缩到床角。\n"
        ),
        script="人物：乔熙、小豆丁\n闹钟响了三声，乔熙一巴掌拍灭。",
        aspect_ratio="9:16",
        failure=RuntimeError("shot director failed"),
    )

    assert '画面动作: "1-1 晨/内/乔熙公寓"' not in fallback
    assert '画面动作: "人物：乔熙、小豆丁"' not in fallback
    assert '画面动作: "特写-闹钟：7:30"' not in fallback
    assert "闹钟响了三声，乔熙一巴掌拍灭" in fallback
    assert "Kiki, cover for me" in fallback
    assert "小豆丁整个身子一扭" in fallback


def test_prompt_compiler_handles_chinese_shot_director_fallback(monkeypatch) -> None:
    def fail_call_llm(*_args, **_kwargs):
        raise RuntimeError("LLM gateway failed")

    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fail_call_llm)
    monkeypatch.setattr(
        prompt_compiler_impl,
        "_persist_update",
        lambda state, update: {**dict(state), **dict(update)},
    )

    planner_output = (
        "- fragment_id: F01\n"
        "  source_script_events:\n"
        "    - 乔熙按掉闹钟。\n"
        "    - 小豆丁扯住乔熙衣角。\n"
    )
    shot_fallback = shot_director_impl._build_local_shot_director_fallback(
        fragment_id="F01",
        fragment_planner_output=planner_output,
        script="乔熙按掉闹钟。小豆丁扯住乔熙衣角。",
        aspect_ratio="9:16",
        failure=RuntimeError("shot director failed"),
    )

    result = prompt_compiler_impl.prompt_compiler_node(
        {
            "active_segment_index": 1,
            "current_segment_index": 1,
            "total_segments": 1,
            "segment_names": ["F01"],
            "script": "乔熙按掉闹钟。小豆丁扯住乔熙衣角。",
            "aspect_ratio": "9:16",
            "agent_outputs": {
                "story_planner": planner_output,
                "shot_director": shot_fallback,
            },
        }
    )

    compiled = result["agent_outputs"]["compiled_segment_1"]
    assert "竖屏中景双人关系镜头" in compiled
    assert "固定机位" in compiled
    assert "台词直接嵌入动作：~" not in compiled
    assert "relationship shot" not in compiled
    assert "local fallback reason" not in compiled


def test_prompt_compiler_accepts_legacy_local_shot_fallback_marker(monkeypatch) -> None:
    def fail_call_llm(*_args, **_kwargs):
        raise RuntimeError("LLM gateway failed")

    monkeypatch.setattr(prompt_compiler_impl, "call_llm", fail_call_llm)
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
