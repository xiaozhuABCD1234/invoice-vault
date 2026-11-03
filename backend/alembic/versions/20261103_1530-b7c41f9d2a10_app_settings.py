"""app settings

Revision ID: b7c41f9d2a10
Revises: e1bfd0b72bea
Create Date: 2026-11-03 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c41f9d2a10"
down_revision: Union[str, None] = "e1bfd0b72bea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_app_settings_key"), ["key"], unique=True)

    op.create_table(
        "app_setting_revisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("app_setting_revisions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_app_setting_revisions_created_at"),
            ["created_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_app_setting_revisions_scope"), ["scope"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("app_setting_revisions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_app_setting_revisions_scope"))
        batch_op.drop_index(batch_op.f("ix_app_setting_revisions_created_at"))

    op.drop_table("app_setting_revisions")
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_app_settings_key"))

    op.drop_table("app_settings")
