from models import NewsArticle, NewsSource


def test_ai_summary_returns_summary(client, session):
    source = NewsSource(code="test", name="Test", source_type="rss", language="vi")
    session.add(source)
    session.commit()
    session.refresh(source)

    article = NewsArticle(
        source_id=source.id,
        url="http://test/1",
        title="Thị trường chứng khoán tăng điểm",
        summary="VNINDEX tăng 1%",
        language="vi",
    )
    session.add(article)
    session.commit()

    response = client.post("/api/v1/news/ai-summary", json={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]
    assert data["article_count"] == 1
    assert isinstance(data["used_ollama"], bool)
