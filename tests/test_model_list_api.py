from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx


class _FakeRequest:
    def __init__(self, payload: dict):
        self._payload = payload
        self.client = SimpleNamespace(host="127.0.0.1")

    async def json(self):
        return self._payload


def _http_response(url: str, **kwargs) -> httpx.Response:
    kwargs.setdefault("status_code", 200)
    return httpx.Response(request=httpx.Request("GET", url), **kwargs)


def _json_body(response) -> dict:
    return json.loads(response.body.decode("utf-8"))


def test_model_list_api_retries_v1_when_root_returns_html(monkeypatch):
    import ui.app as web_app

    calls: list[str] = []
    trust_env_values: list[bool] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.trust_env = kwargs.get("trust_env")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, headers):
            trust_env_values.append(self.trust_env)
            calls.append(url)
            if url.endswith("/v1/models"):
                return _http_response(url, json={"data": [{"id": "gpt-image-1"}]})
            return _http_response(url, text="<html>not an api endpoint</html>", headers={"content-type": "text/html"})

    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {})
    monkeypatch.setattr(web_app.httpx, "Client", FakeClient)

    response = asyncio.run(
        web_app.api_model_list(
            _FakeRequest({"profile": "image", "base_url": "https://ai.comfly.chat", "api_key": "test-key"})
        )
    )

    data = _json_body(response)
    assert response.status_code == 200, response.body.decode("utf-8")
    assert data["success"] is True
    assert data["models"] == ["gpt-image-1"]
    assert data["proxy_mode"] == "直连/绕开环境代理"
    assert calls == ["https://ai.comfly.chat/models", "https://ai.comfly.chat/v1/models"]
    assert trust_env_values == [False, False]


def test_model_list_api_falls_back_to_system_proxy_after_direct_failure(monkeypatch):
    import ui.app as web_app

    attempts: list[tuple[bool, str]] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.trust_env = kwargs.get("trust_env")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, headers):
            attempts.append((self.trust_env, url))
            if self.trust_env is False:
                request = httpx.Request("GET", url)
                raise httpx.ConnectError("simulated direct connect failure", request=request)
            return _http_response(url, json={"data": [{"id": "gpt-5.5"}]})

    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {})
    monkeypatch.setattr(web_app.httpx, "Client", FakeClient)

    response = asyncio.run(
        web_app.api_model_list(
            _FakeRequest({"profile": "text", "base_url": "https://www.xkwuai.cn/v1", "api_key": "test-key"})
        )
    )

    data = _json_body(response)
    assert response.status_code == 200, response.body.decode("utf-8")
    assert data["success"] is True
    assert data["models"] == ["gpt-5.5"]
    assert data["proxy_mode"] == "系统环境代理"
    assert attempts == [
        (False, "https://www.xkwuai.cn/v1/models"),
        (True, "https://www.xkwuai.cn/v1/models"),
    ]


def test_model_list_api_reports_mihomo_fake_ip_hint(monkeypatch):
    import ui.app as web_app

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.trust_env = kwargs.get("trust_env")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, headers):
            request = httpx.Request("GET", url)
            raise httpx.ConnectError("simulated tls eof", request=request)

    def fake_getaddrinfo(*args, **kwargs):
        return [(None, None, None, None, ("198.18.0.16", 443))]

    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {})
    monkeypatch.setattr(web_app.httpx, "Client", FakeClient)
    monkeypatch.setattr(web_app.socket, "getaddrinfo", fake_getaddrinfo)

    response = asyncio.run(
        web_app.api_model_list(
            _FakeRequest({"profile": "text", "base_url": "https://www.xkwuai.cn/v1", "api_key": "test-key"})
        )
    )

    data = _json_body(response)
    assert response.status_code == 502
    assert data["success"] is False
    assert "Mihomo/Clash fake-ip" in data["error"]
    assert "198.18.0.16" in data["error"]


def test_model_list_api_reports_non_json_without_raw_jsondecodeerror(monkeypatch):
    import ui.app as web_app

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, headers):
            return _http_response(url, text="", headers={"content-type": "text/html"})

    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {})
    monkeypatch.setattr(web_app.httpx, "Client", FakeClient)

    response = asyncio.run(
        web_app.api_model_list(
            _FakeRequest({"profile": "text", "base_url": "https://www.xkwuai.cn/v1", "api_key": "test-key"})
        )
    )

    data = _json_body(response)
    assert response.status_code == 502, response.body.decode("utf-8")
    assert data["success"] is False
    assert "不是合法 JSON" in data["error"]
    assert "JSONDecodeError" not in data["error"]


def test_agent_connection_test_uses_current_form_profiles(monkeypatch):
    import ui.app as web_app

    calls: list[dict] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return {
            "agent": kwargs["agent_name"],
            "label": kwargs["label"],
            "category": kwargs["category"],
            "base_url": kwargs["base_url"],
            "model": kwargs["model"],
            "success": True,
            "latency_ms": 12,
            "message": "连接正常",
        }

    monkeypatch.setattr(web_app, "AGENT_LABELS", {
        "director_showrunner": "剧情增强",
        "storyboard_designer": "分镜图片生成",
    })
    monkeypatch.setattr(web_app, "AGENT_CATEGORIES", {"storyboard_designer": "image"})
    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {
        "llm": {"api_key": "old-text-key", "base_url": "https://old-text.example/v1"},
        "image_generation": {"api_key": "old-image-key", "base_url": "https://old-image.example/v1"},
        "agent_models": {
            "director_showrunner": {"model": "old-text-model"},
            "storyboard_designer": {"model": "old-image-model"},
        },
    })
    monkeypatch.setattr(web_app, "_probe_agent_connection", fake_probe)

    response = asyncio.run(
        web_app.api_test_agent_connections(
            _FakeRequest({
                "text_base_url": "https://text.example/v1",
                "text_api_key": "text-key",
                "image_base_url": "https://image.example/v1",
                "image_api_key": "image-key",
                "agent_models": {
                    "director_showrunner": "gpt-5.5",
                    "storyboard_designer": "gpt-image-2",
                },
            })
        )
    )

    data = _json_body(response)
    assert response.status_code == 200, response.body.decode("utf-8")
    assert data["success"] is True
    by_agent = {call["agent_name"]: call for call in calls}
    assert by_agent["director_showrunner"]["base_url"] == "https://text.example/v1"
    assert by_agent["director_showrunner"]["api_key"] == "text-key"
    assert by_agent["director_showrunner"]["model"] == "gpt-5.5"
    assert by_agent["storyboard_designer"]["base_url"] == "https://image.example/v1"
    assert by_agent["storyboard_designer"]["api_key"] == "image-key"
    assert by_agent["storyboard_designer"]["model"] == "gpt-image-2"


def test_agent_connection_test_can_scope_agents_and_include_embedding(monkeypatch):
    import ui.app as web_app

    agent_calls: list[dict] = []
    embedding_calls: list[dict] = []

    async def fake_probe(**kwargs):
        agent_calls.append(kwargs)
        return {
            "agent": kwargs["agent_name"],
            "label": kwargs["label"],
            "category": kwargs["category"],
            "base_url": kwargs["base_url"],
            "model": kwargs["model"],
            "success": True,
            "latency_ms": 9,
            "message": "ok",
        }

    async def fake_embedding_probe(**kwargs):
        embedding_calls.append(kwargs)
        return {
            "agent": "embedding",
            "label": "向量嵌入",
            "category": "embedding",
            "base_url": kwargs["base_url"],
            "model": kwargs["model"],
            "success": True,
            "latency_ms": 8,
            "message": "ok",
        }

    monkeypatch.setattr(web_app, "AGENT_LABELS", {
        "director_showrunner": "剧情增强",
        "story_planner": "拆片规划",
    })
    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {
        "llm": {"api_key": "saved-text-key", "base_url": "https://saved-text.example/v1"},
        "vectordb": {
            "api_key": "saved-embedding-key",
            "base_url": "https://saved-embedding.example/v1",
            "embedding_model": "saved-embedding-model",
        },
        "agent_models": {
            "director_showrunner": {"model": "saved-director-model"},
            "story_planner": {"model": "saved-story-model"},
            "quality_inspector_llm_a": {"model": "saved-deep-qc-model"},
            "shot_director_layout": {"model": "saved-layout-model"},
        },
    })
    monkeypatch.setattr(web_app, "_probe_agent_connection", fake_probe)
    monkeypatch.setattr(web_app, "_probe_embedding_connection", fake_embedding_probe)

    response = asyncio.run(
        web_app.api_test_agent_connections(
            _FakeRequest({
                "text_base_url": "https://text.example/v1",
                "text_api_key": "text-key",
                "embedding_base_url": "https://embedding.example/v1",
                "embedding_api_key": "embedding-key",
                "embedding_model": "text-embedding-3-large",
                "agent_models": {
                    "director_showrunner": "gpt-5.5",
                    "story_planner": "gpt-5.4",
                },
                "agent_names": ["director_showrunner", "quality_inspector_llm_a", "shot_director_layout", "story_planner"],
                "include_embedding": True,
            })
        )
    )

    data = _json_body(response)
    assert response.status_code == 200, response.body.decode("utf-8")
    assert data["success"] is True
    assert data["summary"] == {"total": 3, "ok": 3, "failed": 0}
    assert [call["agent_name"] for call in agent_calls] == ["director_showrunner", "story_planner"]
    assert agent_calls[0]["model"] == "gpt-5.5"
    assert agent_calls[1]["model"] == "gpt-5.4"
    assert embedding_calls == [{
        "base_url": "https://embedding.example/v1",
        "api_key": "embedding-key",
        "model": "text-embedding-3-large",
    }]


def test_public_model_config_removes_quality_review_agents_only(monkeypatch, tmp_path):
    import ui.app as web_app

    public_path = tmp_path / "config" / "settings.yaml"
    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {
        "llm": {"api_key": "text-key"},
        "agent_models": {
            "director_showrunner": {"model": "gpt-5.5", "api_key": "text-key"},
            "story_planner": {"model": "gpt-5.4", "api_key": "text-key"},
            "quality_inspector_llm_a": {"model": "deep-qc-model", "api_key": "hidden-key"},
            "shot_director_layout": {"model": "layout-model", "api_key": "hidden-key"},
        },
    })
    monkeypatch.setattr(web_app, "get_public_config_path", lambda: str(public_path))
    monkeypatch.setattr(web_app, "get_config_path", lambda: str(public_path))

    config = web_app._public_model_config()

    assert set(config["agent_models"]) == {"director_showrunner", "story_planner"}
    assert config["_agent_order"] == ["director_showrunner", "story_planner"]
    assert config["agent_models"]["director_showrunner"]["api_key"] == ""
    assert config["agent_models"]["director_showrunner"]["has_api_key"] is True
    assert config["agent_models"]["story_planner"]["api_key"] == ""
    assert config["agent_models"]["story_planner"]["has_api_key"] is True


def test_save_config_does_not_recreate_deleted_or_hidden_agents(monkeypatch):
    import ui.app as web_app

    raw_config = {
        "llm": {"api_key": "old-text-key", "base_url": "https://old-text.example/v1"},
        "image_generation": {"api_key": "old-image-key", "base_url": "https://old-image.example/v1"},
        "vectordb": {"api_key": "old-embedding-key", "base_url": "https://old-embedding.example/v1"},
        "agent_models": {
            "director_showrunner": {"model": "old-director-model", "fallback_models": ["backup-director-model"]},
            "shot_director_layout": {"model": "hidden-layout-model"},
        },
    }
    saved: dict[str, dict] = {}

    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: raw_config)
    monkeypatch.setattr(web_app, "_save_raw_settings", lambda config: saved.setdefault("config", config))
    monkeypatch.setattr(web_app, "_public_model_config", lambda: {"agent_models": {}})

    response = asyncio.run(
        web_app.api_save_config(
            _FakeRequest({
                "text_base_url": "https://text.example/v1",
                "text_api_key": "text-key",
                "image_base_url": "https://image.example/v1",
                "image_api_key": "image-key",
                "embedding_base_url": "https://embedding.example/v1",
                "embedding_api_key": "embedding-key",
                "default_model": "default-text-model",
                "embedding_model": "text-embedding-3-large",
                "agent_models": {"director_showrunner": "new-director-model"},
            })
        )
    )

    data = _json_body(response)
    assert response.status_code == 200, response.body.decode("utf-8")
    assert data["success"] is True

    agent_models = saved["config"]["agent_models"]
    assert "quality_inspector_llm_a" not in agent_models
    assert agent_models["director_showrunner"]["model"] == "new-director-model"
    assert agent_models["director_showrunner"]["fallback_models"] == ["backup-director-model"]
    assert agent_models["shot_director_layout"].get("model", "") != "hidden-layout-model"
    assert agent_models["scene_vision_analyst"].get("model", "") == agent_models["scene_analyst"].get("model", "")


def test_save_config_rejects_unresolved_placeholder_api_keys(monkeypatch):
    import ui.app as web_app

    monkeypatch.delenv("DIRECTOR_LLM_API_KEY", raising=False)
    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {
        "llm": {"api_key": "${DIRECTOR_LLM_API_KEY}", "base_url": "https://text.example/v1"},
        "image_generation": {"api_key": "${DIRECTOR_IMAGE_API_KEY}", "base_url": "https://image.example/v1"},
        "vectordb": {"api_key": "${DIRECTOR_EMBEDDING_API_KEY}", "base_url": "https://embedding.example/v1"},
        "agent_models": {},
    })

    response = asyncio.run(
        web_app.api_save_config(
            _FakeRequest({
                "text_base_url": "https://text.example/v1",
                "image_base_url": "https://image.example/v1",
                "embedding_base_url": "https://embedding.example/v1",
                "default_model": "gpt-5.5",
                "embedding_model": "text-embedding-3-large",
                "agent_models": {"director_showrunner": "gpt-5.5"},
            })
        )
    )

    data = _json_body(response)
    assert response.status_code == 400
    assert data["success"] is False
    assert "API Key" in data["error"]


def test_public_model_config_reports_public_frontend_source(monkeypatch, tmp_path):
    import ui.app as web_app

    public_path = tmp_path / "config" / "settings.yaml"
    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {})
    monkeypatch.setattr(web_app, "get_public_config_path", lambda: str(public_path))
    monkeypatch.setattr(web_app, "get_config_path", lambda: str(public_path))

    config = web_app._public_model_config()
    source = config["_config_source"]

    assert source["is_private"] is False
    assert source["active_path"] == str(public_path)
    assert source["active_display"].endswith("settings.yaml")
