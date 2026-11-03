"""识别引擎配置 Schema（admin 设置页）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .common import APIModel

#: provider 可取值：auto + 具体实现（与 ExtractionProvider 保持一致，测试兜底）
ProviderValue = Literal["auto", "pdf_text", "paddleocr_local", "multimodal_llm", "mock"]
ConcreteProviderValue = Literal["pdf_text", "paddleocr_local", "multimodal_llm", "mock"]
SettingSource = Literal["database", "env", "default"]
RevisionAction = Literal["update", "rollback", "reset"]


def _clean_optional_url(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("必须是字符串")
    text = value.strip()
    if not text:
        return None
    if len(text) > 500:
        raise ValueError("长度不能超过 500 个字符")
    if not text.startswith(("http://", "https://")):
        raise ValueError("必须以 http:// 或 https:// 开头")
    return text


def _clean_optional_text(value: Any, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("必须是字符串")
    text = value.strip()
    if not text:
        return None
    if len(text) > max_length:
        raise ValueError(f"长度不能超过 {max_length} 个字符")
    return text


class ExtractionSettingsUpdate(APIModel):
    """保存识别引擎配置。

    `llm_api_key` 语义特殊：字段缺省 = 保持不变；null 或空串 = 清除；其余 = 覆盖。
    """

    provider: ProviderValue
    auto_chain: list[ConcreteProviderValue] = Field(min_length=1, max_length=4)
    paddleocr_endpoint: str | None = None
    llm_endpoint: str | None = None
    llm_model: str | None = None
    llm_enabled: bool = False
    llm_api_key: str | None = Field(default=None, max_length=500)
    prompt_version: str = Field(min_length=1, max_length=64)
    http_timeout: float = Field(gt=0, le=300)
    max_attempts: int = Field(ge=1, le=10)
    stale_minutes: int = Field(ge=1, le=1440)
    backoff_seconds: float = Field(ge=0, le=3600)

    @field_validator("paddleocr_endpoint", "llm_endpoint", mode="before")
    @classmethod
    def _validate_endpoint(cls, value: Any) -> str | None:
        return _clean_optional_url(value)

    @field_validator("llm_model", mode="before")
    @classmethod
    def _validate_model(cls, value: Any) -> str | None:
        return _clean_optional_text(value, max_length=120)

    @field_validator("prompt_version", mode="before")
    @classmethod
    def _validate_prompt_version(cls, value: Any) -> str:
        cleaned = _clean_optional_text(value, max_length=64)
        if not cleaned:
            raise ValueError("prompt 版本不能为空")
        return cleaned

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def _validate_api_key(cls, value: Any) -> str | None:
        return _clean_optional_text(value, max_length=500)

    @field_validator("auto_chain")
    @classmethod
    def _unique_chain(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("auto 链路不能包含重复的 provider")
        return value


class ExtractionSettingsValues(APIModel):
    provider: str
    auto_chain: list[str]
    paddleocr_endpoint: str | None = None
    llm_endpoint: str | None = None
    llm_model: str | None = None
    llm_enabled: bool = False
    llm_api_key_set: bool = False
    llm_api_key_hint: str | None = None
    prompt_version: str
    http_timeout: float
    max_attempts: int
    stale_minutes: int
    backoff_seconds: float


class ExtractionSettingsOut(APIModel):
    values: ExtractionSettingsValues
    sources: dict[str, SettingSource]
    revision_id: int | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None


class ExtractionSettingsRevisionOut(APIModel):
    id: int
    action: RevisionAction
    actor_name: str | None = None
    created_at: datetime
    values: dict[str, Any] = Field(default_factory=dict)


class ExtractionSettingsHistoryOut(APIModel):
    items: list[ExtractionSettingsRevisionOut] = Field(default_factory=list)


class ExtractionSettingsRollbackRequest(APIModel):
    revision_id: int = Field(ge=1)
