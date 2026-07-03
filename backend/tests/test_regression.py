import csv
import datetime
import io

from models import Asset, NewsArticle, NewsSource, NewsSymbol
from services.news.alerts import AlertService
from services.smart_import import SmartImportService
from sqlmodel import select


def test_regression_smart_import_select_import(session):
    """Regression: SmartImportService.import_data must not raise NameError for 'select'."""
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
    assert result.created == 1
    assert not result.errors

    asset = session.exec(select(Asset).where(Asset.symbol == "VCB")).first()
    assert asset is not None
    assert asset.name == "Vietcombank"


def test_regression_alert_service_generates_alert(session, client):
    """Regression: AlertService must generate alerts against the test DB."""
    source = NewsSource(code="cafef", name="CafeF", source_type="rss", language="vi")
    session.add(source)
    session.commit()
    session.refresh(source)

    asset = Asset(symbol="HPG", name="Hoa Phat", type="STOCK", currency="VND")
    session.add(asset)
    session.commit()

    article = NewsArticle(
        source_id=source.id,
        url="https://example.com/hpg-news",
        title="Tin HPG quan trọng",
        summary="summary",
        published_at=datetime.datetime.utcnow(),
        impact_score=0.9,
        language="vi",
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    session.add(NewsSymbol(article_id=article.id, symbol="HPG"))
    session.commit()

    count = AlertService(session).generate_alerts(hours=1)
    assert count >= 1

    response = client.get("/api/v1/news/alerts/list")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1
    assert alerts[0]["symbol"] == "HPG"
    assert alerts[0]["alert_type"] == "breaking"
