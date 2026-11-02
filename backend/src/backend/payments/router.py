"""付款与分配路由。

- 付款相关接口挂在 /payments 前缀下；
- 分配修改/撤销接口路径为 /allocations/{id}，通过子路由挂载，避免与付款前缀冲突。
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from ..schemas.common import Page
from ..schemas.payment import (
    AllocationCreate,
    AllocationOut,
    AllocationUpdate,
    PaymentCreate,
    PaymentDetail,
    PaymentOut,
    PaymentUpdate,
)
from ..shared.deps import CurrentUser, DbSession, RequestCtx
from ..shared.enums import PaymentMethod, PaymentStatus
from ..shared.pagination import PageParams
from . import service

router = APIRouter()
payments_router = APIRouter(prefix="/payments", tags=["payments"])
allocations_router = APIRouter(tags=["payments"])


@payments_router.get("", response_model=Page[PaymentOut], summary="付款列表")
def list_payments(
    db: DbSession,
    _current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    q: str | None = Query(default=None, description="按付款人或外部流水号搜索"),
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    method: PaymentMethod | None = Query(default=None),
    date_from: date | None = Query(default=None, description="付款日期起（含）"),
    date_to: date | None = Query(default=None, description="付款日期止（含）"),
    sort: str | None = Query(
        default=None,
        description="排序，格式 字段:顺序（paid_at/amount_cents/created_at/id，默认 paid_at:desc）",
    ),
) -> Page[PaymentOut]:
    result = service.list_payments(
        db,
        page=params.page,
        page_size=params.page_size,
        q=q,
        status=status_filter,
        method=method,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    return Page[PaymentOut](
        items=[service.build_payment_out(payment) for payment in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@payments_router.post(
    "",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建付款",
)
def create_payment(
    payload: PaymentCreate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> PaymentOut:
    payment = service.create_payment(
        db,
        amount_cents=payload.amount_cents,
        paid_at=payload.paid_at,
        method=payload.method,
        actor_id=current_user.id,
        payer_user_id=payload.payer_user_id,
        payer_name=payload.payer_name,
        external_txn_ref=payload.external_txn_ref,
        evidence_document_id=payload.evidence_document_id,
        requested_at=payload.requested_at,
        note=payload.note,
        request=ctx,
    )
    return service.build_payment_out(payment)


@payments_router.get("/{payment_id}", response_model=PaymentDetail, summary="付款详情")
def get_payment(
    payment_id: int,
    db: DbSession,
    _current_user: CurrentUser,
) -> PaymentDetail:
    payment = service.get_payment_or_404(db, payment_id, with_invoices=True)
    return service.build_payment_detail(payment)


@payments_router.patch("/{payment_id}", response_model=PaymentOut, summary="更新付款")
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> PaymentOut:
    payment = service.update_payment(
        db,
        payment_id,
        updates=payload.model_dump(exclude_unset=True),
        actor=current_user,
        request=ctx,
    )
    return service.build_payment_out(payment, include_allocations=True)


@payments_router.post(
    "/{payment_id}/allocations",
    response_model=AllocationOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建付款分配",
)
def create_allocation(
    payment_id: int,
    payload: AllocationCreate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> AllocationOut:
    allocation = service.create_allocation(
        db,
        payment_id,
        invoice_id=payload.invoice_id,
        amount_cents=payload.amount_cents,
        note=payload.note,
        actor_id=current_user.id,
        request=ctx,
    )
    return AllocationOut.model_validate(allocation)


@allocations_router.patch(
    "/allocations/{allocation_id}",
    response_model=AllocationOut,
    summary="更新付款分配",
)
def update_allocation(
    allocation_id: int,
    payload: AllocationUpdate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> AllocationOut:
    updates = payload.model_dump(exclude_unset=True)
    allocation = service.update_allocation(
        db,
        allocation_id,
        amount_cents=updates.get("amount_cents"),
        note=updates.get("note"),
        note_provided="note" in updates,
        actor_id=current_user.id,
        request=ctx,
    )
    return AllocationOut.model_validate(allocation)


@allocations_router.delete(
    "/allocations/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="撤销付款分配",
)
def revoke_allocation(
    allocation_id: int,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> Response:
    service.revoke_allocation(db, allocation_id, actor=current_user, request=ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(payments_router)
router.include_router(allocations_router)
