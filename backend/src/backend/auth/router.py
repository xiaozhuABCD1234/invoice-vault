"""认证路由：登录、刷新、登出、当前用户。"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from ..schemas.auth import LoginRequest, TokenResponse
from ..schemas.user import UserOut
from ..shared.audit import record_audit
from ..shared.config import Settings
from ..shared.deps import AppSettings, CurrentUser, DbSession, RequestCtx
from . import service


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=settings.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse, summary="登录")
def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    ctx: RequestCtx,
) -> TokenResponse:
    user = service.authenticate(
        db, payload.username, payload.password, settings, request=ctx
    )
    tokens = service.issue_tokens(db, user, settings, request=ctx)
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=user,
    )


@router.post("/auth/refresh", response_model=TokenResponse, summary="刷新访问令牌")
def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    ctx: RequestCtx,
) -> TokenResponse:
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    tokens = service.rotate_refresh_token(db, raw_refresh, settings, request=ctx)
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=tokens.user,
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="登出",
)
def logout(
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    current_user: CurrentUser,
    ctx: RequestCtx,
) -> Response:
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    service.logout(db, raw_refresh)
    record_audit(
        db,
        current_user.id,
        "logout",
        "user",
        current_user.id,
        request=ctx,
    )
    db.commit()
    _clear_refresh_cookie(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut, summary="当前登录用户")
def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)
