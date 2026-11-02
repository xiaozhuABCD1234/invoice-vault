"""用 openpyxl 在内存中生成导出工作簿。"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Sequence

from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from ..models.invoice import Invoice, InvoiceItem
from ..schemas.report import ColumnSpec
from .fields import FIELD_CATALOG, FORMULA_PREFIXES, resolve_cell

MONEY_FORMAT = "#,##0.00"
DATE_FORMAT = "yyyy-mm-dd"
INTEGER_FORMAT = "0"
NUMBER_FORMAT = "0.###"

CELL_KINDS = frozenset({"text", "money", "date", "number", "integer"})


def excel_safe_text(value: object) -> str:
    """文本防公式注入：以 = + - @ 开头的字符串前加单引号。"""

    text = "" if value is None else str(value)
    if text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text


def _column_kind(column: ColumnSpec, field_kind: str) -> str:
    if column.format in CELL_KINDS:
        return column.format
    return field_kind


def _write_cell(
    worksheet: Worksheet,
    row: int,
    column: int,
    value: Any,
    kind: str,
    *,
    bold: bool = False,
) -> Cell:
    cell = worksheet.cell(row=row, column=column)
    if value is None or value == "":
        cell.value = "" if kind == "text" else None
    elif kind == "text":
        cell.value = excel_safe_text(value)
    elif kind == "date":
        cell.value = value
        cell.number_format = DATE_FORMAT
    elif kind == "money":
        cell.value = float(value)
        cell.number_format = MONEY_FORMAT
    elif kind == "integer":
        cell.value = int(value)
        cell.number_format = INTEGER_FORMAT
    elif kind == "number":
        cell.value = float(value)
        cell.number_format = NUMBER_FORMAT
    else:
        cell.value = excel_safe_text(value)

    if bold:
        cell.font = Font(bold=True)
    if kind in {"money", "number", "integer"}:
        cell.alignment = Alignment(horizontal="right")
    elif kind == "date":
        cell.alignment = Alignment(horizontal="center")
    return cell


def _build_rows(invoices: Sequence[Invoice]) -> list[tuple[Invoice, InvoiceItem | None]]:
    rows: list[tuple[Invoice, InvoiceItem | None]] = []
    for invoice in invoices:
        items = list(invoice.items or [])
        if items:
            rows.extend((invoice, item) for item in items)
        else:
            rows.append((invoice, None))
    return rows


def _aggregate_sums(
    columns: Sequence[ColumnSpec],
    invoices: Sequence[Invoice],
    rows: Sequence[tuple[Invoice, InvoiceItem | None]],
) -> tuple[dict[str, float], dict[str, float]]:
    invoice_sums: dict[str, float] = {}
    item_sums: dict[str, float] = {}

    for column in columns:
        spec = FIELD_CATALOG.get(column.key)
        if spec is None or spec.aggregate is None:
            continue
        if spec.aggregate == "invoice":
            invoice_sums[column.key] = 0.0
        else:
            item_sums[column.key] = 0.0

    for invoice in invoices:
        for key in invoice_sums:
            value, _ = resolve_cell(invoice, None, key)
            if isinstance(value, (int, float)):
                invoice_sums[key] += float(value)

    for invoice, item in rows:
        for key in item_sums:
            value, _ = resolve_cell(invoice, item, key)
            if isinstance(value, (int, float)):
                item_sums[key] += float(value)

    return invoice_sums, item_sums


def build_workbook(columns: Sequence[ColumnSpec], invoices: Sequence[Invoice]) -> bytes:
    """生成 xlsx 字节；金额转元写数值，日期写 date，冻结表头并追加合计行。"""

    rows = _build_rows(invoices)
    invoice_sums, item_sums = _aggregate_sums(columns, invoices, rows)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "报表"

    last_column = max(1, len(columns))
    for column_index, column in enumerate(columns, start=1):
        header = worksheet.cell(row=1, column=column_index, value=excel_safe_text(column.label))
        header.font = Font(bold=True)
        header.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        spec = FIELD_CATALOG.get(column.key)
        width = column.width or (spec.width if spec is not None else 16)
        worksheet.column_dimensions[get_column_letter(column_index)].width = width

    worksheet.freeze_panes = "A2"
    worksheet.row_dimensions[1].height = 22

    for row_index, (invoice, item) in enumerate(rows, start=2):
        for column_index, column in enumerate(columns, start=1):
            spec = FIELD_CATALOG.get(column.key)
            field_kind = spec.format if spec is not None else "text"
            value, _ = resolve_cell(invoice, item, column.key, index=row_index - 1)
            _write_cell(
                worksheet,
                row_index,
                column_index,
                value,
                _column_kind(column, field_kind),
            )

    total_row = 2 + len(rows)
    for column_index, column in enumerate(columns, start=1):
        if column_index == 1:
            label_cell = worksheet.cell(row=total_row, column=1, value="合计")
            label_cell.font = Font(bold=True)
            continue

        spec = FIELD_CATALOG.get(column.key)
        if spec is None or spec.aggregate is None:
            continue
        if spec.aggregate == "invoice":
            value = invoice_sums.get(column.key, 0.0)
        else:
            value = item_sums.get(column.key, 0.0)
        if spec.format == "money":
            value = round(value, 2)
        _write_cell(
            worksheet,
            total_row,
            column_index,
            value,
            _column_kind(column, spec.format),
            bold=True,
        )

    worksheet.auto_filter.ref = f"A1:{get_column_letter(last_column)}{1 + len(rows)}"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
