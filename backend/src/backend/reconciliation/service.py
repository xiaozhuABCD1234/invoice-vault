"""对账领域服务：汇总口径、问题计算与忽略备注。

对账接口只读计算，不修改发票/付款数据；只有忽略/取消忽略会写入
reconciliation_notes，并记录审计日志。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models.invoice import Invoice, InvoiceItem
from ..models.payment import Payment, PaymentAllocation
from ..models.reconciliation import ReconciliationNote
from ..schemas.reconciliation import (
    IssueCounts,
    ReconciliationIssue,
    ReconciliationSummary,
)
from ..shared.audit import record_audit
from ..shared.enums import (
    AllocationStatus,
    InvoiceStatus,
    IssueSeverity,
    PaymentMethod,
    PaymentStatus,
    ReconciliationIssueType,
)
from ..shared.errors import NotFoundError
from ..shared.pagination import normalize_page

ACTIVE = AllocationStatus.ACTIVE.value
VOID_PAYMENT = PaymentStatus.VOID.value
ACTIVE_INVOICE = InvoiceStatus.ACTIVE.value
VOID_INVOICE = InvoiceStatus.VOID.value
DUPLICATE_INVOICE = InvoiceStatus.DUPLICATE.value

_METHOD_LABELS: dict[str, str] = {
    PaymentMethod.PERSONAL_ADVANCE.value: "个人垫付",
    PaymentMethod.TEACHER_ADVANCE.value: "老师代付",
    PaymentMethod.BANK_TRANSFER.value: "银行转账",
    PaymentMethod.ALIPAY.value: "支付宝",
    PaymentMethod.WECHAT.value: "微信",
    PaymentMethod.CARD.value: "银行卡",
    PaymentMethod.CASH.value: "现金",
    PaymentMethod.OTHER.value: "其他",
}


def _yuan(cents: int | None) -> str:
    """整数分 → 人民币展示文本，避免浮点误差。"""

    value = int(cents or 0)
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    return f"{sign}¥{absolute // 100:,}.{absolute % 100:02d}"

_SEVERITY: dict[ReconciliationIssueType, IssueSeverity] = {
    ReconciliationIssueType.INVOICE_UNPAID: IssueSeverity.ERROR,
    ReconciliationIssueType.INVOICE_PARTIAL: IssueSeverity.WARNING,
    ReconciliationIssueType.PAYMENT_UNALLOCATED: IssueSeverity.ERROR,
    ReconciliationIssueType.PAYMENT_PARTIAL: IssueSeverity.WARNING,
    ReconciliationIssueType.MISSING_EVIDENCE: IssueSeverity.WARNING,
    ReconciliationIssueType.DUPLICATE_INVOICE: IssueSeverity.ERROR,
    ReconciliationIssueType.ITEM_MISMATCH: IssueSeverity.WARNING,
    ReconciliationIssueType.AMOUNT_ANOMALY: IssueSeverity.ERROR,
    ReconciliationIssueType.DATE_ANOMALY: IssueSeverity.WARNING,
}


def _issue(
    issue_type: ReconciliationIssueType,
    entity_type: str,
    entity_id: int,
    *,
    title: str,
    detail: str,
    amount_cents: int | None,
) -> ReconciliationIssue:
    return ReconciliationIssue(
        id=f"{issue_type.value}:{entity_id}",
        type=issue_type,
        severity=_SEVERITY[issue_type],
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        detail=detail,
        amount_cents=amount_cents,
    )


def _active_sum_by(db: Session, key_column: Any) -> dict[int, int]:
    stmt = (
        select(key_column, func.coalesce(func.sum(PaymentAllocation.amount_cents), 0))
        .where(PaymentAllocation.status == ACTIVE)
        .group_by(key_column)
    )
    return {int(key): int(total or 0) for key, total in db.execute(stmt).all()}


def _issue_sort_key(issue: ReconciliationIssue) -> tuple[int, int, str]:
    severity_rank = 0 if issue.severity == IssueSeverity.ERROR else 1
    return (severity_rank, -(issue.amount_cents or 0), issue.id)


def collect_issues(db: Session) -> list[ReconciliationIssue]:
    """计算全部对账问题（含 ignored 标记），不修改业务数据。"""

    candidates: list[ReconciliationIssue] = []

    invoices = list(
        db.scalars(
            select(Invoice).where(
                Invoice.status == ACTIVE_INVOICE,
                Invoice.deleted_at.is_(None),
            )
        ).all()
    )
    paid_by_invoice = _active_sum_by(db, PaymentAllocation.invoice_id)
    allocated_by_payment = _active_sum_by(db, PaymentAllocation.payment_id)
    item_sums = {
        int(invoice_id): int(total or 0)
        for invoice_id, total in db.execute(
            select(
                InvoiceItem.invoice_id,
                func.coalesce(func.sum(InvoiceItem.amount_cents), 0),
            ).group_by(InvoiceItem.invoice_id)
        ).all()
    }

    for invoice in invoices:
        paid = paid_by_invoice.get(invoice.id, 0)
        total = invoice.total_cents
        if total > 0 and paid == 0:
            candidates.append(
                _issue(
                    ReconciliationIssueType.INVOICE_UNPAID,
                    "invoice",
                    invoice.id,
                    title="发票未付款",
                    detail=(
                        f"发票 {invoice.invoice_number}（{invoice.seller_name}）"
                        f"尚未分配任何付款，价税合计 {_yuan(total)}"
                    ),
                    amount_cents=total,
                )
            )
        elif 0 < paid < total:
            candidates.append(
                _issue(
                    ReconciliationIssueType.INVOICE_PARTIAL,
                    "invoice",
                    invoice.id,
                    title="发票部分付款",
                    detail=(
                        f"发票 {invoice.invoice_number} 已分配 {_yuan(paid)}，"
                        f"尚差 {_yuan(total - paid)}"
                    ),
                    amount_cents=total - paid,
                )
            )
        if paid > total:
            candidates.append(
                _issue(
                    ReconciliationIssueType.AMOUNT_ANOMALY,
                    "invoice",
                    invoice.id,
                    title="发票分配超额",
                    detail=(
                        f"发票 {invoice.invoice_number} 已分配 {_yuan(paid)}，"
                        f"超过价税合计 {_yuan(total)}"
                    ),
                    amount_cents=paid - total,
                )
            )

        items_total = item_sums.get(invoice.id, 0)
        diff = abs(items_total - total)
        if diff > 1:
            candidates.append(
                _issue(
                    ReconciliationIssueType.ITEM_MISMATCH,
                    "invoice",
                    invoice.id,
                    title="发票明细合计不一致",
                    detail=(
                        f"发票 {invoice.invoice_number} 明细合计 {_yuan(items_total)}，"
                        f"价税合计 {_yuan(total)}，差额 {_yuan(diff)}"
                    ),
                    amount_cents=diff,
                )
            )

    payments = list(
        db.scalars(select(Payment).where(Payment.status != VOID_PAYMENT)).all()
    )
    for payment in payments:
        allocated = allocated_by_payment.get(payment.id, 0)
        amount = payment.amount_cents
        if allocated == 0:
            candidates.append(
                _issue(
                    ReconciliationIssueType.PAYMENT_UNALLOCATED,
                    "payment",
                    payment.id,
                    title="付款未分配",
                    detail=f"付款 #{payment.id} 金额 {_yuan(amount)} 尚未分配到任何发票",
                    amount_cents=amount,
                )
            )
        elif 0 < allocated < amount:
            candidates.append(
                _issue(
                    ReconciliationIssueType.PAYMENT_PARTIAL,
                    "payment",
                    payment.id,
                    title="付款部分分配",
                    detail=(
                        f"付款 #{payment.id} 已分配 {_yuan(allocated)}，"
                        f"尚余 {_yuan(amount - allocated)} 未分配"
                    ),
                    amount_cents=amount - allocated,
                )
            )
        if allocated > amount:
            candidates.append(
                _issue(
                    ReconciliationIssueType.AMOUNT_ANOMALY,
                    "payment",
                    payment.id,
                    title="付款分配超额",
                    detail=(
                        f"付款 #{payment.id} 已分配 {_yuan(allocated)}，"
                        f"超过付款金额 {_yuan(amount)}"
                    ),
                    amount_cents=allocated - amount,
                )
            )
        if (
            payment.method != PaymentMethod.TEACHER_ADVANCE.value
            and payment.evidence_document_id is None
        ):
            candidates.append(
                _issue(
                    ReconciliationIssueType.MISSING_EVIDENCE,
                    "payment",
                    payment.id,
                    title="付款缺少凭证",
                    detail=(
                        f"付款 #{payment.id}（{_METHOD_LABELS.get(payment.method, payment.method)}）"
                        "未上传付款凭证"
                    ),
                    amount_cents=amount,
                )
            )

    active_allocations = list(
        db.scalars(
            select(PaymentAllocation)
            .options(
                selectinload(PaymentAllocation.payment),
                selectinload(PaymentAllocation.invoice),
            )
            .where(PaymentAllocation.status == ACTIVE)
        ).all()
    )
    for allocation in active_allocations:
        invoice = allocation.invoice
        payment = allocation.payment
        if invoice is None:
            continue
        if (
            invoice.status in (VOID_INVOICE, DUPLICATE_INVOICE)
            or invoice.deleted_at is not None
        ):
            reason = "已删除" if invoice.deleted_at is not None else f"状态为 {invoice.status}"
            candidates.append(
                _issue(
                    ReconciliationIssueType.AMOUNT_ANOMALY,
                    "allocation",
                    allocation.id,
                    title="分配挂到无效发票",
                    detail=(
                        f"分配 #{allocation.id} 关联的发票 "
                        f"{invoice.invoice_number} {reason}"
                    ),
                    amount_cents=allocation.amount_cents,
                )
            )
        if payment is not None and payment.paid_at.date() < invoice.issue_date:
            candidates.append(
                _issue(
                    ReconciliationIssueType.DATE_ANOMALY,
                    "allocation",
                    allocation.id,
                    title="付款日期早于开票日期",
                    detail=(
                        f"付款 #{payment.id} 日期 {payment.paid_at.date().isoformat()} "
                        f"早于发票 {invoice.invoice_number} 开票日期 "
                        f"{invoice.issue_date.isoformat()}"
                    ),
                    amount_cents=allocation.amount_cents,
                )
            )

    # duplicate_invoice：数据库唯一约束下正常不会出现，保留类型但返回空。

    notes = {
        note.issue_key: note
        for note in db.scalars(select(ReconciliationNote)).all()
    }

    issues: list[ReconciliationIssue] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.id in seen:
            continue
        seen.add(candidate.id)
        note = notes.get(candidate.id)
        if note is not None:
            candidate.ignored = True
            candidate.note = note.note
        issues.append(candidate)

    issues.sort(key=_issue_sort_key)
    return issues


def get_summary(db: Session) -> ReconciliationSummary:
    invoice_total_raw, invoice_count_raw = db.execute(
        select(
            func.coalesce(func.sum(Invoice.total_cents), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.status == ACTIVE_INVOICE,
            Invoice.deleted_at.is_(None),
        )
    ).one()
    invoice_paid_raw = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0))
        .join(Invoice, PaymentAllocation.invoice_id == Invoice.id)
        .where(
            PaymentAllocation.status == ACTIVE,
            Invoice.status == ACTIVE_INVOICE,
            Invoice.deleted_at.is_(None),
        )
    )
    payment_total_raw, payment_count_raw = db.execute(
        select(
            func.coalesce(func.sum(Payment.amount_cents), 0),
            func.count(Payment.id),
        ).where(Payment.status != VOID_PAYMENT)
    ).one()
    payment_allocated_raw = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0))
        .join(Payment, PaymentAllocation.payment_id == Payment.id)
        .where(
            PaymentAllocation.status == ACTIVE,
            Payment.status != VOID_PAYMENT,
        )
    )

    invoice_total = int(invoice_total_raw or 0)
    invoice_paid = int(invoice_paid_raw or 0)
    payment_total = int(payment_total_raw or 0)
    payment_allocated = int(payment_allocated_raw or 0)

    counts = IssueCounts()
    for issue in collect_issues(db):
        if issue.ignored:
            continue
        field = issue.type.value
        setattr(counts, field, getattr(counts, field) + 1)

    return ReconciliationSummary(
        invoice_total_cents=invoice_total,
        invoice_paid_cents=invoice_paid,
        invoice_unpaid_cents=max(invoice_total - invoice_paid, 0),
        payment_total_cents=payment_total,
        payment_allocated_cents=payment_allocated,
        payment_unallocated_cents=max(payment_total - payment_allocated, 0),
        invoice_count=int(invoice_count_raw or 0),
        payment_count=int(payment_count_raw or 0),
        issue_counts=counts,
    )


def paginate_issues(
    issues: list[ReconciliationIssue],
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    current_page, current_size = normalize_page(page, page_size)
    start = (current_page - 1) * current_size
    return {
        "items": issues[start : start + current_size],
        "total": len(issues),
        "page": current_page,
        "page_size": current_size,
    }


def find_issue(db: Session, issue_key: str) -> ReconciliationIssue | None:
    for issue in collect_issues(db):
        if issue.id == issue_key:
            return issue
    return None


def ignore_issue(
    db: Session,
    issue_key: str,
    *,
    note: str,
    actor_id: int | None,
    request: Any = None,
) -> ReconciliationIssue:
    issue = find_issue(db, issue_key)
    if issue is None:
        raise NotFoundError("issue_not_found", "对账问题不存在", {"issue_key": issue_key})

    existing = db.scalar(
        select(ReconciliationNote).where(ReconciliationNote.issue_key == issue_key)
    )
    before = (
        {"issue_key": existing.issue_key, "note": existing.note, "ignored_by": existing.ignored_by}
        if existing is not None
        else None
    )
    if existing is None:
        db.add(
            ReconciliationNote(
                issue_key=issue_key,
                note=note,
                ignored_by=actor_id,
            )
        )
    else:
        existing.note = note
        existing.ignored_by = actor_id

    db.flush()
    record_audit(
        db,
        actor_id,
        "reconciliation.ignore",
        "reconciliation_issue",
        issue_key,
        before=before,
        after={"issue_key": issue_key, "note": note, "ignored_by": actor_id},
        request=request,
    )
    db.commit()
    return issue.model_copy(update={"ignored": True, "note": note})


def unignore_issue(
    db: Session,
    issue_key: str,
    *,
    actor_id: int | None,
    request: Any = None,
) -> ReconciliationIssue:
    issue = find_issue(db, issue_key)
    if issue is None:
        raise NotFoundError("issue_not_found", "对账问题不存在", {"issue_key": issue_key})

    existing = db.scalar(
        select(ReconciliationNote).where(ReconciliationNote.issue_key == issue_key)
    )
    if existing is not None:
        before = {
            "issue_key": existing.issue_key,
            "note": existing.note,
            "ignored_by": existing.ignored_by,
        }
        db.delete(existing)
        db.flush()
        record_audit(
            db,
            actor_id,
            "reconciliation.unignore",
            "reconciliation_issue",
            issue_key,
            before=before,
            after=None,
            request=request,
        )
        db.commit()

    return issue.model_copy(update={"ignored": False, "note": None})
