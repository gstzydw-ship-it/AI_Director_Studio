"""
Per-request runtime context for WebUI sessions.

Values here are intentionally process-local and are never persisted. Runtime
API routing is fixed in server config; request scope only carries session and
stream state.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


request_session_id: ContextVar[str] = ContextVar("request_session_id", default="local")
request_stream_callback: ContextVar[Any] = ContextVar("request_stream_callback", default=None)


@contextmanager
def request_scope(
    *,
    session_id: str = "local",
    stream_callback: Any = None,
) -> Iterator[None]:
    tokens: list[tuple[ContextVar[Any], Any]] = [
        (request_session_id, request_session_id.set(session_id or "local")),
        (request_stream_callback, request_stream_callback.set(stream_callback)),
    ]
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)
