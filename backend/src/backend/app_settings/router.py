"""识别引擎设置路由（仅 admin）。"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from ..schemas.settings import (
    ExtractionSettingsHistoryOut,
    ExtractionSettingsOut,
    ExtractionSettingsRollbackRequest,
    ExtractionSettingsUpdate,
)
from ..shared.deps import AdminUser, AppSettings, DbSession, RequestCtx
from . import service

router = APIRouter(prefix="/admin/settings", tags=["settings"])


@router.get(
    "/extraction",
    response_model=ExtractionSettingsOut,
    summary="读取识别引擎设置（admin）",
)
def get_extraction_settings(
    db: DbSession,
    _admin: AdminUser,
    settings: AppSettings,
) -> ExtractionSettingsOut:
    return service.get_extraction_settings(db, settings)


@router.put(
    "/extraction",
    response_model=ExtractionSettingsOut,
    summary="保存识别引擎设置（admin）",
)
def update_extraction_settings(
    payload: ExtractionSettingsUpdate,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    ctx: RequestCtx,
) -> ExtractionSettingsOut:
    return service.update_extraction_settings(
        db, settings=settings, payload=payload, actor=admin, request=ctx
    )


@router.delete(
    "/extraction",
    response_model=ExtractionSettingsOut,
    summary="恢复默认（删除数据库覆盖层，admin）",
)
def reset_extraction_settings(
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    ctx: RequestCtx,
) -> ExtractionSettingsOut:
    return service.reset_extraction_settings(
        db, settings=settings, actor=admin, request=ctx
    )


@router.get(
    "/extraction/history",
    response_model=ExtractionSettingsHistoryOut,
    summary="设置变更历史（admin）",
)
def list_extraction_settings_history(
    db: DbSession,
    _admin: AdminUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> ExtractionSettingsHistoryOut:
    return service.list_revisions(db, limit=limit)


@router.post(
    "/extraction/rollback",
    response_model=ExtractionSettingsOut,
    status_code=status.HTTP_200_OK,
    summary="回滚到指定版本（admin）",
)
def rollback_extraction_settings(
    payload: ExtractionSettingsRollbackRequest,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    ctx: RequestCtx,
) -> ExtractionSettingsOut:
    return service.rollback_extraction_settings(
        db,
        settings=settings,
        revision_id=payload.revision_id,
        actor=admin,
        request=ctx,
    )
