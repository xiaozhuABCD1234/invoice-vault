"""发票路由：CRUD / 列表 / 详情。"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from ..models.user import User
from ..schemas.common import Page
from ..schemas.invoice import InvoiceCreate, InvoiceListItem, InvoiceOut, InvoiceUpdate
from ..shared.deps import AdminUser, CurrentUser, DbSession, RequestCtx
from ..shared.enums import InvoicePaymentStatus, InvoiceStatus, Role
from ..shared.pagination import PageParams
from . import service

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _is_admin(user: User) -> bool:
    return user.role == Role.ADMIN.value


@router.get("", response_model=Page[InvoiceListItem], summary="发票列表")
def list_invoices(
    db: DbSession,
    current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    q: str | None = Query(default=None, description="按发票号码或销方名称模糊搜索"),
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    payment_status: InvoicePaymentStatus | None = Query(default=None),
    category_id: int | None = Query(default=None, gt=0),
    requester_id: int | None = Query(default=None, gt=0),
    owner_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None, description="开票日期下限（含）"),
    date_to: date | None = Query(default=None, description="开票日期上限（含）"),
    sort: str | None = Query(
        default=None,
        description=(
            "单值格式 field:asc|desc；字段 whitelist: "
            "issue_date / total_cents / created_at / id；"
            "默认 issue_date:desc，非法值回退默认"
        ),
    ),
    include_deleted: bool = Query(default=False, description="仅管理员生效"),
) -> Page[InvoiceListItem]:
    result = service.list_invoices(
        db,
        page=params.page,
        page_size=params.page_size,
        q=q,
        status=status_filter.value if status_filter is not None else None,
        payment_status=payment_status.value if payment_status is not None else None,
        category_id=category_id,
        requester_id=requester_id,
        owner_id=owner_id,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        include_deleted=bool(include_deleted and _is_admin(current_user)),
    )
    return Page[InvoiceListItem].model_validate(result)


@router.get("/{invoice_id}", response_model=InvoiceOut, summary="发票详情")
def get_invoice(
    invoice_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> InvoiceOut:
    invoice = service.get_invoice(
        db, invoice_id, include_deleted=_is_admin(current_user)
    )
    return service.to_invoice_out(invoice)


@router.post(
    "",
    response_model=InvoiceOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建发票",
)
def create_invoice(
    payload: InvoiceCreate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> InvoiceOut:
    invoice = service.create_invoice(
        db, payload=payload, actor=current_user, request=ctx
    )
    return service.to_invoice_out(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceOut, summary="更新发票")
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> InvoiceOut:
    invoice = service.update_invoice(
        db,
        invoice_id,
        payload=payload,
        actor=current_user,
        is_admin=_is_admin(current_user),
        request=ctx,
    )
    return service.to_invoice_out(invoice)


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="删除发票（软删）",
)
def delete_invoice(
    invoice_id: int,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> Response:
    service.delete_invoice(db, invoice_id, actor_id=admin.id, request=ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
