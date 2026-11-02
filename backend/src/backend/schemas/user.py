"""用户 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..shared.enums import Role
from .common import APIModel


class UserOut(APIModel):
    id: int
    username: str
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserOption(APIModel):
    id: int
    display_name: str
    role: Role
    is_active: bool


class UserOptionsResponse(APIModel):
    items: list[UserOption] = Field(default_factory=list)


class UserCreate(APIModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.USER


class UserUpdate(APIModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
