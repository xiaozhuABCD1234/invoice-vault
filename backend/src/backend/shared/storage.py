"""通用文件存储。

存储键格式：yyyy/mm/{sha256前两位}/{sha256}.{ext}，数据库只保存相对键。
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .db import utcnow

_ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
_WHITESPACE = re.compile(r"\s+")
_EXTENSION = re.compile(r"[^a-zA-Z0-9]")


def upload_root(settings: Settings | None = None) -> Path:
    current = settings or get_settings()
    return Path(current.upload_dir)


def sanitize_extension(ext: str | None) -> str:
    if not ext:
        return "bin"
    cleaned = _EXTENSION.sub("", ext.strip().lstrip(".").lower())
    return cleaned[:12] or "bin"


def sanitize_filename(name: str | None, *, max_length: int = 150) -> str:
    """NFKC 规范化、去掉非法字符并限制长度，保留扩展名。"""

    normalized = unicodedata.normalize("NFKC", name or "").strip()
    normalized = _ILLEGAL_FILENAME_CHARS.sub("_", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip(" .")
    if not normalized:
        return "file"

    stem, suffix = os.path.splitext(normalized)
    suffix = suffix[:20]
    if not stem:
        stem = "file"
    max_stem = max(1, max_length - len(suffix))
    stem = stem[:max_stem].strip(" .") or "file"
    return stem + suffix


def save_bytes(
    data: bytes,
    ext: str,
    created_at: datetime | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """按内容哈希落盘，返回 storage_key / sha256 / size_bytes。"""

    digest = hashlib.sha256(data).hexdigest()
    timestamp = created_at or utcnow()
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(UTC)
    normalized_ext = sanitize_extension(ext)
    storage_key = f"{timestamp.year:04d}/{timestamp.month:02d}/{digest[:2]}/{digest}.{normalized_ext}"

    root = upload_root(settings)
    path = root / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temp_path.write_bytes(data)
        os.replace(temp_path, path)

    return {
        "storage_key": storage_key,
        "sha256": digest,
        "size_bytes": len(data),
    }


def resolve_path(storage_key: str, *, settings: Settings | None = None) -> Path:
    """把相对存储键解析为绝对路径，拒绝目录穿越。"""

    key = Path(storage_key)
    if key.is_absolute() or any(part == ".." for part in key.parts):
        raise ValueError("非法存储路径")

    root = upload_root(settings).resolve()
    candidate = (root / key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("非法存储路径") from exc
    return candidate
