"""仪表盘聚合查询。

口径：
- 发票只统计 status=active 且未软删；日期按 issue_date 过滤。
- 付款只统计 status!=void；日期按 paid_at 过滤。
- 已付/已分配只统计 allocation.status=active。
- 金额全部为整数分。
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.category import Category
from ..models.invoice import Invoice
from ..models.payment import Payment, PaymentAllocation
from ..schemas.dashboard import (
    CategoryBreakdown,
    DashboardGaps,
    DashboardSummary,
    DashboardTotals,
    MonthBreakdown,
    PayerBreakdown,
)
from ..shared.enums import AllocationStatus, InvoiceStatus, PaymentMethod, PaymentStatus
from ..shared.errors import BadRequestError


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _day_end(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=UTC)


def _invoice_conditions(date_from: date | None, date_to: date | None) -> list[Any]:
    conditions: list[Any] = [
        Invoice.deleted_at.is_(None),
        Invoice.status == InvoiceStatus.ACTIVE.value,
    ]
    if date_from is not None:
        conditions.append(Invoice.issue_date >= date_from)
    if date_to is not None:
        conditions.append(Invoice.issue_date <= date_to)
    return conditions


def _payment_conditions(date_from: date | None, date_to: date | None) -> list[Any]:
    conditions: list[Any] = [Payment.status != PaymentStatus.VOID.value]
    if date_from is not None:
        conditions.append(Payment.paid_at >= _day_start(date_from))
    if date_to is not None:
        conditions.append(Payment.paid_at < _day_end(date_to))
    return conditions


def _paid_cents(db: Session, invoice_conditions: list[Any]) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0))
        .select_from(PaymentAllocation)
        .join(Invoice, Invoice.id == PaymentAllocation.invoice_id)
        .where(
            PaymentAllocation.status == AllocationStatus.ACTIVE.value,
            *invoice_conditions,
        )
    )
    return int(total or 0)


def _missing_evidence_count(db: Session, payment_conditions: list[Any]) -> int:
    count = db.scalar(
        select(func.count(Payment.id)).where(
            *payment_conditions,
            Payment.method != PaymentMethod.TEACHER_ADVANCE.value,
            Payment.evidence_document_id.is_(None),
        )
    )
    return int(count or 0)


def _invoice_unpaid_count(db: Session, invoice_conditions: list[Any]) -> int:
    paid_subquery = (
        select(
            PaymentAllocation.invoice_id.label("invoice_id"),
            func.coalesce(func.sum(PaymentAllocation.amount_cents), 0).label(
                "paid_cents"
            ),
        )
        .where(PaymentAllocation.status == AllocationStatus.ACTIVE.value)
        .group_by(PaymentAllocation.invoice_id)
        .subquery()
    )
    count = db.scalar(
        select(func.count())
        .select_from(Invoice)
        .outerjoin(paid_subquery, paid_subquery.c.invoice_id == Invoice.id)
        .where(
            *invoice_conditions,
            Invoice.total_cents > func.coalesce(paid_subquery.c.paid_cents, 0),
        )
    )
    return int(count or 0)


def _payment_unallocated_count(db: Session, payment_conditions: list[Any]) -> int:
    allocated_subquery = (
        select(
            PaymentAllocation.payment_id.label("payment_id"),
            func.coalesce(func.sum(PaymentAllocation.amount_cents), 0).label(
                "allocated_cents"
            ),
        )
        .where(PaymentAllocation.status == AllocationStatus.ACTIVE.value)
        .group_by(PaymentAllocation.payment_id)
        .subquery()
    )
    count = db.scalar(
        select(func.count())
        .select_from(Payment)
        .outerjoin(allocated_subquery, allocated_subquery.c.payment_id == Payment.id)
        .where(
            *payment_conditions,
            Payment.amount_cents
            > func.coalesce(allocated_subquery.c.allocated_cents, 0),
        )
    )
    return int(count or 0)


def _category_breakdown(
    db: Session, invoice_conditions: list[Any]
) -> list[CategoryBreakdown]:
    rows = db.execute(
        select(
            Invoice.category_id,
            Category.name,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total_cents), 0),
        )
        .select_from(Invoice)
        .outerjoin(Category, Category.id == Invoice.category_id)
        .where(*invoice_conditions)
        .group_by(Invoice.category_id, Category.name)
    ).all()

    items = [
        CategoryBreakdown(
            category_id=category_id,
            name=name or "未分类",
            invoice_count=int(invoice_count or 0),
            total_cents=int(total_cents or 0),
        )
        for category_id, name, invoice_count, total_cents in rows
    ]
    items.sort(key=lambda item: (-item.total_cents, item.name))
    return items


def _month_breakdown(db: Session, invoice_conditions: list[Any]) -> list[MonthBreakdown]:
    month_expression = func.strftime("%Y-%m", Invoice.issue_date)
    rows = db.execute(
        select(
            month_expression.label("month"),
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total_cents), 0),
        )
        .select_from(Invoice)
        .where(*invoice_conditions)
        .group_by(month_expression)
        .order_by(month_expression)
    ).all()
    return [
        MonthBreakdown(
            month=str(month),
            invoice_count=int(invoice_count or 0),
            total_cents=int(total_cents or 0),
        )
        for month, invoice_count, total_cents in rows
    ]


def _payer_breakdown(
    db: Session, payment_conditions: list[Any]
) -> list[PayerBreakdown]:
    rows = db.execute(
        select(
            Payment.payer_name,
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount_cents), 0),
        )
        .select_from(Payment)
        .where(*payment_conditions)
        .group_by(Payment.payer_name)
    ).all()

    merged: dict[str, list[int]] = {}
    for payer_name, payment_count, total_cents in rows:
        name = (payer_name or "").strip() or "未指定"
        bucket = merged.setdefault(name, [0, 0])
        bucket[0] += int(payment_count or 0)
        bucket[1] += int(total_cents or 0)

    items = [
        PayerBreakdown(payer_name=name, payment_count=values[0], total_cents=values[1])
        for name, values in merged.items()
    ]
    items.sort(key=lambda item: (-item.total_cents, item.payer_name))
    return items


def get_summary(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> DashboardSummary:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise BadRequestError("invalid_date_range", "开始日期不能晚于结束日期")

    invoice_conditions = _invoice_conditions(date_from, date_to)
    payment_conditions = _payment_conditions(date_from, date_to)

    row = db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total_cents), 0),
        )
        .select_from(Invoice)
        .where(*invoice_conditions)
    ).one()
    invoice_count = int(row[0] or 0)
    invoice_total_cents = int(row[1] or 0)

    payment_total_cents = int(
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount_cents), 0))
            .select_from(Payment)
            .where(*payment_conditions)
        )
        or 0
    )
    paid_cents = _paid_cents(db, invoice_conditions)
    missing_evidence_count = _missing_evidence_count(db, payment_conditions)
    unpaid_cents = max(invoice_total_cents - paid_cents, 0)

    invoice_unpaid = _invoice_unpaid_count(db, invoice_conditions)
    payment_unallocated = _payment_unallocated_count(db, payment_conditions)

    return DashboardSummary(
        totals=DashboardTotals(
            invoice_count=invoice_count,
            invoice_total_cents=invoice_total_cents,
            payment_total_cents=payment_total_cents,
            paid_cents=paid_cents,
            unpaid_cents=unpaid_cents,
            missing_evidence_count=missing_evidence_count,
        ),
        by_category=_category_breakdown(db, invoice_conditions),
        by_month=_month_breakdown(db, invoice_conditions),
        by_payer=_payer_breakdown(db, payment_conditions),
        gaps=DashboardGaps(
            invoice_unpaid=invoice_unpaid,
            payment_unallocated=payment_unallocated,
            missing_evidence=missing_evidence_count,
        ),
    )
