"""通用 Pydantic Schema。"""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    """所有 ORM 响应模型的基类。"""

    model_config = ConfigDict(from_attributes=True)


class Page(APIModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ErrorResponse(APIModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    trace_id: str


class SortSpec(BaseModel):
    key: str
    order: Literal["asc", "desc"] = "asc"


class MessageResponse(APIModel):
    message: str


class HealthResponse(APIModel):
    status: str
    database: str | None = None
