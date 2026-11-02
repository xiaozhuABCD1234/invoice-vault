"""文档版本上传：sha256 复用、is_latest 切换与软删除保留文件。"""

from __future__ import annotations

from pathlib import Path

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


def _login(app, username: str, password: str) -> TestClient:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def test_upload_version_switches_latest_and_current(user_client, db_session):
    document = upload_document(user_client).json()["document"]
    first_version_id = document["current_version"]["id"]

    response = upload_version(user_client, document["id"])
    assert response.status_code == 201, response.text
    updated = response.json()
    assert updated["current_version"]["version_no"] == 2
    assert updated["current_version"]["is_latest"] is True
    assert updated["current_version"]["mime_type"] == "image/png"
    assert updated["current_version"]["id"] != first_version_id

    detail = user_client.get(f"/api/v1/documents/{document['id']}").json()
    assert detail["version_count"] == 2
    assert detail["document"]["current_version"]["id"] == updated["current_version"]["id"]

    db_session.expire_all()
    stored = db_session.get(Document, document["id"])
    versions = list(
        db_session.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document["id"])
            .order_by(DocumentVersion.version_no)
        ).all()
    )
    assert [version.version_no for version in versions] == [1, 2]
    assert versions[0].is_latest is False
    assert versions[1].is_latest is True
    assert stored.current_version_id == versions[1].id


def test_upload_version_dedupes_same_sha(user_client):
    document = upload_document(user_client).json()["document"]
    first_version_id = document["current_version"]["id"]

    duplicate = upload_version(
        user_client,
        document["id"],
        content=PDF_BYTES,
        filename="same.pdf",
        content_type="application/pdf",
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["current_version"]["id"] == first_version_id
    assert user_client.get(f"/api/v1/documents/{document['id']}").json()["version_count"] == 1


def test_upload_version_reuses_other_document_for_same_sha(admin_client, user_client):
    first = upload_document(admin_client).json()["document"]

    other = upload_document(
        user_client, content=PDF_BYTES + b"\n% other\n", filename="other.pdf"
    ).json()["document"]
    second_version = upload_version(
        user_client,
        other["id"],
        content=PDF_BYTES,
        filename="reuse.pdf",
        content_type="application/pdf",
    )
    assert second_version.status_code == 200, second_version.text
    assert second_version.json()["id"] == first["id"]

    other_detail = user_client.get(f"/api/v1/documents/{other['id']}").json()
    assert other_detail["version_count"] == 1


def test_upload_version_validates_file_type(user_client):
    document = upload_document(user_client).json()["document"]
    disguised = upload_version(
        user_client,
        document["id"],
        content=b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        filename="evil.svg",
        content_type="image/png",
    )
    assert disguised.status_code == 400
    assert disguised.json()["code"] == "invalid_file_type"


def test_upload_version_requires_owner_or_admin(app, user_client, admin_client, make_user):
    document = upload_document(user_client).json()["document"]
    make_user("outsider", "路人", password="outsider-pass-123")
    other = _login(app, "outsider", "outsider-pass-123")
    try:
        denied = upload_version(
            other, document["id"], content=PNG_BYTES, filename="v2.png"
        )
        assert denied.status_code == 403, denied.text
        assert denied.json()["code"] == "forbidden"
    finally:
        other.close()

    allowed = upload_version(
        admin_client, document["id"], content=PNG_BYTES, filename="v2.png"
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["current_version"]["version_no"] == 2


def test_upload_version_deleted_document_returns_404_for_admin(
    user_client, admin_client
):
    document = upload_document(user_client).json()["document"]
    assert admin_client.delete(f"/api/v1/documents/{document['id']}").status_code == 204

    admin_response = upload_version(
        admin_client, document["id"], content=PNG_BYTES, filename="v2.png"
    )
    assert admin_response.status_code == 404
    assert admin_response.json()["code"] == "document_not_found"

    user_response = upload_version(
        user_client, document["id"], content=PNG_BYTES, filename="v2.png"
    )
    assert user_response.status_code == 404


def test_upload_version_sha_from_deleted_document_returns_409(
    user_client, admin_client
):
    first = upload_document(user_client).json()["document"]
    second = upload_document(
        user_client, content=PDF_BYTES + b"\n% second\n", filename="second.pdf"
    ).json()["document"]
    assert admin_client.delete(f"/api/v1/documents/{first['id']}").status_code == 204

    response = upload_version(
        user_client,
        second["id"],
        content=PDF_BYTES,
        filename="reuse.pdf",
        content_type="application/pdf",
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "document_deleted"
    assert "文档已删除" in body["message"]
    assert "联系管理员" in body["message"]
    assert body["details"]["document_id"] == first["id"]

    detail = user_client.get(f"/api/v1/documents/{second['id']}").json()
    assert detail["version_count"] == 1


def test_version_upload_and_delete_permissions(client, user_client, admin_client):
    assert client.post("/api/v1/documents/1/versions").status_code == 401

    document = upload_document(user_client).json()["document"]
    denied = user_client.delete(f"/api/v1/documents/{document['id']}")
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"

    deleted = admin_client.delete(f"/api/v1/documents/{document['id']}")
    assert deleted.status_code == 204


def test_soft_delete_keeps_file_on_disk(admin_client, db_session, settings):
    document = upload_document(admin_client).json()["document"]
    db_session.expire_all()
    stored = db_session.get(Document, document["id"])
    version = db_session.get(DocumentVersion, stored.current_version_id)
    path = Path(settings.upload_dir) / version.storage_key
    assert path.is_file()

    assert admin_client.delete(f"/api/v1/documents/{document['id']}").status_code == 204
    assert path.is_file()

    db_session.expire_all()
    assert db_session.get(Document, document["id"]).deleted_at is not None
