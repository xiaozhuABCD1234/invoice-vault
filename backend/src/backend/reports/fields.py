"""报表导出字段目录：列定义、标签映射与单元格取值。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from ..models.invoice import Invoice, InvoiceItem
from ..schemas.report import ColumnSpec
from ..shared.enums import AllocationStatus, InvoiceForm, InvoiceStatus, PaymentMethod

#: 文本单元格的公式注入前缀
FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@")

INVOICE_FORM_LABELS: dict[str, str] = {
    InvoiceForm.ELECTRONIC.value: "电子",
    InvoiceForm.PAPER.value: "纸质",
}

STATUS_LABELS: dict[str, str] = {
    InvoiceStatus.REVIEW_PENDING.value: "待审核",
    InvoiceStatus.ACTIVE.value: "有效",
    InvoiceStatus.VOID.value: "作废",
    InvoiceStatus.DUPLICATE.value: "重复",
}

PAYMENT_METHOD_LABELS: dict[str, str] = {
    PaymentMethod.PERSONAL_ADVANCE.value: "个人垫付",
    PaymentMethod.TEACHER_ADVANCE.value: "老师代付",
    PaymentMethod.BANK_TRANSFER.value: "银行转账",
    PaymentMethod.ALIPAY.value: "支付宝",
    PaymentMethod.WECHAT.value: "微信",
    PaymentMethod.CARD.value: "银行卡",
    PaymentMethod.CASH.value: "现金",
    PaymentMethod.OTHER.value: "其他",
}


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """一个可选导出列的静态定义。

    aggregate 是合计行口径：item 按明细行累加，invoice 按发票去重累加。
    """

    key: str
    label: str
    width: int = 16
    format: str = "text"
    aggregate: str | None = None


#: 字段目录，key 与 docs/API_CONTRACT.md §8 保持一致。付款金额因与明细
#: amount_cents 重名，使用 payment_amount_cents；另补充默认模板需要的派生列。
FIELD_CATALOG: dict[str, FieldSpec] = {
    # 发票
    "invoice_number": FieldSpec("invoice_number", "发票号码", 24),
    "issue_date": FieldSpec("issue_date", "开票日期", 14, "date"),
    "seller_name": FieldSpec("seller_name", "店铺", 22),
    "total_cents": FieldSpec("total_cents", "单张发票金额", 16, "money", "invoice"),
    "amount_ex_tax_cents": FieldSpec(
        "amount_ex_tax_cents", "不含税金额", 16, "money", "invoice"
    ),
    "tax_cents": FieldSpec("tax_cents", "税额", 14, "money", "invoice"),
    "category_name": FieldSpec("category_name", "类别", 12),
    "requester_name": FieldSpec("requester_name", "申购人", 12),
    "owner_name": FieldSpec("owner_name", "负责人", 12),
    "invoice_form": FieldSpec("invoice_form", "发票形式", 10),
    "status": FieldSpec("status", "状态", 10),
    "note": FieldSpec("note", "备注", 24),
    "product_url": FieldSpec("product_url", "链接", 32),
    # 明细
    "item_name": FieldSpec("item_name", "名称", 22),
    "quantity": FieldSpec("quantity", "购买数量", 10, "number", "item"),
    "unit_price_millis": FieldSpec("unit_price_millis", "单价", 12, "money"),
    "amount_cents": FieldSpec("amount_cents", "总价", 14, "money", "item"),
    # 付款
    "payer_name": FieldSpec("payer_name", "付款人", 12),
    "method": FieldSpec("method", "付款方式", 12),
    "paid_at": FieldSpec("paid_at", "付款日期", 14, "date"),
    "payment_amount_cents": FieldSpec(
        "payment_amount_cents", "付款金额", 14, "money", "invoice"
    ),
    # 文件
    "source_file_name": FieldSpec("source_file_name", "发票图片", 24),
    # 派生列
    "index": FieldSpec("index", "序号", 8, "integer"),
    "payment_summary": FieldSpec("payment_summary", "付款记录", 28),
    "teacher_advance_requested_at": FieldSpec(
        "teacher_advance_requested_at", "申请老师代付时间", 20, "date"
    ),
}

#: 默认模板 16 列（DESIGN §10）
DEFAULT_COLUMN_KEYS: tuple[str, ...] = (
    "index",
    "item_name",
    "quantity",
    "unit_price_millis",
    "amount_cents",
    "total_cents",
    "seller_name",
    "requester_name",
    "owner_name",
    "invoice_number",
    "source_file_name",
    "payment_summary",
    "invoice_form",
    "note",
    "teacher_advance_requested_at",
    "product_url",
)


def default_columns() -> list[ColumnSpec]:
    """返回默认模板的 16 列（每次返回新对象，避免调用方修改共享状态）。"""

    columns: list[ColumnSpec] = []
    for key in DEFAULT_COLUMN_KEYS:
        spec = FIELD_CATALOG[key]
        columns.append(
            ColumnSpec(key=spec.key, label=spec.label, width=spec.width, format=spec.format)
        )
    return columns


def _yuan(cents: int | None) -> float | None:
    if cents is None:
        return None
    return round(int(cents) / 100, 2)


def _active_allocations(invoice: Invoice) -> list[Any]:
    return [
        allocation
        for allocation in (invoice.allocations or [])
        if allocation.status == AllocationStatus.ACTIVE.value
    ]


def _payments(invoice: Invoice) -> list[Any]:
    return [
        allocation.payment
        for allocation in _active_allocations(invoice)
        if allocation.payment is not None
    ]


def _unique_text(values: list[str | None]) -> str:
    seen: list[str] = []
    for value in values:
        text = (value or "").strip() or "未指定"
        if text not in seen:
            seen.append(text)
    return "、".join(seen)


def _payment_summary(invoice: Invoice) -> str:
    parts: list[str] = []
    for allocation in _active_allocations(invoice):
        payment = allocation.payment
        if payment is None:
            continue
        payer = (payment.payer_name or "").strip() or "未指定"
        method = PAYMENT_METHOD_LABELS.get(payment.method, payment.method or "")
        parts.append(f"{payer} {allocation.amount_cents / 100:.2f}元 {method}".strip())
    return "；".join(parts)


def _teacher_advance_requested_at(invoice: Invoice) -> date | None:
    moments = [
        payment.requested_at
        for payment in _payments(invoice)
        if payment.method == PaymentMethod.TEACHER_ADVANCE.value
        and payment.requested_at is not None
    ]
    return min(moments).date() if moments else None


def _source_file_name(invoice: Invoice) -> str:
    document = invoice.source_document
    if document is None:
        return ""
    version = document.current_version
    if version is not None:
        return version.display_name or version.original_name
    return document.title or ""


def _paid_at(invoice: Invoice) -> date | None:
    moments = [
        payment.paid_at for payment in _payments(invoice) if payment.paid_at is not None
    ]
    return min(moments).date() if moments else None


def resolve_cell(
    invoice: Invoice,
    item: InvoiceItem | None,
    key: str,
    *,
    index: int | None = None,
) -> tuple[Any, str]:
    """返回 (单元格值, 类型)。类型：text / money / date / number / integer。"""

    spec = FIELD_CATALOG.get(key)
    kind = spec.format if spec is not None else "text"

    if key == "index":
        return index, "integer"
    if key == "invoice_number":
        return invoice.invoice_number, kind
    if key == "issue_date":
        return invoice.issue_date, kind
    if key == "seller_name":
        return invoice.seller_name, kind
    if key == "total_cents":
        return _yuan(invoice.total_cents), kind
    if key == "amount_ex_tax_cents":
        return _yuan(invoice.amount_ex_tax_cents), kind
    if key == "tax_cents":
        return _yuan(invoice.tax_cents), kind
    if key == "category_name":
        return invoice.category_name or "", kind
    if key == "requester_name":
        return invoice.requester_name or "", kind
    if key == "owner_name":
        return invoice.owner_name or "", kind
    if key == "invoice_form":
        return INVOICE_FORM_LABELS.get(invoice.invoice_form or "", invoice.invoice_form or ""), kind
    if key == "status":
        return STATUS_LABELS.get(invoice.status, invoice.status), kind
    if key == "note":
        return invoice.note or "", kind
    if key == "product_url":
        return invoice.product_url or "", kind
    if key == "item_name":
        return (item.name if item is not None else ""), kind
    if key == "quantity":
        return (float(item.quantity) if item is not None else None), kind
    if key == "unit_price_millis":
        return (
            round(item.unit_price_millis / 1000, 3) if item is not None else None
        ), kind
    if key == "amount_cents":
        return (_yuan(item.amount_cents) if item is not None else None), kind
    if key == "payer_name":
        return _unique_text([payment.payer_name for payment in _payments(invoice)]), kind
    if key == "method":
        return _unique_text(
            [
                PAYMENT_METHOD_LABELS.get(payment.method, payment.method)
                for payment in _payments(invoice)
            ]
        ), kind
    if key == "paid_at":
        return _paid_at(invoice), kind
    if key == "payment_amount_cents":
        total = sum(
            allocation.amount_cents for allocation in _active_allocations(invoice)
        )
        return _yuan(total), kind
    if key == "source_file_name":
        return _source_file_name(invoice), kind
    if key == "payment_summary":
        return _payment_summary(invoice), kind
    if key == "teacher_advance_requested_at":
        return _teacher_advance_requested_at(invoice), kind

    return "", "text"
