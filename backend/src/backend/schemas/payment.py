"""付款与付款分配 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..shared.enums import AllocationStatus, PaymentMethod, PaymentStatus
from .common import APIModel


class AllocationCreate(APIModel):
    invoice_id: int = Field(gt=0)
    amount_cents: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=2000)


class AllocationUpdate(APIModel):
    amount_cents: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=2000)


class AllocationOut(APIModel):
    id: int
    payment_id: int
    invoice_id: int
    amount_cents: int
    status: AllocationStatus
    note: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class PaymentCreate(APIModel):
    amount_cents: int = Field(gt=0)
    paid_at: datetime
    payer_user_id: int | None = Field(default=None, gt=0)
    payer_name: str | None = Field(default=None, max_length=120)
    method: PaymentMethod
    external_txn_ref: str | None = Field(default=None, max_length=255)
    evidence_document_id: int | None = Field(default=None, gt=0)
    requested_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class PaymentUpdate(APIModel):
    amount_cents: int | None = Field(default=None, gt=0)
    paid_at: datetime | None = None
    payer_user_id: int | None = Field(default=None, gt=0)
    payer_name: str | None = Field(default=None, max_length=120)
    method: PaymentMethod | None = None
    external_txn_ref: str | None = Field(default=None, max_length=255)
    evidence_document_id: int | None = Field(default=None, gt=0)
    requested_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class PaymentOut(APIModel):
    id: int
    amount_cents: int
    paid_at: datetime
    payer_user_id: int | None = None
    payer_name: str | None = None
    method: PaymentMethod
    external_txn_ref: str | None = None
    evidence_document_id: int | None = None
    status: PaymentStatus
    requested_at: datetime | None = None
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None
    note: str | None = None
    created_by: int | None = None
    created_at: datetime
    allocated_cents: int = 0
    allocations: list[AllocationOut] = Field(default_factory=list)


class PaymentInvoiceSummary(APIModel):
    invoice_id: int
    invoice_number: str | None = None
    seller_name: str | None = None
    total_cents: int | None = None
    amount_cents: int
    status: AllocationStatus


class PaymentDetail(PaymentOut):
    invoices: list[PaymentInvoiceSummary] = Field(default_factory=list)


class PaymentBrief(APIModel):
    id: int
    amount_cents: int
    paid_at: datetime
    payer_name: str | None = None
    method: PaymentMethod
    status: PaymentStatus
    external_txn_ref: str | None = None


class InvoicePaymentItem(AllocationOut):
    payment: PaymentBrief | None = None


class InvoicePaymentsResult(APIModel):
    items: list[InvoicePaymentItem] = Field(default_factory=list)
