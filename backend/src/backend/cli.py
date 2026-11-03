"""命令行工具：创建管理员、写入默认类别。"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .categories.service import seed_default_categories
from .models.user import User
from .shared.config import get_settings
from .shared.db import create_engine_for, get_session_factory, init_db
from .shared.enums import Role
from .shared.security import hash_password


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend", description="发票管理系统后端命令行")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin = subparsers.add_parser("create-admin", help="创建或重置管理员账号")
    create_admin.add_argument("--username", default="admin", help="用户名，默认 admin")
    create_admin.add_argument("--password", default=None, help="密码（不传则交互输入）")
    create_admin.add_argument("--display-name", default=None, help="显示名，默认与用户名相同")

    subparsers.add_parser("seed-categories", help="类别表为空时写入默认类别")
    return parser


def _read_password(provided: str | None) -> str | None:
    if provided:
        return provided
    try:
        first = getpass.getpass("请输入密码: ")
        second = getpass.getpass("请再次输入密码: ")
    except (EOFError, KeyboardInterrupt):  # pragma: no cover - 交互终端
        return None
    if first != second:
        print("两次输入的密码不一致", file=sys.stderr)
        return None
    return first


def _open_session() -> sessionmaker[Session]:
    settings = get_settings()
    engine = create_engine_for(settings.database_url, echo=settings.sql_echo)
    init_db(engine, settings)
    return get_session_factory(engine)


def _create_admin(args: argparse.Namespace) -> int:
    username = (args.username or "").strip()
    if not username:
        print("用户名不能为空", file=sys.stderr)
        return 2
    password = _read_password(args.password)
    if not password:
        print("密码不能为空", file=sys.stderr)
        return 2
    if len(password) < 8:
        print("警告：密码少于 8 位，仅建议本地开发使用", file=sys.stderr)
    display_name = (args.display_name or username).strip() or username

    factory = _open_session()
    with factory() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is None:
            user = User(
                username=username,
                display_name=display_name,
                password_hash=hash_password(password),
                role=Role.ADMIN.value,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"管理员已创建：{username}")
            return 0

        existing.display_name = display_name
        existing.role = Role.ADMIN.value
        existing.is_active = True
        existing.password_hash = hash_password(password)
        existing.token_version = int(existing.token_version or 0) + 1
        db.commit()
        print(f"管理员已更新：{username}")
        return 0


def _seed_categories() -> int:
    factory = _open_session()
    with factory() as db:
        inserted = seed_default_categories(db)
    if inserted:
        print(f"已写入默认类别 {inserted} 条")
    else:
        print("类别表非空，跳过默认种子")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "create-admin":
        return _create_admin(args)
    if args.command == "seed-categories":
        return _seed_categories()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
