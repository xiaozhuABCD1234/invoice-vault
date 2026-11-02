"""抽取任务路由（approve 由 invoices 领域实现，此处不包含）。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ..schemas.common import Page
from ..schemas.document import DocumentOut
from ..schemas.extraction import (
    ExtractionJobDetail,
    ExtractionJobOut,
    ExtractionRejectRequest,
)
from ..shared.deps import AppSettings, CurrentUser, DbSession, RequestCtx
from ..shared.enums import ExtractionProvider, ExtractionStatus
from ..shared.errors import ForbiddenError
from ..shared.pagination import PageParams
from . import service
from .config import load_config

router = APIRouter(prefix="/extraction-jobs", tags=["extraction"])


@router.get("", response_model=Page[ExtractionJobOut], summary="抽取任务列表")
def list_extraction_jobs(
    db: DbSession,
    _current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    job_status: ExtractionStatus | None = Query(default=None, alias="status"),
    provider: ExtractionProvider | None = Query(default=None),
    document_id: int | None = Query(default=None, ge=1),
) -> Page[ExtractionJobOut]:
    result = service.list_jobs(
        db,
        page=params.page,
        page_size=params.page_size,
        status=job_status,
        provider=provider,
        document_id=document_id,
    )
    return Page[ExtractionJobOut].model_validate(result)


@router.get("/{job_id}", response_model=ExtractionJobDetail, summary="抽取任务详情")
def get_extraction_job(
    job_id: int,
    db: DbSession,
    _current_user: CurrentUser,
) -> ExtractionJobDetail:
    job = service.get_job_or_404(db, job_id)
    document = job.document
    return ExtractionJobDetail(
        job=ExtractionJobOut.model_validate(job),
        document=DocumentOut.model_validate(document) if document is not None else None,
        diff=service.job_diff(db, job),
    )


@router.post(
    "/{job_id}/retry",
    response_model=ExtractionJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="重试抽取任务（admin 或上传者）",
)
def retry_extraction_job(
    job_id: int,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    ctx: RequestCtx,
) -> ExtractionJobOut:
    job = service.get_job_or_404(db, job_id)
    if not service.can_manage_job(job, current_user):
        raise ForbiddenError("forbidden", "只能重试自己上传的任务")
    config = load_config(settings=settings)
    job = service.retry_job(db, job, actor=current_user, config=config, request=ctx)
    return ExtractionJobOut.model_validate(job)


@router.post(
    "/{job_id}/reject",
    response_model=ExtractionJobOut,
    summary="驳回抽取任务（admin 或上传者）",
)
def reject_extraction_job(
    job_id: int,
    payload: ExtractionRejectRequest,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> ExtractionJobOut:
    job = service.get_job_or_404(db, job_id)
    if not service.can_manage_job(job, current_user):
        raise ForbiddenError("forbidden", "只能驳回自己上传的任务")
    job = service.reject_job(
        db, job, actor=current_user, note=payload.note, request=ctx
    )
    return ExtractionJobOut.model_validate(job)
