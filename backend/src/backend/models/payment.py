"""付款与付款分配（多对多）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow
from ..shared.enums import AllocationStatus, PaymentMethod, PaymentStatus, sql_in


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(sql_in("status", PaymentStatus), name="ck_payments_status"),
        CheckConstraint(sql_in("method", PaymentMethod), name="ck_payments_method"),
        Index("ix_payments_paid_at", "paid_at"),
        Index("ix_payments_status_idx", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    payer_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    payer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    external_txn_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentStatus.UNALLOCATED.value,
        server_default=text("'unallocated'"),
    )
    requested_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    allocations = relationship(
        "PaymentAllocation",
        back_populates="payment",
        foreign_keys="PaymentAllocation.payment_id",
    )
    payer = relationship("User", foreign_keys=[payer_user_id])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    creator = relationship("User", foreign_keys=[created_by])
    evidence_document = relationship("Document", foreign_keys=[evidence_document_id])

    @property
    def allocated_cents(self) -> int:
        return sum(
            allocation.amount_cents
            for allocation in (self.allocations or [])
            if allocation.status == AllocationStatus.ACTIVE.value
        )


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        CheckConstraint(
            sql_in("status", AllocationStatus), name="ck_payment_allocations_status"
        ),
        CheckConstraint("amount_cents > 0", name="ck_payment_allocations_amount_positive"),
        Index("ix_payment_allocations_payment_id", "payment_id"),
        Index("ix_payment_allocations_invoice_id", "invoice_id"),
        Index(
            "uq_payment_allocations_active",
            "payment_id",
            "invoice_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AllocationStatus.ACTIVE.value,
        server_default=text("'active'"),
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    payment = relationship("Payment", back_populates="allocations")
    invoice = relationship("Invoice", back_populates="allocations")
    creator = relationship("User", foreign_keys=[created_by])
