"""识别引擎本地配置。

shared/config.py 不包含识别相关配置；这里统一从 IV_ 环境变量读取，
并提供函数入口方便测试覆盖（monkeypatch 环境变量或直接构造 ExtractionConfig）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from ..shared.config import ENV_FILE, Settings, get_settings
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

#: 配置项逻辑名（DB / 前端表单使用的键）与对应环境变量
SETTING_ENV: dict[str, str] = {
    "provider": "IV_EXTRACTION_PROVIDER",
    "auto_chain": "IV_EXTRACTION_AUTO_CHAIN",
    "paddleocr_endpoint": "IV_PADDLEOCR_ENDPOINT",
    "llm_endpoint": "IV_LLM_ENDPOINT",
    "llm_api_key": "IV_LLM_API_KEY",
    "llm_model": "IV_LLM_MODEL",
    "llm_enabled": "IV_LLM_ENABLED",
    "prompt_version": "IV_EXTRACTION_PROMPT_VERSION",
    "http_timeout": "IV_EXTRACTION_HTTP_TIMEOUT",
    "max_attempts": "IV_EXTRACTION_MAX_ATTEMPTS",
    "stale_minutes": "IV_EXTRACTION_STALE_MINUTES",
    "backoff_seconds": "IV_EXTRACTION_BACKOFF_SECONDS",
}

#: 全部可配置项，顺序与前端表单一致
SETTING_KEYS: tuple[str, ...] = tuple(SETTING_ENV)


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


def _dotenv_values() -> dict[str, str]:
    """读取 backend/.env（与 Settings 使用同一文件），让复制 .env.example 后直接生效。

    python-dotenv 由 pydantic-settings 依赖提供，无需新增依赖；文件不存在或解析失败
    时静默跳过，保持环境变量优先。
    """

    if not ENV_FILE.is_file():
        return {}
    try:
        from dotenv import dotenv_values
    except ImportError:  # pragma: no cover - pydantic-settings 已依赖 python-dotenv
        return {}
    try:
        values = dotenv_values(ENV_FILE)
    except (OSError, ValueError):  # 配置格式错误时不要阻断进程启动
        return {}
    return {key: value for key, value in values.items() if value is not None}


def _environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    """环境变量优先；未显式传入 mapping 时用 backend/.env 补齐缺失项。"""

    if environ is not None:
        return dict(environ)
    env: dict[str, str] = dict(os.environ)
    for key, value in _dotenv_values().items():
        env.setdefault(key, value)
    return env


def base_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """进程环境 + backend/.env（进程环境优先）。用于判断某个配置项的来源。"""

    return dict(_environment(environ))


def _render_override(value: Any) -> str:
    """把数据库里的 JSON 值渲染成等价字符串；None 渲染为空串（= 显式清空）。"""

    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return str(value)


def _apply_overrides(env: dict[str, str], overrides: Mapping[str, Any]) -> None:
    """数据库覆盖层优先于进程环境与 .env；空值同样覆盖（表示管理员清空）。"""

    for name, value in overrides.items():
        env_name = SETTING_ENV.get(name)
        if env_name is not None:
            env[env_name] = _render_override(value)


def load_config(
    environ: Mapping[str, str] | None = None,
    settings: Settings | None = None,
    *,
    overrides: Mapping[str, Any] | None = None,
) -> ExtractionConfig:
    """读取配置：默认值 < backend/.env < 进程环境 < overrides（数据库覆盖层）。

    每次调用重新读取，便于测试 monkeypatch；overrides 的键见 SETTING_KEYS。
    """

    env = _environment(environ)
    if overrides:
        _apply_overrides(env, overrides)
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
