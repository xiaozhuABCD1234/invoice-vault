"""文档路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from ..schemas.common import Page
from ..schemas.document import DocumentDetail, DocumentOut, DocumentUploadResult
from ..schemas.extraction import ExtractionJobOut
from ..shared.deps import AppSettings, CurrentUser, DbSession, AdminUser, RequestCtx
from ..shared.enums import DocumentType
from ..shared.pagination import PageParams
from . import service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentUploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="上传文档",
)
def upload_document(
    response: Response,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    ctx: RequestCtx,
    file: Annotated[UploadFile, File(description="文件内容")],
    doc_type: Annotated[DocumentType, Form()] = DocumentType.INVOICE,
    title: Annotated[str | None, Form()] = None,
) -> DocumentUploadResult:
    file.file.seek(0)
    data = file.file.read()
    document, job, reused = service.create_document(
        db,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
        doc_type=doc_type.value,
        title=title,
        owner=current_user,
        settings=settings,
        request=ctx,
    )
    response.status_code = (
        status.HTTP_200_OK if reused else status.HTTP_201_CREATED
    )
    return DocumentUploadResult(
        document=DocumentOut.model_validate(document),
        extraction_job=ExtractionJobOut.model_validate(job) if job else None,
        reused=reused,
    )


@router.get("", response_model=Page[DocumentOut], summary="文档列表")
def list_documents(
    db: DbSession,
    current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    doc_type: DocumentType | None = Query(default=None),
    q: str | None = Query(default=None, description="按标题/原始文件名/展示名搜索"),
    include_deleted: bool = Query(default=False, description="仅管理员生效"),
) -> Page[DocumentOut]:
    result = service.list_documents(
        db,
        page=params.page,
        page_size=params.page_size,
        doc_type=doc_type,
        q=q,
        include_deleted=include_deleted,
        viewer=current_user,
    )
    return Page[DocumentOut].model_validate(result)


@router.get("/{document_id}", response_model=DocumentDetail, summary="文档详情")
def get_document(
    document_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> DocumentDetail:
    document, jobs = service.get_document_detail(db, document_id, current_user)
    return DocumentDetail(
        document=DocumentOut.model_validate(document),
        version_count=document.version_count,
        extraction_jobs=[ExtractionJobOut.model_validate(job) for job in jobs],
    )


@router.get("/{document_id}/preview", summary="在线预览（inline）")
def preview_document(
    document_id: int,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    ctx: RequestCtx,
    version: str = Query(default="latest"),
    version_id: int | None = Query(default=None, ge=1),
) -> FileResponse:
    return service.preview_document(
        db,
        document_id,
        version=version,
        version_id=version_id,
        viewer=current_user,
        settings=settings,
        request=ctx,
    )


@router.get("/{document_id}/download", summary="下载原文件（仅管理员）")
def download_document(
    document_id: int,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    ctx: RequestCtx,
    version: str = Query(default="latest"),
    version_id: int | None = Query(default=None, ge=1),
) -> FileResponse:
    return service.download_document(
        db,
        document_id,
        version=version,
        version_id=version_id,
        admin=admin,
        settings=settings,
        request=ctx,
    )


@router.post(
    "/{document_id}/versions",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="上传新版本",
)
def upload_version(
    response: Response,
    document_id: int,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    ctx: RequestCtx,
    file: Annotated[UploadFile, File(description="文件内容")],
) -> DocumentOut:
    file.file.seek(0)
    data = file.file.read()
    document, reused = service.upload_version(
        db,
        document_id,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
        actor=current_user,
        settings=settings,
        request=ctx,
    )
    response.status_code = status.HTTP_200_OK if reused else status.HTTP_201_CREATED
    return DocumentOut.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除文档（仅管理员）",
)
def delete_document(
    document_id: int,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> Response:
    service.delete_document(db, document_id, admin=admin, request=ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
