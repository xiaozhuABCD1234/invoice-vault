"""FastAPI 依赖：数据库会话、当前用户、管理员校验、请求上下文。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..models.user import User
from .config import Settings, get_settings
from .db import get_db
from .enums import Role
from .errors import ForbiddenError, UnauthorizedError
from .security import InvalidTokenError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class RequestContext:
    ip: str | None = None
    user_agent: str | None = None


def get_request_context(request: Request) -> RequestContext:
    ip: str | None = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",", 1)[0].strip()
    elif request.client is not None:
        ip = request.client.host
    return RequestContext(ip=ip, user_agent=request.headers.get("user-agent"))


def get_settings_dep(request: Request) -> Settings:
    """优先使用 app.state.settings，保证测试注入的配置生效。"""

    return getattr(request.app.state, "settings", None) or get_settings()


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("not_authenticated", "未登录或登录已失效")

    try:
        payload = decode_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        raise UnauthorizedError("invalid_token", "登录凭证无效或已过期") from exc

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("invalid_token", "登录凭证无效或已过期")
    if int(payload["ver"]) != user.token_version:
        raise UnauthorizedError("token_revoked", "登录凭证已失效，请重新登录")
    return user


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != Role.ADMIN.value:
        raise ForbiddenError("forbidden", "需要管理员权限")
    return current_user


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
RequestCtx = Annotated[RequestContext, Depends(get_request_context)]
