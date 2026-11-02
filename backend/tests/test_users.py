"""用户管理权限、CRUD 与 options 接口。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.user import User


def test_options_available_to_normal_user(user_client: TestClient, admin_user):
    response = user_client.get("/api/v1/users/options")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) >= 2
    item = body["items"][0]
    assert set(item) == {"id", "display_name", "role", "is_active"}


def test_options_requires_login(client: TestClient):
    assert client.get("/api/v1/users/options").status_code == 401


def test_admin_can_list_and_filter_users(admin_client: TestClient, normal_user):
    response = admin_client.get("/api/v1/users")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    assert set(body) == {"items", "total", "page", "page_size"}

    searched = admin_client.get("/api/v1/users", params={"q": "admin"})
    assert searched.status_code == 200
    assert searched.json()["total"] == 1

    admins = admin_client.get("/api/v1/users", params={"role": "admin"})
    assert all(item["role"] == "admin" for item in admins.json()["items"])

    active = admin_client.get("/api/v1/users", params={"is_active": True})
    assert all(item["is_active"] for item in active.json()["items"])

    paged = admin_client.get("/api/v1/users", params={"page": 1, "page_size": 1})
    assert paged.json()["page_size"] == 1
    assert len(paged.json()["items"]) == 1


def test_normal_user_cannot_manage_users(user_client: TestClient, normal_user: User):
    assert user_client.get("/api/v1/users").status_code == 403
    created = user_client.post(
        "/api/v1/users",
        json={
            "username": "intruder",
            "display_name": "入侵者",
            "password": "password-123",
            "role": "user",
        },
    )
    assert created.status_code == 403
    patched = user_client.patch(
        f"/api/v1/users/{normal_user.id}", json={"display_name": "改名"}
    )
    assert patched.status_code == 403
    assert patched.json()["code"] == "forbidden"


def test_admin_create_user_and_login(
    app, admin_client: TestClient, client: TestClient, db_session: Session
):
    payload = {
        "username": "newuser",
        "display_name": "新用户",
        "password": "newuser-pass-123",
        "role": "user",
    }
    response = admin_client.post("/api/v1/users", json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["username"] == "newuser"
    assert created["role"] == "user"
    assert "password_hash" not in created

    duplicate = admin_client.post("/api/v1/users", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "username_taken"

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "newuser", "password": "newuser-pass-123"},
    )
    assert login.status_code == 200

    db_session.expire_all()
    stored = db_session.query(User).filter_by(username="newuser").one()
    assert stored.password_hash.startswith("$argon2id$")


def test_admin_update_display_name_and_role(admin_client: TestClient, normal_user: User):
    response = admin_client.patch(
        f"/api/v1/users/{normal_user.id}",
        json={"display_name": "新名字", "role": "admin"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "新名字"
    assert body["role"] == "admin"


def test_cannot_disable_self(admin_client: TestClient, admin_user: User):
    response = admin_client.patch(
        f"/api/v1/users/{admin_user.id}", json={"is_active": False}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "cannot_disable_self"


def test_cannot_demote_last_admin(admin_client: TestClient, admin_user: User):
    response = admin_client.patch(
        f"/api/v1/users/{admin_user.id}", json={"role": "user"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "last_admin_required"


def test_validation_errors(admin_client: TestClient):
    missing = admin_client.post("/api/v1/users", json={"username": "abc"})
    assert missing.status_code == 422
    assert missing.json()["code"] == "validation_error"

    short_password = admin_client.post(
        "/api/v1/users",
        json={
            "username": "shortpwd",
            "display_name": "短密码",
            "password": "123",
            "role": "user",
        },
    )
    assert short_password.status_code == 422

    too_many = admin_client.get("/api/v1/users", params={"page_size": 101})
    assert too_many.status_code == 422


def test_disable_user_excludes_options(admin_client: TestClient, normal_user: User):
    response = admin_client.patch(
        f"/api/v1/users/{normal_user.id}", json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    options = admin_client.get("/api/v1/users/options").json()["items"]
    target = next(item for item in options if item["id"] == normal_user.id)
    assert target["is_active"] is False
