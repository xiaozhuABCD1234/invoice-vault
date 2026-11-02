"""安全与一致性回归：分页上限、统一错误结构与写接口授权。

普通用户下载/历史版本/软删除/越权审核等既有边界由
test_documents_preview_download.py 与 test_invoices_approve.py 覆盖。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_invoices_support import create_invoice, invoice_payload

USER_LIST_ENDPOINTS = [
    "/api/v1/documents",
    "/api/v1/extraction-jobs",
    "/api/v1/invoices",
    "/api/v1/payments",
    "/api/v1/reconciliation/issues",
    "/api/v1/exports",
]

ADMIN_LIST_ENDPOINTS = [
    "/api/v1/users",
    "/api/v1/audit-logs",
]


@pytest.mark.parametrize("path", USER_LIST_ENDPOINTS)
def test_user_page_size_above_limit_is_validation_error(
    user_client: TestClient, path: str
):
    response = user_client.get(path, params={"page_size": 101})
    assert response.status_code == 422, (path, response.text)
    body = response.json()
    assert set(body) == {"code", "message", "details", "trace_id"}
    assert body["code"] == "validation_error"
    assert body["trace_id"]
    locations = [error["loc"] for error in body["details"]["errors"]]
    assert any("page_size" in location for location in locations)


@pytest.mark.parametrize("path", ADMIN_LIST_ENDPOINTS)
def test_admin_page_size_above_limit_is_validation_error(
    admin_client: TestClient, path: str
):
    response = admin_client.get(path, params={"page_size": 101})
    assert response.status_code == 422, (path, response.text)
    assert response.json()["code"] == "validation_error"


def test_page_size_100_is_allowed(user_client: TestClient):
    response = user_client.get("/api/v1/documents", params={"page_size": 100})
    assert response.status_code == 200
    assert response.json()["page_size"] == 100


def test_error_envelope_is_uniform_for_403_404_409(
    user_client: TestClient, db_session
):
    forbidden = user_client.get("/api/v1/users")
    assert forbidden.status_code == 403

    missing = user_client.get("/api/v1/invoices/999999")
    assert missing.status_code == 404

    create_invoice(user_client, db_session, number="ERR-ENVELOPE")
    duplicate = user_client.post(
        "/api/v1/invoices",
        json=invoice_payload(db_session, number="ERR-ENVELOPE"),
    )
    assert duplicate.status_code == 409

    expected_codes = ["forbidden", "invoice_not_found", "invoice_duplicate"]
    for response, expected_code in zip(
        (forbidden, missing, duplicate), expected_codes, strict=True
    ):
        body = response.json()
        assert set(body) == {"code", "message", "details", "trace_id"}
        assert body["code"] == expected_code
        assert body["trace_id"]
