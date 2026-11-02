"""端到端集成流程（不依赖外部网络）。

上传真实 1x1 PNG 发票 -> mock provider 处理 -> approve -> 创建付款 -> 分配
-> 发票 paid -> 对账 summary -> 导出 xlsx -> dashboard。

mock provider 通过 ExtractionConfig 直接注入，不读取外部识别服务。
"""

from __future__ import annotations

import base64
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from backend import worker
from backend.extraction.config import ExtractionConfig
from backend.models.extraction import ExtractionJob
from backend.models.invoice import Invoice
from backend.models.payment import Payment, PaymentAllocation

# 真实 1x1 透明 PNG（IHDR 宽高均为 1）
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
INVOICE_NUMBER = "24512000000012345678"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXPECTED_DISPLAY_NAME = "113.00-普通成员,系统管理员-测试商户-标准件-发票.png"


def _category_id(client: TestClient, name: str = "标准件") -> int:
    response = client.get("/api/v1/categories", params={"kind": "purchase"})
    assert response.status_code == 200, response.text
    return next(item["id"] for item in response.json()["items"] if item["name"] == name)


def test_invoice_end_to_end_flow(
    user_client: TestClient,
    db_session,
    settings,
    normal_user,
    admin_user,
):
    # 1. 上传 PNG 发票：创建文档 + queued 抽取任务
    upload = user_client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", PNG_1X1, "image/png")},
        data={"doc_type": "invoice", "title": "集成测试发票"},
    )
    assert upload.status_code == 201, upload.text
    uploaded = upload.json()
    document_id = uploaded["document"]["id"]
    job_id = uploaded["extraction_job"]["id"]
    assert uploaded["document"]["current_version"]["display_name"].startswith("待识别-")
    assert uploaded["document"]["current_version"]["mime_type"] == "image/png"
    assert uploaded["extraction_job"]["status"] == "queued"

    # 2. mock provider 处理一轮（worker.run_once，不访问网络）
    config = ExtractionConfig(provider="mock", upload_dir=settings.upload_dir)
    processed = worker.run_once(db_session, settings=settings, config=config)
    assert processed is not None
    assert processed.id == job_id
    assert processed.status == "review_pending"
    assert processed.provider == "mock"
    assert processed.parsed_json["invoice_number"] == INVOICE_NUMBER
    assert processed.parsed_json["total_cents"] == 11300

    job_detail = user_client.get(f"/api/v1/extraction-jobs/{job_id}")
    assert job_detail.status_code == 200, job_detail.text
    assert job_detail.json()["job"]["status"] == "review_pending"

    # 3. 审核通过：创建 active 发票，文档展示名改为规范名
    category_id = _category_id(user_client)
    approve = user_client.post(
        f"/api/v1/extraction-jobs/{job_id}/approve",
        json={
            "invoice_number": INVOICE_NUMBER,
            "invoice_code": "024001900111",
            "invoice_type": "电子发票（普通发票）",
            "issue_date": "2026-07-12",
            "seller_name": "测试商户",
            "amount_ex_tax_cents": 10000,
            "tax_cents": 1300,
            "total_cents": 11300,
            "tax_rate_bp": 1300,
            "category_id": category_id,
            "requester_id": normal_user.id,
            "owner_id": admin_user.id,
            "invoice_form": "electronic",
            "items": [
                {
                    "name": "螺栓",
                    "quantity": 10,
                    "unit_price_millis": 1130,
                    "amount_cents": 11300,
                }
            ],
        },
    )
    assert approve.status_code == 201, approve.text
    approved = approve.json()
    invoice = approved["invoice"]
    assert approved["job"]["status"] == "approved"
    assert invoice["status"] == "active"
    assert invoice["invoice_number"] == INVOICE_NUMBER
    assert invoice["total_cents"] == 11300
    assert invoice["paid_cents"] == 0
    assert invoice["payment_status"] == "unpaid"
    assert invoice["source_document_id"] == document_id
    assert invoice["extraction_job_id"] == job_id

    document_detail = user_client.get(f"/api/v1/documents/{document_id}")
    assert document_detail.status_code == 200
    current_version = document_detail.json()["document"]["current_version"]
    assert current_version["display_name"] == EXPECTED_DISPLAY_NAME
    assert current_version["display_name"].endswith(".png")

    # 4. 创建付款并全额分配
    payment_response = user_client.post(
        "/api/v1/payments",
        json={
            "amount_cents": 11300,
            "paid_at": "2026-08-13T10:00:00+00:00",
            "method": "teacher_advance",
            "payer_name": "王老师",
            "requested_at": "2026-08-12T09:00:00+00:00",
            "note": "集成测试付款",
        },
    )
    assert payment_response.status_code == 201, payment_response.text
    payment = payment_response.json()
    assert payment["amount_cents"] == 11300
    assert payment["status"] == "unallocated"

    allocation_response = user_client.post(
        f"/api/v1/payments/{payment['id']}/allocations",
        json={"invoice_id": invoice["id"], "amount_cents": 11300},
    )
    assert allocation_response.status_code == 201, allocation_response.text
    allocation = allocation_response.json()
    assert allocation["amount_cents"] == 11300
    assert allocation["status"] == "active"

    paid_invoice = user_client.get(f"/api/v1/invoices/{invoice['id']}")
    assert paid_invoice.status_code == 200
    paid_body = paid_invoice.json()
    assert paid_body["paid_cents"] == 11300
    assert paid_body["payment_status"] == "paid"
    assert paid_body["allocations"][0]["amount_cents"] == 11300

    payment_detail = user_client.get(f"/api/v1/payments/{payment['id']}")
    assert payment_detail.status_code == 200
    assert payment_detail.json()["status"] == "fully_allocated"
    assert payment_detail.json()["allocated_cents"] == 11300

    # 金额落库仍为整数分，没有浮点
    db_session.expire_all()
    stored_invoice = db_session.get(Invoice, invoice["id"])
    stored_payment = db_session.get(Payment, payment["id"])
    stored_allocation = db_session.get(PaymentAllocation, allocation["id"])
    stored_job = db_session.get(ExtractionJob, job_id)
    assert stored_job is not None and stored_job.status == "approved"
    assert stored_invoice is not None
    assert stored_invoice.total_cents == 11300
    assert stored_invoice.paid_cents == 11300
    assert isinstance(stored_invoice.total_cents, int)
    assert isinstance(stored_invoice.paid_cents, int)
    assert stored_payment is not None and stored_payment.amount_cents == 11300
    assert stored_allocation is not None and stored_allocation.amount_cents == 11300
    assert all(
        isinstance(value, int)
        for value in (
            stored_payment.amount_cents,
            stored_allocation.amount_cents,
        )
    )

    # 5. 对账 summary：全额已付、无异常
    summary = user_client.get("/api/v1/reconciliation/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["invoice_total_cents"] == 11300
    assert summary_body["invoice_paid_cents"] == 11300
    assert summary_body["invoice_unpaid_cents"] == 0
    assert summary_body["payment_total_cents"] == 11300
    assert summary_body["payment_allocated_cents"] == 11300
    assert summary_body["payment_unallocated_cents"] == 0
    assert summary_body["invoice_count"] == 1
    assert summary_body["payment_count"] == 1
    assert summary_body["issue_counts"] == {
        "invoice_unpaid": 0,
        "invoice_partial": 0,
        "payment_unallocated": 0,
        "payment_partial": 0,
        "missing_evidence": 0,
        "duplicate_invoice": 0,
        "item_mismatch": 0,
        "amount_anomaly": 0,
        "date_anomaly": 0,
    }

    # 6. 导出 xlsx 并校验发票号码
    export_response = user_client.post("/api/v1/exports", json={})
    assert export_response.status_code == 202, export_response.text
    export = export_response.json()["export"]
    assert export["status"] == "succeeded"
    download = user_client.get(export["download_url"])
    assert download.status_code == 200, download.text
    assert download.headers["content-type"].startswith(XLSX_MEDIA_TYPE)

    workbook = load_workbook(BytesIO(download.content))
    worksheet = workbook.active
    values = [
        cell.value
        for row in worksheet.iter_rows()
        for cell in row
        if cell.value is not None
    ]
    assert INVOICE_NUMBER in values
    assert "测试商户" in values
    assert 113.0 in values

    # 7. 仪表盘汇总
    dashboard_response = user_client.get("/api/v1/dashboard/summary")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["totals"] == {
        "invoice_count": 1,
        "invoice_total_cents": 11300,
        "payment_total_cents": 11300,
        "paid_cents": 11300,
        "unpaid_cents": 0,
        "missing_evidence_count": 0,
    }
    assert dashboard["by_category"] == [
        {
            "category_id": category_id,
            "name": "标准件",
            "invoice_count": 1,
            "total_cents": 11300,
        }
    ]
    assert dashboard["by_month"] == [
        {"month": "2026-07", "invoice_count": 1, "total_cents": 11300}
    ]
    assert dashboard["by_payer"] == [
        {"payer_name": "王老师", "payment_count": 1, "total_cents": 11300}
    ]
    assert dashboard["gaps"] == {
        "invoice_unpaid": 0,
        "payment_unallocated": 0,
        "missing_evidence": 0,
    }
