"""ORM 模型聚合。

导入本模块即注册全部模型，保证 Base.metadata 完整。
"""

from __future__ import annotations

from .app_setting import AppSetting, AppSettingRevision
from .audit import AuditLog
from .category import Category
from .document import Document, DocumentVersion
from .extraction import ExtractionJob
from .invoice import Invoice, InvoiceItem
from .payment import Payment, PaymentAllocation
from .reconciliation import ReconciliationNote
from .report import ExportJob, ReportTemplate
from .user import PersonAlias, RefreshToken, User

__all__ = [
    "AppSetting",
    "AppSettingRevision",
    "AuditLog",
    "Category",
    "Document",
    "DocumentVersion",
    "ExportJob",
    "ExtractionJob",
    "Invoice",
    "InvoiceItem",
    "Payment",
    "PaymentAllocation",
    "PersonAlias",
    "ReconciliationNote",
    "RefreshToken",
    "ReportTemplate",
    "User",
]
