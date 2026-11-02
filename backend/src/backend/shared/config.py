"""应用配置。

环境变量统一使用 IV_ 前缀，默认从 backend/.env 读取。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/src/backend/shared/config.py -> backend/
BASE_DIR: Path = Path(__file__).resolve().parents[3]
ENV_FILE: Path = BASE_DIR / ".env"


class Settings(BaseSettings):
    """运行期配置。测试可以直接构造该对象注入 create_app。"""

    model_config = SettingsConfigDict(
        env_prefix="IV_",
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "发票管理系统 API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: Path = Path("data/uploads")
    sql_echo: bool = False

    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=15, ge=1)
    refresh_token_days: int = Field(default=7, ge=1)

    cookie_secure: bool = False
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_path: str = "/api/v1/auth"

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    lockout_threshold: int = Field(default=5, ge=1)
    lockout_minutes: int = Field(default=15, ge=1)
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1)

    trace_header: str = "X-Trace-Id"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> Any:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:  # pragma: no cover - 配置错误
                    raise ValueError("IV_CORS_ORIGINS 必须是 JSON 数组或逗号分隔字符串") from exc
                if not isinstance(parsed, list):
                    raise ValueError("IV_CORS_ORIGINS 必须是数组")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @property
    def access_token_seconds(self) -> int:
        return self.access_token_minutes * 60

    @property
    def refresh_token_seconds(self) -> int:
        return self.refresh_token_days * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    """返回进程级配置缓存。测试可构造 Settings 后直接传入 create_app。"""

    return Settings()
