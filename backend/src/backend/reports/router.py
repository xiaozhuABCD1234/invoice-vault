"""报表模板与导出路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse

from ..schemas.common import Page
from ..schemas.report import (
    ExportCreate,
    ExportJobOut,
    ExportResponse,
    ReportTemplateCreate,
    ReportTemplateOut,
    ReportTemplateUpdate,
)
from ..shared.deps import AppSettings, CurrentUser, DbSession, RequestCtx
from ..shared.pagination import PageParams
from . import service
from .schemas import ReportTemplateListResponse

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/report-templates",
    response_model=ReportTemplateListResponse,
    summary="报表模板列表",
)
def list_report_templates(
    db: DbSession,
    current_user: CurrentUser,
) -> ReportTemplateListResponse:
    return ReportTemplateListResponse(items=service.list_templates(db, current_user))


@router.post(
    "/report-templates",
    response_model=ReportTemplateOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建报表模板",
)
def create_report_template(
    payload: ReportTemplateCreate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> ReportTemplateOut:
    template = service.create_template(
        db, user=current_user, payload=payload, request=ctx
    )
    return ReportTemplateOut.model_validate(template)


@router.patch(
    "/report-templates/{template_id}",
    response_model=ReportTemplateOut,
    summary="更新报表模板",
)
def update_report_template(
    template_id: int,
    payload: ReportTemplateUpdate,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> ReportTemplateOut:
    template = service.update_template(
        db, template_id, user=current_user, payload=payload, request=ctx
    )
    return ReportTemplateOut.model_validate(template)


@router.delete(
    "/report-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="删除报表模板",
)
def delete_report_template(
    template_id: int,
    db: DbSession,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> Response:
    service.delete_template(db, template_id, user=current_user, request=ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/exports",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建导出任务",
)
def create_export(
    payload: ExportCreate,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    ctx: RequestCtx,
) -> ExportResponse:
    job = service.create_export(
        db, user=current_user, payload=payload, settings=settings, request=ctx
    )
    return ExportResponse(export=service.export_job_out(job, settings))


@router.get(
    "/exports",
    response_model=Page[ExportJobOut],
    summary="导出任务列表",
)
def list_exports(
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    params: Annotated[PageParams, Depends()],
) -> Page[ExportJobOut]:
    result = service.list_exports(
        db,
        current_user,
        page=params.page,
        page_size=params.page_size,
    )
    return Page[ExportJobOut](
        items=[service.export_job_out(job, settings) for job in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/exports/{export_id}/download",
    summary="下载导出文件",
    response_class=FileResponse,
)
def download_export(
    export_id: int,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    ctx: RequestCtx,
) -> FileResponse:
    job, path = service.prepare_download(
        db, export_id, user=current_user, settings=settings, request=ctx
    )
    return FileResponse(
        path,
        media_type=XLSX_MEDIA_TYPE,
        filename=service.download_filename(job),
    )


@router.get(
    "/exports/{export_id}",
    response_model=ExportJobOut,
    summary="导出任务详情",
)
def get_export(
    export_id: int,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> ExportJobOut:
    job = service.get_export_for_user(db, export_id, current_user)
    return service.export_job_out(job, settings)
