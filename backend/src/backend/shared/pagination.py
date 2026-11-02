"""分页辅助。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PageParams:
    """可直接用 Depends(PageParams) 注入的分页参数。"""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="每页条数")] = DEFAULT_PAGE_SIZE,
    ) -> None:
        self.page = page
        self.page_size = page_size


def normalize_page(page: int, page_size: int) -> tuple[int, int]:
    return max(1, page), min(max(1, page_size), MAX_PAGE_SIZE)


def paginate(
    db: Session,
    query: Select[Any],
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    """执行 count + 分页查询，返回与 Page[T] schema 对应的字典。"""

    current_page, current_size = normalize_page(page, page_size)
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = int(db.scalar(count_query) or 0)
    items = list(
        db.scalars(
            query.offset((current_page - 1) * current_size).limit(current_size)
        ).all()
    )
    return {
        "items": items,
        "total": total,
        "page": current_page,
        "page_size": current_size,
    }
