"""文档与文件版本 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import Field

from ..shared.enums import DocumentType
from .common import APIModel

if TYPE_CHECKING:
    from .extraction import ExtractionJobOut


class DocumentVersionOut(APIModel):
    id: int
    version_no: int
    original_name: str
    display_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    is_latest: bool


class DocumentOut(APIModel):
    id: int
    doc_type: DocumentType
    title: str | None = None
    owner_user_id: int | None = None
    owner_name: str | None = None
    current_version: DocumentVersionOut | None = None
    created_at: datetime
    deleted_at: datetime | None = None


class DocumentDetail(APIModel):
    document: DocumentOut
    version_count: int = 0
    extraction_jobs: list["ExtractionJobOut"] = Field(default_factory=list)


class DocumentUploadResult(APIModel):
    document: DocumentOut
    extraction_job: Optional["ExtractionJobOut"] = None
    reused: bool = False
