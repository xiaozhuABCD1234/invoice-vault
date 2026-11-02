"""报表模板：默认模板、CRUD、权限与审计。"""

from __future__ import annotations

from fastapi.testclient import TestClient

DEFAULT_LABELS = [
    "序号",
    "名称",
    "购买数量",
    "单价",
    "总价",
    "单张发票金额",
    "店铺",
    "申购人",
    "负责人",
    "发票号码",
    "发票图片",
    "付款记录",
    "发票形式",
    "备注",
    "申请老师代付时间",
    "链接",
]

COLUMN = {"key": "invoice_number", "label": "发票号码"}


def _template_ids(response) -> list[int]:
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def _create(client: TestClient, name: str, *, is_shared: bool = False, column=None) -> dict:
    response = client.post(
        "/api/v1/report-templates",
        json={
            "name": name,
            "columns": [column or COLUMN],
            "is_shared": is_shared,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_report_templates_require_login(client: TestClient):
    assert client.get("/api/v1/report-templates").status_code == 401
    assert (
        client.post("/api/v1/report-templates", json={"name": "x", "columns": [COLUMN]}).status_code
        == 401
    )


def test_default_template_visible_with_16_columns(user_client: TestClient):
    response = user_client.get("/api/v1/report-templates")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["id"] == 0
    assert items[0]["name"] == "默认导出"
    assert [column["label"] for column in items[0]["columns"]] == DEFAULT_LABELS
    assert len(items[0]["columns"]) == 16
    assert all(column["key"] for column in items[0]["columns"])
    assert items[0]["is_shared"] is True


def test_template_visibility_owner_or_shared(
    admin_client: TestClient, user_client: TestClient
):
    user_private = _create(user_client, "用户私有模板")
    admin_private = _create(admin_client, "管理员私有模板")
    shared = _create(user_client, "共享模板", is_shared=True)

    user_ids = _template_ids(user_client.get("/api/v1/report-templates"))
    assert user_ids[0] == 0
    assert user_private["id"] in user_ids
    assert shared["id"] in user_ids
    assert admin_private["id"] not in user_ids

    admin_ids = _template_ids(admin_client.get("/api/v1/report-templates"))
    assert admin_ids[0] == 0
    assert admin_private["id"] in admin_ids
    assert shared["id"] in admin_ids
    assert user_private["id"] not in admin_ids


def test_template_columns_required_and_validated(user_client: TestClient):
    empty = user_client.post(
        "/api/v1/report-templates", json={"name": "空模板", "columns": []}
    )
    assert empty.status_code == 422
    assert empty.json()["code"] == "validation_error"

    unknown = user_client.post(
        "/api/v1/report-templates",
        json={"name": "坏模板", "columns": [{"key": "not_a_field", "label": "坏列"}]},
    )
    assert unknown.status_code == 400
    assert unknown.json()["code"] == "invalid_column_key"

    bad_sort = user_client.post(
        "/api/v1/report-templates",
        json={"name": "坏排序", "columns": [COLUMN], "sort": [{"key": "nope", "order": "asc"}]},
    )
    assert bad_sort.status_code == 400
    assert bad_sort.json()["code"] == "invalid_sort_key"

    blank_name = user_client.post(
        "/api/v1/report-templates", json={"name": "   ", "columns": [COLUMN]}
    )
    assert blank_name.status_code == 400
    assert blank_name.json()["code"] == "invalid_template_name"


def test_template_update_and_delete_permissions(
    admin_client: TestClient, user_client: TestClient
):
    user_template = _create(user_client, "用户模板")
    user_id = user_template["id"]

    updated = user_client.patch(
        f"/api/v1/report-templates/{user_id}",
        json={"name": "用户重命名", "is_shared": True},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "用户重命名"
    assert updated.json()["is_shared"] is True

    admin_update = admin_client.patch(
        f"/api/v1/report-templates/{user_id}", json={"name": "管理员改名"}
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["name"] == "管理员改名"

    admin_template = _create(admin_client, "管理员模板")
    forbidden_update = user_client.patch(
        f"/api/v1/report-templates/{admin_template['id']}", json={"name": "越权"}
    )
    assert forbidden_update.status_code == 403
    forbidden_delete = user_client.delete(
        f"/api/v1/report-templates/{admin_template['id']}"
    )
    assert forbidden_delete.status_code == 403

    deleted = admin_client.delete(f"/api/v1/report-templates/{user_id}")
    assert deleted.status_code == 204
    remaining = _template_ids(user_client.get("/api/v1/report-templates"))
    assert user_id not in remaining


def test_default_template_immutable(admin_client: TestClient):
    patched = admin_client.patch(
        "/api/v1/report-templates/0", json={"name": "改默认"}
    )
    assert patched.status_code == 400
    assert patched.json()["code"] == "default_template_immutable"

    deleted = admin_client.delete("/api/v1/report-templates/0")
    assert deleted.status_code == 400
    assert deleted.json()["code"] == "default_template_immutable"

    missing = admin_client.patch(
        "/api/v1/report-templates/999999", json={"name": "不存在"}
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "template_not_found"


def test_template_changes_are_audited(admin_client: TestClient):
    template = _create(admin_client, "审计模板")
    created = admin_client.get(
        "/api/v1/audit-logs",
        params={"action": "report_template.create", "entity_id": template["id"]},
    )
    assert created.status_code == 200
    assert created.json()["total"] == 1
    assert created.json()["items"][0]["after"]["name"] == "审计模板"

    updated = admin_client.patch(
        f"/api/v1/report-templates/{template['id']}", json={"name": "审计模板2"}
    )
    assert updated.status_code == 200
    update_logs = admin_client.get(
        "/api/v1/audit-logs",
        params={"action": "report_template.update", "entity_id": template["id"]},
    )
    assert update_logs.json()["total"] == 1
    log = update_logs.json()["items"][0]
    assert log["before"]["name"] == "审计模板"
    assert log["after"]["name"] == "审计模板2"

    deleted = admin_client.delete(f"/api/v1/report-templates/{template['id']}")
    assert deleted.status_code == 204
    delete_logs = admin_client.get(
        "/api/v1/audit-logs",
        params={"action": "report_template.delete", "entity_id": template["id"]},
    )
    assert delete_logs.json()["total"] == 1
