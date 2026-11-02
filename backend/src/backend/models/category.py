"""发票类别。"""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base
from ..shared.enums import CategoryKind, sql_in


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(sql_in("kind", CategoryKind), name="ck_categories_kind"),
        UniqueConstraint("kind", "name", name="uq_categories_kind_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )

    invoices = relationship("Invoice", back_populates="category")
