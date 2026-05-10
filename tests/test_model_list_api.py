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

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, headers):
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
    assert calls == ["https://ai.comfly.chat/models", "https://ai.comfly.chat/v1/models"]


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
        "scene_card_designer": "场景俯视/九宫格生图",
    })
    monkeypatch.setattr(web_app, "AGENT_CATEGORIES", {"scene_card_designer": "image"})
    monkeypatch.setattr(web_app, "_load_raw_settings", lambda: {
        "llm": {"api_key": "old-text-key", "base_url": "https://old-text.example/v1"},
        "image_generation": {"api_key": "old-image-key", "base_url": "https://old-image.example/v1"},
        "agent_models": {
            "director_showrunner": {"model": "old-text-model"},
            "scene_card_designer": {"model": "old-image-model"},
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
                    "scene_card_designer": "gpt-image-2",
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
    assert by_agent["scene_card_designer"]["base_url"] == "https://image.example/v1"
    assert by_agent["scene_card_designer"]["api_key"] == "image-key"
    assert by_agent["scene_card_designer"]["model"] == "gpt-image-2"
