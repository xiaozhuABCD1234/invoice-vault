"""上传文件的大小、MIME 与 magic bytes 校验。

只允许 PDF / JPEG / PNG / WebP；文件名仅作展示，扩展名以实际内容为准。
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from ..shared.errors import BadRequestError

_EXT_BY_MIME: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
ALLOWED_MIMES: frozenset[str] = frozenset(_EXT_BY_MIME)
_MIME_BY_EXT: dict[str, str] = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
_MIME_ALIASES: dict[str, str] = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
    "application/x-pdf": "application/pdf",
    "image/x-png": "image/png",
}
_TEXT_MARKERS: tuple[bytes, ...] = (
    b"<svg",
    b"<?xml",
    b"<!doctype",
    b"<html",
    b"<head",
    b"<body",
    b"<script",
    b"<iframe",
    b"<object",
    b"javascript:",
    b"vbscript:",
    b"<%",
)


@dataclass(frozen=True, slots=True)
class DetectedFile:
    mime_type: str
    extension: str


def normalize_mime(value: str | None) -> str | None:
    if not value:
        return None
    mime = value.split(";", 1)[0].strip().lower()
    if not mime:
        return None
    return _MIME_ALIASES.get(mime, mime)


def extension_for_mime(mime: str | None) -> str | None:
    normalized = normalize_mime(mime)
    if normalized is None:
        return None
    return _EXT_BY_MIME.get(normalized)


def mime_for_extension(extension: str | None) -> str | None:
    if not extension:
        return None
    return _MIME_BY_EXT.get(extension.strip().lstrip(".").lower())


def detect_mime(data: bytes) -> DetectedFile | None:
    """按 magic bytes 识别文件类型；未知类型返回 None。"""

    if data.startswith(b"%PDF-"):
        return DetectedFile("application/pdf", "pdf")
    if data.startswith(b"\xff\xd8\xff"):
        return DetectedFile("image/jpeg", "jpg")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedFile("image/png", "png")
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return DetectedFile("image/webp", "webp")
    return None


def validate_upload(
    data: bytes,
    *,
    filename: str | None,
    content_type: str | None,
    max_bytes: int,
) -> DetectedFile:
    """校验大小、MIME 与 magic bytes；返回实际文件类型。"""

    if not data:
        raise BadRequestError("empty_file", "上传文件为空")
    if len(data) > max_bytes:
        raise BadRequestError(
            "file_too_large",
            f"文件大小超过限制（上限 {max_bytes} 字节）",
            {"max_upload_bytes": max_bytes, "size_bytes": len(data)},
        )

    header = data[:2048].lstrip(b"\xef\xbb\xbf").lstrip().lower()
    for marker in _TEXT_MARKERS:
        if marker in header:
            raise BadRequestError(
                "invalid_file_type", "不支持的文件类型：仅允许 PDF/JPEG/PNG/WebP"
            )

    detected = detect_mime(data)
    if detected is None:
        raise BadRequestError(
            "invalid_file_type", "无法识别的文件内容：仅允许 PDF/JPEG/PNG/WebP"
        )

    declared = normalize_mime(content_type)
    if declared in ALLOWED_MIMES:
        if declared != detected.mime_type:
            raise BadRequestError(
                "invalid_file_type",
                "文件内容与声明的 MIME 类型不一致",
                {"declared_mime": declared, "detected_mime": detected.mime_type},
            )
        return detected

    if declared not in (None, "application/octet-stream"):
        raise BadRequestError(
            "invalid_file_type", "不支持的文件类型：仅允许 PDF/JPEG/PNG/WebP"
        )

    suffix = Path(filename or "").suffix.lstrip(".").lower()
    guessed = mimetypes.guess_type(filename or "")[0]
    expected = _MIME_BY_EXT.get(suffix) or normalize_mime(guessed)
    if expected is not None and expected != detected.mime_type:
        raise BadRequestError(
            "invalid_file_type",
            "文件内容与文件扩展名不一致",
            {"detected_mime": detected.mime_type, "extension": suffix},
        )
    return detected
