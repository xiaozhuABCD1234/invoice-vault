"""审计日志路由。"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..schemas.audit import AuditLogOut
from ..schemas.common import Page
from ..shared.deps import AdminUser, DbSession
from ..shared.pagination import PageParams
from . import service

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogOut], summary="审计日志列表")
def list_audit_logs(
    db: DbSession,
    _admin: AdminUser,
    params: Annotated[PageParams, Depends()],
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    actor_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> Page[AuditLogOut]:
    result = service.list_audit_logs(
        db,
        page=params.page,
        page_size=params.page_size,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Page[AuditLogOut].model_validate(result)
