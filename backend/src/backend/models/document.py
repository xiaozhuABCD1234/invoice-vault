"""文档与文档版本。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship  # noqa: F401

from ..shared.db import Base, TZDateTime, utcnow
from ..shared.enums import DocumentType, sql_in


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint(sql_in("doc_type", DocumentType), name="ck_documents_doc_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 当前版本不使用数据库外键，避免 documents 与 document_versions 的循环 DDL。
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    owner = relationship("User", foreign_keys=[owner_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id",
        order_by="DocumentVersion.version_no",
    )
    current_version = relationship(
        "DocumentVersion",
        primaryjoin="foreign(Document.current_version_id) == DocumentVersion.id",
        post_update=True,
        uselist=False,
    )
    extraction_jobs = relationship(
        "ExtractionJob", back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def owner_name(self) -> str | None:
        return self.owner.display_name if self.owner is not None else None

    @property
    def version_count(self) -> int:
        return len(self.versions or [])


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    document = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )
    creator = relationship("User", foreign_keys=[created_by])
