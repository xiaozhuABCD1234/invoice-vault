"""识别引擎 provider 实现。

统一接口：``provider.extract(document, version, config) -> ExtractionResult``。
provider 只负责把文件转成原始字段；字段规范化与规则校验见 normalize.py。
所有网络调用都通过 `_http_post_json`，测试可 monkeypatch 该函数避免访问外网。
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import re
import unicodedata
import urllib.request
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from ..models.document import Document, DocumentVersion
from ..shared.enums import ExtractionProvider
from ..shared.storage import resolve_path
from .config import AUTO_PROVIDER, ExtractionConfig
from .normalize import normalize_fields

logger = logging.getLogger(__name__)

#: 调用外部识别服务时使用的显式 UA，避免被 CDN/WAF 按默认 Python UA 拦截
USER_AGENT = "invoice-vault/1.0"


class ProviderError(Exception):
    """识别引擎失败。code 用于写入 extraction_jobs.error_code。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class ExtractionResult:
    provider: str
    fields: dict[str, Any]
    confidence: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    raw_text: str | None = None
    raw_response: Any = None
    model: str | None = None
    prompt_version: str | None = None


class _UploadRoot:
    """resolve_path 只需要 upload_dir 属性，避免为了读取文件构造完整 Settings。"""

    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = Path(upload_dir)


def resolve_version_path(version: DocumentVersion, config: ExtractionConfig) -> Path:
    """把版本 storage_key 解析为磁盘路径，并拒绝目录穿越。"""

    if not version.storage_key:
        raise ProviderError("invalid_storage_key", "文件存储路径为空")
    try:
        path = resolve_path(version.storage_key, settings=_UploadRoot(config.upload_dir))
    except ValueError as exc:
        raise ProviderError("invalid_storage_key", "文件存储路径非法") from exc
    if not path.is_file():
        raise ProviderError("file_missing", "文件不存在")
    return path


# ---------------------------------------------------------------------------
# pdf_text 文本层解析
# ---------------------------------------------------------------------------

_AMOUNT = r"[¥￥]?\s*(-?\d[\d,]*\.\d{2})"
_INVOICE_NUMBER_PATTERN = re.compile(r"发票号码\s*[:：]?\s*(\d{8,20})")
_INVOICE_CODE_PATTERN = re.compile(r"发票代码\s*[:：]?\s*(\d{10,12})")
_ISSUE_DATE_PATTERN = re.compile(
    r"开票日期\s*[:：]?\s*(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})"
)
_GENERIC_DATE_PATTERN = re.compile(
    r"(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})"
)
_TOTAL_PATTERN = re.compile(
    r"(?:价税合计|票价)[^\n]{0,40}?[¥￥]\s*(-?\s*\d[\d,]*\.\d{2})"
)
_TOTAL_FALLBACK_PATTERN = re.compile(
    r"(?:价税合计|合计金额|小写|票价)[^\n]{0,40}?(-?\s*\d[\d,]*\.\d{2})"
)
_TAX_PATTERN = re.compile(r"税额\s*[:：]\s*" + _AMOUNT)
_EX_TAX_PATTERN = re.compile(r"(?:不含税金额|合计金额|金额)\s*[:：]\s*" + _AMOUNT)
_SELLER_PATTERN = re.compile(
    r"(?:销(?:售)?方(?:信息)?)[^\n]{0,20}?名称\s*[:：]\s*([^\n\s]+)"
)
_BUYER_PATTERN = re.compile(
    r"(?:购(?:买)?方(?:信息)?)[^\n]{0,30}?名称\s*[:：]\s*([^\n\s]+)"
)
_TAX_ID_PATTERN = re.compile(
    r"(?:统一社会信用代码|纳税人识别号|税号)\s*[:：]\s*([0-9A-Z]{15,20})"
)
_PARTY_LABEL_PATTERN = re.compile(r"(购买方|购方|销售方|销方)")
_ITEM_PATTERN = re.compile(
    r"^\*?([^\s]+)\s+(\d+(?:\.\d{1,3})?)\s+([\d,]+\.\d{1,3})\s+([\d,]+\.\d{2})"
    r"\s+(\d+(?:\.\d+)?)%\s+([\d,]+\.\d{2})\s*$",
    re.MULTILINE,
)
_INVOICE_TYPE_PATTERN = re.compile(
    r"(电子发票(?:\([^)]*\))?|数电票|增值税专用发票|增值税普通发票)"
)

#: 普通模式缺失这些字段时，再用版式模式解析一遍并补齐
_LAYOUT_RETRY_FIELDS: tuple[str, ...] = (
    "invoice_number",
    "issue_date",
    "total_cents",
    "seller_name",
    "buyer_name",
    "items",
)


def _amount_to_cents(raw: str) -> int:
    return int(round(float(re.sub(r"\s+", "", raw).replace(",", "")) * 100))


def _parse_tax_ids(text: str) -> dict[str, str]:
    """按最近的购/销方标签归属税号，避免买卖双方税号串位。"""

    fields: dict[str, str] = {}
    for match in _TAX_ID_PATTERN.finditer(text):
        context = text[max(0, match.start() - 200) : match.start()]
        labels = _PARTY_LABEL_PATTERN.findall(context)
        key = "buyer_tax_id"
        if labels and labels[-1].startswith("销"):
            key = "seller_tax_id"
        fields.setdefault(key, match.group(1))
    return fields


def parse_invoice_text(text: str) -> dict[str, Any]:
    """从 PDF/OCR 文本中尽力解析发票字段；解析不到的字段不返回。"""

    if not text or not text.strip():
        return {}
    normalized = unicodedata.normalize("NFKC", text)
    fields: dict[str, Any] = {}

    match = _INVOICE_NUMBER_PATTERN.search(normalized)
    if match is None:
        match = re.search(r"(?<!\d)(\d{20})(?!\d)", normalized)
    if match is not None:
        fields["invoice_number"] = match.group(1)

    match = _INVOICE_CODE_PATTERN.search(normalized)
    if match is not None:
        fields["invoice_code"] = match.group(1)

    match = _ISSUE_DATE_PATTERN.search(normalized) or _GENERIC_DATE_PATTERN.search(normalized)
    if match is not None:
        try:
            fields["issue_date"] = date(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            ).isoformat()
        except ValueError:
            pass

    match = _SELLER_PATTERN.search(normalized)
    if match is not None:
        fields["seller_name"] = match.group(1).strip()
    match = _BUYER_PATTERN.search(normalized)
    if match is not None:
        fields["buyer_name"] = match.group(1).strip()
    fields.update(_parse_tax_ids(normalized))

    match = _TOTAL_PATTERN.search(normalized) or _TOTAL_FALLBACK_PATTERN.search(normalized)
    if match is not None:
        fields["total_cents"] = _amount_to_cents(match.group(1))

    match = _TAX_PATTERN.search(normalized)
    if match is not None:
        fields["tax_cents"] = _amount_to_cents(match.group(1))

    match = _EX_TAX_PATTERN.search(normalized)
    if match is not None:
        fields["amount_ex_tax_cents"] = _amount_to_cents(match.group(1))

    match = _INVOICE_TYPE_PATTERN.search(normalized)
    if match is not None:
        fields["invoice_type"] = match.group(1)

    items: list[dict[str, Any]] = []
    for index, item_match in enumerate(_ITEM_PATTERN.finditer(normalized)):
        name = item_match.group(1)
        if "*" in name:
            name = name.rsplit("*", 1)[-1]
        if not name:
            continue
        items.append(
            {
                "name": name,
                "quantity": float(item_match.group(2)),
                "unit_price_millis": int(round(float(item_match.group(3).replace(",", "")) * 1000)),
                "amount_cents": _amount_to_cents(item_match.group(4)),
                "sort_order": index,
            }
        )
    if items:
        fields["items"] = items

    amount_ex_tax = fields.get("amount_ex_tax_cents")
    tax = fields.get("tax_cents")
    if isinstance(amount_ex_tax, int) and isinstance(tax, int) and amount_ex_tax > 0:
        fields["tax_rate_bp"] = int(round(tax / amount_ex_tax * 10000))
    return fields


# ---------------------------------------------------------------------------
# HTTP helper（可被测试 monkeypatch）
# ---------------------------------------------------------------------------


def _http_post_json(
    url: str,
    body: bytes,
    *,
    timeout: float,
    headers: Mapping[str, str] | None = None,
) -> Any:
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            # 不少 OpenAI 兼容网关挂在 Cloudflare 后面，会按 UA 拦截
            # Python-urllib 默认标识（HTTP 403 / error code 1010）。
            "User-Agent": USER_AGENT,
            **(dict(headers) if headers else {}),
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError("invalid_json_response", "识别服务返回的不是合法 JSON") from exc


def _clamp(value: float) -> float:
    return round(min(max(float(value), 0.0), 1.0), 4)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class BaseProvider:
    """provider 统一接口。"""

    name: str = ""

    def is_configured(self, config: ExtractionConfig) -> bool:
        return True

    def extract(
        self,
        document: Document | None,
        version: DocumentVersion,
        config: ExtractionConfig,
        *,
        path: Path | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError

    @staticmethod
    def _path(version: DocumentVersion, config: ExtractionConfig, path: Path | None) -> Path:
        return Path(path) if path is not None else resolve_version_path(version, config)


MOCK_FIELDS: dict[str, Any] = {
    "invoice_number": "24512000000012345678",
    "invoice_code": "024001900111",
    "invoice_type": "电子发票（普通发票）",
    "issue_date": "2026-07-12",
    "seller_name": "测试商户",
    "seller_tax_id": "91320200MA1TEST001",
    "buyer_name": "测试购方",
    "buyer_tax_id": "91320200MA1TEST002",
    "amount_ex_tax_cents": 10000,
    "tax_cents": 1300,
    "total_cents": 11300,
    "tax_rate_bp": 1300,
    "invoice_form": "electronic",
    "items": [
        {
            "name": "螺栓",
            "quantity": 10,
            "unit_price_millis": 1000,
            "amount_cents": 10000,
            "sort_order": 0,
        }
    ],
}


class MockProvider(BaseProvider):
    """测试用固定发票；通过 IV_EXTRACTION_PROVIDER=mock 选择。"""

    name = ExtractionProvider.MOCK.value

    def extract(
        self,
        document: Document | None,
        version: DocumentVersion,
        config: ExtractionConfig,
        *,
        path: Path | None = None,
    ) -> ExtractionResult:
        fields = copy.deepcopy(MOCK_FIELDS)
        return ExtractionResult(
            provider=self.name,
            fields=fields,
            confidence=0.95,
            field_confidence={key: 0.95 for key in fields},
            raw_text="MOCK PROVIDER: 24512000000012345678 价税合计 113.00",
            raw_response={"provider": self.name, "fields": fields},
            model="mock-v1",
            prompt_version="mock-v1",
        )


_FONT_FILE_KEYS = ("/FontFile", "/FontFile2", "/FontFile3")


def _resolve_pdf_object(value: Any) -> Any:
    """解引用 pypdf 的 IndirectObject；普通 dict 原样返回。"""

    getter = getattr(value, "get_object", None)
    if callable(getter):
        try:
            return getter()
        except Exception:  # pragma: no cover - 损坏的间接引用
            return value
    return value


def _font_descriptors(font: Mapping[str, Any]) -> list[Any]:
    descriptors: list[Any] = []
    direct = font.get("/FontDescriptor")
    if direct is not None:
        descriptors.append(direct)

    descendants = _resolve_pdf_object(font.get("/DescendantFonts")) or ()
    if not isinstance(descendants, (list, tuple)):
        return descriptors
    for descendant in descendants:
        resolved = _resolve_pdf_object(descendant)
        if not isinstance(resolved, Mapping):
            continue
        descriptor = resolved.get("/FontDescriptor")
        if descriptor is not None:
            descriptors.append(descriptor)
    return descriptors


def _relax_font_descriptors(reader: Any) -> int:
    """容忍同时声明多个字体文件的 FontDescriptor，返回修复数量。

    pypdf 6 遇到同一字体描述里同时有 /FontFile2 与 /FontFile3 会直接抛
    PdfReadError，但部分电子发票 PDF 会把两个键指向同一个字体流。
    这里只保留一个（优先 TrueType 的 /FontFile2），让文本层仍可读取。
    """

    patched = 0
    seen: set[int] = set()
    try:
        pages = list(reader.pages)
    except Exception:  # pragma: no cover - 无页面的损坏文件
        return 0

    for page in pages:
        try:
            resources = _resolve_pdf_object(page.get("/Resources", {}))
            fonts = _resolve_pdf_object(resources.get("/Font", {})) if resources else {}
            font_objects = list(fonts.values()) if hasattr(fonts, "values") else []
        except Exception:  # pragma: no cover - 结构异常时保持原样
            continue

        for font_ref in font_objects:
            font = _resolve_pdf_object(font_ref)
            if not isinstance(font, Mapping):
                continue
            for descriptor_ref in _font_descriptors(font):
                descriptor = _resolve_pdf_object(descriptor_ref)
                if not isinstance(descriptor, MutableMapping):
                    continue
                if id(descriptor) in seen:
                    continue
                seen.add(id(descriptor))
                present = [key for key in _FONT_FILE_KEYS if key in descriptor]
                if len(present) <= 1:
                    continue
                keep = "/FontFile2" if "/FontFile2" in present else present[0]
                for key in present:
                    if key != keep:
                        del descriptor[key]
                patched += 1
    return patched


def _extract_pdf_text(
    reader: Any, *, layout: bool = False
) -> tuple[str, Exception | None]:
    """逐页读取文本层，返回 (文本, 首个错误)。

    单页字体/编码损坏不拖垮整份 PDF；layout=True 时按版面还原行，
    便于“标签 + 金额”同行的票据（如铁路电子客票）被正则命中。
    """

    pages: list[str] = []
    first_error: Exception | None = None
    for index, page in enumerate(reader.pages, start=1):
        try:
            if layout:
                try:
                    page_text = page.extract_text(extraction_mode="layout")
                except TypeError:
                    # 页面对象不支持版式参数（测试替身或旧接口）
                    return "", None
            else:
                page_text = page.extract_text()
            pages.append(page_text or "")
        except Exception as exc:
            logger.warning("PDF 第 %s 页文本层读取失败：%s", index, exc)
            if first_error is None:
                first_error = exc
            pages.append("")
    return "\n".join(pages).strip(), first_error


class PdfTextProvider(BaseProvider):
    """读取 PDF 文本层并用正则解析；无文本层或字段不足时抛出 ProviderError。"""

    name = ExtractionProvider.PDF_TEXT.value

    def extract(
        self,
        document: Document | None,
        version: DocumentVersion,
        config: ExtractionConfig,
        *,
        path: Path | None = None,
    ) -> ExtractionResult:
        file_path = self._path(version, config, path)
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - 依赖缺失
            raise ProviderError("pdf_text_unavailable", "未安装 pypdf，无法读取文本层") from exc

        try:
            reader = PdfReader(str(file_path))
        except Exception as exc:
            raise ProviderError("pdf_text_failed", f"读取 PDF 失败：{exc}") from exc

        _relax_font_descriptors(reader)

        try:
            text, first_error = _extract_pdf_text(reader)
        except Exception as exc:
            raise ProviderError("pdf_text_failed", f"读取 PDF 失败：{exc}") from exc

        if len(text) < 10:
            if first_error is not None:
                raise ProviderError(
                    "pdf_text_failed", f"读取 PDF 文本层失败：{first_error}"
                ) from first_error
            raise ProviderError("pdf_text_unavailable", "PDF 没有可用的文本层，请使用 OCR 引擎")

        fields = parse_invoice_text(text)
        if any(not fields.get(key) for key in _LAYOUT_RETRY_FIELDS):
            # 普通模式按内容流顺序输出，竖排/表格类 PDF 容易把标签与金额
            # 拆散；此时再用版式模式补一次，只补缺失字段，已识别值优先。
            layout_text, _ = _extract_pdf_text(reader, layout=True)
            if layout_text and layout_text != text:
                layout_fields = parse_invoice_text(layout_text)
                merged = False
                for key, value in layout_fields.items():
                    if value is None or value == "" or value == []:
                        continue
                    if key == "items":
                        if not fields.get("items"):
                            fields["items"] = value
                            merged = True
                    elif key not in fields:
                        fields[key] = value
                        merged = True
                if merged:
                    text = layout_text

        if not fields.get("invoice_number") and not fields.get("total_cents"):
            raise ProviderError("pdf_text_insufficient", "PDF 文本层未解析出发票字段")

        return ExtractionResult(
            provider=self.name,
            fields=fields,
            confidence=0.8,
            field_confidence={key: 0.8 for key in fields},
            raw_text=text,
            raw_response={"text": text},
            model="pypdf",
            prompt_version="pdf-text-v1",
        )


def _block_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        for key in ("text", "words", "transcription"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value
        nested = item.get("result")
        if nested is not None:
            return _ocr_text(nested)
        return ""
    if isinstance(item, (list, tuple)):
        for element in item:
            if (
                isinstance(element, (list, tuple))
                and len(element) == 2
                and isinstance(element[0], str)
            ):
                return element[0]
            if isinstance(element, str) and len(element.strip()) > 1:
                return element
    return ""


def _ocr_text(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, Mapping):
        for key in ("text_blocks", "texts", "lines"):
            value = response.get(key)
            if isinstance(value, (list, tuple)):
                joined = "\n".join(text for text in (_block_text(item) for item in value) if text)
                if joined.strip():
                    return joined
        for key in ("text", "content"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value
        if response.get("result") is not None:
            return _ocr_text(response.get("result"))
        return ""
    if isinstance(response, (list, tuple)):
        joined = "\n".join(text for text in (_block_text(item) for item in response) if text)
        if joined.strip():
            return joined
        return "\n".join(text for text in (_ocr_text(item) for item in response) if text)
    return ""


def _response_confidence(response: Any) -> float | None:
    if isinstance(response, Mapping):
        for key in ("confidence", "score", "mean_confidence"):
            value = response.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return _clamp(float(value))
    return None


class PaddleOcrProvider(BaseProvider):
    """调用配置的本地 PaddleOCR HTTP 端点。"""

    name = ExtractionProvider.PADDLEOCR_LOCAL.value

    def is_configured(self, config: ExtractionConfig) -> bool:
        return bool(config.paddleocr_endpoint)

    def extract(
        self,
        document: Document | None,
        version: DocumentVersion,
        config: ExtractionConfig,
        *,
        path: Path | None = None,
    ) -> ExtractionResult:
        if not config.paddleocr_endpoint:
            raise ProviderError(
                "paddleocr_not_configured",
                "未配置本地 PaddleOCR 服务地址（IV_PADDLEOCR_ENDPOINT）",
            )
        file_path = self._path(version, config, path)
        try:
            payload = {
                "file_name": version.original_name,
                "mime_type": version.mime_type,
                "file_base64": base64.b64encode(file_path.read_bytes()).decode("ascii"),
            }
        except OSError as exc:
            raise ProviderError("file_missing", "文件不存在") from exc

        try:
            response = _http_post_json(
                config.paddleocr_endpoint,
                json.dumps(payload).encode("utf-8"),
                timeout=config.http_timeout,
            )
        except ProviderError:
            raise
        except Exception as exc:  # 网络/解析等失败统一转成 ProviderError
            raise ProviderError("paddleocr_request_failed", f"PaddleOCR 调用失败：{exc}") from exc

        text = _ocr_text(response).strip()
        if not text:
            raise ProviderError("paddleocr_empty", "PaddleOCR 未返回文本")
        fields = parse_invoice_text(text)
        if not fields.get("invoice_number") and not fields.get("total_cents"):
            raise ProviderError("paddleocr_insufficient", "PaddleOCR 文本未解析出发票字段")
        confidence = _response_confidence(response) or 0.6
        return ExtractionResult(
            provider=self.name,
            fields=fields,
            confidence=confidence,
            field_confidence={key: confidence for key in fields},
            raw_text=text,
            raw_response=response,
            model="paddleocr",
            prompt_version="ocr-v1",
        )


_LLM_PROMPT = """你是发票识别助手。请识别发票图片，只返回一个 JSON 对象（不要 ``` 代码块），字段如下：
invoice_number, invoice_code, invoice_type, issue_date (YYYY-MM-DD), seller_name, seller_tax_id,
buyer_name, buyer_tax_id, amount_ex_tax_cents (整数分), tax_cents (整数分), total_cents (整数分),
tax_rate_bp (万分比), invoice_form (electronic/paper), items (数组，元素含 name, quantity,
unit_price_millis, amount_cents)。无法确定的字段请省略。金额一律使用整数分，禁止浮点数。"""


def _llm_content(response: Any) -> str:
    if isinstance(response, Mapping):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], Mapping) else None
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [
                        part.get("text", "")
                        for part in content
                        if isinstance(part, Mapping) and isinstance(part.get("text"), str)
                    ]
                    return "".join(parts)
    if isinstance(response, str):
        return response
    return ""


def _parse_json_object(text: str) -> dict[str, Any]:
    content = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if fence is not None:
        content = fence.group(1).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end <= start:
        raise ProviderError("llm_invalid_response", "大模型未返回 JSON 对象")
    try:
        data = json.loads(content[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderError("llm_invalid_response", "大模型返回的 JSON 无法解析") from exc
    if not isinstance(data, dict):
        raise ProviderError("llm_invalid_response", "大模型返回的 JSON 不是对象")
    return data


class MultimodalLlmProvider(BaseProvider):
    """OpenAI 兼容多模态接口；默认关闭。"""

    name = ExtractionProvider.MULTIMODAL_LLM.value

    def is_configured(self, config: ExtractionConfig) -> bool:
        return bool(
            config.llm_enabled
            and config.llm_endpoint
            and config.llm_api_key
            and config.llm_model
        )

    def extract(
        self,
        document: Document | None,
        version: DocumentVersion,
        config: ExtractionConfig,
        *,
        path: Path | None = None,
    ) -> ExtractionResult:
        if not config.llm_enabled:
            raise ProviderError(
                "llm_disabled", "多模态大模型识别默认关闭（IV_LLM_ENABLED=true 后才启用）"
            )
        if not (config.llm_endpoint and config.llm_api_key and config.llm_model):
            raise ProviderError(
                "llm_not_configured",
                "未配置大模型接口（IV_LLM_ENDPOINT/IV_LLM_API_KEY/IV_LLM_MODEL）",
            )
        file_path = self._path(version, config, path)
        try:
            encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        except OSError as exc:
            raise ProviderError("file_missing", "文件不存在") from exc

        endpoint = config.llm_endpoint.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = endpoint + "/chat/completions"
        mime_type = (version.mime_type or "application/octet-stream").lower()
        data_uri = f"data:{mime_type};base64,{encoded}"
        if mime_type.startswith("image/"):
            media_part: dict[str, Any] = {
                "type": "image_url",
                "image_url": {"url": data_uri},
            }
        else:
            # OpenAI 兼容接口只接受图片走 image_url；PDF 必须用 file 内容块，
            # 否则网关会报 invalid_media（把 PDF 当作图片解码）。
            filename = Path(str(version.original_name or "")).name
            if not filename:
                filename = "invoice.pdf" if mime_type == "application/pdf" else "document"
            media_part = {
                "type": "file",
                "file": {"filename": filename, "file_data": data_uri},
            }
        payload = {
            "model": config.llm_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _LLM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请识别这张发票，按要求返回 JSON。"},
                        media_part,
                    ],
                },
            ],
        }
        try:
            response = _http_post_json(
                endpoint,
                json.dumps(payload).encode("utf-8"),
                timeout=config.http_timeout,
                headers={"Authorization": f"Bearer {config.llm_api_key}"},
            )
        except ProviderError:
            raise
        except Exception as exc:  # 网络/解析等失败统一转成 ProviderError
            raise ProviderError("llm_request_failed", f"大模型调用失败：{exc}") from exc

        fields = normalize_fields(_parse_json_object(_llm_content(response)))
        if not fields.get("invoice_number") and not fields.get("total_cents"):
            raise ProviderError("llm_insufficient", "大模型返回结果缺少发票号码与价税合计")
        return ExtractionResult(
            provider=self.name,
            fields=fields,
            confidence=0.7,
            field_confidence={key: 0.7 for key in fields},
            raw_text=None,
            raw_response=response,
            model=config.llm_model,
            prompt_version=config.prompt_version,
        )


_PROVIDERS: dict[str, BaseProvider] = {
    ExtractionProvider.MOCK.value: MockProvider(),
    ExtractionProvider.PDF_TEXT.value: PdfTextProvider(),
    ExtractionProvider.PADDLEOCR_LOCAL.value: PaddleOcrProvider(),
    ExtractionProvider.MULTIMODAL_LLM.value: MultimodalLlmProvider(),
}


def get_provider(name: str) -> BaseProvider:
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise ProviderError("unknown_provider", f"未知的识别引擎：{name}")
    return provider


def provider_chain(config: ExtractionConfig) -> tuple[str, ...]:
    """auto 模式按配置链路，否则只使用显式配置的 provider。"""

    if config.provider == AUTO_PROVIDER:
        return tuple(config.auto_chain)
    return (config.provider,)


_REQUIRED_CHAIN_FIELDS = ("invoice_number", "issue_date", "total_cents")


def _chain_complete(fields: Mapping[str, Any]) -> bool:
    return all(fields.get(key) not in (None, "") for key in _REQUIRED_CHAIN_FIELDS)


def _merge_chain_result(
    primary: ExtractionResult, extra: ExtractionResult
) -> ExtractionResult:
    """用后续引擎补齐 primary 缺失的字段；已有值保持优先。"""

    fields = dict(primary.fields)
    field_confidence = dict(primary.field_confidence)
    merged = False
    for key, value in extra.fields.items():
        if value in (None, "", []):
            continue
        if key == "items":
            if fields.get("items"):
                continue
        elif fields.get(key) not in (None, ""):
            continue
        fields[key] = value
        field_confidence[key] = extra.field_confidence.get(key, extra.confidence)
        merged = True
    if not merged:
        return primary
    added = ", ".join(sorted(set(fields) - set(primary.fields)))
    logger.info("识别结果由 %s 补齐字段：%s", extra.provider, added)
    return ExtractionResult(
        provider=primary.provider,
        fields=fields,
        confidence=max(primary.confidence, extra.confidence),
        field_confidence=field_confidence,
        raw_text=primary.raw_text or extra.raw_text,
        raw_response=(
            primary.raw_response
            if primary.raw_response is not None
            else extra.raw_response
        ),
        model=primary.model or extra.model,
        prompt_version=primary.prompt_version or extra.prompt_version,
    )


def run_provider_chain(
    chain: tuple[str, ...] | list[str],
    document: Document | None,
    version: DocumentVersion,
    config: ExtractionConfig,
    *,
    path: Path | None = None,
) -> ExtractionResult:
    """按链路依次尝试；单 provider 失败时保留原始错误码。

    某个引擎成功但缺少发票号码/开票日期/价税合计时，继续尝试后续引擎并
    补齐缺失字段，避免 pdf_text 只认出一半就停止。
    """

    names = tuple(chain)
    if not names:
        raise ProviderError("provider_failed", "没有可用的识别引擎")
    errors: list[str] = []
    single = len(names) == 1
    merged: ExtractionResult | None = None
    for name in names:
        provider = get_provider(name)
        if not provider.is_configured(config):
            if single:
                raise ProviderError(f"{name}_not_configured", f"识别引擎 {name} 未配置")
            errors.append(f"{name}: 未配置")
            continue
        try:
            result = provider.extract(document, version, config, path=path)
        except ProviderError as exc:
            logger.warning("识别引擎 %s 失败：%s", name, exc.message)
            if single:
                raise
            errors.append(f"{name}: {exc.message}")
            continue
        merged = result if merged is None else _merge_chain_result(merged, result)
        if _chain_complete(merged.fields):
            return merged
    if merged is not None:
        return merged
    detail = "；".join(errors) if errors else "没有可用的识别引擎"
    raise ProviderError("provider_failed", f"识别失败：{detail}")
