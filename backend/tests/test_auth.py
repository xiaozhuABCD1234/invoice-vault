"""认证、锁定、refresh 轮换与登出。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.user import RefreshToken, User
from backend.shared.enums import Role
from backend.shared.security import (
    create_access_token,
    decode_access_token,
    hash_refresh_token,
)


def _login(client: TestClient, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_success_sets_cookie_and_me(
    client: TestClient, admin_credentials, admin_user
):
    response = _login(client, admin_credentials["username"], admin_credentials["password"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert set(body["user"]) == {
        "id",
        "username",
        "display_name",
        "role",
        "is_active",
        "created_at",
        "last_login_at",
    }
    assert "password_hash" not in body["user"]
    assert body["user"]["role"] == "admin"

    raw_cookie = client.cookies.get("refresh_token")
    assert raw_cookie and raw_cookie.startswith("rt_")
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie

    me = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == admin_credentials["username"]


def test_login_wrong_password(
    client: TestClient, admin_credentials, db_session: Session, admin_user
):
    response = _login(client, admin_credentials["username"], "wrong-password")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "invalid_credentials"
    assert body["message"] == "用户名或密码错误"
    assert body["trace_id"]
    assert "set-cookie" not in response.headers

    db_session.expire_all()
    user = db_session.query(User).filter_by(username=admin_credentials["username"]).one()
    assert user.failed_attempts == 1
    assert user.locked_until is None


def test_login_lockout_after_five_failures(
    client: TestClient, admin_credentials, db_session: Session, admin_user: User
):
    statuses = [
        _login(client, admin_credentials["username"], "wrong-password").status_code
        for _ in range(5)
    ]
    assert statuses == [401, 401, 401, 401, 423]

    locked = _login(client, admin_credentials["username"], admin_credentials["password"])
    assert locked.status_code == 423
    assert locked.json()["code"] == "account_locked"
    assert locked.json()["details"]["locked_until"]

    db_session.expire_all()
    user = db_session.get(User, admin_user.id)
    assert user is not None
    assert user.locked_until is not None
    assert user.failed_attempts >= 5

    user.locked_until = None
    user.failed_attempts = 0
    db_session.commit()

    recovered = _login(client, admin_credentials["username"], admin_credentials["password"])
    assert recovered.status_code == 200


def test_login_unknown_user(client: TestClient):
    response = _login(client, "nobody", "whatever-123")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_disabled_user_cannot_login(
    admin_client: TestClient, normal_user: User, user_credentials
):
    response = admin_client.patch(
        f"/api/v1/users/{normal_user.id}", json={"is_active": False}
    )
    assert response.status_code == 200, response.text

    denied = _login(admin_client, user_credentials["username"], user_credentials["password"])
    assert denied.status_code == 403
    assert denied.json()["code"] == "account_disabled"


def test_refresh_rotation_and_old_token_rejected(
    app, client: TestClient, admin_credentials, admin_user
):
    response = _login(client, admin_credentials["username"], admin_credentials["password"])
    assert response.status_code == 200
    old_token = client.cookies.get("refresh_token")
    old_access = response.json()["access_token"]
    assert old_token

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    new_token = client.cookies.get("refresh_token")
    assert new_token and new_token != old_token
    assert refreshed.json()["access_token"] != old_access
    assert refreshed.json()["user"]["username"] == admin_credentials["username"]

    with TestClient(app) as replay:
        replay.cookies.set("refresh_token", old_token, path="/api/v1/auth")
        reused = replay.post("/api/v1/auth/refresh")
    assert reused.status_code == 401
    assert reused.json()["code"] == "invalid_refresh_token"


def test_logout_revokes_refresh_and_clears_cookie(
    app, client: TestClient, admin_credentials, admin_user
):
    response = _login(client, admin_credentials["username"], admin_credentials["password"])
    assert response.status_code == 200
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    old_token = client.cookies.get("refresh_token")
    assert old_token

    unauthenticated = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": ""},
    )
    assert unauthenticated.status_code == 401

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert not client.cookies.get("refresh_token")

    with TestClient(app) as replay:
        replay.cookies.set("refresh_token", old_token, path="/api/v1/auth")
        refreshed = replay.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 401


def test_me_requires_valid_token(client: TestClient):
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"

    invalid = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "invalid_token"


def test_password_change_invalidates_old_access_and_refresh(
    app,
    user_client: TestClient,
    admin_client: TestClient,
    normal_user: User,
):
    old_access = user_client.headers["Authorization"]
    old_refresh = user_client.cookies.get("refresh_token")
    assert old_refresh

    changed = admin_client.patch(
        f"/api/v1/users/{normal_user.id}", json={"password": "new-pass-123"}
    )
    assert changed.status_code == 200, changed.text

    me = user_client.get("/api/v1/me", headers={"Authorization": old_access})
    assert me.status_code == 401
    assert me.json()["code"] == "token_revoked"

    with TestClient(app) as replay:
        replay.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
        refreshed = replay.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 401

    with TestClient(app) as fresh:
        login = _login(fresh, normal_user.username, "new-pass-123")
    assert login.status_code == 200


def test_password_hash_is_argon2id(admin_user: User):
    assert admin_user.password_hash.startswith("$argon2id$")
    assert admin_user.role == Role.ADMIN.value


def test_refresh_token_is_hashed_in_db(
    client: TestClient, admin_credentials, db_session: Session, admin_user: User
):
    response = _login(client, admin_credentials["username"], admin_credentials["password"])
    assert response.status_code == 200
    raw = client.cookies.get("refresh_token")
    assert raw

    db_session.expire_all()
    stored = db_session.query(RefreshToken).one()
    assert stored.token_hash == hash_refresh_token(raw)
    assert stored.token_hash != raw
    assert len(stored.token_hash) == 64
    assert stored.expires_at > datetime.now(UTC)
    assert stored.revoked_at is None


def test_access_token_claims_and_expiry(settings, client: TestClient, admin_user: User):
    token = create_access_token(admin_user.id, admin_user.token_version, settings)
    payload = decode_access_token(token, settings)
    assert payload["sub"] == admin_user.id
    assert payload["ver"] == admin_user.token_version
    assert payload["type"] == "access"
    assert payload["iat"] < payload["exp"]

    expired = create_access_token(
        admin_user.id,
        admin_user.token_version,
        settings,
        now=datetime.now(UTC) - timedelta(minutes=30),
    )
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"
