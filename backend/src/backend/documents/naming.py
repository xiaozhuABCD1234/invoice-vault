"""审核通过后的规范展示名（DESIGN §6）。

格式：金额-人员-商户或路线-类别-文档类型.扩展名

金额由整数分直接计算，不经过浮点；文件名统一交给 shared.storage.sanitize_filename
做 NFKC、非法字符替换与长度限制。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..shared.storage import sanitize_filename
from . import files

if TYPE_CHECKING:
    from ..models.document import DocumentVersion
    from ..models.invoice import Invoice
    from ..models.user import User

UNSPECIFIED_PERSON = "未指定"
UNSPECIFIED_MERCHANT = "未指定"
UNSPECIFIED_CATEGORY = "未分类"
INVOICE_DOCUMENT_TYPE = "发票"

#: 允许的文档扩展名（jpeg 统一归一为 jpg）
DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({"pdf", "jpg", "jpeg", "png", "webp"})


def format_cents(cents: int) -> str:
    """整数分 -> 两位小数字符串；全程整数运算，避免浮点误差。"""

    value = int(cents)
    sign = "-" if value < 0 else ""
    yuan, fen = divmod(abs(value), 100)
    return f"{sign}{yuan}.{fen:02d}"


def version_extension(version: DocumentVersion | None) -> str:
    """取当前版本实际扩展名：优先 storage_key，其次按 mime 推断。"""

    if version is None:
        return "bin"
    suffix = Path(version.storage_key or "").suffix.lstrip(".").lower()
    if suffix in DOCUMENT_EXTENSIONS:
        return "jpg" if suffix == "jpeg" else suffix
    by_mime = files.extension_for_mime(version.mime_type)
    if by_mime:
        return by_mime
    return suffix or "bin"


def person_names(requester: User | None, owner: User | None) -> str:
    """申购人 + 负责人，去重后用英文逗号连接；都为空时返回“未指定”。"""

    names: list[str] = []
    for user in (requester, owner):
        if user is None:
            continue
        display = (user.display_name or "").strip()
        if display and display not in names:
            names.append(display)
    return ",".join(names) or UNSPECIFIED_PERSON


def build_display_name(
    *,
    total_cents: int,
    requester: User | None,
    owner: User | None,
    seller_name: str | None,
    category_name: str | None,
    version: DocumentVersion | None,
) -> str:
    """生成管理员下载时使用的规范展示名（不含时间戳，带扩展名）。"""

    merchant = (seller_name or "").strip() or UNSPECIFIED_MERCHANT
    category = (category_name or "").strip() or UNSPECIFIED_CATEGORY
    stem = "-".join(
        (
            format_cents(total_cents),
            person_names(requester, owner),
            merchant,
            category,
            INVOICE_DOCUMENT_TYPE,
        )
    )
    return sanitize_filename(f"{stem}.{version_extension(version)}")


def build_for_invoice(invoice: Invoice, version: DocumentVersion | None) -> str:
    """按发票（含关系）生成规范展示名。"""

    return build_display_name(
        total_cents=int(invoice.total_cents),
        requester=invoice.requester,
        owner=invoice.owner,
        seller_name=invoice.seller_name,
        category_name=invoice.category.name if invoice.category is not None else None,
        version=version,
    )
