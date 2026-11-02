"""Alembic 环境：读取应用配置并使用 SQLite batch 模式。"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from backend import models  # noqa: F401  # 注册全部模型到 Base.metadata
from backend.shared.config import get_settings
from backend.shared.db import Base, create_engine_for

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# ConfigParser 会做 % 插值，连接串中的百分号需要转义。
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """自定义 UTC 时间类型在迁移中落地为普通 DateTime。"""

    if type_ == "type" and obj.__class__.__name__ == "UTCDateTime":
        return "sa.DateTime()"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine_for(settings.database_url, echo=settings.sql_echo)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,
            compare_server_default=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
