"""文档列表、详情与软删除可见性。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.models.document import Document

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 16
PDF_ALT_BYTES = PDF_BYTES + b"\n% third invoice\n"


def upload_document(
    client: TestClient,
    *,
    content: bytes = PDF_BYTES,
    filename: str = "invoice.pdf",
    content_type: str = "application/pdf",
    doc_type: str = "invoice",
    title: str | None = None,
):
    data: dict[str, str] = {"doc_type": doc_type}
    if title is not None:
        data["title"] = title
    return client.post(
        "/api/v1/documents",
        files={"file": (filename, content, content_type)},
        data=data,
    )


def upload_version(
    client: TestClient,
    document_id: int,
    *,
    content: bytes = PNG_BYTES,
    filename: str = "v2.png",
    content_type: str = "image/png",
):
    return client.post(
        f"/api/v1/documents/{document_id}/versions",
        files={"file": (filename, content, content_type)},
    )


def test_list_filters_by_doc_type_q_and_pagination(user_client):
    first = upload_document(user_client, title="差旅发票").json()["document"]
    second = upload_document(
        user_client,
        content=PNG_BYTES,
        filename="酒店水单.png",
        content_type="image/png",
        doc_type="payment_evidence",
        title="酒店水单",
    ).json()["document"]
    third = upload_document(
        user_client,
        content=PDF_ALT_BYTES,
        filename="打车发票-7月.pdf",
        title=None,
    ).json()["document"]

    listing = user_client.get("/api/v1/documents")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]

    payment_only = user_client.get(
        "/api/v1/documents", params={"doc_type": "payment_evidence"}
    ).json()
    assert payment_only["total"] == 1
    assert payment_only["items"][0]["id"] == second["id"]

    searched_title = user_client.get("/api/v1/documents", params={"q": "差旅"}).json()
    assert [item["id"] for item in searched_title["items"]] == [first["id"]]

    searched_filename = user_client.get(
        "/api/v1/documents", params={"q": "打车"}
    ).json()
    assert [item["id"] for item in searched_filename["items"]] == [third["id"]]

    page_one = user_client.get(
        "/api/v1/documents", params={"page": 1, "page_size": 1}
    ).json()
    page_two = user_client.get(
        "/api/v1/documents", params={"page": 2, "page_size": 1}
    ).json()
    assert page_one["total"] == 3
    assert len(page_one["items"]) == 1
    assert page_one["items"][0]["id"] != page_two["items"][0]["id"]


def test_detail_returns_versions_and_jobs(user_client):
    document = upload_document(user_client).json()["document"]
    version_response = upload_version(user_client, document["id"])
    assert version_response.status_code == 201, version_response.text
    assert version_response.json()["current_version"]["version_no"] == 2

    detail = user_client.get(f"/api/v1/documents/{document['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["version_count"] == 2
    assert body["document"]["current_version"]["version_no"] == 2
    assert body["document"]["current_version"]["is_latest"] is True
    assert len(body["extraction_jobs"]) == 1
    assert body["extraction_jobs"][0]["document_id"] == document["id"]


def test_missing_document_returns_404(user_client):
    assert user_client.get("/api/v1/documents/999999").status_code == 404
    assert user_client.get("/api/v1/documents/999999").json()["code"] == "document_not_found"


def test_list_and_detail_require_login(client: TestClient):
    assert client.get("/api/v1/documents").status_code == 401
    assert client.get("/api/v1/documents/1").status_code == 401


def test_soft_delete_visibility(admin_client, user_client, db_session):
    document = upload_document(admin_client).json()["document"]

    user_forbidden = user_client.delete(f"/api/v1/documents/{document['id']}")
    assert user_forbidden.status_code == 403

    deleted = admin_client.delete(f"/api/v1/documents/{document['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    db_session.expire_all()
    stored = db_session.get(Document, document["id"])
    assert stored is not None and stored.deleted_at is not None

    assert user_client.get("/api/v1/documents").json()["total"] == 0
    assert admin_client.get("/api/v1/documents").json()["total"] == 0

    with_deleted = admin_client.get(
        "/api/v1/documents", params={"include_deleted": True}
    ).json()
    assert with_deleted["total"] == 1
    assert with_deleted["items"][0]["deleted_at"] is not None

    user_with_deleted = user_client.get(
        "/api/v1/documents", params={"include_deleted": True}
    ).json()
    assert user_with_deleted["total"] == 0

    assert user_client.get(f"/api/v1/documents/{document['id']}").status_code == 404
    admin_detail = admin_client.get(f"/api/v1/documents/{document['id']}")
    assert admin_detail.status_code == 200
    assert admin_detail.json()["document"]["deleted_at"] is not None


def test_detail_jobs_sorted_by_queued_at_desc(user_client, db_session):
    from datetime import timedelta

    from backend.models.extraction import ExtractionJob
    from backend.shared.db import utcnow

    document = upload_document(
        user_client,
        content=PNG_BYTES,
        filename="evidence.png",
        content_type="image/png",
        doc_type="payment_evidence",
    ).json()["document"]
    older = ExtractionJob(
        document_id=document["id"],
        provider="pdf_text",
        status="failed",
        attempts=3,
        queued_at=utcnow() - timedelta(days=1),
    )
    newer = ExtractionJob(
        document_id=document["id"],
        provider="pdf_text",
        status="queued",
        queued_at=utcnow() + timedelta(seconds=1),
    )
    db_session.add_all([older, newer])
    db_session.commit()
    db_session.refresh(older)
    db_session.refresh(newer)

    detail = user_client.get(f"/api/v1/documents/{document['id']}").json()
    job_ids = [job["id"] for job in detail["extraction_jobs"]]
    assert job_ids[0] == newer.id
    assert job_ids[1] == older.id
