"""登录、refresh token 轮换与登出。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models.user import RefreshToken, User
from ..shared.audit import record_audit
from ..shared.config import Settings
from ..shared.db import utcnow
from ..shared.errors import AppError, ForbiddenError, UnauthorizedError
from ..shared.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)


@dataclass(slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


def _locked_error(locked_until: datetime) -> AppError:
    return AppError(
        "account_locked",
        "账号已锁定，请稍后再试",
        423,
        {"locked_until": locked_until.isoformat()},
    )


def authenticate(
    db: Session,
    username: str,
    password: str,
    settings: Settings,
    *,
    request: Any = None,
) -> User:
    """校验用户名密码，处理失败计数与锁定，并写登录审计。"""

    normalized = username.strip()
    user = db.scalar(select(User).where(User.username == normalized))
    if user is None:
        raise UnauthorizedError("invalid_credentials", "用户名或密码错误")

    now = utcnow()
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until > now:
            raise _locked_error(locked_until)
        user.locked_until = None
        user.failed_attempts = 0

    if not verify_password(password, user.password_hash):
        user.failed_attempts = int(user.failed_attempts or 0) + 1
        if user.failed_attempts >= settings.lockout_threshold:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            db.commit()
            raise _locked_error(user.locked_until)
        db.commit()
        raise UnauthorizedError("invalid_credentials", "用户名或密码错误")

    if not user.is_active:
        raise ForbiddenError("account_disabled", "账号已被禁用")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    record_audit(
        db,
        user.id,
        "login",
        "user",
        user.id,
        after={"username": user.username},
        request=request,
    )
    db.commit()
    db.refresh(user)
    return user


def issue_tokens(
    db: Session,
    user: User,
    settings: Settings,
    *,
    request: Any = None,
) -> IssuedTokens:
    """签发 access token 与 refresh token，refresh 只存哈希。"""

    access_token = create_access_token(user.id, user.token_version, settings)
    raw_refresh = generate_refresh_token()
    now = utcnow()
    ip = getattr(request, "ip", None)
    user_agent = getattr(request, "user_agent", None)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=now + timedelta(days=settings.refresh_token_days),
            token_version=user.token_version,
            user_agent=(user_agent or None),
            ip=(ip or None),
            created_at=now,
        )
    )
    db.commit()
    return IssuedTokens(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_seconds,
        user=user,
    )


def rotate_refresh_token(
    db: Session,
    raw_refresh: str | None,
    settings: Settings,
    *,
    request: Any = None,
) -> IssuedTokens:
    """校验并轮换 refresh token；旧 token 立即吊销。"""

    if not raw_refresh:
        raise UnauthorizedError("missing_refresh_token", "缺少刷新令牌")

    token_hash = hash_refresh_token(raw_refresh)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is None or stored.revoked_at is not None:
        raise UnauthorizedError("invalid_refresh_token", "刷新令牌无效或已失效")

    now = utcnow()
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise UnauthorizedError("invalid_refresh_token", "刷新令牌已过期")

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("invalid_refresh_token", "刷新令牌无效或已失效")
    if user.token_version != stored.token_version:
        raise UnauthorizedError("token_revoked", "登录凭证已失效，请重新登录")

    stored.revoked_at = now
    access_token = create_access_token(user.id, user.token_version, settings)
    raw_new_refresh = generate_refresh_token()
    user_agent = getattr(request, "user_agent", None)
    ip = getattr(request, "ip", None)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_new_refresh),
            expires_at=now + timedelta(days=settings.refresh_token_days),
            token_version=user.token_version,
            user_agent=(user_agent or None),
            ip=(ip or None),
            created_at=now,
        )
    )
    db.commit()
    return IssuedTokens(
        access_token=access_token,
        refresh_token=raw_new_refresh,
        expires_in=settings.access_token_seconds,
        user=user,
    )


def logout(db: Session, raw_refresh: str | None) -> None:
    """吊销当前 refresh token；不存在也视为成功。"""

    if not raw_refresh:
        return
    token_hash = hash_refresh_token(raw_refresh)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()


def revoke_user_refresh_tokens(db: Session, user_id: int, *, now: datetime | None = None) -> None:
    """吊销用户全部未失效 refresh token（改密 / 禁用时调用）。"""

    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now or utcnow())
    )


__all__ = [
    "IssuedTokens",
    "authenticate",
    "issue_tokens",
    "logout",
    "revoke_user_refresh_tokens",
    "rotate_refresh_token",
]
