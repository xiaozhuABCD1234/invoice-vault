"""发票与发票明细。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow
from ..shared.enums import (
    InvoiceForm,
    InvoicePaymentStatus,
    InvoiceStatus,
    sql_in,
)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(sql_in("status", InvoiceStatus), name="ck_invoices_status"),
        CheckConstraint(
            sql_in("payment_status", InvoicePaymentStatus), name="ck_invoices_payment_status"
        ),
        CheckConstraint(
            "invoice_form IS NULL OR " + sql_in("invoice_form", InvoiceForm),
            name="ck_invoices_invoice_form",
        ),
        Index("ix_invoices_issue_date", "issue_date"),
        Index("ix_invoices_category_id", "category_id"),
        Index("ix_invoices_requester_id", "requester_id"),
        Index("ix_invoices_status_idx", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    invoice_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invoice_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    seller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    seller_tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    buyer_tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_ex_tax_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_rate_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, default="CNY", server_default=text("'CNY'")
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    requester_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invoice_form: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=InvoiceStatus.REVIEW_PENDING.value,
        server_default=text("'review_pending'"),
    )
    paid_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    payment_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=InvoicePaymentStatus.UNPAID.value,
        server_default=text("'unpaid'"),
    )
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    extraction_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_jobs.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceItem.sort_order",
    )
    allocations = relationship(
        "PaymentAllocation",
        back_populates="invoice",
        foreign_keys="PaymentAllocation.invoice_id",
    )
    category = relationship("Category", back_populates="invoices")
    requester = relationship("User", foreign_keys=[requester_id])
    owner = relationship("User", foreign_keys=[owner_id])
    creator = relationship("User", foreign_keys=[created_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    source_document = relationship("Document", foreign_keys=[source_document_id])
    extraction_job = relationship("ExtractionJob", foreign_keys=[extraction_job_id])

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category is not None else None

    @property
    def requester_name(self) -> str | None:
        return self.requester.display_name if self.requester is not None else None

    @property
    def owner_name(self) -> str | None:
        return self.owner.display_name if self.owner is not None else None


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("1")
    )
    unit_price_millis: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    amount_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    invoice = relationship("Invoice", back_populates="items")
