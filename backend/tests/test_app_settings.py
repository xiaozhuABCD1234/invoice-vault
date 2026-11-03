"""识别引擎设置：权限、校验、持久化、生效、脱敏与回滚。"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.app_settings import service
from backend.extraction.config import load_config
from backend.models.app_setting import AppSetting, AppSettingRevision
from backend.models.audit import AuditLog
from backend.shared.enums import ExtractionProvider

ENV_KEYS = (
    "IV_EXTRACTION_PROVIDER",
    "IV_EXTRACTION_AUTO_CHAIN",
    "IV_PADDLEOCR_ENDPOINT",
    "IV_LLM_ENDPOINT",
    "IV_LLM_API_KEY",
    "IV_LLM_MODEL",
    "IV_LLM_ENABLED",
    "IV_EXTRACTION_PROMPT_VERSION",
    "IV_EXTRACTION_HTTP_TIMEOUT",
    "IV_EXTRACTION_MAX_ATTEMPTS",
    "IV_EXTRACTION_STALE_MINUTES",
    "IV_EXTRACTION_BACKOFF_SECONDS",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "provider": "auto",
        "auto_chain": ["pdf_text", "paddleocr_local"],
        "paddleocr_endpoint": "http://127.0.0.1:8866/predict/ocr_system",
        "llm_endpoint": None,
        "llm_model": None,
        "llm_enabled": False,
        "prompt_version": "v2",
        "http_timeout": 5,
        "max_attempts": 2,
        "stale_minutes": 10,
        "backoff_seconds": 5,
    }
    data.update(overrides)
    return data


def llm_payload(**overrides: Any) -> dict[str, Any]:
    data = payload(
        provider="multimodal_llm",
        llm_enabled=True,
        llm_endpoint="https://llm.example.com/v1",
        llm_model="vision-1",
        llm_api_key="sk-test-secret-1234",
    )
    data.update(overrides)
    return data


def test_settings_endpoints_require_admin(user_client) -> None:
    assert user_client.get("/api/v1/admin/settings/extraction").status_code == 403
    assert (
        user_client.put("/api/v1/admin/settings/extraction", json=payload()).status_code
        == 403
    )
    assert (
        user_client.get("/api/v1/admin/settings/extraction/history").status_code == 403
    )
    assert user_client.delete("/api/v1/admin/settings/extraction").status_code == 403
    assert (
        user_client.post(
            "/api/v1/admin/settings/extraction/rollback", json={"revision_id": 1}
        ).status_code
        == 403
    )


def test_settings_require_authentication(client) -> None:
    assert client.get("/api/v1/admin/settings/extraction").status_code == 401


def test_get_settings_falls_back_to_defaults(admin_client) -> None:
    response = admin_client.get("/api/v1/admin/settings/extraction")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["provider"] == "pdf_text"
    assert body["values"]["auto_chain"] == [
        "pdf_text",
        "paddleocr_local",
        "multimodal_llm",
    ]
    assert body["values"]["llm_api_key_set"] is False
    assert body["values"]["llm_api_key_hint"] is None
    assert body["revision_id"] is None
    assert set(body["sources"].values()) == {"default"}


def test_get_settings_reflects_environment(admin_client, monkeypatch) -> None:
    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "mock")
    monkeypatch.setenv("IV_EXTRACTION_MAX_ATTEMPTS", "7")
    body = admin_client.get("/api/v1/admin/settings/extraction").json()
    assert body["values"]["provider"] == "mock"
    assert body["values"]["max_attempts"] == 7
    assert body["sources"]["provider"] == "env"
    assert body["sources"]["max_attempts"] == "env"
    assert body["sources"]["http_timeout"] == "default"


def test_update_settings_persists_and_audits(admin_client, db_session) -> None:
    response = admin_client.put("/api/v1/admin/settings/extraction", json=payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["provider"] == "auto"
    assert body["values"]["auto_chain"] == ["pdf_text", "paddleocr_local"]
    assert body["values"]["http_timeout"] == 5.0
    assert body["values"]["prompt_version"] == "v2"
    assert body["revision_id"] is not None
    assert body["sources"]["llm_api_key"] == "default"
    assert all(
        source == "database"
        for key, source in body["sources"].items()
        if key != "llm_api_key"
    )

    # 未提交 API Key，且库中原本没有，因此只写入 11 个非密钥配置项
    rows = db_session.scalars(select(AppSetting)).all()
    assert len(rows) == 11
    revision = db_session.get(AppSettingRevision, body["revision_id"])
    assert revision is not None and revision.action == "update"

    audit_actions = [log.action for log in db_session.scalars(select(AuditLog)).all()]
    assert "settings.extraction.update" in audit_actions


def test_update_settings_overrides_env(
    admin_client, db_session, settings, monkeypatch
) -> None:
    monkeypatch.setenv("IV_EXTRACTION_MAX_ATTEMPTS", "9")
    saved = admin_client.put(
        "/api/v1/admin/settings/extraction", json=payload(max_attempts=2)
    )
    assert saved.status_code == 200, saved.text

    effective = service.effective_extraction_config(db_session, settings)
    assert effective.max_attempts == 2
    assert effective.provider == "auto"
    assert effective.prompt_version == "v2"
    # 环境变量层仍然保留原值，证明覆盖来自数据库
    assert load_config(settings=settings).max_attempts == 9


def test_secret_is_masked_everywhere(admin_client, db_session) -> None:
    response = admin_client.put("/api/v1/admin/settings/extraction", json=llm_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["llm_api_key_set"] is True
    assert body["values"]["llm_api_key_hint"] == "••••1234"
    assert "sk-test-secret-1234" not in response.text

    stored = db_session.scalar(
        select(AppSetting).where(AppSetting.key == "extraction.llm_api_key")
    )
    assert stored is not None and stored.value_json == "sk-test-secret-1234"

    history = admin_client.get("/api/v1/admin/settings/extraction/history").json()
    assert "sk-test-secret-1234" not in str(history)
    assert history["items"][0]["values"]["llm_api_key"] == "••••1234"


def test_environment_api_key_survives_save(
    admin_client, db_session, settings, monkeypatch
) -> None:
    """未提交 Key 时，环境变量里的 Key 继续生效，且不会被复制进数据库。"""

    monkeypatch.setenv("IV_LLM_API_KEY", "sk-env-secret-9876")
    response = admin_client.put(
        "/api/v1/admin/settings/extraction",
        json=payload(
            llm_enabled=True,
            llm_endpoint="https://llm.example.com/v1",
            llm_model="vision-1",
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["llm_api_key_set"] is True
    assert body["values"]["llm_api_key_hint"] == "••••9876"
    assert body["sources"]["llm_api_key"] == "env"

    stored = db_session.scalar(
        select(AppSetting).where(AppSetting.key == "extraction.llm_api_key")
    )
    assert stored is None
    assert load_config(settings=settings).llm_api_key == "sk-env-secret-9876"


def test_secret_kept_when_field_omitted(admin_client) -> None:
    admin_client.put("/api/v1/admin/settings/extraction", json=llm_payload())
    body = payload(provider="auto")
    saved = admin_client.put("/api/v1/admin/settings/extraction", json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()["values"]["llm_api_key_set"] is True
    assert saved.json()["values"]["llm_api_key_hint"] == "••••1234"


def test_secret_cleared_with_null(admin_client) -> None:
    admin_client.put("/api/v1/admin/settings/extraction", json=llm_payload())
    body = payload(provider="auto", llm_api_key=None)
    saved = admin_client.put("/api/v1/admin/settings/extraction", json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()["values"]["llm_api_key_set"] is False


def test_llm_enabled_requires_full_config(admin_client) -> None:
    response = admin_client.put(
        "/api/v1/admin/settings/extraction",
        json=payload(llm_enabled=True),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "llm_config_incomplete"
    assert set(response.json()["details"]["missing"]) == {
        "llm_endpoint",
        "llm_model",
        "llm_api_key",
    }


def test_multimodal_provider_requires_enabled_llm(admin_client) -> None:
    response = admin_client.put(
        "/api/v1/admin/settings/extraction",
        json=payload(provider="multimodal_llm", llm_enabled=False),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "llm_disabled"


@pytest.mark.parametrize(
    "broken",
    [
        {"provider": "chatgpt"},
        {"auto_chain": []},
        {"auto_chain": ["pdf_text", "pdf_text"]},
        {"paddleocr_endpoint": "ftp://ocr.local"},
        {"http_timeout": 0},
        {"max_attempts": 0},
        {"stale_minutes": 0},
        {"backoff_seconds": -1},
        {"prompt_version": ""},
    ],
)
def test_update_rejects_invalid_values(admin_client, broken) -> None:
    response = admin_client.put(
        "/api/v1/admin/settings/extraction", json=payload(**broken)
    )
    assert response.status_code == 422, response.text


def test_schema_covers_all_providers(admin_client) -> None:
    for provider in ExtractionProvider:
        body = (
            llm_payload(provider=provider.value)
            if provider is ExtractionProvider.MULTIMODAL_LLM
            else payload(provider=provider.value)
        )
        response = admin_client.put("/api/v1/admin/settings/extraction", json=body)
        assert response.status_code == 200, (provider, response.text)

    assert (
        admin_client.put(
            "/api/v1/admin/settings/extraction", json=payload(provider="auto")
        ).status_code
        == 200
    )


def test_reset_restores_defaults(admin_client, db_session) -> None:
    admin_client.put("/api/v1/admin/settings/extraction", json=llm_payload())
    response = admin_client.delete("/api/v1/admin/settings/extraction")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["provider"] == "pdf_text"
    assert body["values"]["llm_api_key_set"] is False
    assert set(body["sources"].values()) == {"default"}
    assert db_session.scalars(select(AppSetting)).all() == []
    assert body["revision_id"] is not None


def test_rollback_restores_previous_snapshot(admin_client) -> None:
    first = admin_client.put(
        "/api/v1/admin/settings/extraction", json=payload(max_attempts=2)
    )
    assert first.status_code == 200, first.text
    second = admin_client.put(
        "/api/v1/admin/settings/extraction", json=payload(max_attempts=4)
    )
    assert second.status_code == 200, second.text

    history = admin_client.get(
        "/api/v1/admin/settings/extraction/history?limit=10"
    ).json()["items"]
    target = next(item for item in history if item["values"].get("max_attempts") == 2)

    rollback = admin_client.post(
        "/api/v1/admin/settings/extraction/rollback",
        json={"revision_id": target["id"]},
    )
    assert rollback.status_code == 200, rollback.text
    body = rollback.json()
    assert body["values"]["max_attempts"] == 2
    assert body["revision_id"] != target["id"]

    actions = [
        item["action"]
        for item in admin_client.get(
            "/api/v1/admin/settings/extraction/history"
        ).json()["items"]
    ]
    assert actions[0] == "rollback"
    assert "update" in actions


def test_rollback_rejects_unknown_revision(admin_client) -> None:
    response = admin_client.post(
        "/api/v1/admin/settings/extraction/rollback", json={"revision_id": 999}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "settings_revision_not_found"


PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n"
    b"<< /Root 1 0 R >>\n%%EOF\n"
)


def test_worker_uses_saved_database_config(
    admin_client, user_client, settings, db_session
) -> None:
    """保存后无需重启：worker 下一轮直接读数据库覆盖层。"""

    from backend import worker
    from backend.models.extraction import ExtractionJob

    saved = admin_client.put(
        "/api/v1/admin/settings/extraction", json=payload(provider="mock")
    )
    assert saved.status_code == 200, saved.text

    uploaded = user_client.post(
        "/api/v1/documents",
        files={"file": ("worker-config.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type": "invoice"},
    )
    assert uploaded.status_code == 201, uploaded.text
    job_id = uploaded.json()["extraction_job"]["id"]

    processed = worker.run_once(db_session, settings=settings)
    assert processed is not None and processed.id == job_id

    db_session.expire_all()
    job = db_session.get(ExtractionJob, job_id)
    assert job is not None
    assert job.status == "review_pending"
    assert job.provider == "mock"
