"""识别 provider、规范化与规则校验（不访问外网）。"""

from __future__ import annotations

import json
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from backend.extraction import providers
from backend.extraction.config import AUTO_PROVIDER, ExtractionConfig
from backend.extraction.normalize import (
    aggregate_confidence,
    normalize_fields,
    parse_iso_date,
    validate_parsed,
)
from backend.extraction.providers import ProviderError, _ocr_text, parse_invoice_text
from backend.models.extraction import ExtractionJob

SAMPLE_TEXT = """电子发票（普通发票）
发票号码：24512000000012345678
发票代码：024001900111
开票日期：2026年07月12日
购买方信息 名称：测试购方
销售方信息 名称：测试商户
项目名称 数量 单价 金额 税率 税额
*标准件*螺栓 10 10.00 100.00 13% 13.00
合计 金额：100.00 税额：13.00
价税合计（大写）壹佰壹拾叁圆整 （小写）¥113.00
"""

VALID_FIELDS = {
    "invoice_number": "24512000000012345678",
    "invoice_code": "024001900111",
    "issue_date": "2026-07-12",
    "seller_name": "测试商户",
    "buyer_name": "测试购方",
    "amount_ex_tax_cents": 10000,
    "tax_cents": 1300,
    "total_cents": 11300,
    "items": [
        {"name": "螺栓", "quantity": 10, "unit_price_millis": 10000, "amount_cents": 10000}
    ],
}


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakeReader:
    def __init__(self, _path: str) -> None:
        self.pages = [FakePage(SAMPLE_TEXT)]


class EmptyReader:
    def __init__(self, _path: str) -> None:
        self.pages = [FakePage("")]


def _pdf_path(tmp_path):
    path = tmp_path / "invoice.pdf"
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return path


def test_parse_invoice_text_extracts_fields():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["invoice_number"] == "24512000000012345678"
    assert fields["invoice_code"] == "024001900111"
    assert fields["issue_date"] == "2026-07-12"
    assert fields["seller_name"] == "测试商户"
    assert fields["buyer_name"] == "测试购方"
    assert fields["amount_ex_tax_cents"] == 10000
    assert fields["tax_cents"] == 1300
    assert fields["total_cents"] == 11300
    assert fields["tax_rate_bp"] == 1300
    assert fields["items"][0]["name"] == "螺栓"
    assert fields["items"][0]["amount_cents"] == 10000

    assert parse_invoice_text("") == {}


def test_pdf_text_provider_success_and_empty(monkeypatch, tmp_path):
    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", FakeReader)
    config = ExtractionConfig(upload_dir=tmp_path)
    result = providers.PdfTextProvider().extract(
        None, SimpleNamespace(storage_key="x.pdf"), config, path=_pdf_path(tmp_path)
    )
    assert result.provider == "pdf_text"
    assert result.model == "pypdf"
    assert result.fields["invoice_number"] == "24512000000012345678"
    assert result.confidence == 0.8
    assert "发票号码" in result.raw_text

    monkeypatch.setattr(pypdf, "PdfReader", EmptyReader)
    with pytest.raises(ProviderError) as exc_info:
        providers.PdfTextProvider().extract(
            None, SimpleNamespace(storage_key="x.pdf"), config, path=_pdf_path(tmp_path)
        )
    assert exc_info.value.code == "pdf_text_unavailable"


def test_paddleocr_requires_endpoint_and_parses_response(monkeypatch, tmp_path):
    config = ExtractionConfig(upload_dir=tmp_path)
    with pytest.raises(ProviderError) as exc_info:
        providers.PaddleOcrProvider().extract(
            None, SimpleNamespace(storage_key="x.pdf"), config, path=_pdf_path(tmp_path)
        )
    assert exc_info.value.code == "paddleocr_not_configured"

    captured: dict[str, object] = {}

    def fake_post(url, body, *, timeout, headers=None):
        captured["url"] = url
        captured["payload"] = json.loads(body)
        return {"text_blocks": [{"text": SAMPLE_TEXT}], "confidence": 0.88}

    monkeypatch.setattr(providers, "_http_post_json", fake_post)
    configured = ExtractionConfig(
        paddleocr_endpoint="http://ocr.test/recognize", upload_dir=tmp_path
    )
    result = providers.PaddleOcrProvider().extract(
        None,
        SimpleNamespace(
            storage_key="x.pdf", original_name="invoice.pdf", mime_type="application/pdf"
        ),
        configured,
        path=_pdf_path(tmp_path),
    )
    assert result.provider == "paddleocr_local"
    assert result.confidence == 0.88
    assert result.fields["invoice_number"] == "24512000000012345678"
    assert captured["url"] == "http://ocr.test/recognize"
    assert captured["payload"]["file_name"] == "invoice.pdf"


def test_ocr_text_supports_paddleocr_list_format():
    payload = {
        "result": [
            [[[0, 0], [1, 1]], ["发票号码：24512000000012345678", 0.99]],
            [[[0, 2], [1, 3]], ["价税合计 ¥113.00", 0.98]],
        ]
    }
    text = _ocr_text(payload)
    assert "24512000000012345678" in text
    assert "113.00" in text


def test_multimodal_llm_disabled_and_configured(monkeypatch, tmp_path):
    config = ExtractionConfig(upload_dir=tmp_path)
    with pytest.raises(ProviderError) as exc_info:
        providers.MultimodalLlmProvider().extract(
            None, SimpleNamespace(storage_key="x.pdf"), config, path=_pdf_path(tmp_path)
        )
    assert exc_info.value.code == "llm_disabled"

    monkeypatch.setattr(
        providers,
        "_http_post_json",
        lambda url, body, *, timeout, headers=None: {
            "choices": [
                {
                    "message": {
                        "content": "```json\n"
                        + json.dumps(
                            {
                                "invoice_number": "24512000000012345678",
                                "issue_date": "2026-07-12",
                                "seller_name": "大模型商户",
                                "amount_ex_tax_cents": 10000,
                                "tax_cents": 1300,
                                "total_cents": 11300,
                            },
                            ensure_ascii=False,
                        )
                        + "\n```"
                    }
                }
            ]
        },
    )
    enabled = ExtractionConfig(
        llm_enabled=True,
        llm_endpoint="http://llm.test/v1",
        llm_api_key="test-key",
        llm_model="test-vl",
        prompt_version="v2",
        upload_dir=tmp_path,
    )
    result = providers.MultimodalLlmProvider().extract(
        None,
        SimpleNamespace(
            storage_key="x.pdf", original_name="invoice.pdf", mime_type="application/pdf"
        ),
        enabled,
        path=_pdf_path(tmp_path),
    )
    assert result.provider == "multimodal_llm"
    assert result.model == "test-vl"
    assert result.prompt_version == "v2"
    assert result.fields["seller_name"] == "大模型商户"
    assert result.fields["total_cents"] == 11300


def test_auto_chain_falls_back_to_paddleocr(monkeypatch, tmp_path):
    config = ExtractionConfig(
        provider=AUTO_PROVIDER,
        auto_chain=("pdf_text", "paddleocr_local"),
        paddleocr_endpoint="http://ocr.test/recognize",
        upload_dir=tmp_path,
    )
    monkeypatch.setattr(
        providers,
        "_http_post_json",
        lambda url, body, *, timeout, headers=None: {
            "text_blocks": [{"text": SAMPLE_TEXT}]
        },
    )
    result = providers.run_provider_chain(
        providers.provider_chain(config),
        None,
        SimpleNamespace(
            storage_key="x.pdf", original_name="invoice.pdf", mime_type="application/pdf"
        ),
        config,
        path=_pdf_path(tmp_path),
    )
    assert result.provider == "paddleocr_local"
    assert result.fields["total_cents"] == 11300


def test_unknown_provider_and_traversal(tmp_path):
    with pytest.raises(ProviderError) as exc_info:
        providers.get_provider("nope")
    assert exc_info.value.code == "unknown_provider"

    config = ExtractionConfig(upload_dir=tmp_path)
    with pytest.raises(ProviderError) as exc_info:
        providers.resolve_version_path(
            SimpleNamespace(storage_key="../escape.pdf"), config
        )
    assert exc_info.value.code == "invalid_storage_key"

    with pytest.raises(ProviderError) as exc_info:
        providers.resolve_version_path(
            SimpleNamespace(storage_key="2026/01/ab/missing.pdf"), config
        )
    assert exc_info.value.code == "file_missing"


def test_normalize_fields_aliases_and_amounts():
    parsed = normalize_fields(
        {
            "invoiceNo": " 24512000000012345678 ",
            "价税合计": "113.00",
            "税额": 13.0,
            "不含税金额": 10000,
            "开票日期": "2026年7月12日",
            "sellerName": "测试商户",
            "invoiceForm": "电子发票",
            "items": [
                {
                    "商品名称": "螺栓",
                    "数量": "2",
                    "单价": 10.0,
                    "金额": "20.00",
                }
            ],
        }
    )
    assert parsed["invoice_number"] == "24512000000012345678"
    assert parsed["total_cents"] == 11300
    assert parsed["tax_cents"] == 1300
    assert parsed["amount_ex_tax_cents"] == 10000
    assert parsed["issue_date"] == "2026-07-12"
    assert parsed["seller_name"] == "测试商户"
    assert parsed["invoice_form"] == "electronic"
    assert parsed["items"][0] == {
        "name": "螺栓",
        "quantity": 2.0,
        "unit_price_millis": 10000,
        "amount_cents": 2000,
        "note": None,
        "sort_order": 0,
    }

    assert parse_iso_date("2026/07/12") == "2026-07-12"
    assert parse_iso_date("20260712") == "2026-07-12"
    assert parse_iso_date("not-a-date") is None


def test_validate_parsed_rules(db_session):
    valid = normalize_fields(VALID_FIELDS)
    validation = validate_parsed(valid)
    assert validation["errors"] == []
    assert validation["warnings"] == []
    assert validation["field_confidence"]["invoice_number"] == 1.0

    bad_total = {**valid, "total_cents": 12000}
    errors = validate_parsed(bad_total)["errors"]
    assert any("价税合计" in message for message in errors)

    too_future = {**valid, "issue_date": (date.today() + timedelta(days=30)).isoformat()}
    warnings = validate_parsed(too_future)["warnings"]
    assert any("晚于今天" in message for message in warnings)

    missing = validate_parsed({})
    assert {"缺少发票号码", "缺少开票日期", "缺少价税合计"} <= set(missing["errors"])

    from backend.models.invoice import Invoice

    db_session.add(
        Invoice(
            invoice_number="24512000000012345678",
            issue_date=date(2026, 7, 12),
            seller_name="测试商户",
            amount_ex_tax_cents=10000,
            tax_cents=1300,
            total_cents=11300,
        )
    )
    db_session.commit()
    duplicate = validate_parsed(valid, db=db_session)
    assert any("已存在" in message for message in duplicate["warnings"])

    confidences = validate_parsed(
        valid, field_confidence={"invoice_number": 1.5, "total_cents": -1}
    )["field_confidence"]
    assert confidences["invoice_number"] == 1.0
    assert confidences["total_cents"] == 0.0

    assert aggregate_confidence({"a": 0.5, "b": 1.0}, {"a": 1, "b": 2}) == 0.75


def test_mock_provider_result_is_valid():
    result = providers.MockProvider().extract(None, None, ExtractionConfig())
    validation = validate_parsed(normalize_fields(result.fields))
    assert validation["errors"] == []
    assert validation["warnings"] == []
    assert result.confidence == 0.95
    assert result.provider == "mock"


def test_process_job_auto_records_actual_provider(
    user_client, db_session, settings, monkeypatch
):
    body = user_client.post(
        "/api/v1/documents",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n",
                "application/pdf",
            )
        },
        data={"doc_type": "invoice"},
    ).json()
    job_id = body["extraction_job"]["id"]

    monkeypatch.setattr(
        providers,
        "_http_post_json",
        lambda url, body, *, timeout, headers=None: {
            "text_blocks": [{"text": SAMPLE_TEXT}]
        },
    )
    config = ExtractionConfig(
        provider=AUTO_PROVIDER,
        auto_chain=("pdf_text", "paddleocr_local"),
        paddleocr_endpoint="http://ocr.test/recognize",
        upload_dir=settings.upload_dir,
    )
    from backend.extraction import service as extraction_service

    job = extraction_service.process_job(
        db_session, job_id, settings=settings, config=config
    )
    assert job.status == "review_pending"
    assert job.provider == "paddleocr_local"
    assert job.model == "paddleocr"
    assert job.prompt_version == "ocr-v1"
    assert job.parsed_json["invoice_number"] == "24512000000012345678"
    stored = db_session.get(ExtractionJob, job_id)
    assert stored.provider == "paddleocr_local"


def test_load_config_from_env(monkeypatch, settings):
    from backend.extraction.config import load_config

    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "AUTO")
    monkeypatch.setenv("IV_PADDLEOCR_ENDPOINT", "http://ocr.test/recognize")
    monkeypatch.setenv("IV_LLM_ENABLED", "true")
    monkeypatch.setenv("IV_EXTRACTION_MAX_ATTEMPTS", "4")
    config = load_config(settings=settings)
    assert config.provider == "auto"
    assert config.default_job_provider == "pdf_text"
    assert config.paddleocr_endpoint == "http://ocr.test/recognize"
    assert config.llm_enabled is True
    assert config.max_attempts == 4
    assert config.upload_dir == settings.upload_dir

    monkeypatch.setenv("IV_EXTRACTION_PROVIDER", "nonsense")
    assert load_config(settings=settings).provider == "pdf_text"


def test_provider_chain_failure_raises_provider_failed(tmp_path):
    config = ExtractionConfig(
        provider=AUTO_PROVIDER,
        auto_chain=("pdf_text", "paddleocr_local"),
        upload_dir=tmp_path,
    )
    with pytest.raises(ProviderError) as exc_info:
        providers.run_provider_chain(
            providers.provider_chain(config),
            None,
            SimpleNamespace(storage_key="x.pdf"),
            config,
            path=_pdf_path(tmp_path),
        )
    assert exc_info.value.code == "provider_failed"
    assert "paddleocr_local" in exc_info.value.message
