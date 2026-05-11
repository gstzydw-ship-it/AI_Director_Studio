from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .types import OUTPUT_DIR, SESSION_ID_RE


TERMINAL_STATUSES = {"succeeded", "failed", "canceled"}
RUNNING_STATUSES = {"queued", "running", "cancel_requested"}


def _normalise_session_id(session_id: str | None) -> str:
    safe = SESSION_ID_RE.sub("", (session_id or "local").strip())[:80]
    return safe or "local"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _session_dir(session_id: str) -> str:
    return os.path.join(OUTPUT_DIR, "sessions", _normalise_session_id(session_id))


def _db_path(session_id: str) -> str:
    return os.path.join(_session_dir(session_id), "generation_jobs.sqlite")


def _connect(session_id: str) -> sqlite3.Connection:
    os.makedirs(_session_dir(session_id), exist_ok=True)
    conn = sqlite3.connect(_db_path(session_id))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generation_jobs (
            job_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            segment_index INTEGER,
            shot_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            prompt TEXT NOT NULL DEFAULT '',
            prompt_hash TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT '',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT '',
            finished_at TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generation_attempts (
            attempt_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            raw_response TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(job_id) REFERENCES generation_jobs(job_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generation_artifacts (
            artifact_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            thumbnail_path TEXT NOT NULL DEFAULT '',
            segment_index INTEGER,
            shot_id TEXT NOT NULL DEFAULT '',
            candidate_index INTEGER NOT NULL DEFAULT 1,
            selected INTEGER NOT NULL DEFAULT 0,
            score REAL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(job_id) REFERENCES generation_jobs(job_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_generation_jobs_session ON generation_jobs(session_id, created_at)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_generation_artifacts_session "
        "ON generation_artifacts(session_id, segment_index, shot_id, created_at)"
    )
    conn.commit()


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _decode_metadata(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.pop("metadata_json", "{}") or "{}"
    try:
        row["metadata"] = json.loads(raw)
    except json.JSONDecodeError:
        row["metadata"] = {}
    return row


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return _decode_metadata(dict(row))


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [_decode_metadata(dict(row)) for row in rows]


def create_generation_job(
    *,
    session_id: str,
    kind: str,
    segment_index: int | None = None,
    shot_id: str = "",
    prompt: str = "",
    prompt_hash: str = "",
    model: str = "",
    provider: str = "",
    max_attempts: int = 1,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    now = _now_iso()
    clean_session = _normalise_session_id(session_id)
    with _connect(clean_session) as conn:
        conn.execute(
            """
            INSERT INTO generation_jobs (
                job_id, session_id, kind, segment_index, shot_id, status,
                prompt, prompt_hash, model, provider, max_attempts,
                created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                clean_session,
                kind,
                segment_index,
                shot_id or "",
                prompt or "",
                prompt_hash or "",
                model or "",
                provider or "",
                max(1, int(max_attempts or 1)),
                now,
                _json_dumps(metadata),
            ),
        )
        conn.commit()
    job = get_generation_job(clean_session, job_id)
    if job is None:
        raise RuntimeError(f"generation job was not persisted: {job_id}")
    return job


def get_generation_job(session_id: str, job_id: str) -> dict[str, Any] | None:
    with _connect(session_id) as conn:
        row = conn.execute(
            "SELECT * FROM generation_jobs WHERE job_id = ? AND session_id = ?",
            (job_id, _normalise_session_id(session_id)),
        ).fetchone()
    return _row_to_dict(row)


def list_generation_jobs(session_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with _connect(session_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM generation_jobs
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (_normalise_session_id(session_id), max(1, min(int(limit or 100), 500))),
        ).fetchall()
    return _rows_to_dicts(rows)


def is_cancel_requested(session_id: str, job_id: str) -> bool:
    job = get_generation_job(session_id, job_id)
    return bool(job and job.get("status") == "cancel_requested")


def request_cancel_generation_job(session_id: str, job_id: str) -> dict[str, Any] | None:
    now = _now_iso()
    with _connect(session_id) as conn:
        job = conn.execute(
            "SELECT status FROM generation_jobs WHERE job_id = ? AND session_id = ?",
            (job_id, _normalise_session_id(session_id)),
        ).fetchone()
        if not job:
            return None
        status = job["status"]
        next_status = "cancel_requested" if status in RUNNING_STATUSES else status
        if status == "queued":
            next_status = "canceled"
        conn.execute(
            """
            UPDATE generation_jobs
            SET status = ?, finished_at = CASE WHEN ? = 'canceled' THEN ? ELSE finished_at END
            WHERE job_id = ? AND session_id = ?
            """,
            (next_status, next_status, now, job_id, _normalise_session_id(session_id)),
        )
        conn.commit()
    return get_generation_job(session_id, job_id)


def retry_generation_job(session_id: str, job_id: str) -> dict[str, Any] | None:
    with _connect(session_id) as conn:
        row = conn.execute(
            "SELECT status, attempt_count, max_attempts FROM generation_jobs WHERE job_id = ? AND session_id = ?",
            (job_id, _normalise_session_id(session_id)),
        ).fetchone()
        if not row:
            return None
        if row["status"] not in TERMINAL_STATUSES:
            return _row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE job_id = ?", (job_id,)).fetchone())
        next_max_attempts = max(int(row["max_attempts"] or 1), int(row["attempt_count"] or 0) + 1)
        conn.execute(
            """
            UPDATE generation_jobs
            SET status = 'queued', max_attempts = ?, started_at = '', finished_at = '', error = ''
            WHERE job_id = ? AND session_id = ?
            """,
            (next_max_attempts, job_id, _normalise_session_id(session_id)),
        )
        conn.commit()
    return get_generation_job(session_id, job_id)


def start_generation_attempt(session_id: str, job_id: str) -> dict[str, Any]:
    clean_session = _normalise_session_id(session_id)
    attempt_id = uuid.uuid4().hex
    now = _now_iso()
    with _connect(clean_session) as conn:
        job = conn.execute(
            "SELECT status, attempt_count, max_attempts FROM generation_jobs WHERE job_id = ? AND session_id = ?",
            (job_id, clean_session),
        ).fetchone()
        if not job:
            raise KeyError(f"unknown generation job: {job_id}")
        if job["status"] == "cancel_requested":
            raise RuntimeError("generation job was canceled before it started")
        if job["status"] not in {"queued", "failed"}:
            raise RuntimeError(f"generation job is not startable: {job['status']}")
        if int(job["attempt_count"] or 0) >= int(job["max_attempts"] or 1):
            raise RuntimeError("generation job has no attempts remaining")

        conn.execute(
            """
            UPDATE generation_jobs
            SET status = 'running', started_at = CASE WHEN started_at = '' THEN ? ELSE started_at END,
                attempt_count = attempt_count + 1, error = ''
            WHERE job_id = ? AND session_id = ?
            """,
            (now, job_id, clean_session),
        )
        conn.execute(
            """
            INSERT INTO generation_attempts (attempt_id, job_id, status, started_at)
            VALUES (?, ?, 'running', ?)
            """,
            (attempt_id, job_id, now),
        )
        conn.commit()
    return {"attempt_id": attempt_id, "job_id": job_id, "started_at": now}


def finish_generation_attempt(
    session_id: str,
    job_id: str,
    attempt_id: str,
    *,
    status: str,
    error: str = "",
    raw_response: str = "",
) -> dict[str, Any] | None:
    if status not in {"succeeded", "failed", "canceled"}:
        raise ValueError(f"unsupported attempt status: {status}")
    clean_session = _normalise_session_id(session_id)
    now = _now_iso()
    with _connect(clean_session) as conn:
        cursor = conn.execute(
            """
            UPDATE generation_attempts
            SET status = ?, finished_at = ?, error = ?, raw_response = ?
            WHERE attempt_id = ? AND job_id = ? AND status = 'running'
            """,
            (status, now, error or "", raw_response or "", attempt_id, job_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"running generation attempt not found: {attempt_id}")
        job_status = "canceled" if status == "canceled" else status
        conn.execute(
            """
            UPDATE generation_jobs
            SET status = ?, finished_at = ?, error = ?
            WHERE job_id = ? AND session_id = ?
            """,
            (job_status, now, error or "", job_id, clean_session),
        )
        conn.commit()
    return get_generation_job(clean_session, job_id)


def add_generation_artifact(
    *,
    session_id: str,
    job_id: str,
    kind: str,
    path: str,
    thumbnail_path: str = "",
    segment_index: int | None = None,
    shot_id: str = "",
    candidate_index: int | None = None,
    selected: bool = False,
    score: float | None = None,
    notes: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_session = _normalise_session_id(session_id)
    artifact_id = uuid.uuid4().hex
    now = _now_iso()
    with _connect(clean_session) as conn:
        if candidate_index is None:
            row = conn.execute(
                """
                SELECT COALESCE(MAX(candidate_index), 0) + 1 AS next_index
                FROM generation_artifacts
                WHERE session_id = ? AND segment_index IS ? AND shot_id = ?
                """,
                (clean_session, segment_index, shot_id or ""),
            ).fetchone()
            candidate_index = int(row["next_index"] or 1)
        if selected:
            conn.execute(
                """
                UPDATE generation_artifacts
                SET selected = 0
                WHERE session_id = ? AND segment_index IS ? AND shot_id = ?
                """,
                (clean_session, segment_index, shot_id or ""),
            )
        conn.execute(
            """
            INSERT INTO generation_artifacts (
                artifact_id, job_id, session_id, kind, path, thumbnail_path,
                segment_index, shot_id, candidate_index, selected, score, notes,
                created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                job_id,
                clean_session,
                kind,
                path,
                thumbnail_path or "",
                segment_index,
                shot_id or "",
                int(candidate_index or 1),
                1 if selected else 0,
                score,
                notes or "",
                now,
                _json_dumps(metadata),
            ),
        )
        conn.commit()
    artifact = get_generation_artifact(clean_session, artifact_id)
    if artifact is None:
        raise RuntimeError(f"generation artifact was not persisted: {artifact_id}")
    return artifact


def get_generation_artifact(session_id: str, artifact_id: str) -> dict[str, Any] | None:
    with _connect(session_id) as conn:
        row = conn.execute(
            "SELECT * FROM generation_artifacts WHERE artifact_id = ? AND session_id = ?",
            (artifact_id, _normalise_session_id(session_id)),
        ).fetchone()
    return _row_to_dict(row)


def list_generation_artifacts(
    session_id: str,
    *,
    segment_index: int | None = None,
    shot_id: str | None = None,
    job_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses = ["session_id = ?"]
    params: list[Any] = [_normalise_session_id(session_id)]
    if segment_index is not None:
        clauses.append("segment_index = ?")
        params.append(segment_index)
    if shot_id is not None:
        clauses.append("shot_id = ?")
        params.append(shot_id)
    if job_id is not None:
        clauses.append("job_id = ?")
        params.append(job_id)
    params.append(max(1, min(int(limit or 200), 1000)))
    with _connect(session_id) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM generation_artifacts
            WHERE {' AND '.join(clauses)}
            ORDER BY segment_index, shot_id, candidate_index, created_at
            LIMIT ?
            """,
            params,
        ).fetchall()
    return _rows_to_dicts(rows)


def select_generation_artifact(session_id: str, artifact_id: str) -> dict[str, Any] | None:
    clean_session = _normalise_session_id(session_id)
    with _connect(clean_session) as conn:
        artifact = conn.execute(
            "SELECT * FROM generation_artifacts WHERE artifact_id = ? AND session_id = ?",
            (artifact_id, clean_session),
        ).fetchone()
        if not artifact:
            return None
        conn.execute(
            """
            UPDATE generation_artifacts
            SET selected = 0
            WHERE session_id = ? AND segment_index IS ? AND shot_id = ?
            """,
            (clean_session, artifact["segment_index"], artifact["shot_id"]),
        )
        conn.execute(
            "UPDATE generation_artifacts SET selected = 1 WHERE artifact_id = ? AND session_id = ?",
            (artifact_id, clean_session),
        )
        conn.commit()
    return get_generation_artifact(clean_session, artifact_id)


def recover_generation_jobs(session_id: str) -> int:
    clean_session = _normalise_session_id(session_id)
    now = _now_iso()
    with _connect(clean_session) as conn:
        cursor = conn.execute(
            """
            UPDATE generation_jobs
            SET status = 'failed', finished_at = ?, error = 'recovered stale running generation job'
            WHERE session_id = ? AND status IN ('running', 'cancel_requested')
            """,
            (now, clean_session),
        )
        conn.execute(
            """
            UPDATE generation_attempts
            SET status = 'failed', finished_at = ?, error = 'recovered stale running generation attempt'
            WHERE status = 'running'
              AND job_id IN (SELECT job_id FROM generation_jobs WHERE session_id = ?)
            """,
            (now, clean_session),
        )
        conn.commit()
        return int(cursor.rowcount or 0)
