"""审计日志。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    before_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow, index=True
    )

    actor = relationship("User", foreign_keys=[actor_id])

    @property
    def actor_name(self) -> str | None:
        return self.actor.display_name if self.actor is not None else None

    @property
    def before(self) -> Any | None:
        return self.before_json

    @property
    def after(self) -> Any | None:
        return self.after_json
