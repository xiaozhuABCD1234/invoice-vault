"""系统枚举与数据库约束辅助函数。

所有持久化枚举使用字符串值，模型列使用 String + CheckConstraint，
与 docs/API_CONTRACT.md 的枚举取值保持一致。
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class CategoryKind(StrEnum):
    PURCHASE = "purchase"
    EXPENSE = "expense"


class DocumentType(StrEnum):
    INVOICE = "invoice"
    PAYMENT_EVIDENCE = "payment_evidence"
    RECEIPT = "receipt"
    OTHER = "other"


class ExtractionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class ExtractionProvider(StrEnum):
    PDF_TEXT = "pdf_text"
    PADDLEOCR_LOCAL = "paddleocr_local"
    MULTIMODAL_LLM = "multimodal_llm"
    MOCK = "mock"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class InvoiceStatus(StrEnum):
    REVIEW_PENDING = "review_pending"
    ACTIVE = "active"
    VOID = "void"
    DUPLICATE = "duplicate"


class InvoicePaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"


class InvoiceForm(StrEnum):
    ELECTRONIC = "electronic"
    PAPER = "paper"


class PaymentStatus(StrEnum):
    UNALLOCATED = "unallocated"
    PARTIALLY_ALLOCATED = "partially_allocated"
    FULLY_ALLOCATED = "fully_allocated"
    VOID = "void"


class PaymentMethod(StrEnum):
    PERSONAL_ADVANCE = "personal_advance"
    TEACHER_ADVANCE = "teacher_advance"
    BANK_TRANSFER = "bank_transfer"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CARD = "card"
    CASH = "cash"
    OTHER = "other"


class AllocationStatus(StrEnum):
    ACTIVE = "active"
    REVERSED = "reversed"


class ExportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ReconciliationIssueType(StrEnum):
    INVOICE_UNPAID = "invoice_unpaid"
    INVOICE_PARTIAL = "invoice_partial"
    PAYMENT_UNALLOCATED = "payment_unallocated"
    PAYMENT_PARTIAL = "payment_partial"
    MISSING_EVIDENCE = "missing_evidence"
    DUPLICATE_INVOICE = "duplicate_invoice"
    ITEM_MISMATCH = "item_mismatch"
    AMOUNT_ANOMALY = "amount_anomaly"
    DATE_ANOMALY = "date_anomaly"


#: 默认采购类别（DESIGN §5 / API_CONTRACT §2）
DEFAULT_PURCHASE_CATEGORIES: Final[tuple[str, ...]] = (
    "标准件",
    "板材件",
    "机加工",
    "官方器件",
    "硬件",
    "铝方管",
    "大采购",
    "快递",
    "打车",
    "周边",
)

#: 默认费用类别
DEFAULT_EXPENSE_CATEGORIES: Final[tuple[str, ...]] = (
    "报名费",
    "高铁",
    "住宿",
    "货拉拉",
    "打车",
    "快递",
    "采购",
    "周边",
)

DEFAULT_CATEGORIES: Final[dict[CategoryKind, tuple[str, ...]]] = {
    CategoryKind.PURCHASE: DEFAULT_PURCHASE_CATEGORIES,
    CategoryKind.EXPENSE: DEFAULT_EXPENSE_CATEGORIES,
}


def enum_values(enum_cls: type[StrEnum]) -> tuple[str, ...]:
    """返回枚举的全部字符串值。"""

    return tuple(member.value for member in enum_cls)


def sql_in(column: str, values: Iterable[StrEnum | str]) -> str:
    """生成用于 CheckConstraint 的 column IN (...) 片段。"""

    rendered: list[str] = []
    for value in values:
        raw = value.value if isinstance(value, StrEnum) else str(value)
        rendered.append("'" + raw.replace("'", "''") + "'")
    return f"{column} IN ({', '.join(rendered)})"
