"""仪表盘：指标口径、日期过滤、软删/作废排除与空数据。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.document import Document, DocumentVersion
from backend.models.invoice import Invoice
from backend.models.payment import Payment, PaymentAllocation
from backend.models.user import User


def create_category(db: Session, name: str) -> Category:
    category = Category(name=name, kind="purchase", sort_order=1, is_active=True)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_document(db: Session, name: str = "付款凭证.jpg") -> Document:
    digest = uuid4().hex + uuid4().hex
    document = Document(
        doc_type="payment_evidence",
        title=name,
        created_at=datetime.now(UTC),
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_no=1,
        storage_key=f"test/{digest}.jpg",
        original_name=name,
        display_name=name,
        mime_type="image/jpeg",
        size_bytes=10,
        sha256=digest,
        created_at=datetime.now(UTC),
        is_latest=True,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    db.commit()
    db.refresh(document)
    return document


def create_invoice(
    db: Session,
    *,
    number: str,
    total_cents: int = 10000,
    issue_date: date = date(2026, 7, 1),
    category: Category | None = None,
    status: str = "active",
    deleted_at: datetime | None = None,
    requester: User | None = None,
) -> Invoice:
    invoice = Invoice(
        invoice_number=number,
        issue_date=issue_date,
        seller_name="仪表店铺",
        amount_ex_tax_cents=total_cents,
        tax_cents=0,
        total_cents=total_cents,
        category_id=category.id if category is not None else None,
        requester_id=requester.id if requester is not None else None,
        status=status,
        payment_status="unpaid",
        paid_cents=0,
        deleted_at=deleted_at,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def create_payment(
    db: Session,
    *,
    amount_cents: int,
    paid_at: datetime,
    payer_name: str | None = "张三",
    method: str = "wechat",
    status: str = "unallocated",
    evidence_document_id: int | None = None,
) -> Payment:
    payment = Payment(
        amount_cents=amount_cents,
        paid_at=paid_at,
        payer_name=payer_name,
        method=method,
        status=status,
        evidence_document_id=evidence_document_id,
        created_at=datetime.now(UTC),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def allocate(
    db: Session,
    payment: Payment,
    invoice: Invoice,
    amount_cents: int,
    *,
    status: str = "active",
) -> PaymentAllocation:
    allocation = PaymentAllocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount_cents=amount_cents,
        status=status,
        created_at=datetime.now(UTC),
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


def test_dashboard_requires_login(client: TestClient):
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_dashboard_empty_returns_zeros(user_client: TestClient):
    response = user_client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["totals"] == {
        "invoice_count": 0,
        "invoice_total_cents": 0,
        "payment_total_cents": 0,
        "paid_cents": 0,
        "unpaid_cents": 0,
        "missing_evidence_count": 0,
    }
    assert body["by_category"] == []
    assert body["by_month"] == []
    assert body["by_payer"] == []
    assert body["gaps"] == {
        "invoice_unpaid": 0,
        "payment_unallocated": 0,
        "missing_evidence": 0,
    }


def test_dashboard_totals_and_breakdowns(user_client: TestClient, db_session: Session):
    category_a = create_category(db_session, "仪表类别A")
    category_b = create_category(db_session, "仪表类别B")
    evidence = create_document(db_session)

    invoice_one = create_invoice(
        db_session,
        number="DASH-1",
        total_cents=10000,
        issue_date=date(2026, 7, 1),
        category=category_a,
    )
    invoice_two = create_invoice(
        db_session,
        number="DASH-2",
        total_cents=20000,
        issue_date=date(2026, 7, 15),
        category=category_b,
    )
    create_invoice(
        db_session,
        number="DASH-3",
        total_cents=5000,
        issue_date=date(2026, 7, 20),
        category=category_a,
        status="review_pending",
    )
    create_invoice(
        db_session,
        number="DASH-4",
        total_cents=1000,
        issue_date=date(2026, 7, 21),
        category=category_a,
        deleted_at=datetime.now(UTC),
    )

    payment_one = create_payment(
        db_session,
        amount_cents=6000,
        paid_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
        payer_name="张三",
        evidence_document_id=evidence.id,
    )
    payment_two = create_payment(
        db_session,
        amount_cents=20000,
        paid_at=datetime(2026, 7, 16, 10, 0, tzinfo=UTC),
        payer_name="李四",
        method="teacher_advance",
    )
    create_payment(
        db_session,
        amount_cents=3000,
        paid_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
        payer_name=None,
    )
    create_payment(
        db_session,
        amount_cents=1000,
        paid_at=datetime(2026, 7, 21, 10, 0, tzinfo=UTC),
        payer_name="王五",
        status="void",
    )
    allocate(db_session, payment_one, invoice_one, 6000)
    allocate(db_session, payment_two, invoice_two, 20000)

    body = user_client.get("/api/v1/dashboard/summary").json()
    assert body["totals"] == {
        "invoice_count": 2,
        "invoice_total_cents": 30000,
        "payment_total_cents": 29000,
        "paid_cents": 26000,
        "unpaid_cents": 4000,
        "missing_evidence_count": 1,
    }
    assert body["by_category"] == [
        {
            "category_id": category_b.id,
            "name": "仪表类别B",
            "invoice_count": 1,
            "total_cents": 20000,
        },
        {
            "category_id": category_a.id,
            "name": "仪表类别A",
            "invoice_count": 1,
            "total_cents": 10000,
        },
    ]
    assert body["by_month"] == [
        {"month": "2026-07", "invoice_count": 2, "total_cents": 30000}
    ]
    assert body["by_payer"] == [
        {"payer_name": "李四", "payment_count": 1, "total_cents": 20000},
        {"payer_name": "张三", "payment_count": 1, "total_cents": 6000},
        {"payer_name": "未指定", "payment_count": 1, "total_cents": 3000},
    ]
    assert body["gaps"] == {
        "invoice_unpaid": 1,
        "payment_unallocated": 1,
        "missing_evidence": 1,
    }


def test_dashboard_date_filters(user_client: TestClient, db_session: Session):
    create_invoice(
        db_session, number="DATE-1", total_cents=10000, issue_date=date(2026, 6, 10)
    )
    create_invoice(
        db_session, number="DATE-2", total_cents=20000, issue_date=date(2026, 7, 10)
    )
    create_invoice(
        db_session, number="DATE-3", total_cents=30000, issue_date=date(2026, 8, 10)
    )
    create_payment(
        db_session,
        amount_cents=5000,
        paid_at=datetime(2026, 6, 11, 10, 0, tzinfo=UTC),
        payer_name="六月付款人",
    )
    create_payment(
        db_session,
        amount_cents=7000,
        paid_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
        payer_name="七月付款人",
    )
    create_payment(
        db_session,
        amount_cents=9000,
        paid_at=datetime(2026, 8, 11, 10, 0, tzinfo=UTC),
        payer_name="八月付款人",
    )

    full = user_client.get("/api/v1/dashboard/summary").json()
    assert full["totals"]["invoice_count"] == 3
    assert full["totals"]["invoice_total_cents"] == 60000
    assert full["totals"]["payment_total_cents"] == 21000

    july = user_client.get(
        "/api/v1/dashboard/summary",
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    ).json()
    assert july["totals"]["invoice_count"] == 1
    assert july["totals"]["invoice_total_cents"] == 20000
    assert july["totals"]["payment_total_cents"] == 7000
    assert july["by_month"] == [
        {"month": "2026-07", "invoice_count": 1, "total_cents": 20000}
    ]
    assert july["by_payer"] == [
        {"payer_name": "七月付款人", "payment_count": 1, "total_cents": 7000}
    ]

    august = user_client.get(
        "/api/v1/dashboard/summary", params={"date_from": "2026-08-01"}
    ).json()
    assert august["totals"]["invoice_count"] == 1
    assert august["totals"]["invoice_total_cents"] == 30000
    assert august["totals"]["payment_total_cents"] == 9000

    june = user_client.get(
        "/api/v1/dashboard/summary", params={"date_to": "2026-06-30"}
    ).json()
    assert june["totals"]["invoice_count"] == 1
    assert june["totals"]["invoice_total_cents"] == 10000
    assert june["totals"]["payment_total_cents"] == 5000


def test_dashboard_excludes_soft_deleted_and_void(
    user_client: TestClient, db_session: Session
):
    active_invoice = create_invoice(
        db_session, number="CLEAN-1", total_cents=10000
    )
    deleted_invoice = create_invoice(
        db_session,
        number="CLEAN-2",
        total_cents=5000,
        deleted_at=datetime.now(UTC),
    )
    create_invoice(db_session, number="CLEAN-3", total_cents=5000, status="void")

    active_payment = create_payment(
        db_session,
        amount_cents=5000,
        paid_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
        payer_name="甲",
    )
    deleted_payment = create_payment(
        db_session,
        amount_cents=5000,
        paid_at=datetime(2026, 7, 3, 10, 0, tzinfo=UTC),
        payer_name="乙",
    )
    create_payment(
        db_session,
        amount_cents=5000,
        paid_at=datetime(2026, 7, 4, 10, 0, tzinfo=UTC),
        payer_name="丙",
        status="void",
    )
    allocate(db_session, active_payment, active_invoice, 5000)
    allocate(db_session, deleted_payment, deleted_invoice, 5000)

    body = user_client.get("/api/v1/dashboard/summary").json()
    assert body["totals"]["invoice_count"] == 1
    assert body["totals"]["invoice_total_cents"] == 10000
    assert body["totals"]["payment_total_cents"] == 10000
    assert body["totals"]["paid_cents"] == 5000
    assert body["totals"]["unpaid_cents"] == 5000
    assert body["totals"]["missing_evidence_count"] == 2
    assert body["gaps"] == {
        "invoice_unpaid": 1,
        "payment_unallocated": 0,
        "missing_evidence": 2,
    }
    payer_names = {item["payer_name"] for item in body["by_payer"]}
    assert payer_names == {"甲", "乙"}
    assert len(body["by_category"]) == 1
    assert body["by_category"][0]["total_cents"] == 10000


def test_dashboard_partial_payment_and_reversed_allocation(
    user_client: TestClient, db_session: Session
):
    invoice = create_invoice(db_session, number="PART-1", total_cents=10000)
    payment = create_payment(
        db_session,
        amount_cents=10000,
        paid_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
        payer_name="部分付款人",
    )
    allocate(db_session, payment, invoice, 4000, status="active")
    allocate(db_session, payment, invoice, 6000, status="reversed")

    body = user_client.get("/api/v1/dashboard/summary").json()
    assert body["totals"]["invoice_total_cents"] == 10000
    assert body["totals"]["payment_total_cents"] == 10000
    assert body["totals"]["paid_cents"] == 4000
    assert body["totals"]["unpaid_cents"] == 6000
    assert body["gaps"] == {
        "invoice_unpaid": 1,
        "payment_unallocated": 1,
        "missing_evidence": 1,
    }


def test_dashboard_by_payer_merges_unspecified(
    user_client: TestClient, db_session: Session
):
    for amount, payer in ((1000, None), (2000, ""), (3000, "   "), (4000, "张三")):
        create_payment(
            db_session,
            amount_cents=amount,
            paid_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
            payer_name=payer,
        )

    body = user_client.get("/api/v1/dashboard/summary").json()
    assert body["totals"]["payment_total_cents"] == 10000
    assert body["totals"]["missing_evidence_count"] == 4
    assert body["by_payer"] == [
        {"payer_name": "未指定", "payment_count": 3, "total_cents": 6000},
        {"payer_name": "张三", "payment_count": 1, "total_cents": 4000},
    ]
    assert body["gaps"]["payment_unallocated"] == 4
    assert body["gaps"]["invoice_unpaid"] == 0


def test_dashboard_by_month_order_and_uncategorized(
    user_client: TestClient, db_session: Session
):
    create_invoice(
        db_session, number="MONTH-1", total_cents=1000, issue_date=date(2026, 2, 1)
    )
    create_invoice(
        db_session, number="MONTH-2", total_cents=2000, issue_date=date(2025, 12, 1)
    )
    create_invoice(
        db_session, number="MONTH-3", total_cents=3000, issue_date=date(2026, 1, 1)
    )

    body = user_client.get("/api/v1/dashboard/summary").json()
    assert [item["month"] for item in body["by_month"]] == [
        "2025-12",
        "2026-01",
        "2026-02",
    ]
    assert body["by_category"] == [
        {
            "category_id": None,
            "name": "未分类",
            "invoice_count": 3,
            "total_cents": 6000,
        }
    ]


def test_dashboard_invalid_date_range(user_client: TestClient):
    response = user_client.get(
        "/api/v1/dashboard/summary",
        params={"date_from": "2026-08-01", "date_to": "2026-07-01"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_date_range"
