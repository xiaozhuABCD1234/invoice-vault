"""发票领域测试辅助函数（本模块不含测试用例）。"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.audit import AuditLog
from backend.models.category import Category
from backend.models.document import Document, DocumentVersion
from backend.models.extraction import ExtractionJob
from backend.models.payment import Payment, PaymentAllocation
from backend.models.user import User
from backend.shared.config import Settings
from backend.shared.db import utcnow

DEFAULT_ITEMS: list[dict[str, Any]] = [
    {
        "name": "螺栓",
        "quantity": 10,
        "unit_price_millis": 1000,
        "amount_cents": 10000,
    },
    {
        "name": "螺母",
        "quantity": 2,
        "unit_price_millis": 650,
        "amount_cents": 1300,
    },
]


def get_category(db: Session, name: str = "标准件") -> Category:
    category = db.scalar(
        select(Category).where(Category.name == name, Category.kind == "purchase")
    )
    assert category is not None, f"类别 {name} 未种子化"
    return category


def login(client: TestClient, username: str, password: str) -> TestClient:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def make_document(
    db: Session,
    settings: Settings,
    *,
    owner: User,
    created_by: User | None = None,
    title: str = "发票原件",
    doc_type: str = "invoice",
) -> Document:
    creator = created_by or owner
    document = Document(
        doc_type=doc_type,
        title=title,
        owner_user_id=owner.id,
        created_by=creator.id,
    )
    db.add(document)
    db.flush()

    payload = f"{title}-{uuid4()}".encode()
    sha256 = hashlib.sha256(payload).hexdigest()
    storage_key = f"2026/07/{sha256[:2]}/{sha256}.pdf"
    path = Path(settings.upload_dir) / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)

    version = DocumentVersion(
        document_id=document.id,
        version_no=1,
        storage_key=storage_key,
        original_name="invoice.pdf",
        display_name="发票.pdf",
        mime_type="application/pdf",
        size_bytes=len(payload),
        sha256=sha256,
        created_by=creator.id,
        is_latest=True,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    db.commit()
    db.refresh(document)
    return document


def make_job(
    db: Session,
    *,
    document: Document,
    status_value: str = "review_pending",
    provider: str = "mock",
) -> ExtractionJob:
    job = ExtractionJob(
        document_id=document.id,
        provider=provider,
        model="mock-1",
        status=status_value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def invoice_payload(
    db: Session,
    *,
    number: str = "INV-0001",
    category_name: str = "标准件",
    requester: User | None = None,
    owner: User | None = None,
    items: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    category = get_category(db, category_name)
    payload: dict[str, Any] = {
        "invoice_number": number,
        "invoice_code": None,
        "invoice_type": "电子发票",
        "issue_date": "2026-07-12",
        "seller_name": "上海标准件厂",
        "seller_tax_id": None,
        "buyer_name": None,
        "buyer_tax_id": None,
        "amount_ex_tax_cents": 10000,
        "tax_cents": 1300,
        "total_cents": 11300,
        "tax_rate_bp": 1300,
        "category_id": category.id,
        "requester_id": requester.id if requester is not None else None,
        "owner_id": owner.id if owner is not None else None,
        "invoice_form": "electronic",
        "status": "active",
        "note": "测试发票",
        "items": [
            dict(item) for item in (items if items is not None else DEFAULT_ITEMS)
        ],
    }
    payload.update(overrides)
    return payload


def create_invoice(
    client: TestClient,
    db: Session,
    *,
    number: str = "INV-0001",
    **overrides: Any,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/invoices", json=invoice_payload(db, number=number, **overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_allocation(
    db: Session,
    *,
    invoice_id: int,
    amount_cents: int,
    actor: User | None = None,
    allocation_status: str = "active",
) -> PaymentAllocation:
    payment = Payment(
        amount_cents=max(amount_cents, 1),
        paid_at=utcnow(),
        method="bank_transfer",
        status="fully_allocated",
        created_by=actor.id if actor is not None else None,
    )
    db.add(payment)
    db.flush()
    allocation = PaymentAllocation(
        payment_id=payment.id,
        invoice_id=invoice_id,
        amount_cents=amount_cents,
        status=allocation_status,
        created_by=actor.id if actor is not None else None,
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


def audit_actions(db: Session) -> list[str]:
    db.expire_all()
    return list(db.scalars(select(AuditLog.action).order_by(AuditLog.id)).all())
