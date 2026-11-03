"""命令行工具的输入校验。"""

from __future__ import annotations

import pytest

from backend import cli


def test_create_admin_rejects_short_password(monkeypatch, capsys) -> None:
    def _unexpected() -> None:  # pragma: no cover - 不应执行
        pytest.fail("短密码不应打开数据库")

    monkeypatch.setattr(cli, "_open_session", _unexpected)
    code = cli.main(["create-admin", "--username", "admin", "--password", "short"])
    assert code == 2
    assert "密码至少 8 位" in capsys.readouterr().err


def test_create_admin_requires_username(capsys) -> None:
    code = cli.main(["create-admin", "--username", "  ", "--password", "long-enough"])
    assert code == 2
    assert "用户名不能为空" in capsys.readouterr().err
