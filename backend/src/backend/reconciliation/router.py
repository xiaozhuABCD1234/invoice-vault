"""对账路由：汇总、问题列表与忽略/取消忽略。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..schemas.common import Page
from ..schemas.reconciliation import (
    IssueIgnoreRequest,
    ReconciliationIssue,
    ReconciliationSummary,
)
from ..shared.deps import AdminUser, CurrentUser, DbSession, RequestCtx
from ..shared.enums import ReconciliationIssueType
from ..shared.pagination import PageParams
from . import service

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.get("/summary", response_model=ReconciliationSummary, summary="对账汇总")
def get_summary(db: DbSession, _current_user: CurrentUser) -> ReconciliationSummary:
    return service.get_summary(db)


@router.get("/issues", response_model=Page[ReconciliationIssue], summary="对账问题列表")
def list_issues(
    db: DbSession,
    _current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    issue_type: ReconciliationIssueType | None = Query(default=None, alias="type"),
    include_ignored: bool = Query(default=False, description="是否包含已忽略的问题"),
) -> Page[ReconciliationIssue]:
    issues = service.collect_issues(db)
    if issue_type is not None:
        issues = [issue for issue in issues if issue.type == issue_type]
    if not include_ignored:
        issues = [issue for issue in issues if not issue.ignored]

    result = service.paginate_issues(
        issues, page=params.page, page_size=params.page_size
    )
    return Page[ReconciliationIssue](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post(
    "/issues/{issue_key}/ignore",
    response_model=ReconciliationIssue,
    summary="忽略对账问题",
)
def ignore_issue(
    issue_key: str,
    payload: IssueIgnoreRequest,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> ReconciliationIssue:
    return service.ignore_issue(
        db,
        issue_key,
        note=payload.note,
        actor_id=admin.id,
        request=ctx,
    )


@router.delete(
    "/issues/{issue_key}/ignore",
    response_model=ReconciliationIssue,
    summary="取消忽略对账问题",
)
def unignore_issue(
    issue_key: str,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> ReconciliationIssue:
    return service.unignore_issue(
        db,
        issue_key,
        actor_id=admin.id,
        request=ctx,
    )
