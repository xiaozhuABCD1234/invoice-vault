"""发票与发票明细 Schema。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from ..shared.enums import InvoiceForm, InvoicePaymentStatus, InvoiceStatus
from .common import APIModel
from .extraction import ExtractionJobOut
from .payment import AllocationOut


class InvoiceItemInput(APIModel):
    name: str = Field(min_length=1, max_length=255)
    quantity: float = Field(default=1, ge=0)
    unit_price_millis: int = Field(ge=0)
    amount_cents: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0)


class InvoiceItemOut(InvoiceItemInput):
    id: int


class InvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=64)
    invoice_code: str | None = Field(default=None, max_length=64)
    invoice_type: str | None = Field(default=None, max_length=64)
    issue_date: date
    seller_name: str = Field(min_length=1, max_length=255)
    seller_tax_id: str | None = Field(default=None, max_length=64)
    buyer_name: str | None = Field(default=None, max_length=255)
    buyer_tax_id: str | None = Field(default=None, max_length=64)
    amount_ex_tax_cents: int = Field(ge=0)
    tax_cents: int = Field(ge=0)
    total_cents: int = Field(ge=0)
    tax_rate_bp: int | None = Field(default=None, ge=0)
    currency: str = Field(default="CNY", max_length=8)
    category_id: int = Field(gt=0)
    requester_id: int | None = Field(default=None, gt=0)
    owner_id: int | None = Field(default=None, gt=0)
    invoice_form: InvoiceForm | None = None
    status: InvoiceStatus = InvoiceStatus.ACTIVE
    source_document_id: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=4000)
    product_url: str | None = Field(default=None, max_length=1024)
    items: list[InvoiceItemInput]

    @model_validator(mode="after")
    def _validate_amounts(self) -> "InvoiceCreate":
        if abs(self.amount_ex_tax_cents + self.tax_cents - self.total_cents) > 1:
            raise ValueError("不含税金额与税额之和必须等于价税合计（允许 1 分误差）")
        return self


class InvoiceUpdate(BaseModel):
    invoice_number: str | None = Field(default=None, min_length=1, max_length=64)
    invoice_code: str | None = Field(default=None, max_length=64)
    invoice_type: str | None = Field(default=None, max_length=64)
    issue_date: date | None = None
    seller_name: str | None = Field(default=None, min_length=1, max_length=255)
    seller_tax_id: str | None = Field(default=None, max_length=64)
    buyer_name: str | None = Field(default=None, max_length=255)
    buyer_tax_id: str | None = Field(default=None, max_length=64)
    amount_ex_tax_cents: int | None = Field(default=None, ge=0)
    tax_cents: int | None = Field(default=None, ge=0)
    total_cents: int | None = Field(default=None, ge=0)
    tax_rate_bp: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    category_id: int | None = Field(default=None, gt=0)
    requester_id: int | None = Field(default=None, gt=0)
    owner_id: int | None = Field(default=None, gt=0)
    invoice_form: InvoiceForm | None = None
    status: InvoiceStatus | None = None
    source_document_id: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=4000)
    product_url: str | None = Field(default=None, max_length=1024)
    items: list[InvoiceItemInput] | None = None

    @model_validator(mode="after")
    def _validate_amounts(self) -> "InvoiceUpdate":
        values = [self.amount_ex_tax_cents, self.tax_cents, self.total_cents]
        if all(value is not None for value in values):
            amount_ex_tax, tax, total = (int(value) for value in values if value is not None)
            if abs(amount_ex_tax + tax - total) > 1:
                raise ValueError("不含税金额与税额之和必须等于价税合计（允许 1 分误差）")
        return self


class InvoiceOut(APIModel):
    id: int
    invoice_number: str
    invoice_code: str | None = None
    invoice_type: str | None = None
    issue_date: date
    seller_name: str
    seller_tax_id: str | None = None
    buyer_name: str | None = None
    buyer_tax_id: str | None = None
    amount_ex_tax_cents: int
    tax_cents: int
    total_cents: int
    tax_rate_bp: int | None = None
    currency: str = "CNY"
    category_id: int | None = None
    category_name: str | None = None
    requester_id: int | None = None
    requester_name: str | None = None
    owner_id: int | None = None
    owner_name: str | None = None
    invoice_form: InvoiceForm | None = None
    status: InvoiceStatus
    paid_cents: int = 0
    payment_status: InvoicePaymentStatus
    source_document_id: int | None = None
    extraction_job_id: int | None = None
    note: str | None = None
    product_url: str | None = None
    created_by: int | None = None
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    items: list[InvoiceItemOut] = Field(default_factory=list)
    allocations: list[AllocationOut] = Field(default_factory=list)


class InvoiceListItem(APIModel):
    id: int
    invoice_number: str
    invoice_code: str | None = None
    invoice_type: str | None = None
    issue_date: date
    seller_name: str
    total_cents: int
    tax_cents: int
    currency: str = "CNY"
    category_id: int | None = None
    category_name: str | None = None
    requester_id: int | None = None
    requester_name: str | None = None
    owner_id: int | None = None
    owner_name: str | None = None
    invoice_form: InvoiceForm | None = None
    status: InvoiceStatus
    paid_cents: int = 0
    payment_status: InvoicePaymentStatus
    created_at: datetime


class InvoiceApproveResult(APIModel):
    invoice: InvoiceOut
    job: ExtractionJobOut
