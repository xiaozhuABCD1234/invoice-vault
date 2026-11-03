"""命令行工具的输入校验。"""

from __future__ import annotations

from sqlalchemy import select

from backend import cli
from backend.models.user import User
from backend.shared.security import verify_password


def test_create_admin_accepts_short_password(
    app, settings, monkeypatch, capsys
) -> None:
    """CLI 不限制密码长度：本地开发常直接用 admin 这类短口令。"""

    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    code = cli.main(
        [
            "create-admin",
            "--username",
            "shorty",
            "--password",
            "admin",
            "--display-name",
            "短密码管理员",
        ]
    )
    assert code == 0

    with app.state.session_factory() as db:
        user = db.scalar(select(User).where(User.username == "shorty"))
        assert user is not None
        assert user.role == "admin"
        assert verify_password("admin", user.password_hash)
    assert "警告" in capsys.readouterr().err


def test_create_admin_resets_existing_account(app, settings, monkeypatch) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    def create(password: str) -> int:
        return cli.main(
            ["create-admin", "--username", "admin", "--password", password]
        )

    assert create("first-pass") == 0
    assert create("admin") == 0

    with app.state.session_factory() as db:
        user = db.scalar(select(User).where(User.username == "admin"))
        assert user is not None
        assert verify_password("admin", user.password_hash)
        assert not verify_password("first-pass", user.password_hash)


def test_create_admin_requires_username(capsys) -> None:
    code = cli.main(["create-admin", "--username", "  ", "--password", "long-enough"])
    assert code == 2
    assert "用户名不能为空" in capsys.readouterr().err


def test_create_admin_requires_non_empty_password(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "")
    code = cli.main(["create-admin", "--username", "admin"])
    assert code == 2
    assert "密码不能为空" in capsys.readouterr().err
