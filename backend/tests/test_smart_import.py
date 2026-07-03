import csv
import io

from common.models import Asset
from services.import_data.smart_import import SmartImportService
from sqlalchemy import select


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
    headers = ["mã", "tên", "loại tài sản", "sàn", "ngày"]
    mapping = service.suggest_mapping(headers, "assets")

    assert mapping["mã"] == "symbol"
    assert mapping["tên"] == "name"
    assert mapping["loại tài sản"] == "type"
    assert mapping["sàn"] == "exchange"
    assert mapping["ngày"] is None


def test_import_assets_with_mapping(session):
    from common.asset_type_config import seed_asset_types
    seed_asset_types(session)

    content = io.StringIO()
    writer = csv.DictWriter(
        content, fieldnames=["symbol", "name", "type"], lineterminator="\n"
    )
    writer.writeheader()
    writer.writerow({"symbol": "VCB", "name": "Vietcombank", "type": "STOCK"})

    service = SmartImportService()
    mapping = {"symbol": "symbol", "name": "name", "type": "type"}
    result = service.import_data(
        session, content.getvalue().encode("utf-8"), "assets.csv", "assets", mapping
    )

    assert result.created == 1, result.errors
    assert result.skipped == 0
    assert not result.errors

    asset = session.execute(select(Asset).where(Asset.symbol == "VCB")).scalars().first()
    assert asset is not None, "asset was not created"
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
