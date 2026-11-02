"""抽取任务服务：入队、处理、查询、重试与驳回。"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.document import Document, DocumentVersion
from ..models.extraction import ExtractionJob
from ..models.user import User
from ..shared.audit import record_audit
from ..shared.db import utcnow
from ..shared.enums import ExtractionStatus, ReviewDecision, Role
from ..shared.errors import BadRequestError, ConflictError, NotFoundError
from ..shared.pagination import paginate
from . import providers
from .config import ExtractionConfig, load_config
from .normalize import aggregate_confidence, normalize_fields, validate_parsed

logger = logging.getLogger(__name__)

QUEUED = ExtractionStatus.QUEUED.value
RUNNING = ExtractionStatus.RUNNING.value
REVIEW_PENDING = ExtractionStatus.REVIEW_PENDING.value
APPROVED = ExtractionStatus.APPROVED.value
REJECTED = ExtractionStatus.REJECTED.value
FAILED = ExtractionStatus.FAILED.value
RETRYABLE = (FAILED, REVIEW_PENDING, REJECTED)


def is_admin(user: User) -> bool:
    return user.role == Role.ADMIN.value


def _job_load_options() -> tuple[Any, ...]:
    return (
        selectinload(ExtractionJob.document).selectinload(Document.current_version),
        selectinload(ExtractionJob.document).selectinload(Document.owner),
    )


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def enqueue_job(db: Session, document: Document, *, provider: str) -> ExtractionJob:
    """新增 queued 任务并 flush（事务由调用方提交）。"""

    job = ExtractionJob(
        document_id=document.id,
        provider=provider,
        status=QUEUED,
        attempts=0,
        queued_at=utcnow(),
    )
    db.add(job)
    db.flush()
    return job


def latest_job_for_document(
    db: Session,
    document_id: int,
    *,
    statuses: tuple[str, ...] | None = None,
) -> ExtractionJob | None:
    stmt = select(ExtractionJob).where(ExtractionJob.document_id == document_id)
    if statuses:
        stmt = stmt.where(ExtractionJob.status.in_(statuses))
    stmt = stmt.order_by(ExtractionJob.queued_at.desc(), ExtractionJob.id.desc()).limit(1)
    return db.scalar(stmt)


def get_job_or_404(db: Session, job_id: int) -> ExtractionJob:
    job = db.scalar(
        select(ExtractionJob)
        .options(*_job_load_options())
        .where(ExtractionJob.id == job_id)
    )
    if job is None:
        raise NotFoundError("job_not_found", "抽取任务不存在")
    return job


def list_jobs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: Any = None,
    provider: Any = None,
    document_id: int | None = None,
) -> dict[str, Any]:
    stmt = select(ExtractionJob).options(*_job_load_options())
    if status is not None:
        stmt = stmt.where(ExtractionJob.status == _enum_value(status))
    if provider is not None:
        stmt = stmt.where(ExtractionJob.provider == _enum_value(provider))
    if document_id is not None:
        stmt = stmt.where(ExtractionJob.document_id == document_id)
    stmt = stmt.order_by(ExtractionJob.queued_at.desc(), ExtractionJob.id.desc())
    return paginate(db, stmt, page, page_size)


def _current_version(db: Session, document: Document) -> DocumentVersion | None:
    version = document.current_version
    if version is not None:
        return version
    if document.current_version_id is not None:
        version = db.get(DocumentVersion, document.current_version_id)
        if version is not None:
            return version
    return db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )


def _mark_failure(
    db: Session,
    job: ExtractionJob,
    config: ExtractionConfig,
    code: str,
    message: str,
) -> None:
    job.attempts = int(job.attempts or 0) + 1
    job.error_code = code
    job.error_message = message
    if job.attempts >= config.max_attempts:
        job.status = FAILED
        job.finished_at = utcnow()
    else:
        job.status = QUEUED
        job.started_at = None
        job.finished_at = None
        delay = max(config.backoff_seconds, 0.0) * (2 ** (job.attempts - 1))
        job.queued_at = utcnow() + timedelta(seconds=delay)
    db.commit()


def process_job(
    db: Session,
    job_id: int,
    *,
    settings: Any,
    config: ExtractionConfig | None = None,
) -> ExtractionJob:
    """处理一个 queued 任务：queued -> running -> review_pending / failed。

    无论置信度高低都进入 review_pending；失败由 worker 控制重试。
    """

    cfg = config or load_config(settings=settings)
    job = db.get(ExtractionJob, job_id)
    if job is None:
        raise NotFoundError("job_not_found", "抽取任务不存在")
    if job.status != QUEUED:
        return job

    document = job.document or db.get(Document, job.document_id)
    if document is None:
        raise NotFoundError("document_not_found", "文档不存在")
    version = _current_version(db, document)

    job.status = RUNNING
    job.started_at = utcnow()
    job.finished_at = None
    job.error_code = None
    job.error_message = None
    job.review_decision = None
    job.reviewed_by = None
    job.reviewed_at = None
    job.review_note = None
    db.commit()

    try:
        if version is None:
            raise providers.ProviderError("version_missing", "文档没有可用版本")
        path = providers.resolve_version_path(version, cfg)
        chain = providers.provider_chain(cfg)
        result = providers.run_provider_chain(
            chain, document, version, cfg, path=path
        )
        parsed = normalize_fields(result.fields)
        field_confidence = dict(result.field_confidence or {})
        validation = validate_parsed(
            parsed, db=db, field_confidence=field_confidence
        )
        confidence = result.confidence
        if confidence is None or float(confidence) <= 0:
            confidence = aggregate_confidence(field_confidence, parsed)

        job.provider = result.provider
        job.model = result.model
        job.prompt_version = result.prompt_version
        job.raw_text = result.raw_text
        job.raw_response_json = result.raw_response
        job.parsed_json = parsed
        job.validation_json = validation
        job.confidence = round(float(confidence), 4)
        job.status = REVIEW_PENDING
        job.finished_at = utcnow()
        db.commit()
    except providers.ProviderError as exc:
        _mark_failure(db, job, cfg, exc.code, exc.message)
    except Exception as exc:  # 未预期异常同样转成可重试失败，避免 worker 崩溃
        logger.exception("抽取任务 %s 处理失败", job_id)
        _mark_failure(db, job, cfg, "internal_error", str(exc) or exc.__class__.__name__)

    db.refresh(job)
    return job


def previous_approved_job(db: Session, job: ExtractionJob) -> ExtractionJob | None:
    return db.scalar(
        select(ExtractionJob)
        .where(
            ExtractionJob.document_id == job.document_id,
            ExtractionJob.status == APPROVED,
            ExtractionJob.id != job.id,
        )
        .order_by(ExtractionJob.id.desc())
        .limit(1)
    )


def compute_diff(previous: ExtractionJob | None, job: ExtractionJob) -> dict[str, Any] | None:
    """与上一次 approved 任务 parsed_json 的字段差异；没有则返回 None。"""

    if previous is None:
        return None
    before = previous.parsed_json if isinstance(previous.parsed_json, dict) else {}
    after = job.parsed_json if isinstance(job.parsed_json, dict) else {}
    fields: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            fields[key] = {"before": before.get(key), "after": after.get(key)}
    return {"against_job_id": previous.id, "fields": fields}


def job_diff(db: Session, job: ExtractionJob) -> dict[str, Any] | None:
    return compute_diff(previous_approved_job(db, job), job)


def _document_owner_ids(job: ExtractionJob) -> set[int]:
    ids: set[int] = set()
    document = job.document
    if document is not None:
        if document.owner_user_id is not None:
            ids.add(int(document.owner_user_id))
        if document.created_by is not None:
            ids.add(int(document.created_by))
    return ids


def can_manage_job(job: ExtractionJob, user: User) -> bool:
    """admin 或文档 owner/上传者。"""

    return is_admin(user) or int(user.id) in _document_owner_ids(job)


def _job_snapshot(job: ExtractionJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "document_id": job.document_id,
        "status": job.status,
        "attempts": job.attempts,
        "review_decision": job.review_decision,
        "review_note": job.review_note,
    }


def retry_job(
    db: Session,
    job: ExtractionJob,
    *,
    actor: User,
    config: ExtractionConfig,
    request: Any = None,
) -> ExtractionJob:
    if job.status in (QUEUED, RUNNING):
        raise ConflictError("job_running", "任务正在排队或处理中，无法重试")
    if job.status not in RETRYABLE:
        raise ConflictError("job_not_retryable", "当前任务状态不支持重试")
    if int(job.attempts or 0) >= config.max_attempts:
        raise ConflictError(
            "job_attempts_exceeded",
            "任务重试次数已达上限",
            {"attempts": job.attempts, "max_attempts": config.max_attempts},
        )

    before = _job_snapshot(job)
    job.status = QUEUED
    job.queued_at = utcnow()
    job.started_at = None
    job.finished_at = None
    job.error_code = None
    job.error_message = None
    job.review_decision = None
    job.reviewed_by = None
    job.reviewed_at = None
    job.review_note = None
    db.flush()
    record_audit(
        db,
        actor.id,
        "job.retry",
        "extraction_job",
        job.id,
        before=before,
        after=_job_snapshot(job),
        request=request,
    )
    db.commit()
    db.refresh(job)
    return job


def reject_job(
    db: Session,
    job: ExtractionJob,
    *,
    actor: User,
    note: str,
    request: Any = None,
) -> ExtractionJob:
    if job.status != REVIEW_PENDING:
        raise ConflictError("job_not_reviewable", "只有待审核任务可以驳回")
    clean_note = (note or "").strip()
    if not clean_note:
        raise BadRequestError("invalid_note", "驳回原因不能为空")

    before = _job_snapshot(job)
    job.status = REJECTED
    job.reviewed_by = actor.id
    job.reviewed_at = utcnow()
    job.review_decision = ReviewDecision.REJECTED.value
    job.review_note = clean_note
    db.flush()
    record_audit(
        db,
        actor.id,
        "job.reject",
        "extraction_job",
        job.id,
        before=before,
        after=_job_snapshot(job),
        request=request,
    )
    db.commit()
    db.refresh(job)
    return job
