"""仪表盘 Schema。"""

from __future__ import annotations

from pydantic import Field

from .common import APIModel


class DashboardTotals(APIModel):
    invoice_count: int = 0
    invoice_total_cents: int = 0
    payment_total_cents: int = 0
    paid_cents: int = 0
    unpaid_cents: int = 0
    missing_evidence_count: int = 0


class CategoryBreakdown(APIModel):
    category_id: int | None = None
    name: str
    invoice_count: int = 0
    total_cents: int = 0


class MonthBreakdown(APIModel):
    month: str
    invoice_count: int = 0
    total_cents: int = 0


class PayerBreakdown(APIModel):
    payer_name: str
    payment_count: int = 0
    total_cents: int = 0


class DashboardGaps(APIModel):
    invoice_unpaid: int = 0
    payment_unallocated: int = 0
    missing_evidence: int = 0


class DashboardSummary(APIModel):
    totals: DashboardTotals = Field(default_factory=DashboardTotals)
    by_category: list[CategoryBreakdown] = Field(default_factory=list)
    by_month: list[MonthBreakdown] = Field(default_factory=list)
    by_payer: list[PayerBreakdown] = Field(default_factory=list)
    gaps: DashboardGaps = Field(default_factory=DashboardGaps)
