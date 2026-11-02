"""抽取任务：处理、列表/详情、重试、驳回与 worker。"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend import worker
from backend.extraction import service as extraction_service
from backend.models.extraction import ExtractionJob
from backend.shared.db import utcnow

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def upload_invoice(
    client: TestClient,
    *,
    content: bytes = PDF_BYTES,
    filename: str = "invoice.pdf",
    title: str | None = None,
):
    data: dict[str, str] = {"doc_type": "invoice"}
    if title is not None:
        data["title"] = title
    return client.post(
        "/api/v1/documents",
        files={"file": (filename, content, "application/pdf")},
        data=data,
    )


def create_job(
    client: TestClient,
    *,
    content: bytes = PDF_BYTES,
    filename: str = "invoice.pdf",
) -> tuple[int, int]:
    body = upload_invoice(client, content=content, filename=filename).json()
    return body["document"]["id"], body["extraction_job"]["id"]


def test_process_job_with_mock_provider(user_client, db_session, settings, monkeypatch):
    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "mock")
    document_id, job_id = create_job(user_client)

    job = extraction_service.process_job(db_session, job_id, settings=settings)
    assert job.status == "review_pending"
    assert job.provider == "mock"
    assert job.model == "mock-v1"
    assert job.prompt_version == "mock-v1"
    assert job.attempts == 0
    assert job.started_at is not None and job.finished_at is not None
    assert job.raw_text
    assert job.parsed_json["invoice_number"] == "24512000000012345678"
    assert job.parsed_json["total_cents"] == 11300
    assert job.parsed_json["items"][0]["amount_cents"] == 10000
    assert job.validation_json["errors"] == []
    assert job.validation_json["warnings"] == []
    assert job.validation_json["field_confidence"]["invoice_number"] == 0.95
    assert job.confidence == 0.95

    detail = user_client.get(f"/api/v1/extraction-jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["job"]["status"] == "review_pending"
    assert payload["job"]["parsed"]["invoice_number"] == "24512000000012345678"
    assert payload["job"]["validation"]["field_confidence"]["total_cents"] == 0.95
    assert payload["document"]["id"] == document_id
    assert payload["diff"] is None


def test_worker_once_processes_one_job(user_client, db_session, settings, monkeypatch):
    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "mock")
    first = create_job(user_client, filename="a.pdf")
    second = create_job(user_client, content=PDF_BYTES + b"\n% second\n", filename="b.pdf")

    first_job = worker.run_once(db_session, settings=settings)
    assert first_job is not None
    assert first_job.status == "review_pending"

    remaining = user_client.get(
        "/api/v1/extraction-jobs", params={"status": "queued"}
    ).json()
    assert remaining["total"] == 1
    assert remaining["items"][0]["id"] in {first[1], second[1]}

    second_job = worker.run_once(db_session, settings=settings)
    assert second_job is not None
    assert second_job.id != first_job.id
    assert second_job.status == "review_pending"

    assert (
        user_client.get("/api/v1/extraction-jobs", params={"status": "queued"}).json()[
            "total"
        ]
        == 0
    )
    assert worker.run_once(db_session, settings=settings) is None


def test_worker_resets_stale_running_jobs(user_client, db_session, settings):
    _, job_id = create_job(user_client)
    job = db_session.get(ExtractionJob, job_id)
    job.status = "running"
    job.started_at = utcnow() - timedelta(hours=2)
    db_session.commit()

    recovered = worker.reset_stale_running(db_session, stale_minutes=15)
    assert recovered == 1
    db_session.expire_all()
    refreshed = db_session.get(ExtractionJob, job_id)
    assert refreshed.status == "queued"
    assert refreshed.started_at is None
    assert refreshed.error_code == "worker_recovered"


def test_failure_retries_and_attempt_limit(user_client, db_session, settings, monkeypatch):
    monkeypatch.delenv("IV_EXTRACTION_PROVIDER", raising=False)
    _, job_id = create_job(user_client)

    first = extraction_service.process_job(db_session, job_id, settings=settings)
    assert first.status == "queued"
    assert first.attempts == 1
    assert first.error_code == "pdf_text_failed"
    assert first.queued_at > utcnow()

    second = extraction_service.process_job(db_session, job_id, settings=settings)
    assert second.status == "queued"
    assert second.attempts == 2

    third = extraction_service.process_job(db_session, job_id, settings=settings)
    assert third.status == "failed"
    assert third.attempts == 3
    assert third.finished_at is not None

    retry = user_client.post(f"/api/v1/extraction-jobs/{job_id}/retry")
    assert retry.status_code == 409
    assert retry.json()["code"] == "job_attempts_exceeded"


def test_retry_status_and_permissions(admin_client, user_client, db_session, monkeypatch):
    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "mock")
    _, own_job_id = create_job(user_client)

    queued = user_client.post(f"/api/v1/extraction-jobs/{own_job_id}/retry")
    assert queued.status_code == 409
    assert queued.json()["code"] == "job_running"

    job = db_session.get(ExtractionJob, own_job_id)
    job.status = "review_pending"
    db_session.commit()

    retried = user_client.post(f"/api/v1/extraction-jobs/{own_job_id}/retry")
    assert retried.status_code == 202, retried.text
    assert retried.json()["status"] == "queued"
    assert retried.json()["attempts"] == 0

    job = db_session.get(ExtractionJob, own_job_id)
    job.status = "running"
    db_session.commit()
    assert user_client.post(
        f"/api/v1/extraction-jobs/{own_job_id}/retry"
    ).status_code == 409

    job.status = "approved"
    db_session.commit()
    not_retryable = user_client.post(f"/api/v1/extraction-jobs/{own_job_id}/retry")
    assert not_retryable.status_code == 409
    assert not_retryable.json()["code"] == "job_not_retryable"

    _, admin_job_id = create_job(
        admin_client, content=PDF_BYTES + b" % admin", filename="admin.pdf"
    )
    admin_job = db_session.get(ExtractionJob, admin_job_id)
    admin_job.status = "review_pending"
    db_session.commit()

    forbidden = user_client.post(f"/api/v1/extraction-jobs/{admin_job_id}/retry")
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"

    allowed = admin_client.post(f"/api/v1/extraction-jobs/{admin_job_id}/retry")
    assert allowed.status_code == 202


def test_reject_flow_permissions_and_audit(
    admin_client, user_client, normal_user, db_session, monkeypatch
):
    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "mock")
    _, job_id = create_job(user_client)
    job = db_session.get(ExtractionJob, job_id)
    job.status = "review_pending"
    db_session.commit()

    empty = user_client.post(
        f"/api/v1/extraction-jobs/{job_id}/reject", json={"note": ""}
    )
    assert empty.status_code == 422

    blank = user_client.post(
        f"/api/v1/extraction-jobs/{job_id}/reject", json={"note": "   "}
    )
    assert blank.status_code == 400
    assert blank.json()["code"] == "invalid_note"

    rejected = user_client.post(
        f"/api/v1/extraction-jobs/{job_id}/reject", json={"note": "票面模糊，无法确认"}
    )
    assert rejected.status_code == 200, rejected.text
    payload = rejected.json()
    assert payload["status"] == "rejected"
    assert payload["review_decision"] == "rejected"
    assert payload["review_note"] == "票面模糊，无法确认"
    assert payload["reviewed_by"] == normal_user.id
    assert payload["reviewed_at"] is not None

    again = user_client.post(
        f"/api/v1/extraction-jobs/{job_id}/reject", json={"note": "重复"}
    )
    assert again.status_code == 409
    assert again.json()["code"] == "job_not_reviewable"

    _, admin_job_id = create_job(
        admin_client, content=PDF_BYTES + b" % admin", filename="admin.pdf"
    )
    admin_job = db_session.get(ExtractionJob, admin_job_id)
    admin_job.status = "review_pending"
    db_session.commit()
    forbidden = user_client.post(
        f"/api/v1/extraction-jobs/{admin_job_id}/reject", json={"note": "越权"}
    )
    assert forbidden.status_code == 403

    logs = admin_client.get(
        "/api/v1/audit-logs", params={"action": "job.reject"}
    ).json()["items"]
    assert any(log["entity_id"] == str(job_id) for log in logs)


def test_job_list_filters_and_visibility(admin_client, user_client, db_session):
    user_doc_id, user_job_id = create_job(user_client)
    _, admin_job_id = create_job(
        admin_client, content=PDF_BYTES + b"\n% admin\n", filename="admin.pdf"
    )
    _, failed_job_id = create_job(
        user_client, content=PDF_BYTES + b"\n% failed\n", filename="c.pdf"
    )

    failed = db_session.get(ExtractionJob, failed_job_id)
    failed.status = "failed"
    failed.attempts = 3
    failed.error_code = "pdf_text_failed"
    db_session.commit()

    all_jobs = user_client.get("/api/v1/extraction-jobs").json()
    assert all_jobs["total"] == 3
    assert {item["id"] for item in all_jobs["items"]} == {
        user_job_id,
        admin_job_id,
        failed_job_id,
    }

    assert user_client.get(
        "/api/v1/extraction-jobs", params={"status": "failed"}
    ).json()["total"] == 1
    assert user_client.get(
        "/api/v1/extraction-jobs", params={"status": "queued"}
    ).json()["total"] == 2
    assert user_client.get(
        "/api/v1/extraction-jobs", params={"document_id": user_doc_id}
    ).json()["total"] == 1
    assert user_client.get(
        "/api/v1/extraction-jobs", params={"provider": "mock"}
    ).json()["total"] == 0

    paged = user_client.get(
        "/api/v1/extraction-jobs", params={"page": 1, "page_size": 2}
    ).json()
    assert paged["total"] == 3
    assert len(paged["items"]) == 2


def test_job_detail_diff_against_previous_approved(
    user_client, admin_user, db_session
):
    document_id, job_id = create_job(user_client)

    job = db_session.get(ExtractionJob, job_id)
    job.status = "approved"
    job.reviewed_by = admin_user.id
    job.reviewed_at = utcnow()
    job.review_decision = "approved"
    job.parsed_json = {"invoice_number": "11112222", "total_cents": 100}
    db_session.commit()

    newer = ExtractionJob(
        document_id=document_id,
        provider="mock",
        status="review_pending",
        queued_at=utcnow() + timedelta(seconds=1),
        parsed_json={
            "invoice_number": "33334444",
            "total_cents": 100,
            "seller_name": "新商户",
        },
    )
    db_session.add(newer)
    db_session.commit()
    db_session.refresh(newer)

    detail = user_client.get(f"/api/v1/extraction-jobs/{newer.id}").json()
    assert detail["diff"]["against_job_id"] == job_id
    assert detail["diff"]["fields"]["invoice_number"] == {
        "before": "11112222",
        "after": "33334444",
    }
    assert detail["diff"]["fields"]["seller_name"] == {
        "before": None,
        "after": "新商户",
    }
    assert "total_cents" not in detail["diff"]["fields"]
    assert detail["document"]["id"] == document_id

    old_detail = user_client.get(f"/api/v1/extraction-jobs/{job_id}").json()
    assert old_detail["diff"] is None


def test_job_not_found_and_requires_login(client, user_client):
    assert client.get("/api/v1/extraction-jobs").status_code == 401
    missing = user_client.get("/api/v1/extraction-jobs/999999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "job_not_found"


def test_retry_preserves_attempts_below_limit(user_client, db_session):
    _, job_id = create_job(user_client)
    job = db_session.get(ExtractionJob, job_id)
    job.status = "failed"
    job.attempts = 2
    job.error_code = "pdf_text_failed"
    job.error_message = "boom"
    db_session.commit()

    response = user_client.post(f"/api/v1/extraction-jobs/{job_id}/retry")
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["attempts"] == 2
    assert payload["error_code"] is None
    assert payload["error_message"] is None

    queued_reject = user_client.post(
        f"/api/v1/extraction-jobs/{job_id}/reject", json={"note": "还没跑完"}
    )
    assert queued_reject.status_code == 409
    assert queued_reject.json()["code"] == "job_not_reviewable"
