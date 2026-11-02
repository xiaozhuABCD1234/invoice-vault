"""文档预览/下载：鉴权、inline/attachment、文件名扩展名、路径穿越与审计。"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.models.document import Document, DocumentVersion

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 16


def upload_document(client: TestClient, *, content: bytes = PDF_BYTES, filename: str = "invoice.pdf"):
    return client.post(
        "/api/v1/documents",
        files={"file": (filename, content, "application/pdf")},
        data={"doc_type": "invoice"},
    )


def upload_version(client: TestClient, document_id: int, *, content: bytes = PNG_BYTES):
    return client.post(
        f"/api/v1/documents/{document_id}/versions",
        files={"file": ("v2.png", content, "image/png")},
    )


def filename_from_disposition(header: str) -> str:
    assert "filename*=UTF-8''" in header
    encoded = header.split("filename*=UTF-8''", 1)[1].split(";")[0]
    return unquote(encoded)


def test_preview_inline_for_normal_user(user_client):
    document = upload_document(user_client).json()["document"]
    response = user_client.get(f"/api/v1/documents/{document['id']}/preview")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("inline")
    assert "attachment" not in disposition
    assert response.content == PDF_BYTES


def test_preview_user_cannot_select_history_but_admin_can(user_client, admin_client):
    document = upload_document(user_client).json()["document"]
    first_version_id = document["current_version"]["id"]
    assert upload_version(user_client, document["id"]).status_code == 201

    denied = user_client.get(
        f"/api/v1/documents/{document['id']}/preview",
        params={"version_id": first_version_id},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"

    latest = user_client.get(f"/api/v1/documents/{document['id']}/preview")
    assert latest.status_code == 200
    assert latest.headers["content-type"] == "image/png"
    assert latest.content == PNG_BYTES

    history = admin_client.get(
        f"/api/v1/documents/{document['id']}/preview",
        params={"version_id": first_version_id},
    )
    assert history.status_code == 200
    assert history.headers["content-type"] == "application/pdf"
    assert history.content == PDF_BYTES


def test_preview_deleted_document_admin_only(admin_client, user_client):
    document = upload_document(admin_client).json()["document"]
    assert admin_client.delete(f"/api/v1/documents/{document['id']}").status_code == 204

    assert (
        user_client.get(f"/api/v1/documents/{document['id']}/preview").status_code == 404
    )
    admin_preview = admin_client.get(f"/api/v1/documents/{document['id']}/preview")
    assert admin_preview.status_code == 200
    assert admin_preview.content == PDF_BYTES


def test_preview_rejects_invalid_version_parameter(user_client):
    document = upload_document(user_client).json()["document"]
    response = user_client.get(
        f"/api/v1/documents/{document['id']}/preview", params={"version": "2"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_version"


def test_preview_blocks_path_traversal(admin_client, db_session, settings):
    document = upload_document(admin_client).json()["document"]
    db_session.expire_all()
    stored = db_session.get(Document, document["id"])
    version = db_session.get(DocumentVersion, stored.current_version_id)
    version.storage_key = "../escape-secret.txt"
    db_session.commit()

    escape_file = settings.upload_dir.parent / "escape-secret.txt"
    escape_file.write_text("top-secret", encoding="utf-8")
    try:
        response = admin_client.get(f"/api/v1/documents/{document['id']}/preview")
        assert response.status_code == 404
        assert b"top-secret" not in response.content
    finally:
        escape_file.unlink(missing_ok=True)


def test_download_admin_only_with_filename_star(user_client, admin_client):
    document = upload_document(user_client).json()["document"]
    denied = user_client.get(f"/api/v1/documents/{document['id']}/download")
    assert denied.status_code == 403

    downloaded = admin_client.get(f"/api/v1/documents/{document['id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    disposition = downloaded.headers["content-disposition"]
    assert disposition.startswith("attachment")
    filename = filename_from_disposition(disposition)
    assert filename.startswith("待识别-")
    assert filename.endswith(".pdf")
    assert downloaded.content == PDF_BYTES


def test_download_completes_missing_or_wrong_extension(admin_client, db_session):
    document = upload_document(admin_client).json()["document"]
    db_session.expire_all()
    stored = db_session.get(Document, document["id"])
    version = db_session.get(DocumentVersion, stored.current_version_id)

    version.display_name = "旧版本"
    db_session.commit()
    missing_ext = admin_client.get(f"/api/v1/documents/{document['id']}/download")
    assert missing_ext.status_code == 200
    assert filename_from_disposition(
        missing_ext.headers["content-disposition"]
    ).endswith(".pdf")

    version.display_name = "旧版本.png"
    db_session.commit()
    wrong_ext = admin_client.get(f"/api/v1/documents/{document['id']}/download")
    assert wrong_ext.status_code == 200
    assert filename_from_disposition(wrong_ext.headers["content-disposition"]) == "旧版本.pdf"


def test_preview_and_download_write_audit(admin_client, user_client):
    document = upload_document(user_client).json()["document"]
    user_client.get(f"/api/v1/documents/{document['id']}/preview")
    admin_client.get(f"/api/v1/documents/{document['id']}/download")

    preview_logs = admin_client.get(
        "/api/v1/audit-logs", params={"action": "document.preview"}
    ).json()["items"]
    assert any(
        log["entity_id"] == str(document["id"]) for log in preview_logs
    )

    download_logs = admin_client.get(
        "/api/v1/audit-logs", params={"action": "document.download"}
    ).json()["items"]
    assert any(
        log["entity_id"] == str(document["id"]) for log in download_logs
    )


def test_preview_requires_login(client: TestClient):
    assert client.get("/api/v1/documents/1/preview").status_code == 401
    assert client.get("/api/v1/documents/1/download").status_code == 401


def test_preview_rejects_version_from_other_document(admin_client, user_client):
    first = upload_document(user_client).json()["document"]
    second = upload_document(
        admin_client, content=PDF_BYTES + b" % other", filename="other.pdf"
    ).json()["document"]
    response = admin_client.get(
        f"/api/v1/documents/{second['id']}/preview",
        params={"version_id": first["current_version"]["id"]},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "document_version_not_found"
