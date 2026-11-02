"""worker 启动恢复、退避与 --once CLI。"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend import worker
from backend.extraction.config import ExtractionConfig
from backend.models.extraction import ExtractionJob
from backend.shared.db import utcnow

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def upload_invoice(client: TestClient, *, content: bytes = PDF_BYTES, filename: str = "invoice.pdf"):
    body = client.post(
        "/api/v1/documents",
        files={"file": (filename, content, "application/pdf")},
        data={"doc_type": "invoice"},
    ).json()
    return body["document"]["id"], body["extraction_job"]["id"]


def test_worker_main_once_processes_one_job(user_client, settings, db_session, monkeypatch):
    first = upload_invoice(user_client, filename="a.pdf")
    second = upload_invoice(
        user_client, content=PDF_BYTES + b" % second", filename="b.pdf"
    )

    config = ExtractionConfig(provider="mock", upload_dir=settings.upload_dir)
    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "mock")
    assert worker.main(["--once"], settings=settings, config=config) == 0

    db_session.expire_all()
    jobs = {
        job.id: job
        for job in db_session.scalars(select(ExtractionJob)).all()
    }
    statuses = sorted(jobs[job_id].status for job_id in (first[1], second[1]))
    assert statuses == ["queued", "review_pending"]
    processed = next(
        job for job in jobs.values() if job.status == "review_pending"
    )
    assert processed.provider == "mock"
    assert processed.parsed_json["invoice_number"] == "24512000000012345678"


def test_worker_main_once_recovers_stale_running(user_client, settings, db_session):
    _, job_id = upload_invoice(user_client)
    job = db_session.get(ExtractionJob, job_id)
    job.status = "running"
    job.started_at = utcnow() - timedelta(hours=3)
    db_session.commit()

    config = ExtractionConfig(provider="mock", upload_dir=settings.upload_dir)
    assert worker.main(["--once"], settings=settings, config=config) == 0

    db_session.expire_all()
    recovered = db_session.get(ExtractionJob, job_id)
    assert recovered.status == "review_pending"
    assert recovered.provider == "mock"


def test_run_once_skips_jobs_in_backoff(user_client, settings, db_session):
    _, job_id = upload_invoice(user_client)
    job = db_session.get(ExtractionJob, job_id)
    job.status = "queued"
    job.queued_at = utcnow() + timedelta(minutes=5)
    db_session.commit()

    config = ExtractionConfig(provider="mock", upload_dir=settings.upload_dir)
    assert worker.run_once(db_session, settings=settings, config=config) is None
    db_session.expire_all()
    assert db_session.get(ExtractionJob, job_id).status == "queued"
