"""审计日志权限、过滤与写入。"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def test_admin_can_read_audit_logs(admin_client: TestClient):
    response = admin_client.get("/api/v1/audit-logs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert set(body) == {"items", "total", "page", "page_size"}

    log = body["items"][0]
    assert set(log) >= {
        "id",
        "actor_id",
        "actor_name",
        "action",
        "entity_type",
        "entity_id",
        "before",
        "after",
        "ip",
        "user_agent",
        "created_at",
    }
    assert log["actor_name"] == "系统管理员"


def test_login_is_audited(admin_client: TestClient, admin_user):
    response = admin_client.get("/api/v1/audit-logs", params={"action": "login"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["actor_id"] == admin_user.id for item in body["items"])


def test_category_changes_are_audited(admin_client: TestClient):
    created = admin_client.post(
        "/api/v1/categories", json={"name": "审计类别", "kind": "expense"}
    )
    category_id = created.json()["id"]

    response = admin_client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "category", "entity_id": category_id},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["action"] == "category.create"
    assert items[0]["after"]["name"] == "审计类别"


def test_audit_filters_and_pagination(admin_client: TestClient, admin_user):
    filtered = admin_client.get(
        "/api/v1/audit-logs", params={"actor_id": admin_user.id, "page_size": 1}
    )
    assert filtered.status_code == 200
    assert filtered.json()["page_size"] == 1
    assert filtered.json()["total"] >= 1

    future = admin_client.get(
        "/api/v1/audit-logs", params={"date_from": "2100-01-01"}
    )
    assert future.json()["total"] == 0

    past = admin_client.get(
        "/api/v1/audit-logs", params={"date_from": "2000-01-01", "date_to": date(2100, 1, 1).isoformat()}
    )
    assert past.json()["total"] >= 1


def test_normal_user_cannot_read_audit(user_client: TestClient):
    response = user_client.get("/api/v1/audit-logs")
    assert response.status_code == 403


def test_audit_requires_login(client: TestClient):
    assert client.get("/api/v1/audit-logs").status_code == 401


def test_invalid_filter_returns_422(admin_client: TestClient):
    response = admin_client.get("/api/v1/audit-logs", params={"actor_id": "abc"})
    assert response.status_code == 422
