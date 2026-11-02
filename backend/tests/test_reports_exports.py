"""导出：默认模板 happy path、筛选排序、权限、过期与失败状态。"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.document import Document, DocumentVersion
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.payment import Payment, PaymentAllocation
from backend.models.report import ExportJob
from backend.models.user import User
from backend.shared.db import utcnow

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

DEFAULT_LABELS = [
    "序号",
    "名称",
    "购买数量",
    "单价",
    "总价",
    "单张发票金额",
    "店铺",
    "申购人",
    "负责人",
    "发票号码",
    "发票图片",
    "付款记录",
    "发票形式",
    "备注",
    "申请老师代付时间",
    "链接",
]


def create_category(db: Session, name: str = "报表类别") -> Category:
    category = Category(name=name, kind="purchase", sort_order=1, is_active=True)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_document(
    db: Session, name: str = "发票.pdf", doc_type: str = "invoice"
) -> Document:
    digest = uuid4().hex + uuid4().hex
    document = Document(
        doc_type=doc_type,
        title=name,
        created_at=datetime.now(UTC),
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_no=1,
        storage_key=f"test/{digest}.pdf",
        original_name=name,
        display_name=name,
        mime_type="application/pdf",
        size_bytes=10,
        sha256=digest,
        created_at=datetime.now(UTC),
        is_latest=True,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    db.commit()
    db.refresh(document)
    return document


def create_invoice(
    db: Session,
    *,
    number: str,
    total_cents: int = 10000,
    issue_date: date = date(2026, 7, 1),
    category: Category | None = None,
    requester: User | None = None,
    owner: User | None = None,
    items: list[tuple[str, int, int, int]] | None = None,
    status: str = "active",
    seller_name: str = "测试店铺",
    note: str | None = None,
    invoice_form: str | None = "electronic",
    product_url: str | None = None,
    source_document: Document | None = None,
    created_by: int | None = None,
) -> Invoice:
    invoice = Invoice(
        invoice_number=number,
        issue_date=issue_date,
        seller_name=seller_name,
        amount_ex_tax_cents=total_cents,
        tax_cents=0,
        total_cents=total_cents,
        category_id=category.id if category is not None else None,
        requester_id=requester.id if requester is not None else None,
        owner_id=owner.id if owner is not None else None,
        invoice_form=invoice_form,
        status=status,
        paid_cents=0,
        payment_status="unpaid",
        note=note,
        product_url=product_url,
        source_document_id=source_document.id if source_document is not None else None,
        created_by=created_by,
    )
    db.add(invoice)
    db.flush()
    for index, (name, quantity, unit_price_millis, amount_cents) in enumerate(items or []):
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                name=name,
                quantity=Decimal(str(quantity)),
                unit_price_millis=unit_price_millis,
                amount_cents=amount_cents,
                sort_order=index,
            )
        )
    db.commit()
    db.refresh(invoice)
    return invoice


def create_payment(
    db: Session,
    *,
    amount_cents: int = 10000,
    paid_at: datetime | None = None,
    payer_name: str | None = "杨泽",
    method: str = "wechat",
    evidence_document_id: int | None = None,
    requested_at: datetime | None = None,
    status: str = "unallocated",
) -> Payment:
    payment = Payment(
        amount_cents=amount_cents,
        paid_at=paid_at or datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
        payer_name=payer_name,
        method=method,
        evidence_document_id=evidence_document_id,
        requested_at=requested_at,
        status=status,
        created_at=datetime.now(UTC),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def allocate(
    db: Session, payment: Payment, invoice: Invoice, amount_cents: int
) -> PaymentAllocation:
    allocation = PaymentAllocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount_cents=amount_cents,
        status="active",
        created_at=datetime.now(UTC),
    )
    db.add(allocation)
    db.flush()

    paid = int(
        db.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0)).where(
                PaymentAllocation.invoice_id == invoice.id,
                PaymentAllocation.status == "active",
            )
        )
        or 0
    )
    invoice.paid_cents = paid
    invoice.payment_status = (
        "paid" if paid >= invoice.total_cents else ("partial" if paid > 0 else "unpaid")
    )

    allocated = int(
        db.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount_cents), 0)).where(
                PaymentAllocation.payment_id == payment.id,
                PaymentAllocation.status == "active",
            )
        )
        or 0
    )
    payment.status = (
        "fully_allocated"
        if allocated >= payment.amount_cents
        else ("partially_allocated" if allocated > 0 else "unallocated")
    )
    db.commit()
    db.refresh(allocation)
    return allocation


def post_export(client: TestClient, payload: dict | None = None) -> dict:
    response = client.post("/api/v1/exports", json=payload or {})
    assert response.status_code == 202, response.text
    return response.json()["export"]


def download_workbook(client: TestClient, job: dict):
    response = client.get(job["download_url"])
    assert response.status_code == 200, response.text
    return response, load_workbook(BytesIO(response.content))


def column_values(worksheet, column: int = 1) -> list:
    return [
        worksheet.cell(row=row, column=column).value
        for row in range(2, worksheet.max_row)
    ]


def test_export_default_happy_path(
    user_client: TestClient,
    db_session: Session,
    normal_user: User,
    admin_user: User,
):
    category = create_category(db_session)
    document = create_document(db_session, "发票-京东.pdf")
    invoice_one = create_invoice(
        db_session,
        number="INV-1",
        total_cents=11300,
        category=category,
        requester=normal_user,
        owner=admin_user,
        items=[("螺栓", 2, 1000, 2000), ("螺母", 1, 500, 500)],
        seller_name="京东",
        note="含税",
        source_document=document,
    )
    create_invoice(
        db_session,
        number="INV-2",
        total_cents=5000,
        category=category,
        issue_date=date(2026, 7, 2),
        items=[],
        seller_name="淘宝",
    )
    payment = create_payment(db_session, amount_cents=2500, payer_name="杨泽")
    allocate(db_session, payment, invoice_one, 2500)

    job = post_export(user_client)
    assert job["status"] == "succeeded"
    assert job["template_id"] is None
    assert job["file_name"].endswith(".xlsx")
    assert job["download_url"] == f"/api/v1/exports/{job['id']}/download"
    assert job["expires_at"] is not None

    detail = user_client.get(f"/api/v1/exports/{job['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "succeeded"

    response, workbook = download_workbook(user_client, job)
    assert response.headers["content-type"].startswith(XLSX_MEDIA_TYPE)
    disposition = response.headers["content-disposition"]
    assert "attachment" in disposition
    assert "xlsx" in disposition.lower()

    worksheet = workbook.active
    headers = [cell.value for cell in worksheet[1]]
    assert headers == DEFAULT_LABELS
    assert worksheet.freeze_panes == "A2"
    assert worksheet["A1"].font.bold is True
    assert worksheet.max_row == 5

    assert worksheet["A2"].value == 1
    assert worksheet["B2"].value == "螺栓"
    assert worksheet["C2"].value == 2
    assert worksheet["D2"].value == 1.0
    assert worksheet["E2"].value == 20.0
    assert worksheet["F2"].value == 113.0
    assert worksheet["G2"].value == "京东"
    assert worksheet["H2"].value == "普通成员"
    assert worksheet["I2"].value == "系统管理员"
    assert worksheet["J2"].value == "INV-1"
    assert worksheet["K2"].value == "发票-京东.pdf"
    assert worksheet["L2"].value == "杨泽 25.00元 微信"
    assert worksheet["M2"].value == "电子"
    assert worksheet["N2"].value == "含税"
    assert worksheet["D2"].number_format == "#,##0.00"
    assert worksheet["F2"].number_format == "#,##0.00"

    assert worksheet["A3"].value == 2
    assert worksheet["B3"].value == "螺母"
    assert worksheet["A4"].value == 3
    assert worksheet["B4"].value in (None, "")
    assert worksheet["F4"].value == 50.0
    assert worksheet["J4"].value == "INV-2"

    assert worksheet["A5"].value == "合计"
    assert worksheet["C5"].value == 3.0
    assert worksheet["E5"].value == 25.0
    assert worksheet["F5"].value == 163.0
    assert worksheet["E5"].number_format == "#,##0.00"
    assert worksheet["A5"].font.bold is True

    listing = user_client.get("/api/v1/exports").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == job["id"]
    assert listing["items"][0]["download_url"] == job["download_url"]


def test_export_all_requested_columns(
    user_client: TestClient,
    db_session: Session,
    normal_user: User,
    admin_user: User,
):
    category = create_category(db_session, "全部列类别")
    document = create_document(db_session, "发票.pdf")
    evidence = create_document(db_session, "付款凭证.jpg", "payment_evidence")
    invoice = create_invoice(
        db_session,
        number="FULL-1",
        total_cents=10000,
        category=category,
        requester=normal_user,
        owner=admin_user,
        items=[("商品A", 2, 1000, 2000)],
        seller_name="全部列店铺",
        note="备注内容",
        product_url="https://example.com/item",
        source_document=document,
    )
    payment = create_payment(
        db_session,
        amount_cents=5000,
        payer_name="王老师",
        method="teacher_advance",
        evidence_document_id=evidence.id,
        requested_at=datetime(2026, 7, 3, 9, 0, tzinfo=UTC),
        paid_at=datetime(2026, 7, 4, 9, 0, tzinfo=UTC),
    )
    allocate(db_session, payment, invoice, 5000)

    columns = [
        {"key": "index", "label": "序号", "format": "integer"},
        {"key": "issue_date", "label": "开票日期", "format": "date"},
        {"key": "invoice_number", "label": "发票号码"},
        {"key": "item_name", "label": "名称"},
        {"key": "quantity", "label": "购买数量", "format": "number"},
        {"key": "unit_price_millis", "label": "单价", "format": "money"},
        {"key": "amount_cents", "label": "总价", "format": "money"},
        {"key": "total_cents", "label": "单张发票金额", "format": "money"},
        {"key": "amount_ex_tax_cents", "label": "不含税金额", "format": "money"},
        {"key": "tax_cents", "label": "税额", "format": "money"},
        {"key": "category_name", "label": "类别"},
        {"key": "requester_name", "label": "申购人"},
        {"key": "owner_name", "label": "负责人"},
        {"key": "invoice_form", "label": "发票形式"},
        {"key": "status", "label": "状态"},
        {"key": "note", "label": "备注"},
        {"key": "product_url", "label": "链接"},
        {"key": "payer_name", "label": "付款人"},
        {"key": "method", "label": "付款方式"},
        {"key": "paid_at", "label": "付款日期", "format": "date"},
        {"key": "payment_amount_cents", "label": "付款金额", "format": "money"},
        {"key": "source_file_name", "label": "发票图片"},
        {"key": "payment_summary", "label": "付款记录"},
        {"key": "teacher_advance_requested_at", "label": "申请老师代付时间", "format": "date"},
    ]
    job = post_export(user_client, {"columns": columns})
    _, workbook = download_workbook(user_client, job)
    worksheet = workbook.active
    headers = [cell.value for cell in worksheet[1]]
    values = {
        header: worksheet.cell(row=2, column=index).value
        for index, header in enumerate(headers, start=1)
    }

    assert values["序号"] == 1
    assert values["开票日期"].date() == date(2026, 7, 1)
    assert values["发票号码"] == "FULL-1"
    assert values["名称"] == "商品A"
    assert values["购买数量"] == 2.0
    assert values["单价"] == 1.0
    assert values["总价"] == 20.0
    assert values["单张发票金额"] == 100.0
    assert values["不含税金额"] == 100.0
    assert values["税额"] == 0.0
    assert values["类别"] == "全部列类别"
    assert values["申购人"] == "普通成员"
    assert values["负责人"] == "系统管理员"
    assert values["发票形式"] == "电子"
    assert values["状态"] == "有效"
    assert values["备注"] == "备注内容"
    assert values["链接"] == "https://example.com/item"
    assert values["付款人"] == "王老师"
    assert values["付款方式"] == "老师代付"
    assert values["付款日期"].date() == date(2026, 7, 4)
    assert values["付款金额"] == 50.0
    assert values["发票图片"] == "发票.pdf"
    assert "王老师" in values["付款记录"]
    assert "老师代付" in values["付款记录"]
    assert values["申请老师代付时间"].date() == date(2026, 7, 3)
    assert worksheet["B2"].number_format == "yyyy-mm-dd"


def test_export_formula_injection_is_escaped(
    user_client: TestClient, db_session: Session, normal_user: User
):
    create_invoice(
        db_session,
        number="FORMULA-1",
        seller_name='=HYPERLINK("http://evil")',
        note="+SUM(A1:A2)",
        product_url="@cmd",
        items=[("-1+1", 1, 100, 100)],
        requester=normal_user,
    )
    job = post_export(
        user_client,
        {
            "columns": [
                {"key": "seller_name", "label": "店铺"},
                {"key": "note", "label": "备注"},
                {"key": "product_url", "label": "链接"},
                {"key": "item_name", "label": "名称"},
            ]
        },
    )
    _, workbook = download_workbook(user_client, job)
    worksheet = workbook.active
    assert worksheet["A2"].value.startswith("'=HYPERLINK")
    assert "http://evil" in worksheet["A2"].value
    assert worksheet["B2"].value == "'+SUM(A1:A2)"
    assert worksheet["C2"].value == "'@cmd"
    assert worksheet["D2"].value == "'-1+1"
    assert worksheet["A2"].data_type == "s"


def test_export_filters_and_sort(
    user_client: TestClient, db_session: Session
):
    category_a = create_category(db_session, "筛选类别A")
    category_b = create_category(db_session, "筛选类别B")

    create_invoice(
        db_session,
        number="FILTER-1",
        total_cents=10000,
        issue_date=date(2026, 6, 1),
        category=category_a,
        seller_name="A店",
    )
    create_invoice(
        db_session,
        number="FILTER-2",
        total_cents=20000,
        issue_date=date(2026, 7, 1),
        category=category_b,
        seller_name="B店",
    )
    create_invoice(
        db_session,
        number="FILTER-3",
        total_cents=30000,
        issue_date=date(2026, 7, 2),
        category=category_a,
        status="review_pending",
        seller_name="C店",
    )
    create_invoice(
        db_session,
        number="FILTER-4",
        total_cents=40000,
        issue_date=date(2026, 8, 1),
        category=category_a,
        seller_name="D店",
    )

    columns = [
        {"key": "invoice_number", "label": "发票号码"},
        {"key": "total_cents", "label": "金额", "format": "money"},
    ]

    filtered = post_export(
        user_client,
        {
            "columns": columns,
            "filters": {
                "category_id": category_a.id,
                "status": "active",
                "date_from": "2026-06-01",
                "date_to": "2026-07-31",
            },
        },
    )
    _, workbook = download_workbook(user_client, filtered)
    worksheet = workbook.active
    assert column_values(worksheet) == ["FILTER-1"]
    assert worksheet["B2"].value == 100.0

    sorted_job = post_export(
        user_client,
        {
            "columns": columns,
            "filters": {"category_id": category_a.id},
            "sort": [{"key": "total_cents", "order": "desc"}],
        },
    )
    _, sorted_workbook = download_workbook(user_client, sorted_job)
    assert column_values(sorted_workbook.active) == [
        "FILTER-4",
        "FILTER-3",
        "FILTER-1",
    ]

    searched = post_export(
        user_client,
        {
            "columns": columns,
            "filters": {"q": "FILTER-2"},
        },
    )
    _, searched_workbook = download_workbook(user_client, searched)
    assert column_values(searched_workbook.active) == ["FILTER-2"]

    invoice_one = db_session.scalar(
        select(Invoice).where(Invoice.invoice_number == "FILTER-1")
    )
    payment = create_payment(db_session, amount_cents=4000)
    allocate(db_session, payment, invoice_one, 4000)

    partial = post_export(
        user_client,
        {
            "columns": columns,
            "filters": {"payment_status": "partial"},
        },
    )
    _, partial_workbook = download_workbook(user_client, partial)
    assert column_values(partial_workbook.active) == ["FILTER-1"]


def test_export_uses_saved_template(user_client: TestClient, db_session: Session):
    create_invoice(
        db_session,
        number="TPL-1",
        total_cents=10000,
        issue_date=date(2026, 7, 1),
        seller_name="模板店A",
    )
    create_invoice(
        db_session,
        number="TPL-2",
        total_cents=20000,
        issue_date=date(2026, 7, 2),
        seller_name="模板店B",
    )
    create_invoice(
        db_session,
        number="TPL-3",
        total_cents=30000,
        issue_date=date(2026, 7, 3),
        seller_name="模板店C",
        status="review_pending",
    )

    template = user_client.post(
        "/api/v1/report-templates",
        json={
            "name": "我的导出模板",
            "columns": [
                {"key": "invoice_number", "label": "发票号码"},
                {"key": "total_cents", "label": "金额", "format": "money"},
                {"key": "seller_name", "label": "店铺"},
            ],
            "filters": {"status": "active"},
            "sort": [{"key": "total_cents", "order": "desc"}],
            "is_shared": True,
        },
    )
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]

    job = post_export(user_client, {"template_id": template_id})
    assert job["template_id"] == template_id
    _, workbook = download_workbook(user_client, job)
    worksheet = workbook.active
    assert [cell.value for cell in worksheet[1]] == ["发票号码", "金额", "店铺"]
    assert column_values(worksheet) == ["TPL-2", "TPL-1"]
    assert worksheet["B2"].value == 200.0

    overridden = post_export(
        user_client,
        {
            "template_id": template_id,
            "columns": [{"key": "seller_name", "label": "店铺"}],
        },
    )
    _, override_workbook = download_workbook(user_client, overridden)
    assert [cell.value for cell in override_workbook.active[1]] == ["店铺"]


def test_export_expired_returns_410(
    user_client: TestClient, db_session: Session
):
    create_invoice(db_session, number="EXP-1")
    job = post_export(user_client)
    db_session.execute(
        update(ExportJob)
        .where(ExportJob.id == job["id"])
        .values(expires_at=utcnow() - timedelta(hours=1))
    )
    db_session.commit()

    response = user_client.get(job["download_url"])
    assert response.status_code == 410
    assert response.json()["code"] == "export_expired"


def test_export_permissions_and_admin_listing(
    admin_client: TestClient, user_client: TestClient, db_session: Session
):
    create_invoice(db_session, number="PERM-1")
    admin_job = post_export(admin_client)

    forbidden_detail = user_client.get(f"/api/v1/exports/{admin_job['id']}")
    assert forbidden_detail.status_code == 403
    forbidden_download = user_client.get(admin_job["download_url"])
    assert forbidden_download.status_code == 403

    user_listing = user_client.get("/api/v1/exports").json()
    assert all(item["id"] != admin_job["id"] for item in user_listing["items"])

    user_job = post_export(user_client)
    admin_listing = admin_client.get("/api/v1/exports").json()
    listed_ids = {item["id"] for item in admin_listing["items"]}
    assert admin_job["id"] in listed_ids
    assert user_job["id"] in listed_ids

    admin_can_view = admin_client.get(f"/api/v1/exports/{user_job['id']}")
    assert admin_can_view.status_code == 200
    admin_can_download = admin_client.get(user_job["download_url"])
    assert admin_can_download.status_code == 200

    assert user_client.get(f"/api/v1/exports/{user_job['id']}").status_code == 200
    assert user_client.get(user_job["download_url"]).status_code == 200


def test_export_requires_login(client: TestClient):
    assert client.get("/api/v1/exports").status_code == 401
    assert client.post("/api/v1/exports", json={}).status_code == 401
    assert client.get("/api/v1/exports/1/download").status_code == 401


def test_export_list_pagination(user_client: TestClient, db_session: Session):
    create_invoice(db_session, number="PAGE-1")
    for _ in range(3):
        post_export(user_client)

    first_page = user_client.get(
        "/api/v1/exports", params={"page": 1, "page_size": 2}
    ).json()
    assert first_page["total"] == 3
    assert first_page["page"] == 1
    assert first_page["page_size"] == 2
    assert len(first_page["items"]) == 2

    second_page = user_client.get(
        "/api/v1/exports", params={"page": 2, "page_size": 2}
    ).json()
    assert len(second_page["items"]) == 1


def test_export_failure_records_failed_status(
    monkeypatch, user_client: TestClient, db_session: Session
):
    import backend.reports.excel as excel_module

    def broken_build_workbook(columns, invoices):
        raise RuntimeError("生成失败")

    monkeypatch.setattr(excel_module, "build_workbook", broken_build_workbook)
    job = post_export(user_client)
    assert job["status"] == "failed"
    assert "生成失败" in job["error_message"]

    detail = user_client.get(f"/api/v1/exports/{job['id']}").json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "生成失败"

    response = user_client.get(job["download_url"])
    assert response.status_code == 409
    assert response.json()["code"] == "export_not_ready"


def test_export_invalid_payloads(user_client: TestClient, db_session: Session):
    create_invoice(db_session, number="BAD-1")

    missing_template = user_client.post("/api/v1/exports", json={"template_id": 999999})
    assert missing_template.status_code == 404
    assert missing_template.json()["code"] == "template_not_found"

    bad_status = user_client.post(
        "/api/v1/exports", json={"filters": {"status": "not_a_status"}}
    )
    assert bad_status.status_code == 400
    assert bad_status.json()["code"] == "invalid_filter_value"

    bad_filter = user_client.post(
        "/api/v1/exports", json={"filters": {"unknown": 1}}
    )
    assert bad_filter.status_code == 400
    assert bad_filter.json()["code"] == "invalid_filter_key"

    bad_range = user_client.post(
        "/api/v1/exports",
        json={"filters": {"date_from": "2026-08-01", "date_to": "2026-07-01"}},
    )
    assert bad_range.status_code == 400
    assert bad_range.json()["code"] == "invalid_date_range"

    bad_column = user_client.post(
        "/api/v1/exports",
        json={"columns": [{"key": "not_a_field", "label": "坏列"}]},
    )
    assert bad_column.status_code == 400
    assert bad_column.json()["code"] == "invalid_column_key"

    empty_columns = user_client.post("/api/v1/exports", json={"columns": []})
    assert empty_columns.status_code == 400
    assert empty_columns.json()["code"] == "invalid_columns"

    bad_sort = user_client.post(
        "/api/v1/exports", json={"sort": [{"key": "not_a_field", "order": "asc"}]}
    )
    assert bad_sort.status_code == 400
    assert bad_sort.json()["code"] == "invalid_sort_key"


def test_export_audit_actions(admin_client: TestClient, db_session: Session):
    create_invoice(db_session, number="AUDIT-1")
    job = post_export(admin_client)
    assert admin_client.get(job["download_url"]).status_code == 200

    created = admin_client.get(
        "/api/v1/audit-logs",
        params={"action": "export.create", "entity_id": job["id"]},
    ).json()
    assert created["total"] == 1
    assert created["items"][0]["entity_type"] == "export"

    downloaded = admin_client.get(
        "/api/v1/audit-logs",
        params={"action": "export.download", "entity_id": job["id"]},
    ).json()
    assert downloaded["total"] == 1
    assert downloaded["items"][0]["entity_type"] == "export"
