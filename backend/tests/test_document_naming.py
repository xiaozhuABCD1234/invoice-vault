"""审核通过后的规范展示名（DESIGN §6）。

覆盖整数分格式化、人员去重、扩展名推断，以及 approve -> 展示名 / 下载 / 预览
与命名失败时的事务回滚。
"""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import unquote

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.documents import naming
from backend.models.document import Document, DocumentVersion
from backend.models.extraction import ExtractionJob
from backend.models.invoice import Invoice

from tests.test_invoices_support import invoice_payload, make_document, make_job


def filename_from_disposition(header: str) -> str:
    assert "filename*=UTF-8''" in header
    encoded = header.split("filename*=UTF-8''", 1)[1].split(";")[0]
    return unquote(encoded)


def _stored_version(db_session, document_id: int) -> tuple[Document, DocumentVersion]:
    db_session.expire_all()
    document = db_session.get(Document, document_id)
    assert document is not None
    version = db_session.get(DocumentVersion, document.current_version_id)
    assert version is not None
    return document, version


def test_format_cents_never_uses_floats():
    assert naming.format_cents(12400) == "124.00"
    assert naming.format_cents(5) == "0.05"
    assert naming.format_cents(0) == "0.00"
    assert naming.format_cents(100) == "1.00"
    assert naming.format_cents(123456789) == "1234567.89"
    assert naming.format_cents(-5) == "-0.05"


def test_person_names_dedupe_and_fallback():
    yang = SimpleNamespace(display_name="杨泽")
    zhu = SimpleNamespace(display_name="朱建诚")

    assert naming.person_names(yang, zhu) == "杨泽,朱建诚"
    assert naming.person_names(yang, yang) == "杨泽"
    assert naming.person_names(yang, None) == "杨泽"
    assert naming.person_names(None, None) == "未指定"
    assert naming.person_names(SimpleNamespace(display_name="  "), None) == "未指定"


def test_version_extension_prefers_storage_key_then_mime():
    assert (
        naming.version_extension(
            SimpleNamespace(storage_key="2026/07/ab/x.JPEG", mime_type="image/jpeg")
        )
        == "jpg"
    )
    assert (
        naming.version_extension(
            SimpleNamespace(storage_key="2026/07/ab/x.PNG", mime_type="image/png")
        )
        == "png"
    )
    assert (
        naming.version_extension(
            SimpleNamespace(storage_key="2026/07/ab/x.bin", mime_type="image/webp")
        )
        == "webp"
    )
    assert naming.version_extension(SimpleNamespace(storage_key="", mime_type="")) == "bin"


def test_build_display_name_matches_design_example():
    version = SimpleNamespace(storage_key="2026/07/ab/x.jpg", mime_type="image/jpeg")
    name = naming.build_display_name(
        total_cents=12400,
        requester=SimpleNamespace(display_name="杨泽"),
        owner=SimpleNamespace(display_name="朱建诚"),
        seller_name="上海站-无锡站",
        category_name="高铁",
        version=version,
    )
    assert name == "124.00-杨泽,朱建诚-上海站-无锡站-高铁-发票.jpg"


def test_approve_generates_canonical_display_name_and_keeps_original(
    user_client: TestClient,
    admin_client: TestClient,
    db_session,
    normal_user,
    admin_user,
    settings,
):
    document = make_document(db_session, settings, owner=normal_user)
    original = document.current_version
    assert original is not None
    original_name = original.original_name
    storage_key = original.storage_key
    version_no = original.version_no

    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session, number="NAME-1001", requester=normal_user, owner=admin_user
    )

    approved = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert approved.status_code == 201, approved.text

    expected = "113.00-普通成员,系统管理员-上海标准件厂-标准件-发票.pdf"
    detail = user_client.get(f"/api/v1/documents/{document.id}")
    assert detail.status_code == 200
    current = detail.json()["document"]["current_version"]
    assert current["display_name"] == expected
    assert current["original_name"] == original_name
    assert current["version_no"] == version_no
    assert detail.json()["version_count"] == 1

    stored_document, stored_version = _stored_version(db_session, document.id)
    assert stored_version.display_name == expected
    assert stored_version.original_name == original_name
    assert stored_version.storage_key == storage_key
    assert stored_version.version_no == version_no
    assert stored_document.current_version_id == stored_version.id

    preview = user_client.get(f"/api/v1/documents/{document.id}/preview")
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "application/pdf"
    assert preview.headers["content-disposition"].startswith("inline")

    download = admin_client.get(f"/api/v1/documents/{document.id}/download")
    assert download.status_code == 200
    disposition = download.headers["content-disposition"]
    assert disposition.startswith("attachment")
    downloaded_name = filename_from_disposition(disposition)
    assert downloaded_name == expected
    assert downloaded_name.endswith(".pdf")


def test_approve_display_name_dedupes_same_person(
    user_client: TestClient, db_session, normal_user, settings
):
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session, number="NAME-2001", requester=normal_user, owner=normal_user
    )

    response = user_client.post(
        f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
    )
    assert response.status_code == 201, response.text

    detail = user_client.get(f"/api/v1/documents/{document.id}").json()
    assert detail["document"]["current_version"]["display_name"] == (
        "113.00-普通成员-上海标准件厂-标准件-发票.pdf"
    )


def test_approve_display_name_failure_rolls_back(
    app,
    user_client: TestClient,
    db_session,
    normal_user,
    settings,
    monkeypatch,
):
    document = make_document(db_session, settings, owner=normal_user)
    job = make_job(db_session, document=document)
    payload = invoice_payload(
        db_session, number="NAME-ROLLBACK", requester=normal_user, owner=normal_user
    )
    _, version_before = _stored_version(db_session, document.id)
    display_before = version_before.display_name

    def _boom(*args, **kwargs):
        raise RuntimeError("naming failed")

    monkeypatch.setattr(naming, "build_for_invoice", _boom)

    with TestClient(app, raise_server_exceptions=False) as raw_client:
        raw_client.headers.update(user_client.headers)
        response = raw_client.post(
            f"/api/v1/extraction-jobs/{job.id}/approve", json=payload
        )

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"

    db_session.expire_all()
    stored_job = db_session.get(ExtractionJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "review_pending"
    assert stored_job.reviewed_by is None
    assert stored_job.review_decision is None

    _, stored_version = _stored_version(db_session, document.id)
    assert stored_version.display_name == display_before

    invoices = list(
        db_session.scalars(
            select(Invoice).where(Invoice.invoice_number == "NAME-ROLLBACK")
        ).all()
    )
    assert invoices == []
