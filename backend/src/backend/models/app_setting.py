"""应用配置：数据库覆盖层与版本历史。

`app_settings` 只存"管理员显式设置过"的键；未出现的键回落到环境变量 /
backend/.env / 代码默认值（见 extraction/config.py）。`app_setting_revisions`
保存每次变更的完整快照，用于回滚与审计追溯。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.db import Base, TZDateTime, utcnow


class AppSetting(Base):
    """单个配置项（key 形如 `extraction.provider`）。"""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    value_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by = relationship("User", foreign_keys=[updated_by_id])


class AppSettingRevision(Base):
    """配置快照，一次保存/回滚/重置生成一条。"""

    __tablename__ = "app_setting_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow, index=True
    )

    actor = relationship("User", foreign_keys=[actor_id])

    @property
    def actor_name(self) -> str | None:
        return self.actor.display_name if self.actor is not None else None

    @property
    def snapshot(self) -> Any:
        return self.snapshot_json
