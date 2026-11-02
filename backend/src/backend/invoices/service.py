"""发票领域服务。

覆盖发票的查询、创建、更新、软删，以及抽取任务审核通过（approve）。
付款状态在本领域内按 active allocation 合计重算，与付款领域算法保持一致：
0 -> unpaid，>= total -> paid，其余 partial。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from ..models.category import Category
from ..models.document import Document
from ..models.extraction import ExtractionJob
from ..models.invoice import Invoice, InvoiceItem
from ..models.payment import PaymentAllocation
from ..models.user import User
from ..schemas.invoice import InvoiceCreate, InvoiceItemInput, InvoiceOut, InvoiceUpdate
from ..shared.audit import record_audit
from ..shared.db import utcnow
from ..shared.enums import (
    AllocationStatus,
    ExtractionStatus,
    InvoicePaymentStatus,
    InvoiceStatus,
    ReviewDecision,
)
from ..shared.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from ..shared.pagination import paginate

#: 列表排序允许的字段
SORT_COLUMNS: dict[str, Any] = {
    "issue_date": Invoice.issue_date,
    "total_cents": Invoice.total_cents,
    "created_at": Invoice.created_at,
    "id": Invoice.id,
}

#: 默认排序：issue_date desc（再由 id desc 兜底）
DEFAULT_SORT: tuple[str, str] = ("issue_date", "desc")

#: PATCH 时允许显式置空的字段（其余字段收到 null 视为未修改）
NULLABLE_FIELDS: frozenset[str] = frozenset(
    {
        "invoice_code",
        "invoice_type",
        "seller_tax_id",
        "buyer_name",
        "buyer_tax_id",
        "tax_rate_bp",
        "category_id",
        "requester_id",
        "owner_id",
        "invoice_form",
        "source_document_id",
        "note",
        "product_url",
    }
)

#: PATCH 中与模型列同名、可直接赋值的字段
_SIMPLE_FIELDS: tuple[str, ...] = (
    "invoice_code",
    "invoice_type",
    "issue_date",
    "seller_name",
    "seller_tax_id",
    "buyer_name",
    "buyer_tax_id",
    "amount_ex_tax_cents",
    "tax_cents",
    "total_cents",
    "tax_rate_bp",
    "currency",
    "source_document_id",
    "note",
    "product_url",
)


# ---------------------------------------------------------------------------
# 付款状态
# ---------------------------------------------------------------------------


def compute_payment_status(total_cents: int, paid_cents: int) -> str:
    """按 active allocation 合计计算发票付款状态。"""

    if paid_cents <= 0:
        return InvoicePaymentStatus.UNPAID.value
    if paid_cents >= total_cents:
        return InvoicePaymentStatus.PAID.value
    return InvoicePaymentStatus.PARTIAL.value


def active_allocated_cents(db: Session, invoice_id: int) -> int:
    """返回发票 active allocation 的金额合计（分）。"""

    total = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0)).where(
            PaymentAllocation.invoice_id == invoice_id,
            PaymentAllocation.status == AllocationStatus.ACTIVE.value,
        )
    )
    return int(total or 0)


def refresh_payment_status(db: Session, invoice: Invoice) -> None:
    """重算并写回发票的 paid_cents / payment_status。"""

    paid = active_allocated_cents(db, invoice.id)
    invoice.paid_cents = paid
    invoice.payment_status = compute_payment_status(int(invoice.total_cents), paid)


# ---------------------------------------------------------------------------
# 校验辅助
# ---------------------------------------------------------------------------


def ensure_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError(
            "category_not_found", "类别不存在", {"category_id": category_id}
        )
    if not category.is_active:
        raise BadRequestError(
            "category_inactive", "类别已停用", {"category_id": category_id}
        )
    return category


def ensure_user(db: Session, user_id: int | None, field: str) -> User | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(
            "user_not_found", "用户不存在", {"user_id": user_id, "field": field}
        )
    return user


def ensure_document(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError(
            "document_not_found", "文档不存在", {"document_id": document_id}
        )
    return document


def ensure_invoice_number_unique(
    db: Session, invoice_number: str, *, exclude_id: int | None = None
) -> None:
    """发票号码全局唯一，包含软删与作废记录。"""

    stmt = select(Invoice.id).where(Invoice.invoice_number == invoice_number)
    if exclude_id is not None:
        stmt = stmt.where(Invoice.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(
            "invoice_duplicate",
            "发票号码已存在",
            {"invoice_number": invoice_number},
        )


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


def _with_display_names(stmt: Any) -> Any:
    return stmt.options(
        selectinload(Invoice.category),
        selectinload(Invoice.requester),
        selectinload(Invoice.owner),
    )


def get_invoice(
    db: Session, invoice_id: int, *, include_deleted: bool = False
) -> Invoice:
    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.allocations),
            joinedload(Invoice.category),
            joinedload(Invoice.requester),
            joinedload(Invoice.owner),
        )
        .where(Invoice.id == invoice_id)
    )
    if not include_deleted:
        stmt = stmt.where(Invoice.deleted_at.is_(None))
    invoice = db.scalars(stmt).first()
    if invoice is None:
        raise NotFoundError(
            "invoice_not_found", "发票不存在", {"invoice_id": invoice_id}
        )
    return invoice


def parse_sort(sort: str | None) -> tuple[Any, str]:
    """解析前端统一的单值排序参数 `字段:顺序`。

    白名单为 issue_date / total_cents / created_at / id；任何非法值
    （缺少冒号、字段未知、顺序非 asc/desc）都回退默认 issue_date:desc。
    """

    if not sort or not sort.strip():
        field_name, direction = DEFAULT_SORT
        return SORT_COLUMNS[field_name], direction

    field_name, separator, raw_order = sort.strip().partition(":")
    if not separator:
        field_name, direction = DEFAULT_SORT
        return SORT_COLUMNS[field_name], direction

    field_name = field_name.strip()
    direction = raw_order.strip().lower()
    column = SORT_COLUMNS.get(field_name)
    if column is None or direction not in {"asc", "desc"}:
        field_name, direction = DEFAULT_SORT
        return SORT_COLUMNS[field_name], direction
    return column, direction


def list_invoices(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    category_id: int | None = None,
    requester_id: int | None = None,
    owner_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str | None = None,
    include_deleted: bool = False,
) -> dict[str, Any]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise BadRequestError("invalid_date_range", "开始日期不能晚于结束日期")

    stmt = _with_display_names(select(Invoice))
    if not include_deleted:
        stmt = stmt.where(Invoice.deleted_at.is_(None))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Invoice.invoice_number.ilike(pattern),
                Invoice.seller_name.ilike(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    if payment_status is not None:
        stmt = stmt.where(Invoice.payment_status == payment_status)
    if category_id is not None:
        stmt = stmt.where(Invoice.category_id == category_id)
    if requester_id is not None:
        stmt = stmt.where(Invoice.requester_id == requester_id)
    if owner_id is not None:
        stmt = stmt.where(Invoice.owner_id == owner_id)
    if date_from is not None:
        stmt = stmt.where(Invoice.issue_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Invoice.issue_date <= date_to)

    column, direction = parse_sort(sort)
    stmt = stmt.order_by(column.asc() if direction == "asc" else column.desc())
    if column is not Invoice.id:
        stmt = stmt.order_by(Invoice.id.desc())

    return paginate(db, stmt, page, page_size)


def to_invoice_out(invoice: Invoice) -> InvoiceOut:
    """ORM -> 响应 schema，并固定明细 / 分配的展示顺序。"""

    out = InvoiceOut.model_validate(invoice)
    out.items = sorted(out.items, key=lambda item: (item.sort_order, item.id))
    out.allocations = sorted(out.allocations, key=lambda allocation: allocation.id)
    return out


# ---------------------------------------------------------------------------
# 快照（审计 before/after）
# ---------------------------------------------------------------------------


def _iso(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def invoice_snapshot(invoice: Invoice) -> dict[str, Any]:
    items = sorted(invoice.items or [], key=lambda item: (item.sort_order, item.id or 0))
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "invoice_code": invoice.invoice_code,
        "invoice_type": invoice.invoice_type,
        "issue_date": _iso(invoice.issue_date),
        "seller_name": invoice.seller_name,
        "seller_tax_id": invoice.seller_tax_id,
        "buyer_name": invoice.buyer_name,
        "buyer_tax_id": invoice.buyer_tax_id,
        "amount_ex_tax_cents": invoice.amount_ex_tax_cents,
        "tax_cents": invoice.tax_cents,
        "total_cents": invoice.total_cents,
        "tax_rate_bp": invoice.tax_rate_bp,
        "currency": invoice.currency,
        "category_id": invoice.category_id,
        "requester_id": invoice.requester_id,
        "owner_id": invoice.owner_id,
        "invoice_form": invoice.invoice_form,
        "status": invoice.status,
        "paid_cents": invoice.paid_cents,
        "payment_status": invoice.payment_status,
        "source_document_id": invoice.source_document_id,
        "extraction_job_id": invoice.extraction_job_id,
        "note": invoice.note,
        "product_url": invoice.product_url,
        "created_by": invoice.created_by,
        "confirmed_by": invoice.confirmed_by,
        "confirmed_at": _iso(invoice.confirmed_at),
        "created_at": _iso(invoice.created_at),
        "updated_at": _iso(invoice.updated_at),
        "deleted_at": _iso(invoice.deleted_at),
        "items": [
            {
                "name": item.name,
                "quantity": float(item.quantity),
                "unit_price_millis": item.unit_price_millis,
                "amount_cents": item.amount_cents,
                "note": item.note,
                "sort_order": item.sort_order,
            }
            for item in items
        ],
    }


def job_snapshot(job: ExtractionJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "document_id": job.document_id,
        "status": job.status,
        "reviewed_by": job.reviewed_by,
        "reviewed_at": _iso(job.reviewed_at),
        "review_decision": job.review_decision,
        "review_note": job.review_note,
    }


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------


def _item_sort_order(item: InvoiceItemInput, index: int) -> int:
    return item.sort_order if item.sort_order is not None else index


def _build_item(invoice_id: int, item: InvoiceItemInput, index: int) -> InvoiceItem:
    return InvoiceItem(
        invoice_id=invoice_id,
        name=item.name,
        quantity=Decimal(str(item.quantity)),
        unit_price_millis=item.unit_price_millis,
        amount_cents=item.amount_cents,
        note=item.note,
        sort_order=_item_sort_order(item, index),
    )


def build_invoice(
    db: Session,
    *,
    payload: InvoiceCreate,
    actor: User,
    status_value: str | None = None,
    source_document_id: int | None = None,
    extraction_job_id: int | None = None,
) -> Invoice:
    """校验并构造发票 + 明细；只 flush，不 commit，供 create / approve 复用。"""

    invoice_number = payload.invoice_number.strip()
    if not invoice_number:
        raise BadRequestError("invalid_invoice_number", "发票号码不能为空")

    ensure_category(db, payload.category_id)
    ensure_user(db, payload.requester_id, "requester_id")
    ensure_user(db, payload.owner_id, "owner_id")
    if source_document_id is not None:
        ensure_document(db, source_document_id)
    elif payload.source_document_id is not None:
        ensure_document(db, payload.source_document_id)
    ensure_invoice_number_unique(db, invoice_number)

    effective_status = status_value or payload.status.value
    now = utcnow()
    is_active = effective_status == InvoiceStatus.ACTIVE.value

    invoice = Invoice(
        invoice_number=invoice_number,
        invoice_code=payload.invoice_code,
        invoice_type=payload.invoice_type,
        issue_date=payload.issue_date,
        seller_name=payload.seller_name,
        seller_tax_id=payload.seller_tax_id,
        buyer_name=payload.buyer_name,
        buyer_tax_id=payload.buyer_tax_id,
        amount_ex_tax_cents=payload.amount_ex_tax_cents,
        tax_cents=payload.tax_cents,
        total_cents=payload.total_cents,
        tax_rate_bp=payload.tax_rate_bp,
        currency=payload.currency,
        category_id=payload.category_id,
        requester_id=payload.requester_id,
        owner_id=payload.owner_id,
        invoice_form=payload.invoice_form.value if payload.invoice_form else None,
        status=effective_status,
        paid_cents=0,
        payment_status=InvoicePaymentStatus.UNPAID.value,
        source_document_id=(
            source_document_id
            if source_document_id is not None
            else payload.source_document_id
        ),
        extraction_job_id=extraction_job_id,
        note=payload.note,
        product_url=payload.product_url,
        created_by=actor.id,
        confirmed_by=actor.id if is_active else None,
        confirmed_at=now if is_active else None,
        created_at=now,
        updated_at=now,
    )
    db.add(invoice)
    db.flush()

    for index, item in enumerate(payload.items, start=1):
        db.add(_build_item(invoice.id, item, index))
    db.flush()
    return invoice


def _commit(db: Session, invoice_number: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc))
        if "invoice_number" in message:
            raise ConflictError(
                "invoice_duplicate",
                "发票号码已存在",
                {"invoice_number": invoice_number},
            ) from exc
        raise


def create_invoice(
    db: Session,
    *,
    payload: InvoiceCreate,
    actor: User,
    request: Any = None,
) -> Invoice:
    invoice = build_invoice(db, payload=payload, actor=actor)
    record_audit(
        db,
        actor.id,
        "invoice.create",
        "invoice",
        invoice.id,
        after=invoice_snapshot(invoice),
        request=request,
    )
    _commit(db, invoice.invoice_number)
    return get_invoice(db, invoice.id, include_deleted=True)


def _replace_items(
    db: Session, invoice: Invoice, items: list[InvoiceItemInput]
) -> None:
    invoice.items.clear()
    db.flush()
    for index, item in enumerate(items, start=1):
        invoice.items.append(_build_item(invoice.id, item, index))
    db.flush()


def update_invoice(
    db: Session,
    invoice_id: int,
    *,
    payload: InvoiceUpdate,
    actor: User,
    is_admin: bool,
    request: Any = None,
) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if not is_admin and invoice.created_by != actor.id:
        raise ForbiddenError("forbidden", "只能修改自己创建的发票")

    before = invoice_snapshot(invoice)
    fields = payload.model_fields_set

    if "invoice_number" in fields and payload.invoice_number is not None:
        clean_number = payload.invoice_number.strip()
        if not clean_number:
            raise BadRequestError("invalid_invoice_number", "发票号码不能为空")
        if clean_number != invoice.invoice_number:
            ensure_invoice_number_unique(db, clean_number, exclude_id=invoice.id)
            invoice.invoice_number = clean_number

    if "category_id" in fields:
        if payload.category_id is not None:
            ensure_category(db, payload.category_id)
        invoice.category_id = payload.category_id

    if "requester_id" in fields:
        ensure_user(db, payload.requester_id, "requester_id")
        invoice.requester_id = payload.requester_id

    if "owner_id" in fields:
        ensure_user(db, payload.owner_id, "owner_id")
        invoice.owner_id = payload.owner_id

    if (
        "source_document_id" in fields
        and payload.source_document_id is not None
    ):
        ensure_document(db, payload.source_document_id)

    if "total_cents" in fields and payload.total_cents is not None:
        allocated = active_allocated_cents(db, invoice.id)
        if payload.total_cents < allocated:
            raise ConflictError(
                "invoice_amount_below_allocations",
                "发票金额不能小于已分配金额",
                {
                    "total_cents": payload.total_cents,
                    "allocated_cents": allocated,
                },
            )

    for field_name in _SIMPLE_FIELDS:
        if field_name not in fields:
            continue
        value = getattr(payload, field_name)
        if value is None and field_name not in NULLABLE_FIELDS:
            continue
        setattr(invoice, field_name, value)

    if "invoice_form" in fields:
        invoice.invoice_form = (
            payload.invoice_form.value if payload.invoice_form is not None else None
        )

    if "status" in fields and payload.status is not None:
        invoice.status = payload.status.value
        if (
            invoice.status == InvoiceStatus.ACTIVE.value
            and invoice.confirmed_at is None
        ):
            invoice.confirmed_by = actor.id
            invoice.confirmed_at = utcnow()

    if "items" in fields and payload.items is not None:
        _replace_items(db, invoice, payload.items)

    refresh_payment_status(db, invoice)
    invoice.updated_at = utcnow()
    db.flush()

    record_audit(
        db,
        actor.id,
        "invoice.update",
        "invoice",
        invoice.id,
        before=before,
        after=invoice_snapshot(invoice),
        request=request,
    )
    _commit(db, invoice.invoice_number)
    return get_invoice(db, invoice.id, include_deleted=True)


def delete_invoice(
    db: Session,
    invoice_id: int,
    *,
    actor_id: int,
    request: Any = None,
) -> None:
    invoice = get_invoice(db, invoice_id)
    allocated = active_allocated_cents(db, invoice.id)
    if allocated > 0:
        raise ConflictError(
            "invoice_has_allocations",
            "发票存在有效付款分配，不能删除",
            {"invoice_id": invoice.id, "allocated_cents": allocated},
        )

    before = invoice_snapshot(invoice)
    now = utcnow()
    invoice.deleted_at = now
    invoice.updated_at = now
    db.flush()

    record_audit(
        db,
        actor_id,
        "invoice.delete",
        "invoice",
        invoice.id,
        before=before,
        after=invoice_snapshot(invoice),
        request=request,
    )
    _commit(db, invoice.invoice_number)


def approve_extraction_job(
    db: Session,
    job_id: int,
    *,
    payload: InvoiceCreate,
    actor: User,
    is_admin: bool,
    request: Any = None,
) -> tuple[Invoice, ExtractionJob]:
    """审核通过抽取任务并创建 active 发票。失败时整个事务回滚。"""

    job = db.get(ExtractionJob, job_id)
    if job is None:
        raise NotFoundError(
            "extraction_job_not_found", "抽取任务不存在", {"job_id": job_id}
        )

    document = job.document
    if document is None:
        raise NotFoundError(
            "document_not_found", "文档不存在", {"document_id": job.document_id}
        )

    if not is_admin and actor.id not in {
        document.owner_user_id,
        document.created_by,
    }:
        raise ForbiddenError("forbidden", "只能审核自己上传的文档")

    if job.status != ExtractionStatus.REVIEW_PENDING.value:
        raise ConflictError(
            "job_not_review_pending",
            "抽取任务不处于待审核状态",
            {"job_id": job.id, "status": job.status},
        )

    job_before = job_snapshot(job)
    invoice = build_invoice(
        db,
        payload=payload,
        actor=actor,
        status_value=InvoiceStatus.ACTIVE.value,
        source_document_id=job.document_id,
        extraction_job_id=job.id,
    )

    now = utcnow()
    # approve 请求体只包含发票字段，review_note 保留任务原值，避免覆盖抽取阶段备注。
    job.status = ExtractionStatus.APPROVED.value
    job.reviewed_by = actor.id
    job.reviewed_at = now
    job.review_decision = ReviewDecision.APPROVED.value
    db.flush()

    record_audit(
        db,
        actor.id,
        "job.approve",
        "extraction_job",
        job.id,
        before=job_before,
        after=job_snapshot(job),
        request=request,
    )
    record_audit(
        db,
        actor.id,
        "invoice.create",
        "invoice",
        invoice.id,
        after=invoice_snapshot(invoice),
        request=request,
    )

    invoice_number = invoice.invoice_number
    _commit(db, invoice_number)
    return (
        get_invoice(db, invoice.id, include_deleted=True),
        db.get(ExtractionJob, job.id),
    )
