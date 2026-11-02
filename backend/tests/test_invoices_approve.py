"""抽取任务审核通过（approve）与事务回滚。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.audit import AuditLog
from backend.models.extraction import ExtractionJob
from backend.models.invoice import Invoice

from tests.test_invoices_support import (
    audit_actions,
    create_invoice,
    invoice_payload,
    make_document,
    make_job,
)


def _invoice_count(db: Session, number: str | None = None) -> int:
    stmt = select(func.count()).select_from(Invoice)
    if number is not None:
        stmt = stmt.where(Invoice.invoice_number == number)
    return int(db.scalar(stmt) or 0)


def test_approve_job_creates_active_invoice(
    user_client: TestClient, db_session: Session, normal_user, settings
):
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session,
        number="APV-1001",
        requester=normal_user,
        owner=normal_user,
    )

    response = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert response.status_code == 201, response.text
    data = response.json()
    invoice = data["invoice"]
    job_out = data["job"]

    assert invoice["status"] == "active"
    assert invoice["invoice_number"] == "APV-1001"
    assert invoice["source_document_id"] == document.id
    assert invoice["extraction_job_id"] == job.id
    assert invoice["created_by"] == normal_user.id
    assert invoice["confirmed_by"] == normal_user.id
    assert invoice["confirmed_at"] is not None
    assert invoice["payment_status"] == "unpaid"
    assert invoice["paid_cents"] == 0
    assert [item["name"] for item in invoice["items"]] == ["螺栓", "螺母"]
    assert [item["sort_order"] for item in invoice["items"]] == [1, 2]

    assert job_out["id"] == job.id
    assert job_out["status"] == "approved"
    assert job_out["reviewed_by"] == normal_user.id
    assert job_out["reviewed_at"] is not None
    assert job_out["review_decision"] == "approved"
    assert job_out["document_id"] == document.id

    db_session.expire_all()
    stored_job = db_session.get(ExtractionJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "approved"
    assert stored_job.reviewed_by == normal_user.id
    assert stored_job.reviewed_at is not None
    assert stored_job.review_decision == "approved"

    stored_invoice = db_session.get(Invoice, invoice["id"])
    assert stored_invoice is not None
    assert stored_invoice.source_document_id == document.id
    assert stored_invoice.extraction_job_id == job.id
    assert stored_invoice.status == "active"

    actions = audit_actions(db_session)
    assert "job.approve" in actions
    assert "invoice.create" in actions
    job_log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "job.approve")
    )
    assert job_log is not None
    assert job_log.entity_type == "extraction_job"
    assert job_log.entity_id == str(job.id)
    assert job_log.before_json["status"] == "review_pending"
    assert job_log.after_json["status"] == "approved"


def test_approve_job_permission_denied_then_admin_allowed(
    user_client: TestClient,
    admin_client: TestClient,
    db_session: Session,
    make_user,
    settings,
):
    owner = make_user("uploader", "上传者")
    document = make_document(db_session, settings, owner=owner)
    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session, number="APV-2001", requester=owner, owner=owner
    )

    denied = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"

    db_session.expire_all()
    pending_job = db_session.get(ExtractionJob, job.id)
    assert pending_job is not None
    assert pending_job.status == "review_pending"
    assert pending_job.reviewed_by is None
    assert _invoice_count(db_session, "APV-2001") == 0

    allowed = admin_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["job"]["status"] == "approved"
    assert allowed.json()["invoice"]["status"] == "active"


def test_approve_job_not_review_pending_409(
    user_client: TestClient, db_session: Session, normal_user, settings
):
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document, status_value="running")
    payload = invoice_payload(db_session, number="APV-3001")

    response = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "job_not_review_pending"
    assert body["details"]["status"] == "running"

    db_session.expire_all()
    stored_job = db_session.get(ExtractionJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "running"
    assert stored_job.reviewed_by is None
    assert _invoice_count(db_session, "APV-3001") == 0


def test_approve_job_duplicate_invoice_number_rolls_back(
    admin_client: TestClient,
    db_session: Session,
    admin_user,
    normal_user,
    settings,
):
    create_invoice(
        admin_client, db_session, number="APV-DUP", requester=admin_user
    )
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document)
    payload = invoice_payload(db_session, number="APV-DUP")

    response = admin_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invoice_duplicate"

    db_session.expire_all()
    assert _invoice_count(db_session, "APV-DUP") == 1
    stored_job = db_session.get(ExtractionJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "review_pending"
    assert stored_job.reviewed_by is None
    assert stored_job.review_decision is None
    db_session.expire_all()
    assert "job.approve" not in audit_actions(db_session)


def test_approve_job_invalid_payload_leaves_job_pending(
    user_client: TestClient, db_session: Session, normal_user, settings
):
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session, number="APV-4001", category_id=999999
    )

    response = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert response.status_code == 404
    assert response.json()["code"] == "category_not_found"

    db_session.expire_all()
    stored_job = db_session.get(ExtractionJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "review_pending"
    assert stored_job.reviewed_by is None
    assert _invoice_count(db_session, "APV-4001") == 0


def test_approve_deleted_document_returns_409(
    admin_client: TestClient,
    user_client: TestClient,
    db_session: Session,
    normal_user,
    settings,
):
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session, number="APV-DELETED", requester=normal_user, owner=normal_user
    )

    assert admin_client.delete(f"/api/v1/documents/{document.id}").status_code == 204

    response = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "document_deleted"
    assert body["details"]["document_id"] == document.id

    db_session.expire_all()
    stored_job = db_session.get(ExtractionJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "review_pending"
    assert stored_job.reviewed_by is None
    assert stored_job.reviewed_at is None
    assert stored_job.review_decision is None
    assert _invoice_count(db_session, "APV-DELETED") == 0
    assert "job.approve" not in audit_actions(db_session)


def test_approve_requires_login_and_known_job(
    client: TestClient, user_client: TestClient, db_session: Session
):
    payload = invoice_payload(db_session, number="APV-5001")

    unauthenticated = client.post(
        "/api/v1/extraction-jobs/1/approve", json=payload
    )
    assert unauthenticated.status_code == 401

    missing = user_client.post(
        "/api/v1/extraction-jobs/999999/approve", json=payload
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "extraction_job_not_found"
