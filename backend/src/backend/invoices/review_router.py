"""抽取任务审核路由：通过审核并生成发票。"""

from __future__ import annotations

from fastapi import APIRouter, status

from ..schemas.invoice import InvoiceApproveResult, InvoiceCreate
from ..shared.deps import CurrentUser, DbSession, RequestCtx
from ..shared.enums import Role
from . import service

router = APIRouter(prefix="/extraction-jobs", tags=["extraction"])


@router.post(
    "/{job_id}/approve",
    response_model=InvoiceApproveResult,
    status_code=status.HTTP_201_CREATED,
    summary="审核通过抽取任务",
)
def approve_extraction_job(
    job_id: int,
    payload: InvoiceCreate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> InvoiceApproveResult:
    invoice, job = service.approve_extraction_job(
        db,
        job_id,
        payload=payload,
        actor=current_user,
        is_admin=current_user.role == Role.ADMIN.value,
        request=ctx,
    )
    return InvoiceApproveResult(
        invoice=service.to_invoice_out(invoice),
        job=job,
    )
