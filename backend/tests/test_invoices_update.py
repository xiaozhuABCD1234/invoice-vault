"""发票 PATCH、明细替换与软删保护。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.audit import AuditLog
from backend.models.invoice import Invoice, InvoiceItem

from tests.conftest import NORMAL_PASSWORD
from tests.test_invoices_support import (
    add_allocation,
    create_invoice,
    invoice_payload,
    login,
)


def test_patch_invoice_permission(
    user_client: TestClient,
    admin_client: TestClient,
    client: TestClient,
    db_session: Session,
    normal_user,
    make_user,
):
    created = create_invoice(
        user_client, db_session, number="INV-6001", requester=normal_user
    )
    url = f"/api/v1/invoices/{created['id']}"

    make_user("other-user", "其他成员")
    login(client, "other-user", NORMAL_PASSWORD)
    denied = client.patch(url, json={"note": "越权修改"})
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"

    own = user_client.patch(url, json={"note": "本人修改"})
    assert own.status_code == 200, own.text
    assert own.json()["note"] == "本人修改"

    admin = admin_client.patch(url, json={"note": "管理员修改"})
    assert admin.status_code == 200, admin.text
    assert admin.json()["note"] == "管理员修改"


def test_patch_invoice_amount_below_allocations_conflict(
    user_client: TestClient, db_session: Session, normal_user
):
    created = create_invoice(
        user_client, db_session, number="INV-6002", requester=normal_user
    )
    url = f"/api/v1/invoices/{created['id']}"
    add_allocation(
        db_session,
        invoice_id=created["id"],
        amount_cents=6000,
        actor=normal_user,
    )

    lowered = user_client.patch(
        url,
        json={
            "amount_ex_tax_cents": 4000,
            "tax_cents": 1000,
            "total_cents": 5000,
        },
    )
    assert lowered.status_code == 409
    body = lowered.json()
    assert body["code"] == "invoice_amount_below_allocations"
    assert body["details"] == {"total_cents": 5000, "allocated_cents": 6000}

    unchanged = user_client.get(url).json()
    assert unchanged["total_cents"] == 11300

    equal = user_client.patch(
        url,
        json={
            "amount_ex_tax_cents": 5000,
            "tax_cents": 1000,
            "total_cents": 6000,
        },
    )
    assert equal.status_code == 200, equal.text
    data = equal.json()
    assert data["total_cents"] == 6000
    assert data["paid_cents"] == 6000
    assert data["payment_status"] == "paid"


def test_patch_invoice_replaces_items_and_recomputes_payment_status(
    user_client: TestClient, db_session: Session, normal_user
):
    created = create_invoice(
        user_client, db_session, number="INV-6003", requester=normal_user
    )
    url = f"/api/v1/invoices/{created['id']}"
    add_allocation(
        db_session,
        invoice_id=created["id"],
        amount_cents=5000,
        actor=normal_user,
    )

    new_items = [
        {
            "name": "新一",
            "quantity": 1,
            "unit_price_millis": 1000,
            "amount_cents": 1000,
            "sort_order": 3,
        },
        {
            "name": "新二",
            "quantity": 2,
            "unit_price_millis": 500,
            "amount_cents": 1000,
            "sort_order": 1,
        },
    ]
    replaced = user_client.patch(
        url, json={"note": "替换明细", "items": new_items}
    )
    assert replaced.status_code == 200, replaced.text
    data = replaced.json()
    assert [item["name"] for item in data["items"]] == ["新二", "新一"]
    assert [item["sort_order"] for item in data["items"]] == [1, 3]
    assert data["paid_cents"] == 5000
    assert data["payment_status"] == "partial"

    db_session.expire_all()
    item_count = db_session.scalar(
        select(func.count())
        .select_from(InvoiceItem)
        .where(InvoiceItem.invoice_id == created["id"])
    )
    assert item_count == 2
    old_names = list(
        db_session.scalars(
            select(InvoiceItem.name).where(InvoiceItem.invoice_id == created["id"])
        ).all()
    )
    assert sorted(old_names) == ["新一", "新二"]

    add_allocation(
        db_session,
        invoice_id=created["id"],
        amount_cents=6300,
        actor=normal_user,
    )
    paid = user_client.patch(url, json={"note": "付清"})
    assert paid.status_code == 200, paid.text
    assert paid.json()["paid_cents"] == 11300
    assert paid.json()["payment_status"] == "paid"

    db_session.expire_all()
    update_logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "invoice.update")
        ).all()
    )
    assert len(update_logs) == 2
    assert update_logs[0].before_json["items"][0]["name"] == "螺栓"
    assert update_logs[0].after_json["items"][0]["name"] == "新二"
    assert update_logs[-1].after_json["payment_status"] == "paid"


def test_patch_invoice_duplicate_number_409(
    user_client: TestClient, db_session: Session
):
    first = create_invoice(user_client, db_session, number="INV-6004")
    second = create_invoice(user_client, db_session, number="INV-6005")
    url = f"/api/v1/invoices/{second['id']}"

    duplicate = user_client.patch(url, json={"invoice_number": "INV-6004"})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "invoice_duplicate"
    assert user_client.get(url).json()["invoice_number"] == "INV-6005"

    same = user_client.patch(url, json={"invoice_number": "INV-6005"})
    assert same.status_code == 200
    assert same.json()["invoice_number"] == "INV-6005"
    assert first["invoice_number"] == "INV-6004"


def test_delete_invoice_requires_admin_and_protects_allocations(
    user_client: TestClient,
    admin_client: TestClient,
    db_session: Session,
    normal_user,
):
    created = create_invoice(
        user_client, db_session, number="INV-6006", requester=normal_user
    )
    url = f"/api/v1/invoices/{created['id']}"

    forbidden = user_client.delete(url)
    assert forbidden.status_code == 403

    allocation = add_allocation(
        db_session,
        invoice_id=created["id"],
        amount_cents=1000,
        actor=normal_user,
    )
    blocked = admin_client.delete(url)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "invoice_has_allocations"

    allocation.status = "reversed"
    db_session.commit()

    deleted = admin_client.delete(url)
    assert deleted.status_code == 204
    assert deleted.content == b""

    db_session.expire_all()
    invoice = db_session.get(Invoice, created["id"])
    assert invoice is not None
    assert invoice.deleted_at is not None

    assert user_client.get(url).status_code == 404
    admin_detail = admin_client.get(url)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["deleted_at"] is not None

    again = admin_client.delete(url)
    assert again.status_code == 404

    delete_logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "invoice.delete")
        ).all()
    )
    assert len(delete_logs) == 1
    assert delete_logs[0].before_json["deleted_at"] is None
    assert delete_logs[0].after_json["deleted_at"] is not None

    duplicate = user_client.post(
        "/api/v1/invoices", json=invoice_payload(db_session, number="INV-6006")
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "invoice_duplicate"
