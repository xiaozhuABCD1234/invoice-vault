"""发票相关的付款查询路由：GET /invoices/{id}/payments。"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.invoice import Invoice
from ..models.payment import PaymentAllocation
from ..schemas.payment import (
    InvoicePaymentItem,
    InvoicePaymentsResult,
    PaymentBrief,
)
from ..shared.deps import CurrentUser, DbSession
from ..shared.enums import AllocationStatus
from ..shared.errors import NotFoundError

router = APIRouter(prefix="/invoices", tags=["payments"])


@router.get(
    "/{invoice_id}/payments",
    response_model=InvoicePaymentsResult,
    summary="发票的付款分配列表",
)
def list_invoice_payments(
    invoice_id: int,
    db: DbSession,
    _current_user: CurrentUser,
) -> InvoicePaymentsResult:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.deleted_at is not None:
        raise NotFoundError("invoice_not_found", "发票不存在")

    allocations = list(
        db.scalars(
            select(PaymentAllocation)
            .options(selectinload(PaymentAllocation.payment))
            .where(
                PaymentAllocation.invoice_id == invoice_id,
                PaymentAllocation.status == AllocationStatus.ACTIVE.value,
            )
            .order_by(
                PaymentAllocation.created_at.desc(),
                PaymentAllocation.id.desc(),
            )
        ).all()
    )

    items: list[InvoicePaymentItem] = []
    for allocation in allocations:
        item = InvoicePaymentItem.model_validate(allocation)
        if allocation.payment is not None:
            item.payment = PaymentBrief.model_validate(allocation.payment)
        items.append(item)
    return InvoicePaymentsResult(items=items)
