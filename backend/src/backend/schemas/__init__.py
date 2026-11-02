"""Pydantic Schema 聚合。

所有领域 schema 从这里导入；模块底部完成跨模块前向引用的重建。
"""

from __future__ import annotations

from . import audit as audit
from . import auth as auth
from . import category as category
from . import common as common
from . import dashboard as dashboard
from . import document as document
from . import extraction as extraction
from . import invoice as invoice
from . import payment as payment
from . import reconciliation as reconciliation
from . import report as report
from . import user as user
from .audit import AuditLogOut
from .auth import LoginRequest, TokenResponse
from .category import CategoryCreate, CategoryListResponse, CategoryOut, CategoryUpdate
from .common import APIModel, ErrorResponse, HealthResponse, MessageResponse, Page, SortSpec
from .dashboard import (
    CategoryBreakdown,
    DashboardGaps,
    DashboardSummary,
    DashboardTotals,
    MonthBreakdown,
    PayerBreakdown,
)
from .document import (
    DocumentDetail,
    DocumentOut,
    DocumentUploadResult,
    DocumentVersionOut,
)
from .extraction import (
    ExtractionJobDetail,
    ExtractionJobOut,
    ExtractionRejectRequest,
    ExtractionValidation,
)
from .invoice import (
    InvoiceApproveResult,
    InvoiceCreate,
    InvoiceItemInput,
    InvoiceItemOut,
    InvoiceListItem,
    InvoiceOut,
    InvoiceUpdate,
)
from .payment import (
    AllocationCreate,
    AllocationOut,
    AllocationUpdate,
    InvoicePaymentItem,
    InvoicePaymentsResult,
    PaymentBrief,
    PaymentCreate,
    PaymentDetail,
    PaymentInvoiceSummary,
    PaymentOut,
    PaymentUpdate,
)
from .reconciliation import (
    IssueCounts,
    IssueIgnoreRequest,
    ReconciliationIssue,
    ReconciliationSummary,
)
from .report import (
    ColumnSpec,
    ExportCreate,
    ExportJobOut,
    ExportResponse,
    ReportTemplateCreate,
    ReportTemplateOut,
    ReportTemplateUpdate,
)
from .user import UserCreate, UserOption, UserOptionsResponse, UserOut, UserUpdate

document.DocumentDetail.model_rebuild(
    _types_namespace={"ExtractionJobOut": extraction.ExtractionJobOut}
)
document.DocumentUploadResult.model_rebuild(
    _types_namespace={"ExtractionJobOut": extraction.ExtractionJobOut}
)
extraction.ExtractionJobDetail.model_rebuild(
    _types_namespace={"DocumentOut": document.DocumentOut}
)

__all__ = [
    "APIModel",
    "AllocationCreate",
    "AllocationOut",
    "AllocationUpdate",
    "AuditLogOut",
    "CategoryBreakdown",
    "CategoryCreate",
    "CategoryListResponse",
    "CategoryOut",
    "CategoryUpdate",
    "ColumnSpec",
    "DashboardGaps",
    "DashboardSummary",
    "DashboardTotals",
    "DocumentDetail",
    "DocumentOut",
    "DocumentUploadResult",
    "DocumentVersionOut",
    "ErrorResponse",
    "ExportCreate",
    "ExportJobOut",
    "ExportResponse",
    "ExtractionJobDetail",
    "ExtractionJobOut",
    "ExtractionRejectRequest",
    "ExtractionValidation",
    "HealthResponse",
    "InvoiceApproveResult",
    "InvoiceCreate",
    "InvoiceItemInput",
    "InvoiceItemOut",
    "InvoiceListItem",
    "InvoiceOut",
    "InvoicePaymentItem",
    "InvoicePaymentsResult",
    "InvoiceUpdate",
    "IssueCounts",
    "IssueIgnoreRequest",
    "LoginRequest",
    "MessageResponse",
    "MonthBreakdown",
    "Page",
    "PaymentBrief",
    "PaymentCreate",
    "PaymentDetail",
    "PaymentInvoiceSummary",
    "PaymentOut",
    "PaymentUpdate",
    "PayerBreakdown",
    "ReconciliationIssue",
    "ReconciliationSummary",
    "ReportTemplateCreate",
    "ReportTemplateOut",
    "ReportTemplateUpdate",
    "SortSpec",
    "TokenResponse",
    "UserCreate",
    "UserOption",
    "UserOptionsResponse",
    "UserOut",
    "UserUpdate",
]
