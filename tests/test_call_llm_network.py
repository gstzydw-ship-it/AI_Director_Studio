import httpx
import time

from agents import director_graph


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "ok"}}]}


def _patch_llm_settings(monkeypatch):
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "base_url": "https://ai.comfly.chat/v1",
                "model": "test-model",
                "temperature": 0.2,
            },
            "agent_models": {},
        },
    )
    monkeypatch.setattr(
        director_graph,
        "_get_llm_settings",
        lambda agent_name="": ("test-key", "https://ai.comfly.chat/v1", "test-model", 0.2),
    )
    monkeypatch.setattr(director_graph, "_get_llm_extra_params", lambda agent_name="": {})


def test_call_llm_bypasses_proxy_environment_by_default(monkeypatch):
    _patch_llm_settings(monkeypatch)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9674")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9674")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9674")
    captured = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["trust_env"] = kwargs.get("trust_env")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="shot_director_layout") == "ok"
    assert captured["trust_env"] is False


def test_call_llm_retries_with_system_proxy_after_direct_connect_failure(monkeypatch):
    _patch_llm_settings(monkeypatch)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    attempts: list[bool] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.trust_env = kwargs.get("trust_env")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            attempts.append(self.trust_env)
            if self.trust_env is False:
                request = httpx.Request("POST", "https://ai.comfly.chat/v1/chat/completions")
                raise httpx.ConnectError("simulated direct connect failure", request=request)
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="director_showrunner", max_retries=1) == "ok"
    assert attempts == [False, True]


def test_call_llm_retries_connect_error(monkeypatch):
    _patch_llm_settings(monkeypatch)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    attempts = {"count": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING]")
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="shot_director_layout", max_retries=2) == "ok"
    assert attempts["count"] == 2


def test_call_llm_tries_configured_fallback_model_after_retryable_failure(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model": "global-model",
                "max_retries": 1,
            },
            "agent_models": {
                "story_planner": {
                    "model": "primary-model",
                    "fallback_models": ["fallback-model"],
                    "temperature": 0.2,
                }
            },
        },
    )
    attempted_models = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            model = kwargs["json"]["model"]
            attempted_models.append(model)
            if model == "primary-model":
                raise httpx.RemoteProtocolError("server disconnected")
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="story_planner") == "ok"
    assert attempted_models == ["primary-model", "fallback-model"]


def test_call_llm_tries_configured_fallback_route_after_network_failure(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "primary-key",
                "base_url": "https://primary.example/v1",
                "model": "primary-model",
                "max_retries": 1,
            },
            "agent_models": {
                "director_showrunner": {
                    "fallback_routes": [
                        {
                            "api_key": "backup-key",
                            "base_url": "https://backup.example/v1",
                            "model": "backup-model",
                        }
                    ]
                }
            },
        },
    )
    attempts = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, **kwargs):
            attempts.append((url, kwargs["headers"]["Authorization"], kwargs["json"]["model"]))
            if "primary.example" in url:
                raise httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING]")
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="director_showrunner", bypass_proxy=False) == "ok"
    assert attempts == [
        ("https://primary.example/v1/chat/completions", "Bearer primary-key", "primary-model"),
        ("https://backup.example/v1/chat/completions", "Bearer backup-key", "backup-model"),
    ]


def test_shot_director_stage_agents_inherit_parent_model_config(monkeypatch):
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "global-key",
                "base_url": "https://global.example/v1",
                "model": "global-model",
                "temperature": 0.3,
                "extra_params": {"reasoning_effort": "low"},
            },
            "agent_models": {
                "shot_director": {
                    "api_key": "parent-key",
                    "base_url": "https://parent.example/v1",
                    "model": "claude-opus-4-6-thinking",
                    "temperature": 1.0,
                    "extra_params": {"thinking": {"type": "enabled"}},
                },
                "shot_director_guard": {
                    "model": "guard-model",
                    "extra_params": {"guard": True},
                },
            },
        },
    )

    assert director_graph._get_llm_settings("shot_director_layout") == (
        "parent-key",
        "https://parent.example/v1",
        "claude-opus-4-6-thinking",
        1.0,
    )
    assert director_graph._get_llm_settings("shot_director_guard") == (
        "parent-key",
        "https://parent.example/v1",
        "guard-model",
        1.0,
    )

    layout_extra = director_graph._get_llm_extra_params("shot_director_layout")
    guard_extra = director_graph._get_llm_extra_params("shot_director_guard")
    assert layout_extra["thinking"] == {"type": "enabled"}
    assert guard_extra["thinking"] == {"type": "enabled"}
    assert guard_extra["guard"] is True


def test_llm_settings_validation_reports_missing_required_fields():
    settings = director_graph.LLMSettings(
        agent_name="story_planner",
        api_key="",
        base_url="",
        model="",
        temperature=None,
        config_path="config/settings.yaml",
    )

    assert settings.missing_fields() == ["api_key", "base_url", "model"]
    try:
        settings.require_valid()
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected missing LLM settings to raise")

    assert "story_planner" in message
    assert "settings.yaml" in message
    assert "api_key, base_url, model" in message


def test_resolve_llm_settings_returns_config_object(monkeypatch):
    monkeypatch.delenv("DIRECTOR_LLM_API_KEY", raising=False)
    monkeypatch.delenv("DIRECTOR_LLM_MODEL", raising=False)
    full_config = {
        "llm": {
            "api_key": "global-key",
            "base_url": "ai.example/v1",
            "model": "openai/global-model",
            "temperature": "0.25",
        },
        "agent_models": {
            "story_planner": {
                "model": "planner-model",
                "temperature": "0.7",
            }
        },
    }

    settings = director_graph.resolve_llm_settings("story_planner", full_config=full_config)

    assert settings.api_key == "global-key"
    assert settings.base_url == "https://ai.example/v1"
    assert settings.model == "planner-model"
    assert settings.temperature == 0.7
    assert settings.as_tuple() == ("global-key", "https://ai.example/v1", "planner-model", 0.7)


def test_call_llm_uses_configured_timeout_and_retry_defaults(monkeypatch):
    _patch_llm_settings(monkeypatch)
    monkeypatch.setattr(director_graph, "_get_llm_extra_params", lambda agent_name="": {})
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "timeout_seconds": 45,
                "connect_timeout_seconds": 6,
                "read_timeout_seconds": 50,
                "write_timeout_seconds": 11,
                "max_retries": 1,
            }
        },
    )
    captured = {}

    class FakeTimeout:
        def __init__(self, timeout, *, connect, read, write):
            captured["timeout"] = timeout
            captured["connect"] = connect
            captured["read"] = read
            captured["write"] = write

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Timeout", FakeTimeout)
    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="prompt_compiler") == "ok"
    assert captured == {"timeout": 45.0, "connect": 6.0, "read": 50.0, "write": 11.0}


def test_call_llm_uses_longer_default_timeout_for_thinking_models(monkeypatch):
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model": "fallback-model",
            },
            "agent_models": {
                "shot_director_layout": {
                    "model": "claude-opus-4-6-thinking",
                    "extra_params": {"thinking": {"type": "enabled", "budget_tokens": 1024}},
                }
            },
        },
    )
    captured = {}

    class FakeTimeout:
        def __init__(self, timeout, *, connect, read, write):
            captured["timeout"] = timeout
            captured["connect"] = connect
            captured["read"] = read
            captured["write"] = write

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Timeout", FakeTimeout)
    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="shot_director_layout") == "ok"
    assert captured == {"timeout": 240.0, "connect": 30.0, "read": 240.0, "write": 60.0}


def test_call_llm_timeout_error_reports_no_reference_images_when_none_sent(monkeypatch):
    _patch_llm_settings(monkeypatch)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model": "test-model",
                "timeout_seconds": 45,
                "connect_timeout_seconds": 6,
                "read_timeout_seconds": 50,
                "write_timeout_seconds": 11,
                "max_retries": 1,
            }
        },
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    try:
        director_graph.call_llm("system", "user", agent_name="shot_director", max_retries=1)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected timeout to raise RuntimeError")

    assert "agent=shot_director" in message
    assert "model=test-model" in message
    assert "参考图: 未发送" in message
    assert "本次请求未发送参考图" in message
    assert "不要按“参考图过大”排查" in message
    assert "timeout: total=45s, connect=6s, read=50s, write=11s" in message
    assert "环境代理: 已绕开" in message
    assert "read timed out" in message


def test_call_llm_timeout_error_reports_reference_image_count_when_sent(monkeypatch):
    _patch_llm_settings(monkeypatch)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model": "test-model",
                "timeout_seconds": 45,
                "max_retries": 1,
            }
        },
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    try:
        director_graph.call_llm("system", "user", images_base64=["aaa", "bbb"], agent_name="scene_vision_analyst", max_retries=1)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected timeout to raise RuntimeError")

    assert "agent=scene_vision_analyst" in message
    assert "参考图: 2 张" in message
    assert "本次请求发送了 2 张参考图" in message
    assert "压缩或减少参考图" in message


def test_call_llm_forwards_max_tokens_and_expands_for_thinking_budget(monkeypatch):
    monkeypatch.setattr(
        director_graph,
        "load_config",
        lambda: {
            "llm": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model": "fallback-model",
                "max_tokens": 8192,
            },
            "agent_models": {
                "story_planner": {
                    "model": "claude-opus-4-6-thinking",
                    "temperature": 1.0,
                    "extra_params": {"thinking": {"type": "enabled", "budget_tokens": 32000}},
                }
            },
        },
    )
    captured = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            captured["payload"] = kwargs["json"]
            return _FakeResponse()

    monkeypatch.setattr(director_graph.httpx, "Client", FakeClient)

    assert director_graph.call_llm("system", "user", agent_name="story_planner") == "ok"
    payload = captured["payload"]
    assert payload["max_tokens"] == 40192
    assert payload["thinking"] == {"type": "enabled", "budget_tokens": 32000}
    assert payload["temperature"] == 1.0
