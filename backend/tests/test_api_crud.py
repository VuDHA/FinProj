import csv
import io
import datetime
import json

import pytest

from models import Asset, Income, PriceSnapshot, Transaction
from schemas import AllocationTargetCreate, SettingCreate
from services.source_config import DEFAULT_SOURCES
from sqlmodel import select


def _create_asset(session, symbol="VCB", name="Vietcombank", type="STOCK"):
    asset = Asset(symbol=symbol, name=name, type=type, currency="VND")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_list_assets_empty(client):
    response = client.get("/api/v1/assets/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_asset(client):
    response = client.post(
        "/api/v1/assets/",
        json={"symbol": "VCB", "name": "Vietcombank", "type": "STOCK", "currency": "VND"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "VCB"
    assert data["id"]

    get_response = client.get(f"/api/v1/assets/{data['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["symbol"] == "VCB"


def test_create_asset_with_source(client):
    response = client.post(
        "/api/v1/assets/",
        json={
            "symbol": "VCB",
            "name": "Vietcombank",
            "type": "STOCK",
            "currency": "VND",
            "source": "kbs",
        },
    )
    assert response.status_code == 200


def test_create_asset_invalid_type(client):
    response = client.post(
        "/api/v1/assets/",
        json={"symbol": "VCB", "name": "Vietcombank", "type": "INVALID", "currency": "VND"},
    )
    assert response.status_code == 400


def test_create_asset_duplicate_symbol(client):
    client.post(
        "/api/v1/assets/",
        json={"symbol": "VCB", "name": "Vietcombank", "type": "STOCK", "currency": "VND"},
    )
    response = client.post(
        "/api/v1/assets/",
        json={"symbol": "VCB", "name": "Vietcombank 2", "type": "STOCK", "currency": "VND"},
    )
    assert response.status_code == 409


def test_create_asset_unsupported_source_for_type(client):
    response = client.post(
        "/api/v1/assets/",
        json={
            "symbol": "GLD",
            "name": "Gold",
            "type": "GOLD",
            "currency": "VND",
            "source": "kbs",
        },
    )
    assert response.status_code == 400


def test_delete_asset(client, session):
    asset = _create_asset(session, symbol="VCB")
    response = client.delete(f"/api/v1/assets/{asset.id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True

    get_response = client.get(f"/api/v1/assets/{asset.id}")
    assert get_response.status_code == 404


def test_list_transactions(client, session):
    asset = _create_asset(session)
    session.add(Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1)))
    session.commit()
    response = client.get("/api/v1/transactions/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "BUY"


def test_create_transaction(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/transactions/",
        json={
            "asset_id": asset.id,
            "type": "BUY",
            "quantity": 10,
            "price": 100,
            "fee": 5,
            "date": "2023-01-01",
            "notes": "first buy",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 10


def test_create_transaction_asset_not_found(client):
    response = client.post(
        "/api/v1/transactions/",
        json={
            "asset_id": 999,
            "type": "BUY",
            "quantity": 10,
            "price": 100,
            "fee": 0,
            "date": "2023-01-01",
        },
    )
    assert response.status_code == 404


def test_create_transaction_invalid_type(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/transactions/",
        json={
            "asset_id": asset.id,
            "type": "INVALID",
            "quantity": 10,
            "price": 100,
            "fee": 0,
            "date": "2023-01-01",
        },
    )
    assert response.status_code == 400


def test_create_transaction_negative_quantity(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/transactions/",
        json={
            "asset_id": asset.id,
            "type": "BUY",
            "quantity": -1,
            "price": 100,
            "fee": 0,
            "date": "2023-01-01",
        },
    )
    assert response.status_code == 400


def test_create_transaction_sell_exceeds_holding(client, session):
    asset = _create_asset(session)
    session.add(
        Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1))
    )
    session.commit()
    response = client.post(
        "/api/v1/transactions/",
        json={
            "asset_id": asset.id,
            "type": "SELL",
            "quantity": 20,
            "price": 110,
            "fee": 0,
            "date": "2023-01-02",
        },
    )
    assert response.status_code == 400


def test_delete_transaction(client, session):
    asset = _create_asset(session)
    tx = Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1))
    session.add(tx)
    session.commit()
    session.refresh(tx)
    response = client.delete(f"/api/v1/transactions/{tx.id}")
    assert response.status_code == 200


def test_list_income(client, session):
    asset = _create_asset(session)
    session.add(Income(asset_id=asset.id, type="DIVIDEND", amount=1000, date=datetime.date(2023, 1, 1)))
    session.commit()
    response = client.get("/api/v1/income/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_income(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/income/",
        json={"asset_id": asset.id, "type": "DIVIDEND", "amount": 1000, "date": "2023-01-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 1000


def test_create_income_invalid_type(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/income/",
        json={"asset_id": asset.id, "type": "BONUS", "amount": 1000, "date": "2023-01-01"},
    )
    assert response.status_code == 400


def test_create_income_non_positive_amount(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/income/",
        json={"asset_id": asset.id, "type": "DIVIDEND", "amount": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 400


def test_delete_income(client, session):
    asset = _create_asset(session)
    income = Income(asset_id=asset.id, type="DIVIDEND", amount=1000, date=datetime.date(2023, 1, 1))
    session.add(income)
    session.commit()
    session.refresh(income)
    response = client.delete(f"/api/v1/income/{income.id}")
    assert response.status_code == 200


def test_settings_crud(client, session):
    response = client.post("/api/v1/settings/", json={"key": "theme", "value": "dark"})
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "theme"
    assert data["value"] == "dark"

    response = client.post("/api/v1/settings/", json={"key": "theme", "value": "light"})
    assert response.status_code == 200
    assert response.json()["value"] == "light"

    response = client.get("/api/v1/settings/theme")
    assert response.status_code == 200
    assert response.json()["value"] == "light"

    response = client.get("/api/v1/settings/missing")
    assert response.status_code == 404


def test_settings_allocation_targets(client, session):
    response = client.post(
        "/api/v1/settings/allocation-targets/",
        json=[
            {"type": "STOCK", "target_percent": 60},
            {"type": "FUND", "target_percent": 40},
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    response = client.post(
        "/api/v1/settings/allocation-targets/",
        json=[
            {"type": "STOCK", "target_percent": 60},
            {"type": "FUND", "target_percent": 50},
        ],
    )
    assert response.status_code == 400


def test_settings_default_sources(client, session):
    response = client.get("/api/v1/settings/default-sources")
    assert response.status_code == 200
    data = response.json()
    for asset_type in DEFAULT_SOURCES:
        assert asset_type in data

    response = client.post(
        "/api/v1/settings/default-sources",
        json={"STOCK": "cafef"},
    )
    assert response.status_code == 200
    assert response.json()["STOCK"] == "cafef"

    response = client.post(
        "/api/v1/settings/default-sources",
        json={"STOCK": "invalid_source"},
    )
    assert response.status_code == 400


def test_settings_sources(client):
    response = client.get("/api/v1/settings/sources/STOCK")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all("code" in s and "name" in s for s in data)


def test_settings_env_config(client):
    response = client.get("/api/v1/settings/env-config")
    assert response.status_code == 200
    data = response.json()
    keys = {item["key"] for item in data}
    assert "OLLAMA_ENABLED" in keys
    assert "DATABASE_URL" in keys


def test_settings_env_config_update(tmp_path, client, monkeypatch):
    env_file = tmp_path / ".env"
    monkeypatch.setattr("services.env_config._ENV_PATH", env_file)
    env_file.write_text("OLLAMA_ENABLED=true\n")
    response = client.post(
        "/api/v1/settings/env-config",
        json={"OLLAMA_ENABLED": "false"},
    )
    assert response.status_code == 200
    assert response.json()["requires_restart"] is False
    assert env_file.read_text().strip().endswith("OLLAMA_ENABLED=false")


def test_export_assets(client, session):
    _create_asset(session, symbol="VCB", name="Vietcombank")
    response = client.get("/api/v1/import-export/export/assets")
    assert response.status_code == 200
    assert "VCB" in response.text


def test_export_transactions(client, session):
    asset = _create_asset(session, symbol="VCB")
    session.add(Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1)))
    session.commit()
    response = client.get("/api/v1/import-export/export/transactions")
    assert response.status_code == 200
    assert "VCB" in response.text


def test_import_assets(client, session):
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=["symbol", "name", "type", "currency"])
    writer.writeheader()
    writer.writerow({"symbol": "VNM", "name": "Vinamilk", "type": "STOCK", "currency": "VND"})
    response = client.post(
        "/api/v1/import-export/import/assets",
        files={"file": ("assets.csv", content.getvalue(), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert session.exec(select(Asset).where(Asset.symbol == "VNM")).first() is not None


def test_import_assets_invalid_extension(client):
    response = client.post(
        "/api/v1/import-export/import/assets",
        files={"file": ("assets.txt", "not csv", "text/plain")},
    )
    assert response.status_code == 400


def test_import_transactions(client, session):
    _create_asset(session, symbol="VCB")
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=["symbol", "type", "quantity", "price", "fee", "date"])
    writer.writeheader()
    writer.writerow({"symbol": "VCB", "type": "BUY", "quantity": "10", "price": "100", "fee": "0", "date": "2023-01-01"})
    response = client.post(
        "/api/v1/import-export/import/transactions",
        files={"file": ("transactions.csv", content.getvalue(), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1


def test_smart_import_preview(client):
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=["mã", "tên", "loại"])
    writer.writeheader()
    writer.writerow({"mã": "VCB", "tên": "Vietcombank", "loại": "STOCK"})
    response = client.post(
        "/api/v1/import-export/smart-preview",
        files={"file": ("assets.csv", content.getvalue(), "text/csv")},
        data={"import_type": "assets"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["headers"] == ["mã", "tên", "loại"]
    assert "suggested_mapping" in data


def test_smart_import(client, session):
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=["mã", "tên", "loại"], lineterminator="\n")
    writer.writeheader()
    writer.writerow({"mã": "VCB", "tên": "Vietcombank", "loại": "STOCK"})
    payload = json.dumps({"import_type": "assets", "mapping": {"mã": "symbol", "tên": "name", "loại": "type"}})
    response = client.post(
        "/api/v1/import-export/smart-import",
        files={"file": ("assets.csv", content.getvalue(), "text/csv")},
        data={"payload": payload},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert session.exec(select(Asset).where(Asset.symbol == "VCB")).first() is not None


def test_smart_import_invalid_payload(client):
    response = client.post(
        "/api/v1/import-export/smart-import",
        files={"file": ("assets.csv", "mã,tên,loại\nVCB,Vietcombank,STOCK", "text/csv")},
        data={"payload": "not json"},
    )
    assert response.status_code == 400


def test_update_asset(client, session):
    asset = _create_asset(session, symbol="RE", name="Real Estate", type="REAL_ESTATE")
    response = client.put(
        f"/api/v1/assets/{asset.id}",
        json={"name": "Real Estate updated", "currency": "VND", "manual_value": 1500},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Real Estate updated"
    assert data["currency"] == "VND"


def test_update_asset_symbol_and_type_immutable(client, session):
    asset = _create_asset(session, symbol="VCB", name="Vietcombank", type="STOCK")
    response = client.put(
        f"/api/v1/assets/{asset.id}",
        json={"symbol": "VCB2", "type": "FUND", "name": "Vietcombank"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "VCB"
    assert data["type"] == "STOCK"


def test_update_transaction(client, session):
    asset = _create_asset(session)
    tx = Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1))
    session.add(tx)
    session.commit()
    session.refresh(tx)
    response = client.put(
        f"/api/v1/transactions/{tx.id}",
        json={"quantity": 20, "price": 110, "fee": 5, "date": "2023-02-01", "notes": "updated"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 20
    assert data["price"] == 110
    assert data["fee"] == 5
    assert data["notes"] == "updated"


def test_update_transaction_sell_exceeds_holding(client, session):
    asset = _create_asset(session)
    buy = Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1))
    sell = Transaction(asset_id=asset.id, type="SELL", quantity=5, price=110, fee=0, date=datetime.date(2023, 2, 1))
    session.add(buy)
    session.add(sell)
    session.commit()
    session.refresh(sell)
    response = client.put(
        f"/api/v1/transactions/{sell.id}",
        json={"quantity": 15},
    )
    assert response.status_code == 400


def test_create_transaction_manual_price_for_non_market_asset(client, session):
    asset = Asset(symbol="RE", name="Real Estate", type="REAL_ESTATE", currency="VND", is_active=True)
    session.add(asset)
    session.flush()
    session.add(PriceSnapshot(asset_id=asset.id, date=datetime.date.today(), price=1500))
    session.commit()
    session.refresh(asset)
    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "BUY", "quantity": 10, "price": 1500, "fee": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["price"] == 1500


def test_create_transaction_price_fallback_to_market_snapshot(client, session):
    asset = _create_asset(session)
    snapshot = PriceSnapshot(asset_id=asset.id, date=datetime.date(2023, 1, 1), price=95)
    session.add(snapshot)
    session.commit()
    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "BUY", "quantity": 10, "fee": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["price"] == 95


def test_create_transaction_future_date(client, session):
    asset = _create_asset(session)
    future = datetime.date.today() + datetime.timedelta(days=1)
    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "BUY", "quantity": 10, "price": 100, "fee": 0, "date": future.isoformat()},
    )
    assert response.status_code == 400


def test_create_deposit_withdrawal_non_market_asset(client, session):
    asset = Asset(symbol="RE", name="Real Estate", type="REAL_ESTATE", currency="VND", is_active=True)
    session.add(asset)
    session.flush()
    session.add(PriceSnapshot(asset_id=asset.id, date=datetime.date.today(), price=1000))
    session.commit()
    session.refresh(asset)

    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "DEPOSIT", "quantity": 5, "price": 1000, "fee": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["type"] == "DEPOSIT"

    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "WITHDRAWAL", "quantity": 3, "price": 1000, "fee": 0, "date": "2023-01-02"},
    )
    assert response.status_code == 200
    assert response.json()["type"] == "WITHDRAWAL"



def test_deposit_withdrawal_rejected_for_market_asset(client, session):
    asset = _create_asset(session)
    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "DEPOSIT", "quantity": 10, "price": 100, "fee": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "WITHDRAWAL", "quantity": 10, "price": 100, "fee": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 400



def test_withdrawal_exceeds_holding_non_market_asset(client, session):
    asset = Asset(symbol="RE", name="Real Estate", type="REAL_ESTATE", currency="VND", is_active=True)
    session.add(asset)
    session.flush()
    session.add(PriceSnapshot(asset_id=asset.id, date=datetime.date.today(), price=1000))
    session.commit()
    session.refresh(asset)
    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "BUY", "quantity": 10, "price": 1000, "fee": 0, "date": "2023-01-01"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/transactions/",
        json={"asset_id": asset.id, "type": "WITHDRAWAL", "quantity": 15, "price": 1000, "fee": 0, "date": "2023-01-02"},
    )
    assert response.status_code == 400
