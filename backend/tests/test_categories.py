"""类别种子、CRUD 与权限。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.categories.service import seed_default_categories
from backend.models.category import Category


def test_default_seed_counts(client: TestClient, admin_credentials, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": admin_credentials["username"], "password": admin_credentials["password"]},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    all_categories = client.get("/api/v1/categories", headers=headers)
    assert all_categories.status_code == 200
    items = all_categories.json()["items"]
    assert len(items) == 18
    assert sum(1 for item in items if item["kind"] == "purchase") == 10
    assert sum(1 for item in items if item["kind"] == "expense") == 8
    assert {item["name"] for item in items} >= {"标准件", "机加工", "报名费", "高铁"}

    purchases = client.get(
        "/api/v1/categories", headers=headers, params={"kind": "purchase"}
    ).json()["items"]
    assert len(purchases) == 10
    assert all(item["kind"] == "purchase" for item in purchases)


def test_seed_is_idempotent(db_session: Session):
    before = db_session.query(Category).count()
    inserted = seed_default_categories(db_session)
    assert inserted == 0
    assert db_session.query(Category).count() == before


def test_categories_require_login(client: TestClient):
    assert client.get("/api/v1/categories").status_code == 401


def test_normal_user_read_only(user_client: TestClient):
    assert user_client.get("/api/v1/categories").status_code == 200
    response = user_client.post(
        "/api/v1/categories", json={"name": "违规类别", "kind": "purchase"}
    )
    assert response.status_code == 403


def test_admin_crud_and_audit(
    admin_client: TestClient, db_session: Session
):
    created = admin_client.post(
        "/api/v1/categories",
        json={"name": "自定义类别", "kind": "purchase", "sort_order": 99},
    )
    assert created.status_code == 201, created.text
    category = created.json()
    assert category["name"] == "自定义类别"
    assert category["sort_order"] == 99

    duplicate = admin_client.post(
        "/api/v1/categories", json={"name": "自定义类别", "kind": "purchase"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "category_exists"

    same_name_other_kind = admin_client.post(
        "/api/v1/categories", json={"name": "自定义类别", "kind": "expense"}
    )
    assert same_name_other_kind.status_code == 201

    updated = admin_client.patch(
        f"/api/v1/categories/{category['id']}",
        json={"name": "重命名类别", "sort_order": 3, "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "重命名类别"
    assert updated.json()["is_active"] is False
    assert updated.json()["sort_order"] == 3

    visible = admin_client.get("/api/v1/categories").json()["items"]
    assert all(item["id"] != category["id"] for item in visible)

    all_items = admin_client.get(
        "/api/v1/categories", params={"include_inactive": True}
    ).json()["items"]
    assert any(item["id"] == category["id"] for item in all_items)

    db_session.expire_all()
    logs = admin_client.get(
        "/api/v1/audit-logs", params={"entity_type": "category"}
    ).json()["items"]
    actions = {log["action"] for log in logs}
    assert "category.create" in actions
    assert "category.update" in actions
    update_log = next(log for log in logs if log["action"] == "category.update")
    assert update_log["before"]["name"] == "自定义类别"
    assert update_log["after"]["name"] == "重命名类别"


def test_missing_category_returns_404(admin_client: TestClient):
    response = admin_client.patch(
        "/api/v1/categories/999999", json={"sort_order": 1}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "category_not_found"


def test_invalid_kind_returns_422(admin_client: TestClient):
    response = admin_client.post(
        "/api/v1/categories", json={"name": "坏类别", "kind": "unknown"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
