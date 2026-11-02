"""发票抽取任务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow
from ..shared.enums import (
    ExtractionProvider,
    ExtractionStatus,
    ReviewDecision,
    sql_in,
)


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"
    __table_args__ = (
        CheckConstraint(sql_in("status", ExtractionStatus), name="ck_extraction_jobs_status"),
        CheckConstraint(sql_in("provider", ExtractionProvider), name="ck_extraction_jobs_provider"),
        CheckConstraint(
            "review_decision IS NULL OR " + sql_in("review_decision", ReviewDecision),
            name="ck_extraction_jobs_review_decision",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=ExtractionStatus.QUEUED.value,
        server_default=text("'queued'"),
        index=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    parsed_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    validation_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("Document", back_populates="extraction_jobs")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    @property
    def parsed(self) -> Any | None:
        return self.parsed_json

    @property
    def validation(self) -> Any | None:
        return self.validation_json

    @property
    def document_name(self) -> str | None:
        document = self.document
        if document is None:
            return None
        if document.title:
            return document.title
        version = document.current_version
        if version is None:
            return None
        return version.display_name or version.original_name

    @property
    def document_doc_type(self) -> str | None:
        return self.document.doc_type if self.document is not None else None
