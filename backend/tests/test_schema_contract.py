"""模型、Schema、OpenAPI、存储与数据库基础设施契约。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend import models  # noqa: F401
from backend.models import (
    AuditLog,
    Category,
    Document,
    DocumentVersion,
    ExportJob,
    ExtractionJob,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentAllocation,
    ReconciliationNote,
    RefreshToken,
    ReportTemplate,
    User,
)
from backend.schemas import (
    AuditLogOut,
    CategoryOut,
    DashboardSummary,
    DocumentDetail,
    DocumentOut,
    DocumentVersionOut,
    ExportJobOut,
    ExtractionJobDetail,
    ExtractionJobOut,
    InvoiceCreate,
    InvoiceListItem,
    InvoiceOut,
    Page,
    PaymentDetail,
    PaymentOut,
    ReconciliationIssue,
    ReconciliationSummary,
    ReportTemplateOut,
    TokenResponse,
    UserOption,
    UserOut,
)
from backend.shared.db import Base
from backend.shared.storage import resolve_path, sanitize_filename, save_bytes


EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "person_aliases",
    "categories",
    "documents",
    "document_versions",
    "extraction_jobs",
    "invoices",
    "invoice_items",
    "payments",
    "payment_allocations",
    "report_templates",
    "export_jobs",
    "audit_logs",
    "reconciliation_notes",
}


def test_metadata_contains_all_tables():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_expected_model_columns():
    assert {"failed_attempts", "locked_until", "token_version"} <= set(
        User.__table__.columns.keys()
    )
    assert {"token_hash", "expires_at", "revoked_at", "token_version", "user_agent", "ip"} <= set(
        RefreshToken.__table__.columns.keys()
    )
    assert {"sha256", "storage_key", "is_latest", "version_no"} <= set(
        DocumentVersion.__table__.columns.keys()
    )
    assert {
        "provider",
        "model",
        "prompt_version",
        "status",
        "attempts",
        "raw_text",
        "raw_response_json",
        "parsed_json",
        "confidence",
        "error_code",
        "error_message",
        "queued_at",
        "started_at",
        "finished_at",
        "reviewed_by",
        "reviewed_at",
        "review_decision",
        "review_note",
        "document_id",
    } <= set(ExtractionJob.__table__.columns.keys())
    assert {"paid_cents", "payment_status", "invoice_number", "issue_date"} <= set(
        Invoice.__table__.columns.keys()
    )
    assert {"file_document_id", "expires_at", "file_path", "file_name"} <= set(
        ExportJob.__table__.columns.keys()
    )


def test_partial_unique_index_exists(app):
    with app.state.engine.connect() as connection:
        sql = connection.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'index' AND name = 'uq_payment_allocations_active'"
            )
        ).scalar()
    assert sql is not None
    assert "WHERE status = 'active'" in sql


def test_sqlite_pragmas(db_session: Session):
    assert db_session.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert str(db_session.execute(text("PRAGMA journal_mode")).scalar()).lower() == "wal"
    assert db_session.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_openapi_generates(app):
    spec = app.openapi()
    paths = spec["paths"]
    expected_paths = {
        "/healthz",
        "/readyz",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/me",
        "/api/v1/users",
        "/api/v1/users/options",
        "/api/v1/users/{user_id}",
        "/api/v1/categories",
        "/api/v1/categories/{category_id}",
        "/api/v1/audit-logs",
    }
    assert expected_paths <= set(paths)
    components = spec["components"]["schemas"]
    for name in ("UserOut", "TokenResponse", "CategoryOut", "AuditLogOut"):
        assert name in components
    assert any(name.startswith("Page_") for name in components)

    # 占位领域尚未注册路由，这里直接验证 schema 均可生成 JSON Schema。
    for schema in (
        InvoiceOut,
        InvoiceListItem,
        PaymentOut,
        DocumentOut,
        ExtractionJobOut,
        ReportTemplateOut,
        ReconciliationSummary,
        DashboardSummary,
    ):
        generated = schema.model_json_schema()
        assert generated["title"] == schema.__name__


def test_health_and_trace_header(client: TestClient):
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert health.headers.get("X-Trace-Id")

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    traced = client.get("/healthz", headers={"X-Trace-Id": "trace-test-123"})
    assert traced.headers["X-Trace-Id"] == "trace-test-123"


def test_error_envelope(client: TestClient):
    unauthorized = client.get("/api/v1/me")
    body = unauthorized.json()
    assert set(body) == {"code", "message", "details", "trace_id"}
    assert unauthorized.headers.get("X-Trace-Id")

    missing = client.get("/api/v1/nonexistent")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert missing.json()["message"] == "请求的资源不存在"

    validation = client.get("/healthz", params={"unused": 1})
    assert validation.status_code == 200


def test_invoice_create_amount_validation():
    base = {
        "invoice_number": "INV-1",
        "issue_date": "2026-07-12",
        "seller_name": "店铺",
        "amount_ex_tax_cents": 10000,
        "tax_cents": 1300,
        "total_cents": 11300,
        "category_id": 1,
        "items": [],
    }
    model = InvoiceCreate(**base)
    assert model.total_cents == 11300

    with pytest.raises(ValidationError):
        InvoiceCreate(**{**base, "total_cents": 12000})


def test_schema_exports_and_configs():
    assert Page[UserOut].model_fields.keys() == {"items", "total", "page", "page_size"}
    assert "password_hash" not in UserOut.model_fields
    assert UserOut.model_config.get("from_attributes") is True
    assert InvoiceOut.model_config.get("from_attributes") is True
    assert TokenResponse.model_fields["token_type"].default == "bearer"
    for schema in (
        UserOption,
        CategoryOut,
        DocumentVersionOut,
        DocumentOut,
        DocumentDetail,
        ExtractionJobOut,
        ExtractionJobDetail,
        InvoiceListItem,
        PaymentOut,
        PaymentDetail,
        ReconciliationSummary,
        ReconciliationIssue,
        ReportTemplateOut,
        ExportJobOut,
        AuditLogOut,
        DashboardSummary,
    ):
        assert schema.model_config.get("from_attributes") is True


def test_storage_helpers(tmp_path: Path, settings):
    payload = b"%PDF-1.4 fake invoice"
    first = save_bytes(payload, "pdf", settings=settings)
    second = save_bytes(payload, "pdf", settings=settings)
    assert first["storage_key"] == second["storage_key"]
    assert first["sha256"] == second["sha256"]
    assert first["size_bytes"] == len(payload)

    key = first["storage_key"]
    assert key.startswith(f"{datetime.now(UTC).year:04d}/")
    path = resolve_path(key, settings=settings)
    assert path.read_bytes() == payload
    assert str(path).startswith(str(settings.upload_dir.resolve()))

    with pytest.raises(ValueError):
        resolve_path("../escape.txt", settings=settings)
    with pytest.raises(ValueError):
        resolve_path("/etc/passwd", settings=settings)

    assert sanitize_filename('  foo/bar:baz*?.pdf  ') == "foo_bar_baz__.pdf"
    assert len(sanitize_filename("长" * 500 + ".pdf")) <= 150


def test_orm_models_importable_and_mapped():
    for model in (
        User,
        RefreshToken,
        Category,
        Document,
        DocumentVersion,
        ExtractionJob,
        Invoice,
        InvoiceItem,
        Payment,
        PaymentAllocation,
        ReportTemplate,
        ExportJob,
        AuditLog,
        ReconciliationNote,
    ):
        assert hasattr(model, "__tablename__")
        assert model.__table__ is not None
