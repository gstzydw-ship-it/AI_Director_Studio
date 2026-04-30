"""分段清除辅助函数的单元测试。

对应改造：
  - ui/app.py
    * _clear_segment_and_downstream(state, segment_index) —— 新增：清除指定段及其后续
    * _clear_previous_segment_in_state(state) —— 重构：改为调用上面的辅助

运行：
  cd AI_Director_Studio
  python -m pytest tests/test_clear_segment.py -v
"""

from __future__ import annotations

import os
import sys
import types
import importlib.util

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _module_missing(name: str) -> bool:
    return name not in sys.modules and importlib.util.find_spec(name) is None


# --- 重依赖打桩：让 ui.app 在测试环境里能被 import -----------------------------

class _FakeFastAPI:
    def __init__(self, *a, **kw):
        self.title = kw.get("title", "")
        self.version = kw.get("version", "")

    def mount(self, *a, **kw):
        pass

    def _decorator(self, *a, **kw):
        def wrap(fn):
            return fn
        return wrap

    get = post = put = delete = patch = _decorator

    def on_event(self, *a, **kw):
        return lambda f: f

    def add_middleware(self, *a, **kw):
        pass


def _form_default(default=..., *a, **kw):
    # fastapi.Form(...) 在函数签名里用作默认值；测试不跑 HTTP 路由，直接返回原值或 None
    return default if default is not ... else None


def _file_default(default=..., *a, **kw):
    return default if default is not ... else None


class _FakeStaticFiles:
    def __init__(self, *a, **kw):
        pass


class _FakeJinja2Templates:
    def __init__(self, *a, **kw):
        pass

    def TemplateResponse(self, *a, **kw):  # noqa: N802
        return None


if _module_missing("fastapi"):
    _stub_module(
        "fastapi",
        FastAPI=_FakeFastAPI,
        Request=object,
        UploadFile=object,
        File=_file_default,
        Form=_form_default,
    )
    _stub_module(
        "fastapi.responses",
        HTMLResponse=lambda *a, **kw: None,
        JSONResponse=lambda *a, **kw: None,
        FileResponse=lambda *a, **kw: None,
    )
    _stub_module("fastapi.staticfiles", StaticFiles=_FakeStaticFiles)
    _stub_module("fastapi.templating", Jinja2Templates=_FakeJinja2Templates)


if _module_missing("PIL"):
    _stub_module(
        "PIL",
        Image=types.SimpleNamespace(),
        ImageOps=types.SimpleNamespace(),
        UnidentifiedImageError=Exception,
    )
    _stub_module("PIL.Image", open=lambda *_a, **_kw: None)


if _module_missing("uvicorn"):
    _stub_module("uvicorn", run=lambda *a, **kw: None)


# agents.* 是 ui.app 真实依赖，这里只 stub 用到的几个符号即可
if False and "agents" not in sys.modules:
    _stub_module("agents")
if False and "agents.knowledge_base" not in sys.modules:
    _stub_module(
        "agents.knowledge_base",
        build_vectordb=lambda *_a, **_kw: None,
        load_config=lambda: {"ui": {}, "llm": {}, "vectordb": {}, "agent_models": {}},
    )
if False and "agents.request_context" not in sys.modules:
    import contextlib

    @contextlib.contextmanager
    def _noop_scope(*_a, **_kw):
        yield None

    _stub_module("agents.request_context", request_scope=_noop_scope)
if False and "agents.utils" not in sys.modules:
    _stub_module("agents.utils", COMFLY_BASE_URL="https://example.invalid/v1")


# director_graph 顶部的间接依赖（防止 agents.knowledge_base 存根被其他 import 绕过）
if False and "langgraph" not in sys.modules:
    _stub_module("langgraph")
    _stub_module("langgraph.checkpoint")
    _stub_module("langgraph.checkpoint.sqlite", SqliteSaver=object)
    _stub_module(
        "langgraph.graph",
        END="__end__",
        START="__start__",
        StateGraph=object,
    )
    _stub_module("langgraph.types", Command=object, interrupt=lambda *_a, **_kw: None)
if False and "numpy" not in sys.modules:
    _stub_module("numpy")
if False and "openai" not in sys.modules:
    _stub_module("openai", OpenAI=object)


from ui.app import (  # noqa: E402
    _clear_previous_segment_in_state,
    _clear_segment_and_downstream,
    _compiled_prompt_result,
    _previous_generated_segment_index,
)


# ---------------------------------------------------------------------------
# 构造一个"已跑到第 3 段"的 state 作为通用 fixture
# ---------------------------------------------------------------------------

def _make_state(total: int = 4, generated_up_to: int = 3) -> dict:
    outputs: dict = {}
    for i in range(1, generated_up_to + 1):
        outputs[f"compiled_segment_{i}"] = f"Prompt for segment {i}"
        outputs[f"quality_inspector_segment_{i}"] = f"QC report for segment {i}"
    # prompt_compiler / quality_inspector 指向最近一段（符合运行时实际写入方式）
    outputs["prompt_compiler"] = outputs.get(f"compiled_segment_{generated_up_to}", "")
    outputs["quality_inspector"] = outputs.get(f"quality_inspector_segment_{generated_up_to}", "")
    # 模拟全局规划产出
    outputs["scene_analyst"] = "全局场景分析"
    outputs["story_planner"] = "全局结构"
    outputs["shot_director"] = "全局镜头"

    return {
        "status": "waiting_for_user_input",
        "step": "step_3_direct",
        "message": "等待上传第三段视频",
        "result": _compiled_prompt_result(outputs),
        "error": "",
        "total_segments": total,
        "current_segment_index": generated_up_to + 1 if generated_up_to < total else generated_up_to,
        "agent_outputs": outputs,
        "active_segment_index": generated_up_to,
        "tail_frame_analysis": "已抽取尾帧",
        "system_guard_report": "xxx",
        "qc_retry_count": 2,
        "revision_instruction": "旧的修订指令",
        "last_qc_status": "pass",
    }


# ---------------------------------------------------------------------------
# _clear_segment_and_downstream
# ---------------------------------------------------------------------------

class TestClearSegmentAndDownstream:

    def test_clears_middle_segment_and_all_after(self):
        """从第 2 段起清除，应该把 2、3 的编译产出一起删掉。"""
        state = _make_state(total=4, generated_up_to=3)
        ok, cleared_idx, msg = _clear_segment_and_downstream(state, 2)
        assert ok is True
        assert cleared_idx == 2
        outputs = state["agent_outputs"]
        # 片段 1 保留
        assert "compiled_segment_1" in outputs
        assert "quality_inspector_segment_1" in outputs
        # 片段 2、3 被清掉
        assert "compiled_segment_2" not in outputs
        assert "quality_inspector_segment_2" not in outputs
        assert "compiled_segment_3" not in outputs
        assert "quality_inspector_segment_3" not in outputs
        # current_segment_index 回到 2
        assert state["current_segment_index"] == 2
        # 状态复位
        assert state["status"] == "waiting_for_user_input"
        assert state["qc_retry_count"] == 0
        assert state["revision_instruction"] == ""
        # message 说明清了 2 段
        assert "及其后" in msg or "片段 2" in msg

    def test_clears_only_last_segment_when_target_is_last(self):
        """清除最后一段时，只清这一段，没有后续。"""
        state = _make_state(total=4, generated_up_to=3)
        ok, cleared_idx, _ = _clear_segment_and_downstream(state, 3)
        assert ok is True
        outputs = state["agent_outputs"]
        assert "compiled_segment_2" in outputs
        assert "compiled_segment_3" not in outputs
        assert "quality_inspector_segment_3" not in outputs
        assert state["current_segment_index"] == 3

    def test_clears_all_when_target_is_first(self):
        """从第 1 段起清除，整个已编译列表都应被清空。"""
        state = _make_state(total=4, generated_up_to=3)
        ok, _, _ = _clear_segment_and_downstream(state, 1)
        assert ok is True
        outputs = state["agent_outputs"]
        for i in range(1, 4):
            assert f"compiled_segment_{i}" not in outputs
            assert f"quality_inspector_segment_{i}" not in outputs
        # prompt_compiler / quality_inspector 也应被移除（没有上一段可回落）
        assert "prompt_compiler" not in outputs
        assert "quality_inspector" not in outputs
        # 全局规划保留
        assert outputs.get("scene_analyst") == "全局场景分析"

    def test_prompt_compiler_falls_back_to_prior_segment(self):
        """清除第 3 段后，prompt_compiler 应指向第 2 段的 Prompt。"""
        state = _make_state(total=4, generated_up_to=3)
        _clear_segment_and_downstream(state, 3)
        outputs = state["agent_outputs"]
        assert outputs["prompt_compiler"] == "Prompt for segment 2"
        assert outputs["quality_inspector"] == "QC report for segment 2"

    def test_returns_false_when_target_below_one(self):
        state = _make_state()
        ok, _, msg = _clear_segment_and_downstream(state, 0)
        assert ok is False
        assert "必须" in msg or ">=" in msg

    def test_returns_false_when_target_beyond_total(self):
        state = _make_state(total=4, generated_up_to=3)
        ok, _, msg = _clear_segment_and_downstream(state, 10)
        assert ok is False
        assert "超出" in msg

    def test_returns_false_when_nothing_to_clear(self):
        """目标段及之后都没有编译产出时返回 False。"""
        state = _make_state(total=4, generated_up_to=2)
        # 清第 4 段（还没生成过）
        ok, _, msg = _clear_segment_and_downstream(state, 4)
        assert ok is False
        assert "暂无" in msg or "没有" in msg

    def test_result_is_recomputed_from_remaining_segments(self):
        """被清除后，state['result'] 应只包含保留段的 Prompt。"""
        state = _make_state(total=4, generated_up_to=3)
        _clear_segment_and_downstream(state, 2)
        assert "Prompt for segment 1" in state["result"]
        assert "Prompt for segment 2" not in state["result"]
        assert "Prompt for segment 3" not in state["result"]

    def test_preserves_global_planner_outputs(self):
        """不应清掉全局 Agent 产出（scene_analyst / story_planner / shot_director）。"""
        state = _make_state(total=4, generated_up_to=3)
        _clear_segment_and_downstream(state, 2)
        outputs = state["agent_outputs"]
        assert outputs["scene_analyst"] == "全局场景分析"
        assert outputs["story_planner"] == "全局结构"
        assert outputs["shot_director"] == "全局镜头"

    def test_resets_per_segment_flags(self):
        state = _make_state(total=4, generated_up_to=3)
        _clear_segment_and_downstream(state, 2)
        assert "active_segment_index" not in state
        assert "tail_frame_analysis" not in state
        assert "system_guard_report" not in state
        assert state["qc_retry_count"] == 0
        assert state["revision_instruction"] == ""
        assert state["last_qc_status"] == ""
        assert state["last_cleared_segment"] == 2

    def test_idempotent_on_repeated_call(self):
        """重复清同一段：第一次成功，第二次返回 False（没东西可清）。"""
        state = _make_state(total=4, generated_up_to=3)
        ok1, _, _ = _clear_segment_and_downstream(state, 2)
        ok2, _, _ = _clear_segment_and_downstream(state, 2)
        assert ok1 is True
        assert ok2 is False


# ---------------------------------------------------------------------------
# _clear_previous_segment_in_state —— 回归：旧接口仍然按预期只清最后一段
# ---------------------------------------------------------------------------

class TestClearPreviousSegmentBackwardCompat:

    def test_only_clears_last_generated_segment(self):
        state = _make_state(total=4, generated_up_to=3)
        ok, cleared_idx, _ = _clear_previous_segment_in_state(state)
        assert ok is True
        assert cleared_idx == 3
        outputs = state["agent_outputs"]
        # 片段 3 被清
        assert "compiled_segment_3" not in outputs
        # 片段 1、2 保留
        assert "compiled_segment_1" in outputs
        assert "compiled_segment_2" in outputs

    def test_returns_false_when_no_segment_generated(self):
        state = _make_state(total=4, generated_up_to=0)
        # generated_up_to=0 时 outputs 里没有 compiled_segment_*，current 会算成 0
        state["current_segment_index"] = 1
        state["status"] = "waiting_for_user_input"
        # _previous_generated_segment_index 在无产出时返回 0
        ok, cleared_idx, msg = _clear_previous_segment_in_state(state)
        assert ok is False
        assert cleared_idx == 0
        assert "没有可清除" in msg

    def test_current_segment_rolls_back_to_cleared_index(self):
        state = _make_state(total=4, generated_up_to=3)
        _clear_previous_segment_in_state(state)
        assert state["current_segment_index"] == 3


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
