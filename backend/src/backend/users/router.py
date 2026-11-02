"""用户管理路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ..schemas.common import Page
from ..schemas.user import (
    UserCreate,
    UserOption,
    UserOptionsResponse,
    UserOut,
    UserUpdate,
)
from ..shared.deps import AdminUser, CurrentUser, DbSession, RequestCtx
from ..shared.enums import Role
from ..shared.pagination import PageParams
from . import service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/options", response_model=UserOptionsResponse, summary="用户选择项")
def list_options(db: DbSession, _current_user: CurrentUser) -> UserOptionsResponse:
    users = service.list_user_options(db)
    return UserOptionsResponse(items=[UserOption.model_validate(user) for user in users])


@router.get("", response_model=Page[UserOut], summary="用户列表")
def list_users(
    db: DbSession,
    _admin: AdminUser,
    params: Annotated[PageParams, Depends()],
    q: str | None = Query(default=None, description="按用户名或显示名搜索"),
    role: Role | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> Page[UserOut]:
    result = service.list_users(
        db,
        page=params.page,
        page_size=params.page_size,
        q=q,
        role=role,
        is_active=is_active,
    )
    return Page[UserOut].model_validate(result)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="创建用户")
def create_user(
    payload: UserCreate,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> UserOut:
    user = service.create_user(
        db,
        username=payload.username,
        display_name=payload.display_name,
        password=payload.password,
        role=payload.role,
        actor_id=admin.id,
        request=ctx,
    )
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut, summary="更新用户")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    admin: AdminUser,
    ctx: RequestCtx,
) -> UserOut:
    user = service.update_user(
        db,
        user_id,
        display_name=payload.display_name,
        role=payload.role,
        is_active=payload.is_active,
        password=payload.password,
        actor_id=admin.id,
        request=ctx,
    )
    return UserOut.model_validate(user)
