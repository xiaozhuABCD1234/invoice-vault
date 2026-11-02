"""识别引擎本地配置。

shared/config.py 不包含识别相关配置；这里统一从 IV_ 环境变量读取，
并提供函数入口方便测试覆盖（monkeypatch 环境变量或直接构造 ExtractionConfig）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from ..shared.config import Settings, get_settings
from ..shared.enums import ExtractionProvider

AUTO_PROVIDER = "auto"
DEFAULT_PROVIDER = ExtractionProvider.PDF_TEXT.value
CONCRETE_PROVIDERS: tuple[str, ...] = tuple(provider.value for provider in ExtractionProvider)
ALLOWED_PROVIDERS: tuple[str, ...] = (AUTO_PROVIDER, *CONCRETE_PROVIDERS)
DEFAULT_AUTO_CHAIN: tuple[str, ...] = (
    ExtractionProvider.PDF_TEXT.value,
    ExtractionProvider.PADDLEOCR_LOCAL.value,
    ExtractionProvider.MULTIMODAL_LLM.value,
)
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _TRUE_VALUES


def _parse_float(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    """识别引擎配置快照。测试可直接构造后注入 process_job / worker。"""

    provider: str = DEFAULT_PROVIDER
    auto_chain: tuple[str, ...] = DEFAULT_AUTO_CHAIN
    paddleocr_endpoint: str | None = None
    llm_endpoint: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_enabled: bool = False
    prompt_version: str = "v1"
    http_timeout: float = 10.0
    max_attempts: int = 3
    stale_minutes: int = 15
    backoff_seconds: float = 30.0
    upload_dir: Path = Path("data/uploads")

    @property
    def is_auto(self) -> bool:
        return self.provider == AUTO_PROVIDER

    @property
    def default_job_provider(self) -> str:
        """入队时写入 extraction_jobs.provider 的值（auto/非法值落到 pdf_text）。"""

        if self.provider in CONCRETE_PROVIDERS:
            return self.provider
        return DEFAULT_PROVIDER

    def with_options(self, **changes: Any) -> "ExtractionConfig":
        return replace(self, **changes)


def load_config(
    environ: Mapping[str, str] | None = None,
    settings: Settings | None = None,
) -> ExtractionConfig:
    """从环境变量读取配置；每次调用重新读取，便于测试 monkeypatch。"""

    env = os.environ if environ is None else environ
    raw_provider = (env.get("IV_EXTRACTION_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    provider = raw_provider if raw_provider in ALLOWED_PROVIDERS else DEFAULT_PROVIDER

    raw_chain = env.get("IV_EXTRACTION_AUTO_CHAIN")
    if raw_chain:
        chain = tuple(
            item.strip().lower()
            for item in raw_chain.split(",")
            if item.strip().lower() in CONCRETE_PROVIDERS
        )
        auto_chain = chain or DEFAULT_AUTO_CHAIN
    else:
        auto_chain = DEFAULT_AUTO_CHAIN

    current = settings or get_settings()
    return ExtractionConfig(
        provider=provider,
        auto_chain=auto_chain,
        paddleocr_endpoint=_clean(env.get("IV_PADDLEOCR_ENDPOINT")),
        llm_endpoint=_clean(env.get("IV_LLM_ENDPOINT")),
        llm_api_key=_clean(env.get("IV_LLM_API_KEY")),
        llm_model=_clean(env.get("IV_LLM_MODEL")),
        llm_enabled=_parse_bool(env.get("IV_LLM_ENABLED"), default=False),
        prompt_version=_clean(env.get("IV_EXTRACTION_PROMPT_VERSION")) or "v1",
        http_timeout=_parse_float(env.get("IV_EXTRACTION_HTTP_TIMEOUT"), 10.0),
        max_attempts=_parse_int(env.get("IV_EXTRACTION_MAX_ATTEMPTS"), 3),
        stale_minutes=_parse_int(env.get("IV_EXTRACTION_STALE_MINUTES"), 15),
        backoff_seconds=_parse_float(env.get("IV_EXTRACTION_BACKOFF_SECONDS"), 30.0),
        upload_dir=Path(current.upload_dir),
    )
