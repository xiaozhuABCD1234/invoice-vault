"""审计日志 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .common import APIModel


class AuditLogOut(APIModel):
    id: int
    actor_id: int | None = None
    actor_name: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None
    created_at: datetime
