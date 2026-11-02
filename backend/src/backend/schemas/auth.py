"""认证相关 Schema。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import APIModel
from .user import UserOut


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(APIModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut
