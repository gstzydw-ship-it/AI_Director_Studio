import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import knowledge_base as kb  # noqa: E402


class _FakeEmbeddingsAPI:
    def create(self, *, input, model, encoding_format):
        assert input == ["alpha", "beta"]
        assert model == "test-embedding-model"
        assert encoding_format == "float"
        return json.dumps(
            {
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]},
                ]
            }
        )


class _FakeClient:
    embeddings = _FakeEmbeddingsAPI()


class _FakeRawResponse:
    text = json.dumps(
        {
            "data": [
                {"embedding": [0.7, 0.8]},
                {"embedding": [0.9, 1.0]},
            ]
        }
    )


class _FakeRawEmbeddingsAPI:
    def create(self, *, input, model, encoding_format):
        assert input == ["gamma", "delta"]
        assert model == "test-embedding-model"
        assert encoding_format == "float"
        return _FakeRawResponse()


class _FakeEmbeddingsAPIWithRawFallback:
    with_raw_response = _FakeRawEmbeddingsAPI()

    def create(self, *, input, model, encoding_format):
        assert encoding_format == "float"
        raise AttributeError("'str' object has no attribute 'data'")


class _FakeClientWithRawFallback:
    embeddings = _FakeEmbeddingsAPIWithRawFallback()


def test_embed_texts_accepts_json_string_response(monkeypatch):
    monkeypatch.setattr(kb, "_get_embed_client", lambda: _FakeClient())

    vectors = kb._embed_texts(["alpha", "beta"], model="test-embedding-model", batch_size=20)

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_embed_texts_falls_back_to_raw_response_when_sdk_parser_fails(monkeypatch):
    monkeypatch.setattr(kb, "_get_embed_client", lambda: _FakeClientWithRawFallback())

    vectors = kb._embed_texts(["gamma", "delta"], model="test-embedding-model", batch_size=20)

    assert vectors == [[0.7, 0.8], [0.9, 1.0]]
