"""识别引擎配置：数据库覆盖层的读取、保存、重置与回滚。

优先级：代码默认值 < backend/.env < 进程环境变量 < `app_settings` 表。
保存时整组写入全部键（即使值为 null），保证管理员清空某项后不会回落到 .env。
唯一例外是 API Key：本次未提交且数据库从未保存过时不落库，继续沿用环境变量，
避免把环境变量里的密钥隐式复制进数据库。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..extraction.config import (
    SETTING_ENV,
    SETTING_KEYS,
    ExtractionConfig,
    base_environment,
    load_config,
)
from ..models.app_setting import AppSetting, AppSettingRevision
from ..schemas.settings import (
    ExtractionSettingsHistoryOut,
    ExtractionSettingsOut,
    ExtractionSettingsRevisionOut,
    ExtractionSettingsUpdate,
    ExtractionSettingsValues,
)
from ..shared.audit import record_audit
from ..shared.db import utcnow
from ..shared.errors import BadRequestError, NotFoundError

EXTRACTION_SCOPE = "extraction"
_KEY_PREFIX = f"{EXTRACTION_SCOPE}."
SECRET_KEYS = frozenset({"llm_api_key"})
LLM_LABELS = {
    "llm_endpoint": "接口地址",
    "llm_model": "模型名",
    "llm_api_key": "API Key",
}


def _stored_values(db: Session) -> dict[str, Any]:
    """读取数据库中的覆盖值；键为逻辑名（如 provider）。"""

    rows = db.scalars(
        select(AppSetting).where(AppSetting.key.startswith(_KEY_PREFIX))
    ).all()
    return {row.key[len(_KEY_PREFIX) :]: row.value_json for row in rows}


def effective_extraction_config(db: Session, settings: Any) -> ExtractionConfig:
    """当前生效的识别配置（数据库覆盖层优先）。抽取/入队/worker 都走这里。"""

    return load_config(settings=settings, overrides=_stored_values(db))


def _mask_secret(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if len(text) <= 4:
        return "••••"
    return f"••••{text[-4:]}"


def _masked(values: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in values.items():
        masked[key] = _mask_secret(value) if key in SECRET_KEYS else value
    return masked


def _sources(stored: dict[str, Any]) -> dict[str, str]:
    environ = base_environment()
    result: dict[str, str] = {}
    for name in SETTING_KEYS:
        if name in stored:
            result[name] = "database"
        elif (environ.get(SETTING_ENV[name]) or "").strip():
            result[name] = "env"
        else:
            result[name] = "default"
    return result


def _latest_revision(db: Session) -> AppSettingRevision | None:
    return db.scalar(
        select(AppSettingRevision)
        .options(selectinload(AppSettingRevision.actor))
        .where(AppSettingRevision.scope == EXTRACTION_SCOPE)
        .order_by(AppSettingRevision.id.desc())
        .limit(1)
    )


def get_extraction_settings(db: Session, settings: Any) -> ExtractionSettingsOut:
    stored = _stored_values(db)
    config = load_config(settings=settings, overrides=stored)
    latest = _latest_revision(db)
    values = ExtractionSettingsValues(
        provider=config.provider,
        auto_chain=list(config.auto_chain),
        paddleocr_endpoint=config.paddleocr_endpoint,
        llm_endpoint=config.llm_endpoint,
        llm_model=config.llm_model,
        llm_enabled=config.llm_enabled,
        llm_api_key_set=bool(config.llm_api_key),
        llm_api_key_hint=_mask_secret(config.llm_api_key),
        prompt_version=config.prompt_version,
        http_timeout=config.http_timeout,
        max_attempts=config.max_attempts,
        stale_minutes=config.stale_minutes,
        backoff_seconds=config.backoff_seconds,
    )
    return ExtractionSettingsOut(
        values=values,
        sources=_sources(stored),
        revision_id=latest.id if latest is not None else None,
        updated_at=latest.created_at if latest is not None else None,
        updated_by=latest.actor_name if latest is not None else None,
    )


def _validate(values: dict[str, Any], *, api_key: str | None) -> None:
    if values.get("llm_enabled"):
        missing = [
            name
            for name in LLM_LABELS
            if not (api_key if name == "llm_api_key" else values.get(name))
        ]
        if missing:
            labels = " / ".join(LLM_LABELS[name] for name in missing)
            raise BadRequestError(
                "llm_config_incomplete",
                f"启用多模态大模型前必须填写：{labels}",
                {"missing": missing},
            )
    if values.get("provider") == "multimodal_llm" and not values.get("llm_enabled"):
        raise BadRequestError(
            "llm_disabled",
            "选择多模态大模型作为识别引擎前，请先启用大模型并填写接口、模型名与 API Key",
        )


def _replace_rows(db: Session, values: dict[str, Any], actor_id: int | None) -> None:
    """用给定值整体替换数据库行：未出现在 values 中的键会被删除。"""

    rows = {
        row.key: row
        for row in db.scalars(
            select(AppSetting).where(AppSetting.key.startswith(_KEY_PREFIX))
        ).all()
    }
    now = utcnow()
    for name in SETTING_KEYS:
        key = f"{_KEY_PREFIX}{name}"
        row = rows.pop(key, None)
        if name in values:
            if row is None:
                db.add(
                    AppSetting(
                        key=key,
                        value_json=values[name],
                        updated_at=now,
                        updated_by_id=actor_id,
                    )
                )
            else:
                row.value_json = values[name]
                row.updated_at = now
                row.updated_by_id = actor_id
        elif row is not None:
            db.delete(row)
    # 前缀匹配到但不属于当前版本已知键的历史脏数据，一并清理
    for row in rows.values():
        db.delete(row)
    db.flush()


def _record_revision(
    db: Session, *, values: dict[str, Any], action: str, actor_id: int | None
) -> AppSettingRevision:
    revision = AppSettingRevision(
        scope=EXTRACTION_SCOPE,
        action=action,
        snapshot_json=values,
        actor_id=actor_id,
    )
    db.add(revision)
    db.flush()
    return revision


def update_extraction_settings(
    db: Session,
    *,
    settings: Any,
    payload: ExtractionSettingsUpdate,
    actor: Any,
    request: Any = None,
) -> ExtractionSettingsOut:
    before = _stored_values(db)
    values: dict[str, Any] = {
        "provider": payload.provider,
        "auto_chain": list(payload.auto_chain),
        "paddleocr_endpoint": payload.paddleocr_endpoint,
        "llm_endpoint": payload.llm_endpoint,
        "llm_model": payload.llm_model,
        "llm_enabled": payload.llm_enabled,
        "prompt_version": payload.prompt_version,
        "http_timeout": payload.http_timeout,
        "max_attempts": payload.max_attempts,
        "stale_minutes": payload.stale_minutes,
        "backoff_seconds": payload.backoff_seconds,
    }
    # 字段缺省 = 保持原值；null / 空串 = 清除。
    # 库中从未保存过 Key 时保持缺省，让环境变量继续生效，避免隐式复制密钥；
    # 若库中已有记录（包括显式清空的 null），则沿用该记录。
    if "llm_api_key" in payload.model_fields_set:
        values["llm_api_key"] = payload.llm_api_key
    elif "llm_api_key" in before:
        values["llm_api_key"] = before["llm_api_key"]

    effective_key = load_config(settings=settings, overrides=values).llm_api_key
    _validate(values, api_key=effective_key)

    _replace_rows(db, values, actor.id)
    revision = _record_revision(db, values=values, action="update", actor_id=actor.id)
    record_audit(
        db,
        actor.id,
        "settings.extraction.update",
        "app_settings",
        revision.id,
        before=_masked(before),
        after=_masked(values),
        request=request,
    )
    db.commit()
    return get_extraction_settings(db, settings)


def reset_extraction_settings(
    db: Session,
    *,
    settings: Any,
    actor: Any,
    request: Any = None,
) -> ExtractionSettingsOut:
    before = _stored_values(db)
    _replace_rows(db, {}, actor.id)
    revision = _record_revision(db, values={}, action="reset", actor_id=actor.id)
    record_audit(
        db,
        actor.id,
        "settings.extraction.reset",
        "app_settings",
        revision.id,
        before=_masked(before),
        after={},
        request=request,
    )
    db.commit()
    return get_extraction_settings(db, settings)


def list_revisions(db: Session, *, limit: int = 20) -> ExtractionSettingsHistoryOut:
    rows = db.scalars(
        select(AppSettingRevision)
        .options(selectinload(AppSettingRevision.actor))
        .where(AppSettingRevision.scope == EXTRACTION_SCOPE)
        .order_by(AppSettingRevision.id.desc())
        .limit(max(1, min(limit, 100)))
    ).all()
    items = [
        ExtractionSettingsRevisionOut(
            id=row.id,
            action=row.action,
            actor_name=row.actor_name,
            created_at=row.created_at,
            values=_masked(dict(row.snapshot_json or {})),
        )
        for row in rows
    ]
    return ExtractionSettingsHistoryOut(items=items)


def rollback_extraction_settings(
    db: Session,
    *,
    settings: Any,
    revision_id: int,
    actor: Any,
    request: Any = None,
) -> ExtractionSettingsOut:
    revision = db.get(AppSettingRevision, revision_id)
    if revision is None or revision.scope != EXTRACTION_SCOPE:
        raise NotFoundError("settings_revision_not_found", "配置版本不存在")

    snapshot = revision.snapshot_json
    if not isinstance(snapshot, dict):
        raise BadRequestError("settings_snapshot_invalid", "该版本快照已损坏，无法回滚")

    before = _stored_values(db)
    values = {name: snapshot[name] for name in SETTING_KEYS if name in snapshot}
    effective_key = load_config(settings=settings, overrides=values).llm_api_key
    _validate(values, api_key=effective_key)
    _replace_rows(db, values, actor.id)
    new_revision = _record_revision(
        db, values=values, action="rollback", actor_id=actor.id
    )
    record_audit(
        db,
        actor.id,
        "settings.extraction.rollback",
        "app_settings",
        new_revision.id,
        before=_masked(before),
        after=_masked(values),
        request=request,
    )
    db.commit()
    return get_extraction_settings(db, settings)
