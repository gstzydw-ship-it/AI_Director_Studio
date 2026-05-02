import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import knowledge_base as kb  # noqa: E402


class _FakeEmbeddingsAPI:
    def create(self, *, input, model):
        assert input == ["alpha", "beta"]
        assert model == "test-embedding-model"
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


def test_embed_texts_accepts_json_string_response(monkeypatch):
    monkeypatch.setattr(kb, "_get_embed_client", lambda: _FakeClient())

    vectors = kb._embed_texts(["alpha", "beta"], model="test-embedding-model", batch_size=20)

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
