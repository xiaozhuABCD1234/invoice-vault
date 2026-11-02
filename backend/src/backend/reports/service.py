"""报表模板与导出的业务逻辑。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models.document import Document
from ..models.invoice import Invoice, InvoiceItem
from ..models.payment import PaymentAllocation
from ..models.report import ExportJob, ReportTemplate
from ..schemas.report import (
    ColumnSpec,
    ExportCreate,
    ExportJobOut,
    ReportTemplateOut,
    SortSpec,
)
from ..shared.audit import record_audit
from ..shared.config import Settings
from ..shared.db import utcnow
from ..shared.enums import ExportStatus, InvoicePaymentStatus, InvoiceStatus, Role
from ..shared.errors import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from ..shared.pagination import paginate
from ..shared.storage import resolve_path, sanitize_filename, save_bytes
from . import excel
from .fields import FIELD_CATALOG, default_columns

DEFAULT_TEMPLATE_ID = 0
DEFAULT_TEMPLATE_NAME = "默认导出"
#: 内置默认模板不是数据库行，使用固定的虚拟创建时间。
BUILTIN_TEMPLATE_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

FILTER_KEYS: tuple[str, ...] = (
    "q",
    "status",
    "payment_status",
    "category_id",
    "requester_id",
    "owner_id",
    "date_from",
    "date_to",
)

SORTABLE: dict[str, Any] = {
    "id": Invoice.id,
    "invoice_number": Invoice.invoice_number,
    "issue_date": Invoice.issue_date,
    "seller_name": Invoice.seller_name,
    "total_cents": Invoice.total_cents,
    "amount_ex_tax_cents": Invoice.amount_ex_tax_cents,
    "tax_cents": Invoice.tax_cents,
    "status": Invoice.status,
    "payment_status": Invoice.payment_status,
    "category_name": Invoice.category_id,
    "requester_name": Invoice.requester_id,
    "owner_name": Invoice.owner_id,
    "created_at": Invoice.created_at,
    "updated_at": Invoice.updated_at,
}


@dataclass(slots=True)
class InvoiceFilters:
    q: str | None = None
    status: str | None = None
    payment_status: str | None = None
    category_id: int | None = None
    requester_id: int | None = None
    owner_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in FILTER_KEYS:
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, date):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result


@dataclass(slots=True)
class ExportConfig:
    template_id: int | None
    columns: list[ColumnSpec]
    filters: InvoiceFilters
    sort: list[SortSpec]


def _as_int(key: str, value: Any) -> int:
    if isinstance(value, bool):
        raise BadRequestError(
            "invalid_filter_value", f"{key} 必须是正整数", {"filter": key}
        )
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise BadRequestError(
            "invalid_filter_value", f"{key} 必须是正整数", {"filter": key}
        ) from exc
    if number <= 0:
        raise BadRequestError(
            "invalid_filter_value", f"{key} 必须是正整数", {"filter": key}
        )
    return number


def _as_date(key: str, value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise BadRequestError(
            "invalid_filter_value", f"{key} 必须是 YYYY-MM-DD 日期", {"filter": key}
        ) from exc


def _as_enum(key: str, value: Any, enum_cls: Any) -> str:
    try:
        return enum_cls(str(value)).value
    except ValueError as exc:
        raise BadRequestError(
            "invalid_filter_value",
            f"{key} 取值无效：{value}",
            {"filter": key, "value": str(value)},
        ) from exc


def parse_filters(raw: Any) -> InvoiceFilters:
    """解析并校验 filters 对象；未知字段与非法取值统一返回 400。"""

    if raw is None:
        return InvoiceFilters()
    if not isinstance(raw, dict):
        raise BadRequestError("invalid_filters", "filters 必须是对象")

    unknown = sorted(set(raw) - set(FILTER_KEYS))
    if unknown:
        raise BadRequestError(
            "invalid_filter_key",
            f"不支持的筛选字段：{unknown[0]}",
            {"filter": unknown[0]},
        )

    filters = InvoiceFilters()
    for key in FILTER_KEYS:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if key == "q":
            filters.q = str(value).strip()
        elif key == "status":
            filters.status = _as_enum(key, value, InvoiceStatus)
        elif key == "payment_status":
            filters.payment_status = _as_enum(key, value, InvoicePaymentStatus)
        elif key in ("category_id", "requester_id", "owner_id"):
            setattr(filters, key, _as_int(key, value))
        elif key == "date_from":
            filters.date_from = _as_date(key, value)
        elif key == "date_to":
            filters.date_to = _as_date(key, value)

    if (
        filters.date_from is not None
        and filters.date_to is not None
        and filters.date_from > filters.date_to
    ):
        raise BadRequestError("invalid_date_range", "开始日期不能晚于结束日期")
    return filters


def _normalize_sort(sort: Sequence[SortSpec] | None) -> list[SortSpec]:
    specs: list[SortSpec] = []
    for item in sort or []:
        spec = SortSpec.model_validate(item) if isinstance(item, dict) else item
        if spec.key not in SORTABLE:
            raise BadRequestError(
                "invalid_sort_key",
                f"不支持的排序字段：{spec.key}",
                {"key": spec.key},
            )
        specs.append(spec)
    return specs


def validate_columns(columns: Sequence[ColumnSpec]) -> None:
    if not columns:
        raise BadRequestError("invalid_columns", "至少需要一列")
    for column in columns:
        if column.key not in FIELD_CATALOG:
            raise BadRequestError(
                "invalid_column_key",
                f"不支持的导出列：{column.key}",
                {"key": column.key},
            )


def _columns_json(columns: Sequence[ColumnSpec]) -> list[dict[str, Any]]:
    validate_columns(columns)
    return [column.model_dump() for column in columns]


def _sort_json(sort: Sequence[SortSpec] | None) -> list[dict[str, Any]]:
    return [spec.model_dump() for spec in _normalize_sort(sort)]


def _template_snapshot(template: ReportTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "columns": template.columns,
        "filters": template.filters,
        "sort": template.sort,
        "created_by": template.created_by,
        "is_shared": template.is_shared,
    }


def default_template_out() -> ReportTemplateOut:
    return ReportTemplateOut(
        id=DEFAULT_TEMPLATE_ID,
        name=DEFAULT_TEMPLATE_NAME,
        columns=default_columns(),
        filters={},
        sort=[],
        created_by=None,
        is_shared=True,
        created_at=BUILTIN_TEMPLATE_CREATED_AT,
    )


def list_templates(db: Session, user: Any) -> list[ReportTemplateOut]:
    stmt = (
        select(ReportTemplate)
        .where(
            or_(
                ReportTemplate.created_by == user.id,
                ReportTemplate.is_shared.is_(True),
            )
        )
        .order_by(ReportTemplate.id.asc())
    )
    templates = list(db.scalars(stmt).all())
    return [default_template_out()] + [
        ReportTemplateOut.model_validate(template) for template in templates
    ]


def get_template_or_404(db: Session, template_id: int) -> ReportTemplate:
    template = db.get(ReportTemplate, template_id)
    if template is None:
        raise NotFoundError("template_not_found", "报表模板不存在")
    return template


def _can_modify(template: ReportTemplate, user: Any) -> bool:
    return template.created_by == user.id or user.role == Role.ADMIN.value


def _can_use(template: ReportTemplate, user: Any) -> bool:
    return (
        template.created_by == user.id
        or bool(template.is_shared)
        or user.role == Role.ADMIN.value
    )


def create_template(
    db: Session,
    *,
    user: Any,
    payload: Any,
    request: Any = None,
) -> ReportTemplate:
    name = payload.name.strip()
    if not name:
        raise BadRequestError("invalid_template_name", "模板名称不能为空")

    template = ReportTemplate(
        name=name,
        columns_json=_columns_json(payload.columns),
        filters_json=parse_filters(payload.filters).to_dict(),
        sort_json=_sort_json(payload.sort),
        created_by=user.id,
        is_shared=bool(payload.is_shared),
        created_at=utcnow(),
    )
    db.add(template)
    db.flush()
    record_audit(
        db,
        user.id,
        "report_template.create",
        "report_template",
        template.id,
        after=_template_snapshot(template),
        request=request,
    )
    db.commit()
    db.refresh(template)
    return template


def update_template(
    db: Session,
    template_id: int,
    *,
    user: Any,
    payload: Any,
    request: Any = None,
) -> ReportTemplate:
    if template_id == DEFAULT_TEMPLATE_ID:
        raise BadRequestError("default_template_immutable", "默认模板不可修改或删除")
    template = get_template_or_404(db, template_id)
    if not _can_modify(template, user):
        raise ForbiddenError("forbidden", "没有权限修改该模板")

    before = _template_snapshot(template)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise BadRequestError("invalid_template_name", "模板名称不能为空")
        template.name = name
    if payload.columns is not None:
        template.columns_json = _columns_json(payload.columns)
    if payload.filters is not None:
        template.filters_json = parse_filters(payload.filters).to_dict()
    if payload.sort is not None:
        template.sort_json = _sort_json(payload.sort)
    if payload.is_shared is not None:
        template.is_shared = payload.is_shared

    db.flush()
    record_audit(
        db,
        user.id,
        "report_template.update",
        "report_template",
        template.id,
        before=before,
        after=_template_snapshot(template),
        request=request,
    )
    db.commit()
    db.refresh(template)
    return template


def delete_template(
    db: Session,
    template_id: int,
    *,
    user: Any,
    request: Any = None,
) -> None:
    if template_id == DEFAULT_TEMPLATE_ID:
        raise BadRequestError("default_template_immutable", "默认模板不可修改或删除")
    template = get_template_or_404(db, template_id)
    if not _can_modify(template, user):
        raise ForbiddenError("forbidden", "没有权限修改该模板")

    before = _template_snapshot(template)
    db.delete(template)
    db.flush()
    record_audit(
        db,
        user.id,
        "report_template.delete",
        "report_template",
        template_id,
        before=before,
        request=request,
    )
    db.commit()


def resolve_export_config(
    db: Session, payload: ExportCreate, user: Any
) -> ExportConfig:
    template: ReportTemplate | None = None
    if payload.template_id not in (None, DEFAULT_TEMPLATE_ID):
        template = get_template_or_404(db, int(payload.template_id))
        if not _can_use(template, user):
            raise ForbiddenError("forbidden", "没有权限使用该模板")

    if payload.columns is not None:
        columns = list(payload.columns)
    elif template is not None:
        columns = [ColumnSpec.model_validate(item) for item in template.columns]
    else:
        columns = default_columns()

    if payload.filters is not None:
        filters = parse_filters(payload.filters)
    elif template is not None:
        filters = parse_filters(template.filters)
    else:
        filters = InvoiceFilters()

    if payload.sort is not None:
        sort = _normalize_sort(payload.sort)
    elif template is not None:
        sort = _normalize_sort(template.sort)
    else:
        sort = []

    validate_columns(columns)
    return ExportConfig(
        template_id=template.id if template is not None else None,
        columns=columns,
        filters=filters,
        sort=sort,
    )


def _order_by(sort: Sequence[SortSpec]) -> list[Any]:
    if not sort:
        return [Invoice.issue_date.asc(), Invoice.id.asc()]
    clauses: list[Any] = []
    for spec in sort:
        column = SORTABLE[spec.key]
        clauses.append(column.desc() if spec.order == "desc" else column.asc())
    if not any(spec.key == "id" for spec in sort):
        clauses.append(Invoice.id.asc())
    return clauses


def _invoice_query(filters: InvoiceFilters, sort: Sequence[SortSpec]) -> Select[Any]:
    stmt = (
        select(Invoice)
        .where(Invoice.deleted_at.is_(None))
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.category),
            selectinload(Invoice.requester),
            selectinload(Invoice.owner),
            selectinload(Invoice.source_document).selectinload(Document.current_version),
            selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
        )
    )
    if filters.q:
        pattern = f"%{filters.q}%"
        stmt = stmt.where(
            or_(
                Invoice.invoice_number.ilike(pattern),
                Invoice.seller_name.ilike(pattern),
                Invoice.note.ilike(pattern),
                Invoice.items.any(InvoiceItem.name.ilike(pattern)),
            )
        )
    if filters.status is not None:
        stmt = stmt.where(Invoice.status == filters.status)
    if filters.payment_status is not None:
        stmt = stmt.where(Invoice.payment_status == filters.payment_status)
    if filters.category_id is not None:
        stmt = stmt.where(Invoice.category_id == filters.category_id)
    if filters.requester_id is not None:
        stmt = stmt.where(Invoice.requester_id == filters.requester_id)
    if filters.owner_id is not None:
        stmt = stmt.where(Invoice.owner_id == filters.owner_id)
    if filters.date_from is not None:
        stmt = stmt.where(Invoice.issue_date >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(Invoice.issue_date <= filters.date_to)
    return stmt.order_by(*_order_by(sort))


def export_job_out(job: ExportJob, settings: Settings) -> ExportJobOut:
    data = ExportJobOut.model_validate(job)
    return data.model_copy(
        update={"download_url": f"{settings.api_prefix}/exports/{job.id}/download"}
    )


def create_export(
    db: Session,
    *,
    user: Any,
    payload: ExportCreate,
    settings: Settings,
    request: Any = None,
) -> ExportJob:
    config = resolve_export_config(db, payload, user)
    now = utcnow()
    job = ExportJob(
        template_id=config.template_id,
        filters_json=config.filters.to_dict(),
        status=ExportStatus.QUEUED.value,
        created_by=user.id,
        created_at=now,
    )
    db.add(job)
    db.flush()
    job_id = job.id
    record_audit(
        db,
        user.id,
        "export.create",
        "export",
        job.id,
        after={
            "template_id": config.template_id,
            "columns": [column.model_dump() for column in config.columns],
            "filters": config.filters.to_dict(),
            "sort": [spec.model_dump() for spec in config.sort],
        },
        request=request,
    )
    db.commit()

    try:
        invoices = list(db.scalars(_invoice_query(config.filters, config.sort)).all())
        data = excel.build_workbook(config.columns, invoices)
        stored = save_bytes(data, "xlsx", created_at=now, settings=settings)
    except Exception as exc:  # 生成失败也要落最终状态，供前端轮询
        db.rollback()
        failed = db.get(ExportJob, job_id)
        if failed is None:
            raise
        failed.status = ExportStatus.FAILED.value
        failed.error_message = str(exc)[:2000] or exc.__class__.__name__
        db.commit()
        db.refresh(failed)
        return failed

    job.file_path = stored["storage_key"]
    job.file_name = sanitize_filename(
        f"发票导出-{job.id}-{now.strftime('%Y%m%d%H%M%S')}.xlsx"
    )
    job.expires_at = now + timedelta(hours=24)
    job.status = ExportStatus.SUCCEEDED.value
    job.error_message = None
    db.commit()
    db.refresh(job)
    return job


def list_exports(
    db: Session,
    user: Any,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    stmt = select(ExportJob)
    if user.role != Role.ADMIN.value:
        stmt = stmt.where(ExportJob.created_by == user.id)
    stmt = stmt.order_by(ExportJob.created_at.desc(), ExportJob.id.desc())
    return paginate(db, stmt, page, page_size)


def get_export_for_user(db: Session, export_id: int, user: Any) -> ExportJob:
    job = db.get(ExportJob, export_id)
    if job is None:
        raise NotFoundError("export_not_found", "导出任务不存在")
    if job.created_by != user.id and user.role != Role.ADMIN.value:
        raise ForbiddenError("forbidden", "没有权限访问该导出任务")
    return job


def _resolve_download_path(job: ExportJob, settings: Settings) -> Path:
    if job.status != ExportStatus.SUCCEEDED.value:
        raise ConflictError("export_not_ready", "导出文件尚未生成")

    expires_at = job.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= utcnow():
            raise AppError("export_expired", "导出文件已过期，请重新生成", 410)

    if not job.file_path:
        raise NotFoundError("export_file_missing", "导出文件不存在")
    try:
        path = resolve_path(job.file_path, settings=settings)
    except ValueError as exc:
        raise NotFoundError("export_file_missing", "导出文件不存在") from exc
    if not path.exists():
        raise NotFoundError("export_file_missing", "导出文件不存在")
    return path


def download_filename(job: ExportJob) -> str:
    name = (job.file_name or "").strip()
    if not name.lower().endswith(".xlsx"):
        name = f"发票导出-{job.id}.xlsx"
    return name


def prepare_download(
    db: Session,
    export_id: int,
    *,
    user: Any,
    settings: Settings,
    request: Any = None,
) -> tuple[ExportJob, Path]:
    job = get_export_for_user(db, export_id, user)
    path = _resolve_download_path(job, settings)
    record_audit(
        db,
        user.id,
        "export.download",
        "export",
        job.id,
        request=request,
    )
    db.commit()
    return job, path
