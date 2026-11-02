"""审计日志写入。调用方负责 commit。"""

from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from .db import utcnow


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    return jsonable_encoder(value)


def _request_meta(request: Any) -> tuple[str | None, str | None]:
    if request is None:
        return None, None

    ip = getattr(request, "ip", None)
    user_agent = getattr(request, "user_agent", None)

    client = getattr(request, "client", None)
    if client is not None:
        ip = getattr(client, "host", ip)

    headers = getattr(request, "headers", None)
    if headers is not None:
        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",", 1)[0].strip()
        user_agent = headers.get("user-agent") or user_agent

    return ip, user_agent


def record_audit(
    db: Session,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    before: Any = None,
    after: Any = None,
    request: Any = None,
) -> Any:
    """新增一条审计日志并 flush；事务由调用方提交。"""

    from ..models.audit import AuditLog

    ip, user_agent = _request_meta(request)
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before_json=_json_safe(before),
        after_json=_json_safe(after),
        ip=ip,
        user_agent=user_agent,
        created_at=utcnow(),
    )
    db.add(log)
    db.flush()
    return log
