"""发票类别 Schema。"""

from __future__ import annotations

from pydantic import Field

from ..shared.enums import CategoryKind
from .common import APIModel


class CategoryOut(APIModel):
    id: int
    name: str
    kind: CategoryKind
    sort_order: int
    is_active: bool


class CategoryCreate(APIModel):
    name: str = Field(min_length=1, max_length=64)
    kind: CategoryKind
    sort_order: int | None = Field(default=None, ge=0)


class CategoryUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CategoryListResponse(APIModel):
    items: list[CategoryOut] = Field(default_factory=list)
