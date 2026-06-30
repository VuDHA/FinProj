import re
from typing import List, Tuple


VIETNAMESE_HIGH_IMPACT = [
    "kết quả kinh doanh", "công bố KQKD", "báo cáo tài chính", "chia cổ tức",
    "thâu tóm", "mua lại", "sáp nhập", "M&A", "phá sản", "điều tra", "kiện tụng",
    "trừng phạt", "phạt nặng", "cấm", "đình chỉ", "thu hồi giấy phép", "lãi suất",
    "Fed", "tỷ giá", "biến động tỷ giá", "khủng hoảng", "suy thoái", "chiến tranh",
    "xung đột địa chính trị", "bán tháo", "rút vốn", "cắt giảm", "sa thải hàng loạt",
    "thay đổi luật", "chính sách mới", "quyết định của chính phủ", "thông qua luật",
    "thị trường chứng khoán sụt giảm", "VN-Index giảm mạnh", "HNX-Index", "UPCoM",
]

VIETNAMESE_MEDIUM_IMPACT = [
    "dự báo", "triển vọng", "kế hoạch", "mở rộng", "đầu tư mới", "hợp tác",
    "thắng thầu", "ký hợp đồng", "tăng vốn", "phát hành thêm", "mua cổ phiếu quỹ",
    "cải thiện", "tăng trưởng", "thị phần", "cạnh tranh", "thay đổi ban lãnh đạo",
    "bổ nhiệm", "miễn nhiệm", "tái cấu trúc",
]

ENGLISH_HIGH_IMPACT = [
    "earnings", "earnings report", "quarterly results", "dividend", "merger",
    "acquisition", "M&A", "bankruptcy", "investigation", "lawsuit", "scandal",
    "fraud", "penalty", "fine", "sanctions", "ban", "suspend", "rate hike",
    "Fed decision", "interest rate", "currency crisis", "recession", "war",
    "geopolitical", "market crash", "sell-off", "mass layoff", "policy change",
    "new law", "government decision", "SEC", "FDA approval", "patent approval",
]

ENGLISH_MEDIUM_IMPACT = [
    "forecast", "outlook", "guidance", "plan", "expansion", "new investment",
    "partnership", "contract", "share buyback", "restructuring", "leadership change",
    "appointment", "resignation", "market share", "competition", "upgrade",
    "downgrade", "analyst rating",
]


def _find_matches(text: str, keywords: List[str]) -> List[Tuple[str, int]]:
    matches = []
    text_lower = text.lower()
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword.lower()), text_lower):
            matches.append((keyword, match.start()))
    return matches


def analyze_impact(text: str, language: str = "vi") -> float:
    """
    Rule-based impact scoring.
    Returns a score in [0.0, 1.0] where higher means more market-moving.
    """
    if not text:
        return 0.0

    if language == "vi":
        high_keywords = VIETNAMESE_HIGH_IMPACT
        medium_keywords = VIETNAMESE_MEDIUM_IMPACT
    else:
        high_keywords = ENGLISH_HIGH_IMPACT
        medium_keywords = ENGLISH_MEDIUM_IMPACT

    high_matches = len(_find_matches(text, high_keywords))
    medium_matches = len(_find_matches(text, medium_keywords))

    score = min(high_matches * 0.4 + medium_matches * 0.15, 1.0)
    return round(score, 2)


def impact_label(score: float) -> str:
    if score is None:
        return "low"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"
