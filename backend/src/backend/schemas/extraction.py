"""抽取任务 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

from ..shared.enums import DocumentType, ExtractionProvider, ExtractionStatus, ReviewDecision
from .common import APIModel

if TYPE_CHECKING:
    from .document import DocumentOut


class ExtractionValidation(APIModel):
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)


class ExtractionJobOut(APIModel):
    id: int
    document_id: int
    document_name: str | None = None
    document_doc_type: DocumentType | None = None
    provider: ExtractionProvider
    model: str | None = None
    prompt_version: str | None = None
    status: ExtractionStatus
    attempts: int = 0
    confidence: float | None = None
    parsed: dict[str, Any] | None = None
    validation: ExtractionValidation | None = None
    error_code: str | None = None
    error_message: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_decision: ReviewDecision | None = None
    review_note: str | None = None


class ExtractionJobDetail(APIModel):
    job: ExtractionJobOut
    document: Optional["DocumentOut"] = None
    diff: dict[str, Any] | None = None


class ExtractionRejectRequest(APIModel):
    note: str = Field(min_length=1, max_length=2000)
