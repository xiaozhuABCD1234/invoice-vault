"""类别查询、维护与默认种子。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models.category import Category
from ..shared.audit import record_audit
from ..shared.enums import DEFAULT_CATEGORIES, CategoryKind
from ..shared.errors import BadRequestError, ConflictError, NotFoundError


def _snapshot(category: Category) -> dict[str, Any]:
    return {
        "id": category.id,
        "name": category.name,
        "kind": category.kind,
        "sort_order": category.sort_order,
        "is_active": category.is_active,
    }


def list_categories(
    db: Session,
    *,
    kind: CategoryKind | None = None,
    include_inactive: bool = False,
) -> list[Category]:
    stmt = select(Category)
    if kind is not None:
        stmt = stmt.where(Category.kind == kind.value)
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    kind_order = case((Category.kind == CategoryKind.PURCHASE.value, 0), else_=1)
    stmt = stmt.order_by(kind_order, Category.sort_order.asc(), Category.id.asc())
    return list(db.scalars(stmt).all())


def get_category_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("category_not_found", "类别不存在")
    return category


def _ensure_unique_name(
    db: Session,
    *,
    name: str,
    kind: str,
    exclude_id: int | None = None,
) -> None:
    stmt = select(Category).where(Category.name == name, Category.kind == kind)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError("category_exists", "同类别的类别名称已存在", {"name": name})


def create_category(
    db: Session,
    *,
    name: str,
    kind: CategoryKind,
    sort_order: int | None = None,
    actor_id: int | None,
    request: Any = None,
) -> Category:
    clean_name = name.strip()
    if not clean_name:
        raise BadRequestError("invalid_category_name", "类别名称不能为空")
    _ensure_unique_name(db, name=clean_name, kind=kind.value)

    if sort_order is None:
        max_order = db.scalar(
            select(func.max(Category.sort_order)).where(Category.kind == kind.value)
        )
        sort_order = int(max_order or 0) + 1

    category = Category(
        name=clean_name,
        kind=kind.value,
        sort_order=sort_order,
        is_active=True,
    )
    db.add(category)
    db.flush()
    record_audit(
        db,
        actor_id,
        "category.create",
        "category",
        category.id,
        after=_snapshot(category),
        request=request,
    )
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category_id: int,
    *,
    name: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
    actor_id: int | None,
    request: Any = None,
) -> Category:
    category = get_category_or_404(db, category_id)
    before = _snapshot(category)

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise BadRequestError("invalid_category_name", "类别名称不能为空")
        if clean_name != category.name:
            _ensure_unique_name(
                db, name=clean_name, kind=category.kind, exclude_id=category.id
            )
            category.name = clean_name
    if sort_order is not None:
        category.sort_order = sort_order
    if is_active is not None:
        category.is_active = is_active

    db.flush()
    record_audit(
        db,
        actor_id,
        "category.update",
        "category",
        category.id,
        before=before,
        after=_snapshot(category),
        request=request,
    )
    db.commit()
    db.refresh(category)
    return category


def seed_default_categories(db: Session) -> int:
    """categories 为空时写入默认种子，返回新增条数。"""

    existing = int(db.scalar(select(func.count()).select_from(Category)) or 0)
    if existing:
        return 0

    count = 0
    for kind, names in DEFAULT_CATEGORIES.items():
        for index, name in enumerate(names, start=1):
            db.add(Category(name=name, kind=kind.value, sort_order=index, is_active=True))
            count += 1
    db.commit()
    return count
