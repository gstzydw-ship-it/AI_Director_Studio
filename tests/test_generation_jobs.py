from __future__ import annotations

from agents.director_graph_package import generation_jobs as jobs


def test_generation_job_lifecycle_records_attempt_and_artifact(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "OUTPUT_DIR", str(tmp_path))

    job = jobs.create_generation_job(
        session_id="session_a",
        kind="storyboard_image",
        segment_index=1,
        prompt="draw the first storyboard",
        prompt_hash="abc",
        max_attempts=1,
        metadata={"source": "test"},
    )

    assert job["status"] == "queued"
    assert job["metadata"]["source"] == "test"

    attempt = jobs.start_generation_attempt("session_a", job["job_id"])
    running = jobs.get_generation_job("session_a", job["job_id"])
    assert running is not None
    assert running["status"] == "running"
    assert running["attempt_count"] == 1

    artifact = jobs.add_generation_artifact(
        session_id="session_a",
        job_id=job["job_id"],
        kind="image",
        path="output/storyboard.png",
        segment_index=1,
        selected=True,
        metadata={"prompt": "draw the first storyboard"},
    )
    jobs.finish_generation_attempt(
        "session_a",
        job["job_id"],
        attempt["attempt_id"],
        status="succeeded",
        raw_response="ok",
    )
    try:
        jobs.finish_generation_attempt(
            "session_a",
            job["job_id"],
            "missing-attempt",
            status="succeeded",
        )
    except KeyError:
        pass
    else:
        raise AssertionError("stale attempts must not finish a job")

    finished = jobs.get_generation_job("session_a", job["job_id"])
    assert finished is not None
    assert finished["status"] == "succeeded"
    artifacts = jobs.list_generation_artifacts("session_a", segment_index=1)
    assert [item["artifact_id"] for item in artifacts] == [artifact["artifact_id"]]
    assert artifacts[0]["selected"] == 1
    assert artifacts[0]["metadata"]["prompt"] == "draw the first storyboard"


def test_cancel_retry_select_and_recover(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "OUTPUT_DIR", str(tmp_path))

    queued = jobs.create_generation_job(session_id="session_b", kind="storyboard_image", segment_index=2)
    canceled = jobs.request_cancel_generation_job("session_b", queued["job_id"])
    assert canceled is not None
    assert canceled["status"] == "canceled"

    retry = jobs.retry_generation_job("session_b", queued["job_id"])
    assert retry is not None
    assert retry["status"] == "queued"
    assert retry["max_attempts"] >= 1

    attempt = jobs.start_generation_attempt("session_b", retry["job_id"])
    assert jobs.request_cancel_generation_job("session_b", retry["job_id"])["status"] == "cancel_requested"
    assert jobs.is_cancel_requested("session_b", retry["job_id"])
    jobs.finish_generation_attempt(
        "session_b",
        retry["job_id"],
        attempt["attempt_id"],
        status="canceled",
        error="user canceled",
    )

    stale = jobs.create_generation_job(session_id="session_b", kind="storyboard_image", segment_index=3)
    jobs.start_generation_attempt("session_b", stale["job_id"])
    assert jobs.recover_generation_jobs("session_b") == 1
    recovered = jobs.get_generation_job("session_b", stale["job_id"])
    assert recovered is not None
    assert recovered["status"] == "failed"

    selected_job = jobs.create_generation_job(session_id="session_b", kind="storyboard_image", segment_index=4)
    first = jobs.add_generation_artifact(
        session_id="session_b",
        job_id=selected_job["job_id"],
        kind="image",
        path="a.png",
        segment_index=4,
        selected=True,
    )
    second = jobs.add_generation_artifact(
        session_id="session_b",
        job_id=selected_job["job_id"],
        kind="image",
        path="b.png",
        segment_index=4,
        selected=True,
    )
    artifacts = jobs.list_generation_artifacts("session_b", segment_index=4)
    selected = {item["path"]: item["selected"] for item in artifacts}
    assert selected[first["path"]] == 0
    assert selected[second["path"]] == 1
