from services.news.processor import NewsProcessor


def test_extract_vn_symbol():
    processor = NewsProcessor()
    text = "Cổ phiếu FPT và VNM tăng mạnh trong phiên giao dịch hôm nay"
    symbols = processor.extract_symbols(text)
    assert "FPT" in symbols
    assert "VNM" in symbols


def test_extract_us_symbol():
    processor = NewsProcessor()
    text = "Apple (AAPL) and Tesla (TSLA) rose after earnings"
    symbols = processor.extract_symbols(text)
    assert "AAPL" in symbols
    assert "TSLA" in symbols


def test_sentiment_positive_vi():
    processor = NewsProcessor()
    article = {
        "title": "Lợi nhuận tăng trưởng vượt kỳ vọng",
        "summary": "Công ty báo lãi lớn, cổ tức cao",
        "content_text": "",
        "language": "vi",
    }
    result = processor.process(article)
    assert result["sentiment_score"] > 0


def test_sentiment_negative_vi():
    processor = NewsProcessor()
    article = {
        "title": "Công ty lỗ nặng, rủi ro phá sản",
        "summary": "",
        "content_text": "",
        "language": "vi",
    }
    result = processor.process(article)
    assert result["sentiment_score"] < 0


def test_impact_high():
    processor = NewsProcessor()
    article = {
        "title": "Fed tăng lãi suất đột ngột",
        "summary": "Thị trường chứng khoán chao đảo",
        "content_text": "",
        "language": "vi",
    }
    result = processor.process(article)
    assert result["impact_score"] >= 0.3


def test_summary_fallback():
    processor = NewsProcessor()
    article = {
        "title": "Test",
        "summary": None,
        "content_text": "Câu một. Câu hai. Câu ba.",
        "language": "vi",
    }
    result = processor.process(article)
    assert result["summary"] is not None
    assert "Câu một" in result["summary"]


def test_extract_vn_symbol_no_number_noise():
    processor = NewsProcessor()
    text = (
        "MBS dự báo lợi nhuận một đại gia dầu khí có thể tăng trưởng "
        "hơn 380% trong quý 2, 30/06/2026 00:03"
    )
    symbols = processor.extract_symbols(text)
    assert "MBS" in symbols
    assert "380" not in symbols
    assert "2026" not in symbols
    assert "06" not in symbols
    assert "30" not in symbols
    assert "00" not in symbols
    assert "03" not in symbols
    assert "2" not in symbols


def test_extract_vn_symbol_no_vietnamese_fragments():
    processor = NewsProcessor()
    text = "Cổ phiếu FPT và VNM tăng trong phiên giao dịch khí hôm nay"
    symbols = processor.extract_symbols(text)
    assert "FPT" in symbols
    assert "VNM" in symbols
    # Vietnamese consonant clusters inside diacritic words should not be extracted
    assert "KH" not in symbols
    assert "TH" not in symbols
    assert "TR" not in symbols
    assert "TRONG" not in symbols
    assert "GIAO" not in symbols
    assert "H" not in symbols


def test_extract_known_symbol_overrides_stop_word():
    processor = NewsProcessor()
    # "SAN" is both a real ticker and a common Vietnamese word ("sản"). When it
    # appears as a standalone uppercase token it should still be extracted.
    text = "Cổ phiếu SAN tăng trong phiên giao dịch bất động sản"
    symbols = processor.extract_symbols(text)
    assert "SAN" in symbols
