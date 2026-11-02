"""文档上传、版本、列表、预览、下载与软删除。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from ..extraction.config import ExtractionConfig, load_config
from ..extraction.service import enqueue_job, latest_job_for_document
from ..models.document import Document, DocumentVersion
from ..models.extraction import ExtractionJob
from ..models.user import User
from ..shared.audit import record_audit
from ..shared.db import utcnow
from ..shared.enums import DocumentType, Role
from ..shared.errors import BadRequestError, ForbiddenError, NotFoundError
from ..shared.pagination import paginate
from ..shared.storage import resolve_path, sanitize_filename, save_bytes
from . import files

DISPLAY_PREFIX = "待识别"
LATEST = "latest"
_DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def is_admin(user: User) -> bool:
    return user.role == Role.ADMIN.value


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _document_options(*, versions: bool = False, jobs: bool = False) -> tuple[Any, ...]:
    options: list[Any] = [
        selectinload(Document.current_version),
        selectinload(Document.owner),
    ]
    if versions:
        options.append(selectinload(Document.versions))
    if jobs:
        options.append(selectinload(Document.extraction_jobs))
    return tuple(options)


def _clean_title(title: str | None) -> str | None:
    if title is None:
        return None
    cleaned = title.strip()
    if not cleaned:
        return None
    if len(cleaned) > 255:
        raise BadRequestError("invalid_title", "标题不能超过 255 个字符")
    return cleaned


def _find_version_by_sha(db: Session, sha256: str) -> DocumentVersion | None:
    return db.scalar(
        select(DocumentVersion)
        .options(selectinload(DocumentVersion.document))
        .where(DocumentVersion.sha256 == sha256)
        .order_by(DocumentVersion.id.desc())
        .limit(1)
    )


def _snapshot(
    document: Document,
    version: DocumentVersion | None = None,
    job: ExtractionJob | None = None,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "document_id": document.id,
        "doc_type": document.doc_type,
        "title": document.title,
        "owner_user_id": document.owner_user_id,
    }
    if version is not None:
        snapshot["version"] = {
            "id": version.id,
            "version_no": version.version_no,
            "sha256": version.sha256,
            "original_name": version.original_name,
            "display_name": version.display_name,
            "mime_type": version.mime_type,
            "size_bytes": version.size_bytes,
        }
    if job is not None:
        snapshot["extraction_job_id"] = job.id
    return snapshot


def _display_name(now: Any, extension: str) -> str:
    stamp = now.strftime("%Y%m%d%H%M%S")
    return sanitize_filename(f"{DISPLAY_PREFIX}-{stamp}.{extension}")


def create_document(
    db: Session,
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    doc_type: str,
    title: str | None,
    owner: User,
    settings: Any,
    config: ExtractionConfig | None = None,
    request: Any = None,
) -> tuple[Document, ExtractionJob | None, bool]:
    """上传文档；sha256 已存在时复用现有文档/版本。返回 (document, job, reused)。"""

    clean_title = _clean_title(title)
    detected = files.validate_upload(
        data,
        filename=filename,
        content_type=content_type,
        max_bytes=settings.max_upload_bytes,
    )
    saved = save_bytes(data, detected.extension, settings=settings)
    cfg = config or load_config(settings=settings)

    existing = _find_version_by_sha(db, saved["sha256"])
    if existing is not None:
        document = existing.document
        job = latest_job_for_document(db, document.id)
        if (
            job is None
            and _enum_value(doc_type) == DocumentType.INVOICE.value
            and document.doc_type == DocumentType.INVOICE.value
        ):
            job = enqueue_job(db, document, provider=cfg.default_job_provider)
        record_audit(
            db,
            owner.id,
            "document.create",
            "document",
            document.id,
            after={
                "reused": True,
                "sha256": saved["sha256"],
                "doc_type": document.doc_type,
                "extraction_job_id": job.id if job is not None else None,
            },
            request=request,
        )
        db.commit()
        db.refresh(document)
        return document, job, True

    now = utcnow()
    document = Document(
        doc_type=_enum_value(doc_type),
        title=clean_title,
        owner_user_id=owner.id,
        created_by=owner.id,
        created_at=now,
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(
        document_id=document.id,
        version_no=1,
        storage_key=saved["storage_key"],
        original_name=sanitize_filename(filename or f"file.{detected.extension}"),
        display_name=_display_name(now, detected.extension),
        mime_type=detected.mime_type,
        size_bytes=saved["size_bytes"],
        sha256=saved["sha256"],
        created_by=owner.id,
        created_at=now,
        is_latest=True,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id

    job = None
    if _enum_value(doc_type) == DocumentType.INVOICE.value:
        job = enqueue_job(db, document, provider=cfg.default_job_provider)

    record_audit(
        db,
        owner.id,
        "document.create",
        "document",
        document.id,
        after=_snapshot(document, version, job),
        request=request,
    )
    db.commit()
    db.refresh(document)
    db.refresh(version)
    return document, job, False


def list_documents(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    doc_type: Any = None,
    q: str | None = None,
    include_deleted: bool = False,
    viewer: User | None = None,
) -> dict[str, Any]:
    stmt = select(Document).options(*_document_options())
    show_deleted = bool(include_deleted and viewer is not None and is_admin(viewer))
    if not show_deleted:
        stmt = stmt.where(Document.deleted_at.is_(None))
    if doc_type is not None:
        stmt = stmt.where(Document.doc_type == _enum_value(doc_type))
    search = (q or "").strip()
    if search:
        term = f"%{search}%"
        matched_versions = select(DocumentVersion.id).where(
            or_(
                DocumentVersion.original_name.ilike(term),
                DocumentVersion.display_name.ilike(term),
            )
        )
        stmt = stmt.where(
            or_(
                Document.title.ilike(term),
                Document.current_version_id.in_(matched_versions),
            )
        )
    stmt = stmt.order_by(Document.created_at.desc(), Document.id.desc())
    return paginate(db, stmt, page, page_size)


def get_document_or_404(
    db: Session,
    document_id: int,
    *,
    viewer: User | None = None,
    versions: bool = False,
    jobs: bool = False,
) -> Document:
    document = db.scalar(
        select(Document)
        .options(*_document_options(versions=versions, jobs=jobs))
        .where(Document.id == document_id)
    )
    if document is None:
        raise NotFoundError("document_not_found", "文档不存在")
    if document.deleted_at is not None and (viewer is None or not is_admin(viewer)):
        raise NotFoundError("document_not_found", "文档不存在")
    return document


def get_document_detail(
    db: Session,
    document_id: int,
    viewer: User,
) -> tuple[Document, list[ExtractionJob]]:
    document = get_document_or_404(
        db, document_id, viewer=viewer, versions=True, jobs=True
    )
    jobs = sorted(
        document.extraction_jobs,
        key=lambda job: (job.queued_at, job.id),
        reverse=True,
    )
    return document, jobs


def _latest_version(db: Session, document: Document) -> DocumentVersion | None:
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


def resolve_version(
    db: Session,
    document: Document,
    *,
    version: str | None,
    version_id: int | None,
    viewer: User,
) -> DocumentVersion:
    """user 只能看最新版；admin 可通过 version_id 指定任意版本。"""

    if version_id is not None:
        if not is_admin(viewer):
            raise ForbiddenError("forbidden", "只有管理员可以查看历史版本")
        target = db.get(DocumentVersion, version_id)
        if target is None or target.document_id != document.id:
            raise NotFoundError("document_version_not_found", "文档版本不存在")
        return target

    value = (version or LATEST).strip().lower()
    if value != LATEST:
        raise BadRequestError("invalid_version", "仅支持 version=latest，历史版本请使用 version_id")

    latest = _latest_version(db, document)
    if latest is None:
        raise NotFoundError("document_version_not_found", "文档还没有版本")
    if not is_admin(viewer) and not latest.is_latest:
        latest = db.scalar(
            select(DocumentVersion)
            .where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.is_latest.is_(True),
            )
            .order_by(DocumentVersion.version_no.desc())
            .limit(1)
        )
        if latest is None:
            raise NotFoundError("document_version_not_found", "文档还没有版本")
    return latest


def _version_path(version: DocumentVersion, settings: Any) -> Path:
    try:
        path = resolve_path(version.storage_key, settings=settings)
    except ValueError as exc:
        raise NotFoundError("file_not_found", "文件不存在") from exc
    if not path.is_file():
        raise NotFoundError("file_not_found", "文件不存在")
    return path


def _actual_extension(version: DocumentVersion) -> str:
    suffix = Path(version.storage_key or "").suffix.lstrip(".").lower()
    if suffix in _DOCUMENT_EXTENSIONS:
        return "jpg" if suffix == "jpeg" else suffix
    by_mime = files.extension_for_mime(version.mime_type)
    if by_mime:
        return by_mime
    return suffix or "bin"


def _media_type(version: DocumentVersion) -> str:
    mime = (version.mime_type or "").strip().lower()
    if mime in files.ALLOWED_MIMES:
        return mime
    return files.mime_for_extension(_actual_extension(version)) or "application/octet-stream"


def download_filename(version: DocumentVersion) -> str:
    """展示名补齐/纠正为当前版本实际扩展名。"""

    display = sanitize_filename(
        version.display_name or version.original_name or f"document-{version.id}"
    )
    correct = _actual_extension(version)
    suffix = Path(display).suffix.lower().lstrip(".")
    if suffix in _DOCUMENT_EXTENSIONS and suffix != correct:
        display = display[: -(len(suffix) + 1)]
    if not display.lower().endswith("." + correct):
        display = f"{display}.{correct}"
    return sanitize_filename(display, max_length=150)


def _content_disposition(filename: str, *, inline: bool) -> str:
    disposition = "inline" if inline else "attachment"
    fallback = _INVALID_FILENAME_CHARS.sub("_", filename)
    fallback = re.sub(r"[^A-Za-z0-9._-]+", "_", fallback).strip("._") or "download"
    encoded = quote(filename, safe="")
    return f'{disposition}; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'


def _file_response(
    version: DocumentVersion,
    settings: Any,
    *,
    inline: bool,
) -> FileResponse:
    path = _version_path(version, settings)
    filename = download_filename(version)
    return FileResponse(
        path,
        media_type=_media_type(version),
        headers={"Content-Disposition": _content_disposition(filename, inline=inline)},
    )


def _audit_file_action(
    db: Session,
    *,
    actor: User,
    action: str,
    document: Document,
    version: DocumentVersion,
    request: Any,
) -> None:
    record_audit(
        db,
        actor.id,
        action,
        "document",
        document.id,
        after={
            "version_id": version.id,
            "version_no": version.version_no,
            "display_name": version.display_name,
            "mime_type": version.mime_type,
        },
        request=request,
    )
    db.commit()


def preview_document(
    db: Session,
    document_id: int,
    *,
    version: str | None,
    version_id: int | None,
    viewer: User,
    settings: Any,
    request: Any = None,
) -> FileResponse:
    document = get_document_or_404(db, document_id, viewer=viewer)
    target = resolve_version(
        db, document, version=version, version_id=version_id, viewer=viewer
    )
    response = _file_response(target, settings, inline=True)
    _audit_file_action(
        db,
        actor=viewer,
        action="document.preview",
        document=document,
        version=target,
        request=request,
    )
    return response


def download_document(
    db: Session,
    document_id: int,
    *,
    version: str | None,
    version_id: int | None,
    admin: User,
    settings: Any,
    request: Any = None,
) -> FileResponse:
    document = get_document_or_404(db, document_id, viewer=admin)
    target = resolve_version(
        db, document, version=version, version_id=version_id, viewer=admin
    )
    response = _file_response(target, settings, inline=False)
    _audit_file_action(
        db,
        actor=admin,
        action="document.download",
        document=document,
        version=target,
        request=request,
    )
    return response


def upload_version(
    db: Session,
    document_id: int,
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    actor: User,
    settings: Any,
    request: Any = None,
) -> tuple[Document, bool]:
    """新增版本；sha256 已存在则复用已有版本/文档，返回 (document, reused)。"""

    document = get_document_or_404(db, document_id, viewer=actor)
    detected = files.validate_upload(
        data,
        filename=filename,
        content_type=content_type,
        max_bytes=settings.max_upload_bytes,
    )
    saved = save_bytes(data, detected.extension, settings=settings)

    existing = _find_version_by_sha(db, saved["sha256"])
    if existing is not None:
        return existing.document, True

    max_no = db.scalar(
        select(func.max(DocumentVersion.version_no)).where(
            DocumentVersion.document_id == document.id
        )
    )
    now = utcnow()
    db.execute(
        update(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .values(is_latest=False)
        .execution_options(synchronize_session=False)
    )
    version = DocumentVersion(
        document_id=document.id,
        version_no=int(max_no or 0) + 1,
        storage_key=saved["storage_key"],
        original_name=sanitize_filename(filename or f"file.{detected.extension}"),
        display_name=_display_name(now, detected.extension),
        mime_type=detected.mime_type,
        size_bytes=saved["size_bytes"],
        sha256=saved["sha256"],
        created_by=actor.id,
        created_at=now,
        is_latest=True,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id

    record_audit(
        db,
        actor.id,
        "document.upload_version",
        "document",
        document.id,
        after=_snapshot(document, version),
        request=request,
    )
    db.commit()
    db.refresh(document)
    db.refresh(version)
    return document, False


def delete_document(
    db: Session,
    document_id: int,
    *,
    admin: User,
    request: Any = None,
) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError("document_not_found", "文档不存在")
    before = {
        "deleted_at": document.deleted_at.isoformat() if document.deleted_at else None
    }
    if document.deleted_at is None:
        document.deleted_at = utcnow()
    db.flush()
    record_audit(
        db,
        admin.id,
        "document.delete",
        "document",
        document.id,
        before=before,
        after={
            "deleted_at": document.deleted_at.isoformat()
            if document.deleted_at
            else None
        },
        request=request,
    )
    db.commit()
    db.refresh(document)
    return document
