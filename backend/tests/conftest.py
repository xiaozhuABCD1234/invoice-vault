"""可复用测试 fixtures。

后续领域智能体可直接使用：app、client、admin_client、user_client、db_session、
admin_user、normal_user、make_user、settings、admin_credentials、user_credentials。

每个测试使用独立临时 SQLite 文件与上传目录（tmp_path），互不影响。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import create_app
from backend.models.user import User
from backend.shared.config import Settings
from backend.shared.enums import Role
from backend.shared.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-pass-123"
NORMAL_USERNAME = "member"
NORMAL_PASSWORD = "member-pass-123"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_name="发票管理系统 API",
        api_prefix="/api/v1",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        sql_echo=False,
        jwt_secret="test-secret-key-for-pytest-only-0123456789",
        jwt_algorithm="HS256",
        access_token_minutes=15,
        refresh_token_days=7,
        cookie_secure=False,
        refresh_cookie_name="refresh_token",
        refresh_cookie_path="/api/v1/auth",
        cors_origins=["http://testserver"],
        lockout_threshold=5,
        lockout_minutes=15,
        max_upload_bytes=20 * 1024 * 1024,
        trace_header="X-Trace-Id",
    )


@pytest.fixture()
def app(settings: Settings):
    application = create_app(settings)
    try:
        yield application
    finally:
        application.state.engine.dispose()


@pytest.fixture()
def db_session(app) -> Iterator[Session]:
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_user(db_session: Session) -> Callable[..., User]:
    def _make(
        username: str,
        display_name: str | None = None,
        password: str = NORMAL_PASSWORD,
        role: Role | str = Role.USER,
    ) -> User:
        role_value = role.value if isinstance(role, Role) else role
        user = User(
            username=username,
            display_name=display_name or username,
            password_hash=hash_password(password),
            role=role_value,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def admin_user(make_user: Callable[..., User]) -> User:
    return make_user(ADMIN_USERNAME, "系统管理员", ADMIN_PASSWORD, Role.ADMIN)


@pytest.fixture()
def normal_user(make_user: Callable[..., User]) -> User:
    return make_user(NORMAL_USERNAME, "普通成员", NORMAL_PASSWORD, Role.USER)


@pytest.fixture()
def admin_credentials() -> dict[str, str]:
    return {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}


@pytest.fixture()
def user_credentials() -> dict[str, str]:
    return {"username": NORMAL_USERNAME, "password": NORMAL_PASSWORD}


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client(app, admin_user: User, admin_credentials: dict[str, str]) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/auth/login", json=admin_credentials)
        assert response.status_code == 200, response.text
        test_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield test_client


@pytest.fixture()
def user_client(app, normal_user: User, user_credentials: dict[str, str]) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/auth/login", json=user_credentials)
        assert response.status_code == 200, response.text
        test_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield test_client
