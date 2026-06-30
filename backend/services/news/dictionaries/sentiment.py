import re
from typing import Dict, List, Tuple


VIETNAMESE_POSITIVE = [
    "tăng trưởng", "tăng", "lợi nhuận tăng", "lãi lớn", "kỳ vọng tích cực",
    "cổ tức", "chia cổ tức", "mua vào", "tăng giá", "thuận lợi", "phục hồi",
    "bứt phá", "lạc quan", "tích cực", "khả quan", "vượt kỳ vọng", "cao hơn dự báo",
    "cải thiện", "mở rộng", "đầu tư", "tăng vốn", "hợp tác", "thắng thầu",
    "được chấp thuận", "phê duyệt", "thông qua", "thành công", "tốt hơn",
    "củng cố", "đứng đầu", "dẫn đầu", "vững mạnh", "sinh lời", "hiệu quả",
]

VIETNAMESE_NEGATIVE = [
    "giảm", "lỗ", "suy giảm", "rủi ro", "bán ra", "giảm giá", "khó khăn",
    "áp lực", "lo ngại", "phá sản", "thua lỗ", "bê bối", "điều tra", "kiện tụng",
    "trừng phạt", "phạt", "vi phạm", "cảnh báo", "tiêu cực", "bi quan",
    "thấp hơn kỳ vọng", "miss", "không đạt", "sụt giảm", "lao dốc", "sụt giảm mạnh",
    "bán tháo", "rút vốn", "cắt giảm", "sa thải", "đình chỉ", "thu hồi",
    "phá giá", "lạm phát cao", "lãi suất tăng", "khủng hoảng", "suy thoái",
    "chiến tranh", "xung đột", "bất ổn", "cú sốc", "thất bại", "trì hoãn",
]

ENGLISH_POSITIVE = [
    "growth", "increase", "profit", "earnings beat", "beat expectations", "dividend",
    "buy", "bullish", "rally", "recovery", "rebound", "surge", "soar", "jump",
    "rise", "gain", "strong", "optimistic", "positive", "outperform", "upgrade",
    "approve", "approval", "breakthrough", "partnership", "expansion", "investment",
    "acquisition", "merger", "deal", "contract", "win", "success", "milestone",
    "robust", "solid", "healthy", "improve", "upside", "momentum", "growth story",
]

ENGLISH_NEGATIVE = [
    "decrease", "decline", "loss", "earnings miss", "miss expectations", "sell",
    "bearish", "crash", "plunge", "drop", "fall", "tumble", "slump", "weak",
    "pessimistic", "negative", "underperform", "downgrade", "cut", "layoff",
    "bankruptcy", "default", "investigation", "lawsuit", "scandal", "fraud",
    "penalty", "fine", "violation", "warning", "risk", "concern", "recession",
    "inflation", "rate hike", "war", "conflict", "uncertainty", "delay", "fail",
    "disappoint", "lower guidance", "cut guidance", "withdraw", "suspend",
]

NEGATION_VIETNAMESE = ["không", "chưa", "chẳng", "không phải", "chưa phải"]
NEGATION_ENGLISH = ["not", "no", "never", "n't", "without", "fail to"]


def _find_matches(text: str, keywords: List[str]) -> List[Tuple[str, int]]:
    """Return list of (keyword, position) for each match in text."""
    matches = []
    text_lower = text.lower()
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword.lower()), text_lower):
            matches.append((keyword, match.start()))
    return matches


def _has_negation_nearby(text: str, position: int, window: int = 20) -> bool:
    """Check if a negation word appears within `window` characters before position."""
    start = max(0, position - window)
    snippet = text[start:position].lower()
    negations = NEGATION_VIETNAMESE + NEGATION_ENGLISH
    return any(neg in snippet for neg in negations)


def analyze_sentiment(text: str, language: str = "vi") -> float:
    """
    Rule-based sentiment analysis.
    Returns a score in [-1.0, +1.0] where 0 is neutral.
    """
    if not text:
        return 0.0

    if language == "vi":
        positive_keywords = VIETNAMESE_POSITIVE
        negative_keywords = VIETNAMESE_NEGATIVE
    else:
        positive_keywords = ENGLISH_POSITIVE
        negative_keywords = ENGLISH_NEGATIVE

    pos_score = 0.0
    neg_score = 0.0

    for keyword, pos in _find_matches(text, positive_keywords):
        if _has_negation_nearby(text, pos):
            neg_score += 0.5
        else:
            pos_score += 1.0

    for keyword, pos in _find_matches(text, negative_keywords):
        if _has_negation_nearby(text, pos):
            pos_score += 0.5
        else:
            neg_score += 1.0

    total = pos_score + neg_score
    if total == 0:
        return 0.0

    score = (pos_score - neg_score) / total
    # Clamp to [-1, 1]
    return max(-1.0, min(1.0, score))


def sentiment_label(score: float) -> str:
    if score is None:
        return "neutral"
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"
