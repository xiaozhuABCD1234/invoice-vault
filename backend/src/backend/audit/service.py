"""审计日志查询。"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.audit import AuditLog
from ..shared.pagination import paginate


def list_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    stmt = select(AuditLog).options(selectinload(AuditLog.actor))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == str(entity_id))
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=UTC)
        stmt = stmt.where(AuditLog.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        stmt = stmt.where(AuditLog.created_at < end)
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return paginate(db, stmt, page, page_size)
