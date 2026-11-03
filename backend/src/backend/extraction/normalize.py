"""抽取结果规范化与规则校验。

输出字段名与 InvoiceCreate 保持一致（金额一律整数分），供人工审核页直接回填。
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

INVOICE_NUMBER_RE = re.compile(r"^\d{8,20}$")
INVOICE_CODE_RE = re.compile(r"^\d{10,12}$")
_DATE_PATTERN = re.compile(r"(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})")

CENTS_FIELDS: tuple[str, ...] = ("amount_ex_tax_cents", "tax_cents", "total_cents")
_KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        "invoice_number",
        "invoice_code",
        "invoice_type",
        "issue_date",
        "seller_name",
        "seller_tax_id",
        "buyer_name",
        "buyer_tax_id",
        "amount_ex_tax_cents",
        "tax_cents",
        "total_cents",
        "tax_rate_bp",
        "currency",
        "invoice_form",
        "note",
        "items",
    }
)

_ALIASES: dict[str, str] = {
    "invoiceNo": "invoice_number",
    "invoice_num": "invoice_number",
    "invoiceNumber": "invoice_number",
    "发票号码": "invoice_number",
    "invoiceCode": "invoice_code",
    "发票代码": "invoice_code",
    "invoiceType": "invoice_type",
    "发票类型": "invoice_type",
    "issueDate": "issue_date",
    "开票日期": "issue_date",
    "sellerName": "seller_name",
    "seller": "seller_name",
    "销售方名称": "seller_name",
    "销方名称": "seller_name",
    "销方": "seller_name",
    "sellerTaxId": "seller_tax_id",
    "seller_tax_no": "seller_tax_id",
    "销方税号": "seller_tax_id",
    "buyerName": "buyer_name",
    "buyer": "buyer_name",
    "购买方名称": "buyer_name",
    "购方名称": "buyer_name",
    "购方": "buyer_name",
    "buyerTaxId": "buyer_tax_id",
    "buyer_tax_no": "buyer_tax_id",
    "购方税号": "buyer_tax_id",
    "amountExTaxCents": "amount_ex_tax_cents",
    "amount_excluding_tax_cents": "amount_ex_tax_cents",
    "不含税金额": "amount_ex_tax_cents",
    "金额": "amount_ex_tax_cents",
    "taxCents": "tax_cents",
    "税额": "tax_cents",
    "totalCents": "total_cents",
    "totalAmountCents": "total_cents",
    "价税合计": "total_cents",
    "价税合计金额": "total_cents",
    "taxRateBp": "tax_rate_bp",
    "taxRate": "tax_rate_bp",
    "税率": "tax_rate_bp",
    "invoiceForm": "invoice_form",
    "发票形式": "invoice_form",
    "currency": "currency",
    "币种": "currency",
    "note": "note",
    "备注": "note",
    "items": "items",
    "明细": "items",
    "invoice_items": "items",
}

_ITEM_ALIASES: dict[str, str] = {
    "name": "name",
    "商品名称": "name",
    "名称": "name",
    "product_name": "name",
    "item_name": "name",
    "quantity": "quantity",
    "qty": "quantity",
    "数量": "quantity",
    "unitPriceMillis": "unit_price_millis",
    "unit_price_millis": "unit_price_millis",
    "unit_price": "unit_price_millis",
    "unitPrice": "unit_price_millis",
    "单价": "unit_price_millis",
    "amountCents": "amount_cents",
    "amount_cents": "amount_cents",
    "amount": "amount_cents",
    "总价": "amount_cents",
    "金额": "amount_cents",
    "note": "note",
    "备注": "note",
    "sortOrder": "sort_order",
    "sort_order": "sort_order",
}

_FORM_MAP = {
    "electronic": "electronic",
    "电子": "electronic",
    "电子发票": "electronic",
    "数电票": "electronic",
    "paper": "paper",
    "纸质": "paper",
    "纸质发票": "paper",
}


def _camel_to_snake(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", value)
    return text.lower()


def _map_key(key: Any) -> str | None:
    if not isinstance(key, str):
        return None
    raw = key.strip()
    if not raw:
        return None
    if raw in _ALIASES:
        return _ALIASES[raw]
    snake = _camel_to_snake(raw)
    if snake in _KNOWN_FIELDS:
        return snake
    return _ALIASES.get(snake)


def parse_iso_date(value: Any) -> str | None:
    """把日期字符串/日期对象统一成 ISO 日期。"""

    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return None
    match = _DATE_PATTERN.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return None
    compact = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", text)
    if compact:
        try:
            return date(
                int(compact.group(1)), int(compact.group(2)), int(compact.group(3))
            ).isoformat()
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None


def _clean_number_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip()
    return re.sub(r"\s+", "", text)


def _to_cents(value: Any) -> int | None:
    """整数按分解释；小数/带小数点的字符串按元换算成分。"""

    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        return int(round(value * 100))
    text = _clean_number_text(value)
    for token in ("¥", "￥", "元", ",", "CNY"):
        text = text.replace(token, "")
    if not text:
        return None
    try:
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        return int(round(float(text) * 100))
    except ValueError:
        return None


def _to_millis(value: Any) -> int | None:
    """整数按 1/1000 元解释；小数/带小数点的字符串按元换算。"""

    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value * 1000))
    text = _clean_number_text(value)
    for token in ("¥", "￥", "元", ",", "CNY"):
        text = text.replace(token, "")
    if not text:
        return None
    try:
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        return int(round(float(text) * 1000))
    except ValueError:
        return None


def _to_basis_points(value: Any) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = unicodedata.normalize("NFKC", value).strip()
        if text.endswith("%"):
            try:
                return int(round(float(text[:-1].strip()) * 100))
            except ValueError:
                return None
        value = text
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    if number >= 100:
        return int(round(number))
    if number >= 1:
        return int(round(number * 100))
    return int(round(number * 10000))


def _to_quantity(value: Any) -> float:
    if value is None or isinstance(value, bool):
        return 1.0
    try:
        quantity = float(value)
    except (TypeError, ValueError):
        return 1.0
    if quantity != quantity or quantity < 0:
        return 1.0
    return round(quantity, 3)


def _normalize_item(item: Any, index: int) -> dict[str, Any] | None:
    if isinstance(item, str):
        item = {"name": item}
    if not isinstance(item, Mapping):
        return None
    mapped: dict[str, Any] = {}
    for key, value in item.items():
        if not isinstance(key, str):
            continue
        field = _ITEM_ALIASES.get(key.strip())
        if field is None:
            field = _ITEM_ALIASES.get(_camel_to_snake(key.strip()))
        if field is not None:
            mapped[field] = value

    name = str(mapped.get("name") or "").strip()
    if not name:
        return None
    unit_price = _to_millis(mapped.get("unit_price_millis"))
    amount = _to_cents(mapped.get("amount_cents"))
    sort_order = mapped.get("sort_order")
    try:
        sort_order_value = int(sort_order) if sort_order is not None else index
    except (TypeError, ValueError):
        sort_order_value = index
    note = mapped.get("note")
    return {
        "name": name[:255],
        "quantity": _to_quantity(mapped.get("quantity")),
        "unit_price_millis": unit_price if unit_price is not None else 0,
        "amount_cents": amount if amount is not None else 0,
        "note": str(note)[:2000] if note else None,
        "sort_order": sort_order_value,
    }


def normalize_fields(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """把 provider 原始字段规范化为 InvoiceCreate 兼容的字典。"""

    if not isinstance(raw, Mapping):
        return {}

    result: dict[str, Any] = {}
    for key, value in raw.items():
        field = _map_key(key)
        if field is None or field not in _KNOWN_FIELDS:
            continue
        if value is None or value == "":
            continue

        if field in CENTS_FIELDS:
            cents = _to_cents(value)
            if cents is not None:
                result[field] = cents
        elif field == "issue_date":
            parsed = parse_iso_date(value)
            if parsed is not None:
                result[field] = parsed
        elif field == "tax_rate_bp":
            basis_points = _to_basis_points(value)
            if basis_points is not None:
                result[field] = basis_points
        elif field == "invoice_form":
            text = str(value).strip().lower()
            if text in _FORM_MAP:
                result[field] = _FORM_MAP[text]
            elif unicodedata.normalize("NFKC", str(value)).strip() in _FORM_MAP:
                result[field] = _FORM_MAP[unicodedata.normalize("NFKC", str(value)).strip()]
        elif field == "items":
            if isinstance(value, (list, tuple)):
                items = []
                for index, item in enumerate(value):
                    normalized = _normalize_item(item, index)
                    if normalized is not None:
                        items.append(normalized)
                if items:
                    result["items"] = items
        elif field in ("invoice_number", "invoice_code"):
            text = _clean_number_text(value)
            if text:
                result[field] = text[:64]
        elif field in ("seller_tax_id", "buyer_tax_id"):
            text = _clean_number_text(value)
            if text:
                result[field] = text[:64]
        elif field in ("seller_name", "buyer_name", "invoice_type"):
            text = str(value).strip()
            if text:
                result[field] = text[:255]
        elif field == "currency":
            text = str(value).strip().upper()[:8]
            if text:
                result[field] = text
        elif field == "note":
            text = str(value).strip()
            if text:
                result[field] = text[:4000]

    if (
        "total_cents" not in result
        and "amount_ex_tax_cents" in result
        and "tax_cents" in result
    ):
        result["total_cents"] = result["amount_ex_tax_cents"] + result["tax_cents"]
    return result


def _invoice_number_exists(db: Session, invoice_number: str) -> bool:
    from ..models.invoice import Invoice

    return (
        db.scalar(select(Invoice.id).where(Invoice.invoice_number == invoice_number))
        is not None
    )


def validate_parsed(
    parsed: Mapping[str, Any],
    *,
    db: Session | None = None,
    today: date | None = None,
    field_confidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """规则校验，返回 {errors, warnings, field_confidence}。"""

    errors: list[str] = []
    warnings: list[str] = []
    current_day = today or date.today()

    number = parsed.get("invoice_number")
    if not number:
        errors.append("缺少发票号码")
    else:
        text = str(number)
        if not INVOICE_NUMBER_RE.fullmatch(text):
            errors.append("发票号码格式不正确：应为 8-20 位数字")
        elif db is not None and _invoice_number_exists(db, text):
            warnings.append(f"发票号码已存在：{text}")

    issue_date_raw = parsed.get("issue_date")
    if not issue_date_raw:
        errors.append("缺少开票日期")
    else:
        try:
            issue_date = date.fromisoformat(str(issue_date_raw))
        except ValueError:
            errors.append("开票日期格式不正确")
        else:
            if issue_date > current_day + timedelta(days=1):
                warnings.append("开票日期晚于今天")
            elif issue_date < current_day - timedelta(days=365 * 10):
                warnings.append("开票日期超过 10 年前")

    total = parsed.get("total_cents")
    amount_ex_tax = parsed.get("amount_ex_tax_cents")
    tax = parsed.get("tax_cents")
    if total is None:
        errors.append("缺少价税合计")
    elif int(total) < 0:
        errors.append(
            "价税合计不能为负数（红冲/退款票暂不支持，请人工处理或驳回）"
        )
    if amount_ex_tax is not None and int(amount_ex_tax) < 0:
        errors.append("不含税金额不能为负数")
    if tax is not None and int(tax) < 0:
        errors.append("税额不能为负数")
    if (
        total is not None
        and amount_ex_tax is not None
        and tax is not None
        and abs(int(amount_ex_tax) + int(tax) - int(total)) > 1
    ):
        errors.append("不含税金额与税额之和不等于价税合计")

    if not parsed.get("seller_name"):
        warnings.append("缺少销方名称")

    items = parsed.get("items") or []
    if isinstance(items, list) and items:
        item_sum = sum(int(item.get("amount_cents") or 0) for item in items)
        baseline = amount_ex_tax if amount_ex_tax is not None else total
        if baseline is not None and abs(item_sum - int(baseline)) > 1:
            warnings.append("明细金额合计与发票金额不一致")

    confidences: dict[str, float] = {}
    for key in parsed:
        raw_value = (field_confidence or {}).get(key, 1.0)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = 1.0
        confidences[str(key)] = round(min(max(value, 0.0), 1.0), 4)

    return {"errors": errors, "warnings": warnings, "field_confidence": confidences}


def aggregate_confidence(
    field_confidence: Mapping[str, Any] | None,
    parsed: Mapping[str, Any],
    *,
    fallback: float = 0.0,
) -> float:
    values: list[float] = []
    for key in parsed:
        value = (field_confidence or {}).get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    if not values:
        return round(float(fallback), 4)
    return round(sum(values) / len(values), 4)
