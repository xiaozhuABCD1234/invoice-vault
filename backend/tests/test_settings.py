"""Settings 安全校验：JWT 密钥强度。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.shared.config import Settings


def test_default_and_test_secrets_meet_min_length(settings):
    default_secret = Settings.model_fields["jwt_secret"].default
    assert isinstance(default_secret, str)
    assert len(default_secret) >= 32
    assert len(settings.jwt_secret) >= 32

    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    secret_line = next(
        line
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line.startswith("IV_JWT_SECRET=")
    )
    assert len(secret_line.split("=", 1)[1]) >= 32


def test_jwt_secret_shorter_than_32_chars_is_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(jwt_secret="too-short-secret")

    message = str(exc_info.value)
    assert "IV_JWT_SECRET" in message
    assert "至少 32 个字符" in message


def test_jwt_secret_exactly_32_chars_is_accepted():
    secret = "x" * 32
    assert Settings(jwt_secret=secret).jwt_secret == secret
