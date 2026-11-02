"""对账异常人工备注 / 忽略记录。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow


class ReconciliationNote(Base):
    __tablename__ = "reconciliation_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    ignored_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    ignored_by_user = relationship("User", foreign_keys=[ignored_by])
