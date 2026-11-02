"""对账汇总、问题列表与忽略/取消忽略测试。"""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.document import Document
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.payment import Payment, PaymentAllocation
from backend.models.reconciliation import ReconciliationNote


def _make_invoice(
    db_session: Session,
    number: str,
    total_cents: int,
    *,
    status: str = "active",
    issue_date: date = date(2026, 8, 1),
    deleted_at=None,
    items: list[int] | None = None,
) -> Invoice:
    invoice = Invoice(
        invoice_number=number,
        issue_date=issue_date,
        seller_name="测试店铺",
        amount_ex_tax_cents=total_cents,
        tax_cents=0,
        total_cents=total_cents,
        status=status,
        paid_cents=0,
        payment_status="unpaid",
        deleted_at=deleted_at,
    )
    db_session.add(invoice)
    db_session.flush()
    for index, item_amount in enumerate(items or [], start=1):
        db_session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                name=f"明细{index}",
                quantity=1,
                unit_price_millis=item_amount * 10,
                amount_cents=item_amount,
                sort_order=index,
            )
        )
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


def _create_payment(client: TestClient, **overrides) -> dict:
    payload = {
        "amount_cents": 10000,
        "paid_at": "2026-08-13T10:00:00+00:00",
        "method": "bank_transfer",
        "payer_name": "杨泽",
        "external_txn_ref": "TXN-RECON",
    }
    payload.update(overrides)
    response = client.post("/api/v1/payments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _allocate(
    client: TestClient,
    payment_id: int,
    invoice_id: int,
    amount_cents: int,
):
    return client.post(
        f"/api/v1/payments/{payment_id}/allocations",
        json={"invoice_id": invoice_id, "amount_cents": amount_cents},
    )


def _insert_allocation(
    db_session: Session,
    payment_id: int,
    invoice_id: int,
    amount_cents: int,
    *,
    status: str = "active",
) -> PaymentAllocation:
    allocation = PaymentAllocation(
        payment_id=payment_id,
        invoice_id=invoice_id,
        amount_cents=amount_cents,
        status=status,
    )
    db_session.add(allocation)
    db_session.commit()
    db_session.refresh(allocation)
    return allocation


def _make_document(db_session: Session, user_id: int | None = None) -> Document:
    document = Document(
        doc_type="payment_evidence",
        title="付款凭证",
        owner_user_id=user_id,
        created_by=user_id,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def _issues(client: TestClient, **params) -> dict:
    response = client.get("/api/v1/reconciliation/issues", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_summary_scope(admin_client: TestClient, db_session: Session):
    active_a = _make_invoice(db_session, "SUM-A", 10000, items=[10000])
    active_b = _make_invoice(db_session, "SUM-B", 5000, items=[5000])
    _make_invoice(db_session, "SUM-DELETED", 7000, items=[7000], deleted_at=datetime(2026, 8, 2, tzinfo=UTC))
    _make_invoice(db_session, "SUM-PENDING", 8000, items=[8000], status="review_pending")

    void_payment = _create_payment(admin_client, amount_cents=3000)
    payment_row = db_session.get(Payment, void_payment["id"])
    payment_row.status = "void"
    db_session.commit()

    active_payment = _create_payment(admin_client, amount_cents=10000)
    _insert_allocation(db_session, active_payment["id"], active_a.id, 4000)
    _insert_allocation(
        db_session, active_payment["id"], active_b.id, 1000, status="reversed"
    )

    response = admin_client.get("/api/v1/reconciliation/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["invoice_total_cents"] == 15000
    assert body["invoice_paid_cents"] == 4000
    assert body["invoice_unpaid_cents"] == 11000
    assert body["invoice_count"] == 2
    assert body["payment_total_cents"] == 10000
    assert body["payment_allocated_cents"] == 4000
    assert body["payment_unallocated_cents"] == 6000
    assert body["payment_count"] == 1
    assert body["issue_counts"] == {
        "invoice_unpaid": 1,
        "invoice_partial": 1,
        "payment_unallocated": 0,
        "payment_partial": 1,
        "missing_evidence": 1,
        "duplicate_invoice": 0,
        "item_mismatch": 0,
        "amount_anomaly": 0,
        "date_anomaly": 0,
    }


def test_issue_types_ids_and_pagination(admin_client: TestClient, db_session: Session):
    unpaid = _make_invoice(db_session, "ISSUE-UNPAID", 8000, items=[8000])
    partial = _make_invoice(db_session, "ISSUE-PARTIAL", 10000, items=[10000])
    payment = _create_payment(admin_client, amount_cents=15000, payer_name="杨泽")
    assert _allocate(admin_client, payment["id"], partial.id, 5000).status_code == 201

    body = _issues(admin_client, include_ignored="true")
    assert body["total"] == 4
    items = {item["id"]: item for item in body["items"]}

    unpaid_issue = items[f"invoice_unpaid:{unpaid.id}"]
    assert unpaid_issue["type"] == "invoice_unpaid"
    assert unpaid_issue["severity"] == "error"
    assert unpaid_issue["entity_type"] == "invoice"
    assert unpaid_issue["entity_id"] == unpaid.id
    assert unpaid_issue["amount_cents"] == 8000

    partial_issue = items[f"invoice_partial:{partial.id}"]
    assert partial_issue["type"] == "invoice_partial"
    assert partial_issue["severity"] == "warning"
    assert partial_issue["amount_cents"] == 5000

    assert items[f"payment_partial:{payment['id']}"]["entity_type"] == "payment"
    evidence_issue = items[f"missing_evidence:{payment['id']}"]
    assert evidence_issue["entity_type"] == "payment"
    assert evidence_issue["amount_cents"] == 15000

    # 严重程度优先，error 在最前
    assert body["items"][0]["id"] == f"invoice_unpaid:{unpaid.id}"

    filtered = _issues(admin_client, type="invoice_unpaid")
    assert filtered["total"] == 1
    assert filtered["items"][0]["id"] == f"invoice_unpaid:{unpaid.id}"

    duplicate = _issues(admin_client, type="duplicate_invoice")
    assert duplicate["total"] == 0
    assert duplicate["items"] == []

    paged = _issues(admin_client, page=1, page_size=2, include_ignored="true")
    assert paged["total"] == 4
    assert len(paged["items"]) == 2
    assert paged["page_size"] == 2


def test_missing_evidence_teacher_advance_exempt(
    admin_client: TestClient, db_session: Session, admin_user
):
    document = _make_document(db_session, admin_user.id)
    teacher = _create_payment(admin_client, amount_cents=5000, method="teacher_advance")
    missing = _create_payment(admin_client, amount_cents=6000, method="bank_transfer")
    with_evidence = _create_payment(
        admin_client,
        amount_cents=7000,
        method="alipay",
        evidence_document_id=document.id,
    )

    body = _issues(admin_client, type="missing_evidence")
    ids = {item["id"] for item in body["items"]}
    assert ids == {f"missing_evidence:{missing['id']}"}
    assert f"missing_evidence:{teacher['id']}" not in ids
    assert f"missing_evidence:{with_evidence['id']}" not in ids


def test_item_mismatch_issue(admin_client: TestClient, db_session: Session):
    mismatch = _make_invoice(db_session, "ITEM-MISMATCH", 10000, items=[9000])
    _make_invoice(db_session, "ITEM-MATCH", 10000, items=[10000])
    _make_invoice(db_session, "ITEM-ROUNDING", 10000, items=[9999])

    body = _issues(admin_client, type="item_mismatch")
    assert body["total"] == 1
    issue = body["items"][0]
    assert issue["id"] == f"item_mismatch:{mismatch.id}"
    assert issue["entity_type"] == "invoice"
    assert issue["severity"] == "warning"
    assert issue["amount_cents"] == 1000


def test_amount_anomaly_invoice_over_allocation(
    admin_client: TestClient, db_session: Session
):
    _make_invoice(db_session, "AMOUNT-DUMMY", 1000, items=[1000])
    target = _make_invoice(db_session, "AMOUNT-INVOICE", 5000, items=[5000])
    payment = _create_payment(admin_client, amount_cents=10000)
    _insert_allocation(db_session, payment["id"], target.id, 6000)

    body = _issues(admin_client, type="amount_anomaly")
    ids = {item["id"] for item in body["items"]}
    assert ids == {f"amount_anomaly:{target.id}"}
    issue = body["items"][0]
    assert issue["entity_type"] == "invoice"
    assert issue["severity"] == "error"
    assert issue["amount_cents"] == 1000


def test_amount_anomaly_payment_over_allocation(
    admin_client: TestClient, db_session: Session
):
    _create_payment(admin_client, amount_cents=1000)
    target = _create_payment(admin_client, amount_cents=5000)
    invoice = _make_invoice(db_session, "AMOUNT-PAYMENT", 10000, items=[10000])
    _insert_allocation(db_session, target["id"], invoice.id, 6000)

    body = _issues(admin_client, type="amount_anomaly")
    ids = {item["id"] for item in body["items"]}
    assert ids == {f"amount_anomaly:{target['id']}"}
    issue = body["items"][0]
    assert issue["entity_type"] == "payment"
    assert issue["amount_cents"] == 1000


def test_amount_anomaly_allocation_on_void_invoice(
    admin_client: TestClient, db_session: Session
):
    invoice = _make_invoice(
        db_session, "AMOUNT-VOID", 5000, status="void", items=[5000]
    )
    payment = _create_payment(admin_client, amount_cents=5000)
    allocation = _insert_allocation(db_session, payment["id"], invoice.id, 5000)

    body = _issues(admin_client, type="amount_anomaly")
    assert body["total"] == 1
    issue = body["items"][0]
    assert issue["id"] == f"amount_anomaly:{allocation.id}"
    assert issue["entity_type"] == "allocation"
    assert issue["amount_cents"] == 5000


def test_date_anomaly_issue(admin_client: TestClient, db_session: Session):
    invoice = _make_invoice(
        db_session,
        "DATE-ANOMALY",
        1000,
        issue_date=date(2026, 8, 10),
        items=[1000],
    )
    payment = _create_payment(
        admin_client, amount_cents=1000, paid_at="2026-08-01T09:00:00+00:00"
    )
    allocation = _allocate(admin_client, payment["id"], invoice.id, 1000).json()

    body = _issues(admin_client, type="date_anomaly")
    assert body["total"] == 1
    issue = body["items"][0]
    assert issue["id"] == f"date_anomaly:{allocation['id']}"
    assert issue["entity_type"] == "allocation"
    assert issue["severity"] == "warning"
    assert issue["amount_cents"] == 1000


def test_ignore_and_unignore_issue(
    admin_client: TestClient, user_client: TestClient, db_session: Session
):
    invoice = _make_invoice(db_session, "IGNORE-1", 8000, items=[8000])
    issue_key = f"invoice_unpaid:{invoice.id}"

    forbidden = user_client.post(
        f"/api/v1/reconciliation/issues/{issue_key}/ignore", json={"note": "越权"}
    )
    assert forbidden.status_code == 403

    ignored = admin_client.post(
        f"/api/v1/reconciliation/issues/{issue_key}/ignore",
        json={"note": "已确认由老师代付"},
    )
    assert ignored.status_code == 200, ignored.text
    assert ignored.json()["ignored"] is True
    assert ignored.json()["note"] == "已确认由老师代付"

    db_session.expire_all()
    note_count = db_session.scalar(select(func.count()).select_from(ReconciliationNote))
    assert note_count == 1

    default_list = _issues(admin_client)
    assert issue_key not in {item["id"] for item in default_list["items"]}

    included = _issues(admin_client, include_ignored="true")
    ignored_item = next(item for item in included["items"] if item["id"] == issue_key)
    assert ignored_item["ignored"] is True
    assert ignored_item["note"] == "已确认由老师代付"

    summary = admin_client.get("/api/v1/reconciliation/summary").json()
    assert summary["issue_counts"]["invoice_unpaid"] == 0

    updated = admin_client.post(
        f"/api/v1/reconciliation/issues/{issue_key}/ignore",
        json={"note": "更新后的备注"},
    )
    assert updated.status_code == 200
    assert updated.json()["note"] == "更新后的备注"
    db_session.expire_all()
    assert (
        db_session.scalar(select(func.count()).select_from(ReconciliationNote)) == 1
    )

    forbidden_delete = user_client.delete(
        f"/api/v1/reconciliation/issues/{issue_key}/ignore"
    )
    assert forbidden_delete.status_code == 403

    unignored = admin_client.delete(
        f"/api/v1/reconciliation/issues/{issue_key}/ignore"
    )
    assert unignored.status_code == 200
    assert unignored.json()["ignored"] is False
    assert unignored.json()["note"] is None

    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(ReconciliationNote)) == 0

    visible_again = _issues(admin_client)
    assert issue_key in {item["id"] for item in visible_again["items"]}

    missing_key = "invoice_unpaid:999999"
    assert (
        admin_client.post(
            f"/api/v1/reconciliation/issues/{missing_key}/ignore",
            json={"note": "不存在"},
        ).status_code
        == 404
    )
    assert (
        admin_client.delete(
            f"/api/v1/reconciliation/issues/{missing_key}/ignore"
        ).status_code
        == 404
    )

    logs = admin_client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "reconciliation_issue", "entity_id": issue_key},
    ).json()["items"]
    actions = {log["action"] for log in logs}
    assert "reconciliation.ignore" in actions
    assert "reconciliation.unignore" in actions


def test_issue_ignore_note_is_single_row(
    admin_client: TestClient, db_session: Session
):
    invoice = _make_invoice(db_session, "IGNORE-UNIQUE", 4000, items=[4000])
    issue_key = f"invoice_unpaid:{invoice.id}"
    for note in ("第一次", "第二次", "第三次"):
        response = admin_client.post(
            f"/api/v1/reconciliation/issues/{issue_key}/ignore",
            json={"note": note},
        )
        assert response.status_code == 200

    db_session.expire_all()
    notes = list(
        db_session.scalars(
            select(ReconciliationNote).where(
                ReconciliationNote.issue_key == issue_key
            )
        ).all()
    )
    assert len(notes) == 1
    assert notes[0].note == "第三次"


def test_summary_empty_and_auth(client: TestClient, admin_client: TestClient):
    assert client.get("/api/v1/reconciliation/summary").status_code == 401
    assert client.get("/api/v1/reconciliation/issues").status_code == 401

    summary = admin_client.get("/api/v1/reconciliation/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["invoice_total_cents"] == 0
    assert body["payment_total_cents"] == 0
    assert body["invoice_count"] == 0
    assert body["payment_count"] == 0
    assert set(body["issue_counts"].values()) == {0}

    invalid_type = admin_client.get(
        "/api/v1/reconciliation/issues", params={"type": "unknown_type"}
    )
    assert invalid_type.status_code == 422
