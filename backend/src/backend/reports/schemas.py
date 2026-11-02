"""本领域补充响应 Schema（复用 backend.schemas 中已有的模板 Schema）。"""

from __future__ import annotations

from pydantic import Field

from ..schemas.common import APIModel
from ..schemas.report import ReportTemplateOut


class ReportTemplateListResponse(APIModel):
    items: list[ReportTemplateOut] = Field(default_factory=list)
