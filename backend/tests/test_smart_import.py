import csv
import io

from models import Asset
from services.smart_import import SmartImportService
from sqlmodel import select


def test_preview_csv_returns_headers_and_sample_rows():
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=["mã", "tên", "loại"])
    writer.writeheader()
    writer.writerow({"mã": "VCB", "tên": "Vietcombank", "loại": "STOCK"})
    writer.writerow({"mã": "VNM", "tên": "Vinamilk", "loại": "STOCK"})

    service = SmartImportService()
    preview = service.preview(content.getvalue().encode("utf-8"), "assets.csv")

    assert preview["headers"] == ["mã", "tên", "loại"]
    assert preview["row_count"] == 2
    assert len(preview["sample_rows"]) == 2


def test_suggest_mapping_fallback_without_ollama():
    service = SmartImportService()
    service._is_ai_enabled = lambda: False
    headers = ["mã", "tên", "loại tài sản", "sàn", "ngày"]
    mapping = service.suggest_mapping(headers, "assets")

    assert mapping["mã"] == "symbol"
    assert mapping["tên"] == "name"
    assert mapping["loại tài sản"] == "type"
    assert mapping["sàn"] == "exchange"
    assert mapping["ngày"] is None


def test_import_assets_with_mapping(session):
    content = io.StringIO()
    writer = csv.DictWriter(
        content, fieldnames=["mã", "tên", "loại"], lineterminator="\n"
    )
    writer.writeheader()
    writer.writerow({"mã": "VCB", "tên": "Vietcombank", "loại": "STOCK"})

    service = SmartImportService()
    mapping = {"mã": "symbol", "tên": "name", "loại": "type"}
    result = service.import_data(
        session, content.getvalue().encode("utf-8"), "assets.csv", "assets", mapping
    )

    assert result.created == 1, result.errors
    assert result.skipped == 0
    assert not result.errors

    asset = session.exec(select(Asset).where(Asset.symbol == "VCB")).first()
    assert asset is not None
    assert asset.name == "Vietcombank"


def test_import_assets_missing_mapping_returns_error(session):
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=["mã", "tên"])
    writer.writeheader()
    writer.writerow({"mã": "VCB", "tên": "Vietcombank"})

    service = SmartImportService()
    mapping = {"mã": "symbol", "tên": "name"}
    result = service.import_data(
        session, content.getvalue().encode("utf-8"), "assets.csv", "assets", mapping
    )

    assert result.created == 0
    assert "type" in result.errors[0]
