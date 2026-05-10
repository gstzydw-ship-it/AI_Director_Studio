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
