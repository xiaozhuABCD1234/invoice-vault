"""仪表盘路由。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from ..schemas.dashboard import DashboardSummary
from ..shared.deps import CurrentUser, DbSession
from . import service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary, summary="仪表盘汇总")
def get_summary(
    db: DbSession,
    _current_user: CurrentUser,
    date_from: date | None = Query(default=None, description="开票/付款开始日期"),
    date_to: date | None = Query(default=None, description="开票/付款结束日期"),
) -> DashboardSummary:
    return service.get_summary(db, date_from=date_from, date_to=date_to)
