"""付款、分配与发票付款查询接口测试。"""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.document import Document
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.payment import Payment, PaymentAllocation


def _make_document(db_session: Session, *, user_id: int | None = None) -> Document:
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
        "external_txn_ref": "TXN-001",
    }
    payload.update(overrides)
    response = client.post("/api/v1/payments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _payment_detail(client: TestClient, payment_id: int) -> dict:
    response = client.get(f"/api/v1/payments/{payment_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _allocate(
    client: TestClient,
    payment_id: int,
    invoice_id: int,
    amount_cents: int,
    note: str | None = None,
):
    payload: dict = {"invoice_id": invoice_id, "amount_cents": amount_cents}
    if note is not None:
        payload["note"] = note
    return client.post(
        f"/api/v1/payments/{payment_id}/allocations", json=payload
    )


def _invoice_state(db_session: Session, invoice_id: int) -> Invoice:
    db_session.expire_all()
    return db_session.get(Invoice, invoice_id)


def _payment_state(db_session: Session, payment_id: int) -> Payment:
    db_session.expire_all()
    return db_session.get(Payment, payment_id)


def _login(app, username: str, password: str) -> TestClient:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def test_create_payment_returns_unallocated_and_audits(
    admin_client: TestClient, db_session: Session, admin_user
):
    document = _make_document(db_session, user_id=admin_user.id)
    body = _create_payment(
        admin_client,
        amount_cents=12400,
        payer_user_id=admin_user.id,
        evidence_document_id=document.id,
        requested_at="2026-08-12T09:00:00+00:00",
        note="高铁票",
    )

    assert body["amount_cents"] == 12400
    assert body["status"] == "unallocated"
    assert body["allocated_cents"] == 0
    assert body["allocations"] == []
    assert body["created_by"] == admin_user.id
    assert body["payer_user_id"] == admin_user.id
    assert body["evidence_document_id"] == document.id
    assert body["requested_at"] is not None
    assert body["paid_at"].startswith("2026-08-13T10:00:00")

    logs = admin_client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "payment", "entity_id": body["id"]},
    ).json()["items"]
    assert [log["action"] for log in logs] == ["payment.create"]
    assert logs[0]["after"]["amount_cents"] == 12400


def test_create_payment_validates_references(
    user_client: TestClient, db_session: Session
):
    missing_user = user_client.post(
        "/api/v1/payments",
        json={
            "amount_cents": 100,
            "paid_at": "2026-08-13T10:00:00+00:00",
            "method": "cash",
            "payer_user_id": 999999,
        },
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["code"] == "payer_user_not_found"

    missing_document = user_client.post(
        "/api/v1/payments",
        json={
            "amount_cents": 100,
            "paid_at": "2026-08-13T10:00:00+00:00",
            "method": "cash",
            "evidence_document_id": 999999,
        },
    )
    assert missing_document.status_code == 404
    assert missing_document.json()["code"] == "document_not_found"


def test_list_payments_filters_and_order(admin_client: TestClient, db_session: Session):
    first = _create_payment(
        admin_client,
        amount_cents=10000,
        paid_at="2026-08-01T08:00:00+00:00",
        payer_name="杨泽",
        method="bank_transfer",
        external_txn_ref="TXN-AAA",
    )
    second = _create_payment(
        admin_client,
        amount_cents=20000,
        paid_at="2026-08-10T08:00:00+00:00",
        payer_name="朱建诚",
        method="alipay",
        external_txn_ref="TXN-BBB",
    )
    third = _create_payment(
        admin_client,
        amount_cents=30000,
        paid_at="2026-08-20T08:00:00+00:00",
        payer_name="杨洋",
        method="wechat",
        external_txn_ref=None,
    )

    invoice = _make_invoice(db_session, "LIST-1", 6000)
    assert _allocate(admin_client, first["id"], invoice.id, 4000).status_code == 201

    listing = admin_client.get("/api/v1/payments")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]
    assert all(item["allocations"] == [] for item in body["items"])
    first_item = next(item for item in body["items"] if item["id"] == first["id"])
    assert first_item["allocated_cents"] == 4000
    assert first_item["status"] == "partially_allocated"

    by_payer = admin_client.get("/api/v1/payments", params={"q": "杨"}).json()
    assert by_payer["total"] == 2

    by_ref = admin_client.get("/api/v1/payments", params={"q": "TXN-BBB"}).json()
    assert by_ref["total"] == 1
    assert by_ref["items"][0]["id"] == second["id"]

    unallocated = admin_client.get(
        "/api/v1/payments", params={"status": "unallocated"}
    ).json()
    assert unallocated["total"] == 2
    assert {item["id"] for item in unallocated["items"]} == {
        second["id"],
        third["id"],
    }

    by_method = admin_client.get(
        "/api/v1/payments", params={"method": "alipay"}
    ).json()
    assert by_method["total"] == 1
    assert by_method["items"][0]["id"] == second["id"]

    by_date = admin_client.get(
        "/api/v1/payments",
        params={"date_from": "2026-08-05", "date_to": "2026-08-15"},
    ).json()
    assert by_date["total"] == 1
    assert by_date["items"][0]["id"] == second["id"]

    paged = admin_client.get(
        "/api/v1/payments", params={"page": 2, "page_size": 1}
    ).json()
    assert paged["total"] == 3
    assert paged["page"] == 2
    assert paged["items"][0]["id"] == second["id"]

    by_amount = admin_client.get(
        "/api/v1/payments", params={"sort": "amount_cents:asc"}
    ).json()
    assert [item["id"] for item in by_amount["items"]] == [
        first["id"],
        second["id"],
        third["id"],
    ]

    by_amount_desc = admin_client.get(
        "/api/v1/payments", params={"sort": "amount_cents:desc"}
    ).json()
    assert [item["id"] for item in by_amount_desc["items"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]

    invalid_sort = admin_client.get(
        "/api/v1/payments", params={"sort": "not_a_field:desc"}
    ).json()
    assert [item["id"] for item in invalid_sort["items"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]


def test_payment_detail_includes_allocations_and_invoice_summary(
    admin_client: TestClient, db_session: Session
):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice_a = _make_invoice(db_session, "DETAIL-A", 6000)
    invoice_b = _make_invoice(db_session, "DETAIL-B", 8000)

    assert _allocate(admin_client, payment["id"], invoice_a.id, 3000).status_code == 201
    assert _allocate(admin_client, payment["id"], invoice_b.id, 2000).status_code == 201

    detail = _payment_detail(admin_client, payment["id"])
    assert detail["allocated_cents"] == 5000
    assert detail["status"] == "partially_allocated"
    assert len(detail["allocations"]) == 2
    assert all(item["status"] == "active" for item in detail["allocations"])

    summaries = {item["invoice_id"]: item for item in detail["invoices"]}
    assert summaries[invoice_a.id] == {
        "invoice_id": invoice_a.id,
        "invoice_number": "DETAIL-A",
        "seller_name": "测试店铺",
        "total_cents": 6000,
        "amount_cents": 3000,
        "status": "active",
    }
    assert summaries[invoice_b.id]["amount_cents"] == 2000

    missing = admin_client.get("/api/v1/payments/999999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "payment_not_found"


def test_allocate_124_to_two_62(admin_client: TestClient, db_session: Session):
    payment = _create_payment(admin_client, amount_cents=12400)
    invoice_a = _make_invoice(db_session, "HIGH-SPEED-1", 6200)
    invoice_b = _make_invoice(db_session, "HIGH-SPEED-2", 6200)

    first = _allocate(admin_client, payment["id"], invoice_a.id, 6200)
    second = _allocate(admin_client, payment["id"], invoice_b.id, 6200)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    detail = _payment_detail(admin_client, payment["id"])
    assert detail["status"] == "fully_allocated"
    assert detail["allocated_cents"] == 12400
    assert len(detail["allocations"]) == 2

    for invoice in (invoice_a, invoice_b):
        state = _invoice_state(db_session, invoice.id)
        assert state.paid_cents == 6200
        assert state.payment_status == "paid"


def test_allocate_198_to_three_66(admin_client: TestClient, db_session: Session):
    payment = _create_payment(admin_client, amount_cents=19800)
    invoices = [
        _make_invoice(db_session, f"HIGH-SPEED-66-{index}", 6600)
        for index in range(3)
    ]

    for invoice in invoices:
        response = _allocate(admin_client, payment["id"], invoice.id, 6600)
        assert response.status_code == 201, response.text

    detail = _payment_detail(admin_client, payment["id"])
    assert detail["status"] == "fully_allocated"
    assert detail["allocated_cents"] == 19800
    assert len(detail["allocations"]) == 3
    for invoice in invoices:
        state = _invoice_state(db_session, invoice.id)
        assert state.paid_cents == 6600
        assert state.payment_status == "paid"


def test_partial_allocation_updates_both_statuses(
    user_client: TestClient, db_session: Session
):
    payment = _create_payment(user_client, amount_cents=30000)
    invoice = _make_invoice(db_session, "PARTIAL-1", 50000)

    assert _allocate(user_client, payment["id"], invoice.id, 10000).status_code == 201

    detail = _payment_detail(user_client, payment["id"])
    assert detail["status"] == "partially_allocated"
    assert detail["allocated_cents"] == 10000
    state = _invoice_state(db_session, invoice.id)
    assert state.paid_cents == 10000
    assert state.payment_status == "partial"

    assert _allocate(user_client, payment["id"], invoice.id, 20000).status_code == 409
    other_invoice = _make_invoice(db_session, "PARTIAL-2", 50000)
    assert _allocate(user_client, payment["id"], other_invoice.id, 20000).status_code == 201
    detail = _payment_detail(user_client, payment["id"])
    assert detail["status"] == "fully_allocated"
    state = _invoice_state(db_session, other_invoice.id)
    assert state.paid_cents == 20000
    assert state.payment_status == "partial"


def test_over_allocation_rejected(admin_client: TestClient, db_session: Session):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice = _make_invoice(db_session, "OVER-PAYMENT", 20000)
    assert _allocate(admin_client, payment["id"], invoice.id, 8000).status_code == 201

    another_invoice = _make_invoice(db_session, "OVER-PAYMENT-2", 20000)
    over_payment = _allocate(admin_client, payment["id"], another_invoice.id, 3000)
    assert over_payment.status_code == 409
    assert over_payment.json()["code"] == "allocation_exceeds_payment"

    payment_b = _create_payment(admin_client, amount_cents=20000)
    invoice_b = _make_invoice(db_session, "OVER-INVOICE", 10000)
    assert _allocate(admin_client, payment_b["id"], invoice_b.id, 6000).status_code == 201

    invoice_c = _make_invoice(db_session, "OVER-INVOICE-2", 3000)
    over_invoice = _allocate(admin_client, payment_b["id"], invoice_c.id, 4000)
    assert over_invoice.status_code == 409
    assert over_invoice.json()["code"] == "allocation_exceeds_invoice"

    detail = _payment_detail(admin_client, payment["id"])
    assert detail["allocated_cents"] == 8000
    assert len(detail["allocations"]) == 1


def test_duplicate_active_allocation_rejected(
    admin_client: TestClient, db_session: Session
):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice = _make_invoice(db_session, "DUP-ALLOC", 10000)
    first = _allocate(admin_client, payment["id"], invoice.id, 1000)
    assert first.status_code == 201

    duplicate = _allocate(admin_client, payment["id"], invoice.id, 1000)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "allocation_exists"

    revoked = admin_client.delete(f"/api/v1/allocations/{first.json()['id']}")
    assert revoked.status_code == 204

    recreated = _allocate(admin_client, payment["id"], invoice.id, 1000)
    assert recreated.status_code == 201, recreated.text

    db_session.expire_all()
    allocations = list(
        db_session.scalars(
            select(PaymentAllocation)
            .where(
                PaymentAllocation.payment_id == payment["id"],
                PaymentAllocation.invoice_id == invoice.id,
            )
            .order_by(PaymentAllocation.id)
        ).all()
    )
    assert [item.status for item in allocations] == ["reversed", "active"]


def test_reverse_allocation_recomputes_both_sides(
    admin_client: TestClient, db_session: Session
):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice = _make_invoice(db_session, "REVOKE-1", 10000)
    allocation = _allocate(admin_client, payment["id"], invoice.id, 4000).json()

    response = admin_client.delete(f"/api/v1/allocations/{allocation['id']}")
    assert response.status_code == 204
    assert response.content == b""

    detail = _payment_detail(admin_client, payment["id"])
    assert detail["status"] == "unallocated"
    assert detail["allocated_cents"] == 0
    assert len(detail["allocations"]) == 1
    assert detail["allocations"][0]["status"] == "reversed"

    state = _invoice_state(db_session, invoice.id)
    assert state.paid_cents == 0
    assert state.payment_status == "unpaid"

    invoice_payments = admin_client.get(f"/api/v1/invoices/{invoice.id}/payments")
    assert invoice_payments.status_code == 200
    assert invoice_payments.json()["items"] == []


def test_update_allocation_amount_and_boundaries(
    admin_client: TestClient, db_session: Session
):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice = _make_invoice(db_session, "ALLOC-UPDATE", 10000)
    allocation = _allocate(admin_client, payment["id"], invoice.id, 5000).json()

    updated = admin_client.patch(
        f"/api/v1/allocations/{allocation['id']}", json={"amount_cents": 8000}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount_cents"] == 8000

    detail = _payment_detail(admin_client, payment["id"])
    assert detail["status"] == "partially_allocated"
    assert detail["allocated_cents"] == 8000
    state = _invoice_state(db_session, invoice.id)
    assert state.paid_cents == 8000
    assert state.payment_status == "partial"

    too_large = admin_client.patch(
        f"/api/v1/allocations/{allocation['id']}", json={"amount_cents": 11000}
    )
    assert too_large.status_code == 409
    assert too_large.json()["code"] == "allocation_exceeds_payment"

    assert admin_client.delete(f"/api/v1/allocations/{allocation['id']}").status_code == 204
    reversed_update = admin_client.patch(
        f"/api/v1/allocations/{allocation['id']}", json={"amount_cents": 1000}
    )
    assert reversed_update.status_code == 409
    assert reversed_update.json()["code"] == "allocation_not_active"


def test_payment_amount_update_protection(admin_client: TestClient, db_session: Session):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice = _make_invoice(db_session, "PAYMENT-UPDATE", 10000)
    allocation = _allocate(admin_client, payment["id"], invoice.id, 6000).json()

    blocked = admin_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"amount_cents": 5999}
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "payment_amount_below_allocated"

    allowed = admin_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"amount_cents": 7000}
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "partially_allocated"
    assert allowed.json()["allocated_cents"] == 6000

    exact = admin_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"amount_cents": 6000}
    )
    assert exact.status_code == 200
    assert exact.json()["status"] == "fully_allocated"

    larger = admin_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"amount_cents": 20000}
    )
    assert larger.status_code == 200
    assert larger.json()["status"] == "partially_allocated"

    # 分配金额未变，发票侧缓存也不应被破坏
    state = _invoice_state(db_session, invoice.id)
    assert state.paid_cents == 6000
    allocation_row = db_session.get(PaymentAllocation, allocation["id"])
    assert allocation_row.amount_cents == 6000


def test_payment_and_allocation_permissions(
    app, user_client: TestClient, admin_client: TestClient, db_session: Session, make_user
):
    payment = _create_payment(user_client, amount_cents=10000, payer_name="普通成员")
    invoice = _make_invoice(db_session, "PERMISSION-1", 10000)
    allocation = _allocate(user_client, payment["id"], invoice.id, 2000).json()

    make_user("intruder", "路人", password="intruder-pass-1")
    other = _login(app, "intruder", "intruder-pass-1")
    try:
        forbidden_update = other.patch(
            f"/api/v1/payments/{payment['id']}", json={"note": "越权修改"}
        )
        assert forbidden_update.status_code == 403
        assert forbidden_update.json()["code"] == "forbidden"

        forbidden_delete = other.delete(f"/api/v1/allocations/{allocation['id']}")
        assert forbidden_delete.status_code == 403

        forbidden_allocation_update = other.patch(
            f"/api/v1/allocations/{allocation['id']}", json={"amount_cents": 3000}
        )
        assert forbidden_allocation_update.status_code == 403
        assert forbidden_allocation_update.json()["code"] == "forbidden"
    finally:
        other.close()

    owner_update = user_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"note": "本人修改"}
    )
    assert owner_update.status_code == 200
    assert owner_update.json()["note"] == "本人修改"

    admin_update = admin_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"note": "管理员修改"}
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["note"] == "管理员修改"

    owner_allocation_update = user_client.patch(
        f"/api/v1/allocations/{allocation['id']}", json={"amount_cents": 3000}
    )
    assert owner_allocation_update.status_code == 200, owner_allocation_update.text
    assert owner_allocation_update.json()["amount_cents"] == 3000

    owner_delete = user_client.delete(f"/api/v1/allocations/{allocation['id']}")
    assert owner_delete.status_code == 204


def test_allocation_requires_active_invoice(
    admin_client: TestClient, db_session: Session
):
    payment = _create_payment(admin_client, amount_cents=100000)

    missing = _allocate(admin_client, payment["id"], 999999, 1000)
    assert missing.status_code == 404
    assert missing.json()["code"] == "invoice_not_found"

    pending = _make_invoice(db_session, "PENDING-1", 5000, status="review_pending")
    not_active = _allocate(admin_client, payment["id"], pending.id, 1000)
    assert not_active.status_code == 409
    assert not_active.json()["code"] == "invoice_not_active"

    void_invoice = _make_invoice(db_session, "VOID-1", 5000, status="void")
    assert _allocate(admin_client, payment["id"], void_invoice.id, 1000).status_code == 409

    deleted = _make_invoice(
        db_session,
        "DELETED-1",
        5000,
        deleted_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    assert _allocate(admin_client, payment["id"], deleted.id, 1000).status_code == 404

    payment_row = _payment_state(db_session, payment["id"])
    payment_row.status = "void"
    db_session.commit()
    void_payment = _allocate(admin_client, payment["id"], 999999, 1000)
    assert void_payment.status_code == 409
    assert void_payment.json()["code"] == "payment_void"


def test_invoice_payments_only_active_allocations(
    admin_client: TestClient,
    user_client: TestClient,
    db_session: Session,
):
    invoice = _make_invoice(db_session, "INVOICE-PAYMENTS", 10000)
    payment_a = _create_payment(admin_client, amount_cents=10000, payer_name="杨泽")
    payment_b = _create_payment(admin_client, amount_cents=10000, payer_name="朱建诚")

    active_allocation = _allocate(
        admin_client, payment_a["id"], invoice.id, 3000
    ).json()
    reversed_allocation = _allocate(
        admin_client, payment_b["id"], invoice.id, 2000
    ).json()
    assert (
        admin_client.delete(f"/api/v1/allocations/{reversed_allocation['id']}").status_code
        == 204
    )

    response = user_client.get(f"/api/v1/invoices/{invoice.id}/payments")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == active_allocation["id"]
    assert item["status"] == "active"
    assert item["amount_cents"] == 3000
    assert item["payment"]["id"] == payment_a["id"]
    assert item["payment"]["amount_cents"] == 10000
    assert item["payment"]["status"] == "partially_allocated"
    assert item["payment"]["payer_name"] == "杨泽"
    assert item["payment"]["method"] == "bank_transfer"

    missing = user_client.get("/api/v1/invoices/999999/payments")
    assert missing.status_code == 404
    assert missing.json()["code"] == "invoice_not_found"


def test_payment_audit_actions(admin_client: TestClient, db_session: Session):
    payment = _create_payment(admin_client, amount_cents=10000)
    invoice = _make_invoice(db_session, "AUDIT-1", 10000)

    patched = admin_client.patch(
        f"/api/v1/payments/{payment['id']}", json={"note": "备注"}
    )
    assert patched.status_code == 200

    allocation = _allocate(admin_client, payment["id"], invoice.id, 3000).json()
    updated = admin_client.patch(
        f"/api/v1/allocations/{allocation['id']}", json={"note": "分配备注"}
    )
    assert updated.status_code == 200

    assert (
        admin_client.delete(f"/api/v1/allocations/{allocation['id']}").status_code
        == 204
    )

    payment_logs = admin_client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "payment", "entity_id": payment["id"]},
    ).json()["items"]
    assert {log["action"] for log in payment_logs} == {
        "payment.create",
        "payment.update",
    }

    allocation_logs = admin_client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "allocation", "entity_id": allocation["id"]},
    ).json()["items"]
    assert {log["action"] for log in allocation_logs} == {
        "allocation.create",
        "allocation.update",
        "allocation.revoke",
    }


def test_payments_require_login(client: TestClient):
    assert client.get("/api/v1/payments").status_code == 401
    assert client.post("/api/v1/payments", json={}).status_code == 401
    assert client.get("/api/v1/invoices/1/payments").status_code == 401
    assert (
        client.patch("/api/v1/allocations/1", json={"amount_cents": 1}).status_code
        == 401
    )
