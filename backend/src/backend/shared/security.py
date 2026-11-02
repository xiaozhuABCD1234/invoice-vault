"""密码哈希、JWT 与 refresh token 工具。"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import Settings

_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(ValueError):
    """JWT 无效、过期或类型不符。"""


def hash_password(password: str) -> str:
    """使用 Argon2id 生成密码哈希。"""

    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def create_access_token(
    user_id: int,
    token_version: int,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> str:
    """签发 15 分钟 access token（HS256）。"""

    issued_at = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ver": token_version,
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """解码并校验 access token。"""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type", "ver"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("无效的访问令牌") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("令牌类型不正确")
    try:
        payload["sub"] = int(payload["sub"])
        payload["ver"] = int(payload["ver"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("令牌载荷不完整") from exc
    return payload


def generate_refresh_token() -> str:
    """生成不透明 refresh token（只在 Cookie 中传递）。"""

    return "rt_" + secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    """refresh token 仅存 sha256 哈希。"""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
