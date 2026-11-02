"""报表模板与导出任务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow
from ..shared.enums import ExportStatus, sql_in


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    columns_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    filters_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    sort_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_shared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    creator = relationship("User", foreign_keys=[created_by])
    exports = relationship("ExportJob", back_populates="template")

    @property
    def columns(self) -> Any:
        return self.columns_json or []

    @property
    def filters(self) -> Any:
        return self.filters_json or {}

    @property
    def sort(self) -> Any:
        return self.sort_json or []


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        CheckConstraint(sql_in("status", ExportStatus), name="ck_export_jobs_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True
    )
    filters_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ExportStatus.QUEUED.value,
        server_default=text("'queued'"),
        index=True,
    )
    file_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    template = relationship("ReportTemplate", back_populates="exports")
    creator = relationship("User", foreign_keys=[created_by])
    file_document = relationship("Document", foreign_keys=[file_document_id])
