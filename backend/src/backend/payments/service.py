"""付款与分配领域服务。

集中处理付款查询、引用校验、额度校验、两端状态重算与审计快照。
所有金额均为整数分；所有变更由调用方在同一事务内 commit。
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..models.document import Document
from ..models.invoice import Invoice
from ..models.payment import Payment, PaymentAllocation
from ..models.user import User
from ..schemas.payment import (
    AllocationOut,
    PaymentDetail,
    PaymentInvoiceSummary,
    PaymentOut,
)
from ..shared.audit import record_audit
from ..shared.enums import (
    AllocationStatus,
    InvoicePaymentStatus,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    Role,
)
from ..shared.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from ..shared.pagination import paginate

ACTIVE = AllocationStatus.ACTIVE.value
REVERSED = AllocationStatus.REVERSED.value
VOID_PAYMENT = PaymentStatus.VOID.value

_PAYMENT_SORT_FIELDS: dict[str, Any] = {
    "paid_at": Payment.paid_at,
    "amount_cents": Payment.amount_cents,
    "created_at": Payment.created_at,
    "id": Payment.id,
}
_DEFAULT_PAYMENT_SORT = ("paid_at", "desc")

_PAYMENT_SNAPSHOT_FIELDS = (
    "id",
    "amount_cents",
    "paid_at",
    "payer_user_id",
    "payer_name",
    "method",
    "external_txn_ref",
    "evidence_document_id",
    "status",
    "requested_at",
    "confirmed_by",
    "confirmed_at",
    "note",
    "created_by",
    "created_at",
)

_ALLOCATION_SNAPSHOT_FIELDS = (
    "id",
    "payment_id",
    "invoice_id",
    "amount_cents",
    "status",
    "note",
    "created_by",
    "created_at",
    "updated_at",
)


def payment_snapshot(payment: Payment) -> dict[str, Any]:
    return {field: getattr(payment, field) for field in _PAYMENT_SNAPSHOT_FIELDS}


def allocation_snapshot(allocation: PaymentAllocation) -> dict[str, Any]:
    return {field: getattr(allocation, field) for field in _ALLOCATION_SNAPSHOT_FIELDS}


def is_admin(user: User) -> bool:
    return user.role == Role.ADMIN.value


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


def get_payment_or_404(
    db: Session, payment_id: int, *, with_invoices: bool = False
) -> Payment:
    loader = selectinload(Payment.allocations)
    if with_invoices:
        loader = loader.selectinload(PaymentAllocation.invoice)
    payment = db.scalar(select(Payment).options(loader).where(Payment.id == payment_id))
    if payment is None:
        raise NotFoundError("payment_not_found", "付款记录不存在")
    return payment


def get_allocation_or_404(db: Session, allocation_id: int) -> PaymentAllocation:
    allocation = db.scalar(
        select(PaymentAllocation)
        .options(
            selectinload(PaymentAllocation.payment),
            selectinload(PaymentAllocation.invoice),
        )
        .where(PaymentAllocation.id == allocation_id)
    )
    if allocation is None:
        raise NotFoundError("allocation_not_found", "付款分配记录不存在")
    return allocation


def parse_payment_sort(sort: str | None) -> tuple[str, str]:
    """解析“字段:顺序”排序参数；非法值回退 paid_at:desc。"""

    if not sort:
        return _DEFAULT_PAYMENT_SORT
    field, _, order = sort.partition(":")
    field = field.strip()
    order = order.strip().lower()
    if field not in _PAYMENT_SORT_FIELDS or order not in ("asc", "desc"):
        return _DEFAULT_PAYMENT_SORT
    return field, order


def list_payments(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    status: PaymentStatus | None = None,
    method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    stmt = select(Payment).options(selectinload(Payment.allocations))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Payment.payer_name.ilike(pattern),
                Payment.external_txn_ref.ilike(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(Payment.status == status.value)
    if method is not None:
        stmt = stmt.where(Payment.method == method.value)
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=UTC)
        stmt = stmt.where(Payment.paid_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        stmt = stmt.where(Payment.paid_at < end)
    sort_field, sort_order = parse_payment_sort(sort)
    sort_column = _PAYMENT_SORT_FIELDS[sort_field]
    stmt = stmt.order_by(
        sort_column.asc() if sort_order == "asc" else sort_column.desc()
    )
    if sort_field != "id":
        stmt = stmt.order_by(Payment.id.desc())
    return paginate(db, stmt, page, page_size)


def build_payment_out(payment: Payment, *, include_allocations: bool = False) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    if not include_allocations:
        out = out.model_copy(update={"allocations": []})
    return out


def build_payment_detail(payment: Payment) -> PaymentDetail:
    allocations = sorted(payment.allocations or [], key=lambda item: item.id)
    detail = PaymentDetail.model_validate(payment)
    detail.allocations = [AllocationOut.model_validate(item) for item in allocations]
    detail.invoices = [
        PaymentInvoiceSummary(
            invoice_id=item.invoice_id,
            invoice_number=item.invoice.invoice_number if item.invoice else None,
            seller_name=item.invoice.seller_name if item.invoice else None,
            total_cents=item.invoice.total_cents if item.invoice else None,
            amount_cents=item.amount_cents,
            status=item.status,
        )
        for item in allocations
    ]
    return detail


# ---------------------------------------------------------------------------
# 引用校验
# ---------------------------------------------------------------------------


def ensure_user_exists(db: Session, user_id: int) -> None:
    if db.get(User, user_id) is None:
        raise NotFoundError("payer_user_not_found", "付款人用户不存在")


def ensure_document_exists(db: Session, document_id: int) -> None:
    if db.get(Document, document_id) is None:
        raise NotFoundError("document_not_found", "付款凭证文档不存在")


def get_active_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.deleted_at is not None:
        raise NotFoundError("invoice_not_found", "发票不存在")
    if invoice.status != InvoiceStatus.ACTIVE.value:
        raise ConflictError(
            "invoice_not_active",
            "只能向 status=active 的发票分配付款",
            {"invoice_id": invoice_id, "status": invoice.status},
        )
    return invoice


# ---------------------------------------------------------------------------
# 额度与唯一性校验
# ---------------------------------------------------------------------------


def active_payment_allocated_cents(
    db: Session, payment_id: int, *, exclude_allocation_id: int | None = None
) -> int:
    stmt = select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0)).where(
        PaymentAllocation.payment_id == payment_id,
        PaymentAllocation.status == ACTIVE,
    )
    if exclude_allocation_id is not None:
        stmt = stmt.where(PaymentAllocation.id != exclude_allocation_id)
    return int(db.scalar(stmt) or 0)


def active_invoice_paid_cents(
    db: Session, invoice_id: int, *, exclude_allocation_id: int | None = None
) -> int:
    stmt = select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0)).where(
        PaymentAllocation.invoice_id == invoice_id,
        PaymentAllocation.status == ACTIVE,
    )
    if exclude_allocation_id is not None:
        stmt = stmt.where(PaymentAllocation.id != exclude_allocation_id)
    return int(db.scalar(stmt) or 0)


def ensure_payment_amount_supported(
    db: Session, payment: Payment, new_amount_cents: int
) -> None:
    allocated = active_payment_allocated_cents(db, payment.id)
    if new_amount_cents < allocated:
        raise ConflictError(
            "payment_amount_below_allocated",
            "付款金额不能小于当前生效分配合计",
            {"amount_cents": new_amount_cents, "allocated_cents": allocated},
        )


def ensure_no_active_allocation(db: Session, payment_id: int, invoice_id: int) -> None:
    existing = db.scalar(
        select(PaymentAllocation.id).where(
            PaymentAllocation.payment_id == payment_id,
            PaymentAllocation.invoice_id == invoice_id,
            PaymentAllocation.status == ACTIVE,
        )
    )
    if existing is not None:
        raise ConflictError(
            "allocation_exists",
            "该付款与该发票已存在生效的分配",
            {"payment_id": payment_id, "invoice_id": invoice_id},
        )


def ensure_allocation_within_limits(
    db: Session,
    payment: Payment,
    invoice: Invoice,
    amount_cents: int,
    *,
    exclude_allocation_id: int | None = None,
) -> None:
    payment_allocated = active_payment_allocated_cents(
        db, payment.id, exclude_allocation_id=exclude_allocation_id
    )
    if payment_allocated + amount_cents > payment.amount_cents:
        raise ConflictError(
            "allocation_exceeds_payment",
            "分配金额超过付款剩余可分配额度",
            {
                "payment_id": payment.id,
                "amount_cents": amount_cents,
                "allocated_cents": payment_allocated,
                "remaining_cents": max(payment.amount_cents - payment_allocated, 0),
            },
        )

    invoice_paid = active_invoice_paid_cents(
        db, invoice.id, exclude_allocation_id=exclude_allocation_id
    )
    if invoice_paid + amount_cents > invoice.total_cents:
        raise ConflictError(
            "allocation_exceeds_invoice",
            "分配金额超过发票剩余可分配额度",
            {
                "invoice_id": invoice.id,
                "amount_cents": amount_cents,
                "paid_cents": invoice_paid,
                "remaining_cents": max(invoice.total_cents - invoice_paid, 0),
            },
        )


# ---------------------------------------------------------------------------
# 状态重算（所有变更后都必须调用）
# ---------------------------------------------------------------------------


def recompute_payment_status(db: Session, payment: Payment) -> Payment:
    """按 active allocation 合计重算付款状态；void 保持。"""

    if payment.status == VOID_PAYMENT:
        return payment

    db.flush()
    allocated = active_payment_allocated_cents(db, payment.id)
    if allocated <= 0:
        payment.status = PaymentStatus.UNALLOCATED.value
    elif allocated >= payment.amount_cents:
        payment.status = PaymentStatus.FULLY_ALLOCATED.value
    else:
        payment.status = PaymentStatus.PARTIALLY_ALLOCATED.value
    db.flush()
    return payment


def recompute_invoice_payment_status(db: Session, invoice: Invoice) -> Invoice:
    """按 active allocation 合计重算发票 paid_cents / payment_status。"""

    db.flush()
    paid = active_invoice_paid_cents(db, invoice.id)
    invoice.paid_cents = paid
    if paid <= 0:
        invoice.payment_status = InvoicePaymentStatus.UNPAID.value
    elif paid >= invoice.total_cents:
        invoice.payment_status = InvoicePaymentStatus.PAID.value
    else:
        invoice.payment_status = InvoicePaymentStatus.PARTIAL.value
    db.flush()
    return invoice


def recompute_payment_and_invoice(
    db: Session, payment: Payment, invoice: Invoice
) -> None:
    recompute_payment_status(db, payment)
    recompute_invoice_payment_status(db, invoice)


# ---------------------------------------------------------------------------
# 写操作
# ---------------------------------------------------------------------------


def create_payment(
    db: Session,
    *,
    amount_cents: int,
    paid_at: datetime,
    method: PaymentMethod,
    actor_id: int | None,
    payer_user_id: int | None = None,
    payer_name: str | None = None,
    external_txn_ref: str | None = None,
    evidence_document_id: int | None = None,
    requested_at: datetime | None = None,
    note: str | None = None,
    request: Any = None,
) -> Payment:
    if payer_user_id is not None:
        ensure_user_exists(db, payer_user_id)
    if evidence_document_id is not None:
        ensure_document_exists(db, evidence_document_id)

    payment = Payment(
        amount_cents=amount_cents,
        paid_at=paid_at,
        payer_user_id=payer_user_id,
        payer_name=payer_name,
        method=method.value,
        external_txn_ref=external_txn_ref,
        evidence_document_id=evidence_document_id,
        status=PaymentStatus.UNALLOCATED.value,
        requested_at=requested_at,
        note=note,
        created_by=actor_id,
    )
    db.add(payment)
    db.flush()
    record_audit(
        db,
        actor_id,
        "payment.create",
        "payment",
        payment.id,
        after=payment_snapshot(payment),
        request=request,
    )
    db.commit()
    db.refresh(payment)
    return payment


def update_payment(
    db: Session,
    payment_id: int,
    *,
    updates: dict[str, Any],
    actor: User,
    request: Any = None,
) -> Payment:
    payment = get_payment_or_404(db, payment_id)
    if not is_admin(actor) and payment.created_by != actor.id:
        raise ForbiddenError("forbidden", "只有管理员或付款创建人可以修改该付款")

    before = payment_snapshot(payment)

    for required in ("amount_cents", "paid_at", "method"):
        if required in updates and updates[required] is None:
            raise BadRequestError(
                "invalid_payment_update", "付款金额、付款日期与付款方式不能为空"
            )

    if updates.get("payer_user_id") is not None:
        ensure_user_exists(db, updates["payer_user_id"])
    if updates.get("evidence_document_id") is not None:
        ensure_document_exists(db, updates["evidence_document_id"])

    if updates.get("amount_cents") is not None:
        ensure_payment_amount_supported(db, payment, updates["amount_cents"])

    nullable_fields = (
        "payer_user_id",
        "payer_name",
        "external_txn_ref",
        "evidence_document_id",
        "requested_at",
        "note",
    )
    for field in nullable_fields:
        if field in updates:
            setattr(payment, field, updates[field])

    if "amount_cents" in updates:
        payment.amount_cents = updates["amount_cents"]
    if "paid_at" in updates:
        payment.paid_at = updates["paid_at"]
    if "method" in updates:
        method = updates["method"]
        payment.method = method.value if isinstance(method, PaymentMethod) else str(method)

    db.flush()
    recompute_payment_status(db, payment)
    record_audit(
        db,
        actor.id,
        "payment.update",
        "payment",
        payment.id,
        before=before,
        after=payment_snapshot(payment),
        request=request,
    )
    db.commit()
    db.refresh(payment)
    return payment


def create_allocation(
    db: Session,
    payment_id: int,
    *,
    invoice_id: int,
    amount_cents: int,
    note: str | None,
    actor_id: int | None,
    request: Any = None,
) -> PaymentAllocation:
    payment = get_payment_or_404(db, payment_id)
    if payment.status == VOID_PAYMENT:
        raise ConflictError("payment_void", "作废付款不能继续分配", {"payment_id": payment_id})

    invoice = get_active_invoice_or_404(db, invoice_id)
    ensure_no_active_allocation(db, payment.id, invoice.id)
    ensure_allocation_within_limits(db, payment, invoice, amount_cents)

    allocation = PaymentAllocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount_cents=amount_cents,
        status=ACTIVE,
        note=note,
        created_by=actor_id,
    )
    db.add(allocation)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "allocation_exists",
            "该付款与该发票已存在生效的分配",
            {"payment_id": payment_id, "invoice_id": invoice_id},
        ) from exc

    recompute_payment_and_invoice(db, payment, invoice)
    record_audit(
        db,
        actor_id,
        "allocation.create",
        "allocation",
        allocation.id,
        after=allocation_snapshot(allocation),
        request=request,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "allocation_exists",
            "该付款与该发票已存在生效的分配",
            {"payment_id": payment_id, "invoice_id": invoice_id},
        ) from exc
    db.refresh(allocation)
    return allocation


def update_allocation(
    db: Session,
    allocation_id: int,
    *,
    amount_cents: int | None = None,
    note: str | None = None,
    note_provided: bool = False,
    actor_id: int | None,
    request: Any = None,
) -> PaymentAllocation:
    allocation = get_allocation_or_404(db, allocation_id)
    if allocation.status != ACTIVE:
        raise ConflictError(
            "allocation_not_active", "只能修改生效中的分配", {"allocation_id": allocation_id}
        )

    payment = allocation.payment or db.get(Payment, allocation.payment_id)
    invoice = allocation.invoice or db.get(Invoice, allocation.invoice_id)
    if payment is None or invoice is None:
        raise NotFoundError("allocation_target_missing", "分配关联的付款或发票不存在")

    before = allocation_snapshot(allocation)

    if amount_cents is not None:
        ensure_allocation_within_limits(
            db,
            payment,
            invoice,
            amount_cents,
            exclude_allocation_id=allocation.id,
        )
        allocation.amount_cents = amount_cents
    if note_provided:
        allocation.note = note

    db.flush()
    recompute_payment_and_invoice(db, payment, invoice)
    record_audit(
        db,
        actor_id,
        "allocation.update",
        "allocation",
        allocation.id,
        before=before,
        after=allocation_snapshot(allocation),
        request=request,
    )
    db.commit()
    db.refresh(allocation)
    return allocation


def revoke_allocation(
    db: Session,
    allocation_id: int,
    *,
    actor: User,
    request: Any = None,
) -> None:
    allocation = get_allocation_or_404(db, allocation_id)
    payment = allocation.payment or db.get(Payment, allocation.payment_id)
    if not is_admin(actor) and allocation.created_by != actor.id:
        if payment is None or payment.created_by != actor.id:
            raise ForbiddenError(
                "forbidden", "只有管理员、分配创建人或付款创建人可以撤销该分配"
            )

    if allocation.status != ACTIVE:
        raise ConflictError(
            "allocation_not_active", "该分配已经撤销", {"allocation_id": allocation_id}
        )

    invoice = allocation.invoice or db.get(Invoice, allocation.invoice_id)
    if payment is None or invoice is None:
        raise NotFoundError("allocation_target_missing", "分配关联的付款或发票不存在")

    before = allocation_snapshot(allocation)
    allocation.status = REVERSED
    db.flush()

    recompute_payment_and_invoice(db, payment, invoice)
    record_audit(
        db,
        actor.id,
        "allocation.revoke",
        "allocation",
        allocation.id,
        before=before,
        after=allocation_snapshot(allocation),
        request=request,
    )
    db.commit()
