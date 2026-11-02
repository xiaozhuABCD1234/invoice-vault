"""发票创建、列表、详情与 OpenAPI 契约。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.audit import AuditLog
from backend.models.category import Category
from backend.models.invoice import Invoice, InvoiceItem

from tests.test_invoices_support import (
    add_allocation,
    create_invoice,
    invoice_payload,
)


def _list(client: TestClient, **params) -> dict:
    response = client.get("/api/v1/invoices", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_create_invoice_success(user_client: TestClient, db_session: Session, normal_user):
    payload = invoice_payload(
        db_session, number="INV-1001", requester=normal_user, owner=normal_user
    )
    response = user_client.post("/api/v1/invoices", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["invoice_number"] == "INV-1001"
    assert data["issue_date"] == "2026-07-12"
    assert data["total_cents"] == 11300
    assert data["status"] == "active"
    assert data["payment_status"] == "unpaid"
    assert data["paid_cents"] == 0
    assert data["category_name"] == "标准件"
    assert data["requester_name"] == normal_user.display_name
    assert data["owner_name"] == normal_user.display_name
    assert data["created_by"] == normal_user.id
    assert data["confirmed_by"] == normal_user.id
    assert data["confirmed_at"] is not None
    assert data["allocations"] == []
    assert [item["name"] for item in data["items"]] == ["螺栓", "螺母"]
    assert [item["sort_order"] for item in data["items"]] == [1, 2]

    db_session.expire_all()
    invoice = db_session.scalar(select(Invoice).where(Invoice.id == data["id"]))
    assert invoice is not None
    names = list(
        db_session.scalars(
            select(InvoiceItem.name)
            .where(InvoiceItem.invoice_id == invoice.id)
            .order_by(InvoiceItem.sort_order)
        ).all()
    )
    assert names == ["螺栓", "螺母"]

    logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "invoice.create")
        ).all()
    )
    assert len(logs) == 1
    assert logs[0].entity_type == "invoice"
    assert logs[0].entity_id == str(data["id"])
    assert logs[0].after_json["invoice_number"] == "INV-1001"
    assert logs[0].after_json["items"][0]["name"] == "螺栓"


def test_create_invoice_amount_mismatch_422(
    user_client: TestClient, db_session: Session
):
    payload = invoice_payload(db_session, number="INV-1002", total_cents=12000)
    response = user_client.post("/api/v1/invoices", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"]["errors"]


def test_create_invoice_duplicate_number_409(
    user_client: TestClient, db_session: Session
):
    create_invoice(user_client, db_session, number="INV-1003")
    response = user_client.post(
        "/api/v1/invoices", json=invoice_payload(db_session, number="INV-1003")
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "invoice_duplicate"
    assert body["details"]["invoice_number"] == "INV-1003"


def test_create_invoice_invalid_category(
    user_client: TestClient, db_session: Session
):
    missing = user_client.post(
        "/api/v1/invoices",
        json=invoice_payload(db_session, number="INV-1004", category_id=999999),
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "category_not_found"

    inactive = Category(
        name="停用类别", kind="purchase", sort_order=99, is_active=False
    )
    db_session.add(inactive)
    db_session.commit()
    db_session.refresh(inactive)

    disabled = user_client.post(
        "/api/v1/invoices",
        json=invoice_payload(
            db_session, number="INV-1005", category_id=inactive.id
        ),
    )
    assert disabled.status_code == 400
    assert disabled.json()["code"] == "category_inactive"


def test_create_invoice_missing_requester_or_owner(
    user_client: TestClient, db_session: Session
):
    requester = user_client.post(
        "/api/v1/invoices",
        json=invoice_payload(
            db_session, number="INV-1006", requester_id=999999
        ),
    )
    assert requester.status_code == 404
    assert requester.json()["code"] == "user_not_found"
    assert requester.json()["details"]["field"] == "requester_id"

    owner = user_client.post(
        "/api/v1/invoices",
        json=invoice_payload(db_session, number="INV-1007", owner_id=888888),
    )
    assert owner.status_code == 404
    assert owner.json()["code"] == "user_not_found"
    assert owner.json()["details"]["field"] == "owner_id"


def test_invoice_endpoints_require_login(client: TestClient, db_session: Session):
    assert client.get("/api/v1/invoices").status_code == 401
    assert client.get("/api/v1/invoices/1").status_code == 401
    response = client.post(
        "/api/v1/invoices", json=invoice_payload(db_session, number="INV-1008")
    )
    assert response.status_code == 401


def test_list_invoices_filters_sort_and_pagination(
    user_client: TestClient, db_session: Session, normal_user, make_user
):
    other = make_user("other", "其他成员")
    create_invoice(
        user_client,
        db_session,
        number="INV-2001",
        issue_date="2026-07-01",
        requester=normal_user,
        owner=normal_user,
    )
    create_invoice(
        user_client,
        db_session,
        number="INV-2002",
        issue_date="2026-07-05",
        seller_name="无锡机加工厂",
        category_name="机加工",
        amount_ex_tax_cents=20000,
        tax_cents=2600,
        total_cents=22600,
        requester=other,
        owner=normal_user,
    )
    create_invoice(
        user_client,
        db_session,
        number="INV-2003",
        issue_date="2026-06-01",
        status="review_pending",
        amount_ex_tax_cents=5000,
        tax_cents=0,
        total_cents=5000,
        requester=normal_user,
        owner=other,
    )

    default_order = _list(user_client)
    assert default_order["total"] == 3
    assert [item["invoice_number"] for item in default_order["items"]] == [
        "INV-2002",
        "INV-2001",
        "INV-2003",
    ]
    first = default_order["items"][0]
    assert first["category_name"] == "机加工"
    assert first["requester_name"] == "其他成员"
    assert first["owner_name"] == "普通成员"

    assert _list(user_client, q="标准件")["total"] == 2
    assert _list(user_client, q="INV-2002")["total"] == 1
    assert _list(user_client, status="active")["total"] == 2
    assert _list(user_client, status="review_pending")["total"] == 1
    assert _list(user_client, payment_status="unpaid")["total"] == 3
    assert _list(user_client, payment_status="paid")["total"] == 0

    standard = db_session.scalar(
        select(Category).where(
            Category.name == "标准件", Category.kind == "purchase"
        )
    )
    assert standard is not None
    assert _list(user_client, category_id=standard.id)["total"] == 2
    assert _list(user_client, requester_id=other.id)["total"] == 1
    assert _list(user_client, owner_id=other.id)["total"] == 1
    assert (
        _list(user_client, date_from="2026-07-01", date_to="2026-07-31")["total"]
        == 2
    )

    ascending = _list(user_client, sort="total_cents:asc")
    assert [item["total_cents"] for item in ascending["items"]] == [
        5000,
        11300,
        22600,
    ]
    descending = _list(user_client, sort="total_cents:desc")
    assert [item["total_cents"] for item in descending["items"]] == [
        22600,
        11300,
        5000,
    ]
    by_date = _list(user_client, sort="issue_date:asc")
    assert [item["issue_date"] for item in by_date["items"]] == [
        "2026-06-01",
        "2026-07-01",
        "2026-07-05",
    ]
    by_id = _list(user_client, sort="id:asc")
    assert [item["invoice_number"] for item in by_id["items"]] == [
        "INV-2001",
        "INV-2002",
        "INV-2003",
    ]

    for invalid_sort in ("", "bogus", "issue_date:sideways", "issue_date", "-total_cents"):
        fallback = _list(user_client, sort=invalid_sort)
        assert [item["invoice_number"] for item in fallback["items"]] == [
            "INV-2002",
            "INV-2001",
            "INV-2003",
        ]

    page_one = _list(user_client, page=1, page_size=2)
    assert page_one["total"] == 3
    assert page_one["page"] == 1
    assert page_one["page_size"] == 2
    assert len(page_one["items"]) == 2
    page_two = _list(user_client, page=2, page_size=2)
    assert len(page_two["items"]) == 1
    assert page_two["items"][0]["invoice_number"] == "INV-2003"


def test_get_invoice_detail_items_and_allocations(
    user_client: TestClient, db_session: Session, normal_user
):
    items = [
        {
            "name": "甲",
            "quantity": 1,
            "unit_price_millis": 1000,
            "amount_cents": 1000,
            "sort_order": 2,
        },
        {
            "name": "乙",
            "quantity": 2,
            "unit_price_millis": 500,
            "amount_cents": 1000,
            "sort_order": 1,
        },
    ]
    created = create_invoice(
        user_client,
        db_session,
        number="INV-4001",
        requester=normal_user,
        owner=normal_user,
        items=items,
    )
    assert [item["name"] for item in created["items"]] == ["乙", "甲"]
    assert [item["sort_order"] for item in created["items"]] == [1, 2]

    allocation = add_allocation(
        db_session,
        invoice_id=created["id"],
        amount_cents=3000,
        actor=normal_user,
    )

    response = user_client.get(f"/api/v1/invoices/{created['id']}")
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["category_name"] == "标准件"
    assert detail["requester_name"] == "普通成员"
    assert detail["owner_name"] == "普通成员"
    assert [item["name"] for item in detail["items"]] == ["乙", "甲"]
    assert len(detail["allocations"]) == 1
    assert detail["allocations"][0]["id"] == allocation.id
    assert detail["allocations"][0]["status"] == "active"
    assert detail["allocations"][0]["amount_cents"] == 3000

    missing = user_client.get("/api/v1/invoices/999999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "invoice_not_found"


def test_soft_deleted_invoice_visibility(
    admin_client: TestClient, user_client: TestClient, db_session: Session
):
    created = create_invoice(user_client, db_session, number="INV-5001")
    detail_url = f"/api/v1/invoices/{created['id']}"

    deleted = admin_client.delete(detail_url)
    assert deleted.status_code == 204
    assert deleted.content == b""

    assert _list(user_client)["total"] == 0
    assert _list(admin_client)["total"] == 0
    admin_all = _list(admin_client, include_deleted="true")
    assert admin_all["total"] == 1
    assert admin_all["items"][0]["id"] == created["id"]

    assert user_client.get(detail_url).status_code == 404
    admin_detail = admin_client.get(detail_url)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["deleted_at"] is not None

    duplicate = user_client.post(
        "/api/v1/invoices", json=invoice_payload(db_session, number="INV-5001")
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "invoice_duplicate"


def test_invoices_openapi_contract(app):
    spec = app.openapi()
    paths = spec["paths"]
    assert {"get", "post"} <= set(paths["/api/v1/invoices"])
    assert {"get", "patch", "delete"} <= set(
        paths["/api/v1/invoices/{invoice_id}"]
    )
    assert "post" in paths["/api/v1/extraction-jobs/{job_id}/approve"]

    components = spec["components"]["schemas"]
    for name in (
        "InvoiceOut",
        "InvoiceListItem",
        "InvoiceCreate",
        "InvoiceUpdate",
        "InvoiceApproveResult",
    ):
        assert name in components
    assert "status" in {
        parameter["name"]
        for parameter in paths["/api/v1/invoices"]["get"]["parameters"]
    }
