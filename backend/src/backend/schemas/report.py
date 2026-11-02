"""报表模板与导出 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from ..shared.enums import ExportStatus
from .common import APIModel, SortSpec


class ColumnSpec(APIModel):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    width: int | None = Field(default=None, ge=1)
    format: str = Field(default="text", max_length=32)


class ReportTemplateOut(APIModel):
    id: int
    name: str
    columns: list[ColumnSpec] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: list[SortSpec] = Field(default_factory=list)
    created_by: int | None = None
    is_shared: bool = False
    created_at: datetime


class ReportTemplateCreate(APIModel):
    name: str = Field(min_length=1, max_length=128)
    columns: list[ColumnSpec] = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: list[SortSpec] = Field(default_factory=list)
    is_shared: bool = False


class ReportTemplateUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    columns: list[ColumnSpec] | None = Field(default=None, min_length=1)
    filters: dict[str, Any] | None = None
    sort: list[SortSpec] | None = None
    is_shared: bool | None = None


class ExportCreate(APIModel):
    template_id: int | None = Field(default=None, ge=0)
    columns: list[ColumnSpec] | None = None
    filters: dict[str, Any] | None = None
    sort: list[SortSpec] | None = None


class ExportJobOut(APIModel):
    id: int
    template_id: int | None = None
    status: ExportStatus
    file_document_id: int | None = None
    file_name: str | None = None
    error_message: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    download_url: str | None = None


class ExportResponse(APIModel):
    export: ExportJobOut
