"""文档上传：类型/大小校验、sha256 去重、入队与文件名处理。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
)
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 16 + b"\xff\xd9"
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16


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


def test_upload_invoice_creates_document_and_queued_job(user_client, normal_user):
    response = upload_document(user_client, title="7月差旅发票")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reused"] is False

    document = body["document"]
    assert document["doc_type"] == "invoice"
    assert document["title"] == "7月差旅发票"
    assert document["owner_user_id"] == normal_user.id
    assert document["owner_name"] == "普通成员"
    assert document["deleted_at"] is None

    version = document["current_version"]
    assert version["version_no"] == 1
    assert version["is_latest"] is True
    assert version["mime_type"] == "application/pdf"
    assert version["size_bytes"] == len(PDF_BYTES)
    assert version["original_name"] == "invoice.pdf"
    assert version["display_name"].startswith("待识别-")
    assert version["display_name"].endswith(".pdf")

    job = body["extraction_job"]
    assert job["status"] == "queued"
    assert job["provider"] == "pdf_text"
    assert job["attempts"] == 0
    assert job["document_id"] == document["id"]
    assert job["document_doc_type"] == "invoice"
    assert job["queued_at"]


def test_upload_payment_evidence_does_not_enqueue(user_client):
    response = upload_document(
        user_client,
        content=PNG_BYTES,
        filename="payment.png",
        content_type="image/png",
        doc_type="payment_evidence",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document"]["doc_type"] == "payment_evidence"
    assert body["document"]["current_version"]["mime_type"] == "image/png"
    assert body["document"]["current_version"]["display_name"].endswith(".png")
    assert body["extraction_job"] is None


def test_upload_requires_login(client: TestClient):
    response = upload_document(client)
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_upload_invalid_doc_type_returns_422(user_client):
    response = upload_document(user_client, doc_type="unknown")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_upload_rejects_oversized_file(user_client, settings):
    settings.max_upload_bytes = 32
    response = upload_document(user_client)
    assert response.status_code == 400
    assert response.json()["code"] == "file_too_large"
    assert response.json()["details"]["max_upload_bytes"] == 32


def test_upload_rejects_disallowed_mime_and_scripts(user_client):
    cases = [
        (b"GIF89a" + b"\x00" * 20, "image/gif", "anim.gif"),
        (b"<html><body>hello</body></html>", "text/html", "page.html"),
        (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', "image/svg+xml", "logo.svg"),
        (b"#!/bin/sh\necho hacked", "application/octet-stream", "run.sh"),
    ]
    for content, content_type, filename in cases:
        response = upload_document(
            user_client, content=content, content_type=content_type, filename=filename
        )
        assert response.status_code == 400, (content_type, response.text)
        assert response.json()["code"] == "invalid_file_type"


def test_upload_rejects_magic_bytes_mismatch(user_client):
    disguised_png = upload_document(
        user_client,
        content=PDF_BYTES,
        content_type="image/png",
        filename="fake.png",
    )
    assert disguised_png.status_code == 400
    assert disguised_png.json()["code"] == "invalid_file_type"
    assert disguised_png.json()["details"]["detected_mime"] == "application/pdf"

    disguised_pdf = upload_document(
        user_client,
        content=PNG_BYTES,
        content_type="application/pdf",
        filename="fake.pdf",
    )
    assert disguised_pdf.status_code == 400
    assert disguised_pdf.json()["code"] == "invalid_file_type"


def test_upload_accepts_jpeg_and_webp(user_client):
    jpeg = upload_document(
        user_client,
        content=JPEG_BYTES,
        filename="photo.jpg",
        content_type="image/jpeg",
        doc_type="receipt",
    )
    assert jpeg.status_code == 201, jpeg.text
    assert jpeg.json()["document"]["current_version"]["mime_type"] == "image/jpeg"

    webp = upload_document(
        user_client,
        content=WEBP_BYTES,
        filename="photo.webp",
        content_type="image/webp",
        doc_type="other",
    )
    assert webp.status_code == 201, webp.text
    assert webp.json()["document"]["current_version"]["mime_type"] == "image/webp"


def test_upload_dedupes_by_sha256(admin_client, user_client):
    first = upload_document(admin_client)
    assert first.status_code == 201
    first_body = first.json()

    second = upload_document(user_client)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["reused"] is True
    assert second_body["document"]["id"] == first_body["document"]["id"]
    assert second_body["extraction_job"]["id"] == first_body["extraction_job"]["id"]

    detail = user_client.get(
        f"/api/v1/documents/{first_body['document']['id']}"
    )
    assert detail.status_code == 200
    assert detail.json()["version_count"] == 1
    assert detail.json()["document"]["owner_user_id"] == first_body["document"]["owner_user_id"]

    listing = user_client.get("/api/v1/documents")
    assert listing.json()["total"] == 1


def test_upload_same_sha_after_soft_delete_returns_409(user_client, admin_client):
    first = upload_document(user_client)
    assert first.status_code == 201, first.text
    document_id = first.json()["document"]["id"]
    assert admin_client.delete(f"/api/v1/documents/{document_id}").status_code == 204

    repeated = upload_document(user_client)
    assert repeated.status_code == 409, repeated.text
    body = repeated.json()
    assert body["code"] == "document_deleted"
    assert "文档已删除" in body["message"]
    assert "联系管理员" in body["message"]
    assert body["details"]["document_id"] == document_id
    assert body["details"]["sha256"]


def test_upload_sanitizes_display_filename(user_client):
    response = upload_document(
        user_client,
        filename="../../evil:na*me?.pdf",
    )
    assert response.status_code == 201, response.text
    version = response.json()["document"]["current_version"]
    assert "/" not in version["original_name"]
    assert "\\" not in version["original_name"]
    assert ".." not in Path(version["original_name"]).parts
    assert version["display_name"].startswith("待识别-")
    assert version["display_name"].endswith(".pdf")


def test_upload_rejects_empty_file(user_client):
    response = upload_document(user_client, content=b"")
    assert response.status_code == 400
    assert response.json()["code"] == "empty_file"
