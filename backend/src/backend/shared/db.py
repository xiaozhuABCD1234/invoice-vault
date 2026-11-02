"""SQLAlchemy 引擎、会话与建表入口。"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

from .config import Settings, get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def utcnow() -> datetime:
    """当前 UTC 时间（带时区）。"""

    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """SQLite 不保存时区；统一按 UTC 写入，读取时补回 UTC 时区。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


#: 模型统一使用的 UTC 时间类型别名
TZDateTime = UTCDateTime


def _sqlite_path(url: str) -> Path | None:
    parsed = make_url(url)
    database = parsed.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return None
    return Path(database)


def ensure_directories(settings: Settings | None = None) -> None:
    """创建上传目录与 SQLite 所在目录。"""

    current = settings or get_settings()
    current.upload_dir.mkdir(parents=True, exist_ok=True)
    path = _sqlite_path(current.database_url)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite_connection(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:  # 内存库不支持 WAL
            pass
    finally:
        cursor.close()


def create_engine_for(url: str, *, echo: bool = False) -> Engine:
    """按 URL 创建引擎；SQLite 自动开启 foreign_keys / WAL / busy_timeout。"""

    kwargs: dict[str, Any] = {"echo": echo, "future": True}
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        database = parsed.database or ""
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 5.0}
        if database in ("", ":memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if parsed.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


engine: Engine = create_engine_for(get_settings().database_url, echo=get_settings().sql_echo)
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def get_session_factory(bind: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=bind, autoflush=False, expire_on_commit=False, future=True)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI 依赖：优先使用 app.state.session_factory（便于测试注入）。"""

    factory: sessionmaker[Session] | None = getattr(
        request.app.state, "session_factory", None
    )
    session_factory = factory or SessionLocal
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope(factory: sessionmaker[Session] | None = None) -> Iterator[Session]:
    """非请求场景（CLI / 测试）使用的会话上下文。"""

    current = (factory or SessionLocal)()
    try:
        yield current
        current.commit()
    except Exception:
        current.rollback()
        raise
    finally:
        current.close()


def init_db(engine_: Engine | None = None, settings: Settings | None = None) -> None:
    """创建目录并 create_all。Alembic 迁移在集成阶段统一生成。"""

    from backend import models  # noqa: F401  # 确保 Base.metadata 完整

    current_settings = settings or get_settings()
    ensure_directories(current_settings)
    Base.metadata.create_all(bind=engine_ or engine)
