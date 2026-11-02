"""对账 Schema。"""

from __future__ import annotations

from pydantic import Field

from ..shared.enums import IssueSeverity, ReconciliationIssueType
from .common import APIModel


class IssueCounts(APIModel):
    invoice_unpaid: int = 0
    invoice_partial: int = 0
    payment_unallocated: int = 0
    payment_partial: int = 0
    missing_evidence: int = 0
    duplicate_invoice: int = 0
    item_mismatch: int = 0
    amount_anomaly: int = 0
    date_anomaly: int = 0


class ReconciliationSummary(APIModel):
    invoice_total_cents: int = 0
    invoice_paid_cents: int = 0
    invoice_unpaid_cents: int = 0
    payment_total_cents: int = 0
    payment_allocated_cents: int = 0
    payment_unallocated_cents: int = 0
    invoice_count: int = 0
    payment_count: int = 0
    issue_counts: IssueCounts = Field(default_factory=IssueCounts)


class ReconciliationIssue(APIModel):
    id: str
    type: ReconciliationIssueType
    severity: IssueSeverity
    entity_type: str
    entity_id: int
    title: str
    detail: str | None = None
    amount_cents: int | None = None
    ignored: bool = False
    note: str | None = None


class IssueIgnoreRequest(APIModel):
    note: str = Field(min_length=1, max_length=2000)
