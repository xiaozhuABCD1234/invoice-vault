"""类别路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from ..schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryOut,
    CategoryUpdate,
)
from ..shared.deps import AdminUser, CurrentUser, DbSession, RequestCtx
from ..shared.enums import CategoryKind
from . import service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse, summary="类别列表")
def list_categories(
    db: DbSession,
    _current_user: CurrentUser,
    kind: CategoryKind | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> CategoryListResponse:
    categories = service.list_categories(
        db, kind=kind, include_inactive=include_inactive
    )
    return CategoryListResponse(
        items=[CategoryOut.model_validate(category) for category in categories]
    )


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建类别",
)
def create_category(
    payload: CategoryCreate,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> CategoryOut:
    category = service.create_category(
        db,
        name=payload.name,
        kind=payload.kind,
        sort_order=payload.sort_order,
        actor_id=admin.id,
        request=ctx,
    )
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryOut, summary="更新类别")
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> CategoryOut:
    category = service.update_category(
        db,
        category_id,
        name=payload.name,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        actor_id=admin.id,
        request=ctx,
    )
    return CategoryOut.model_validate(category)
