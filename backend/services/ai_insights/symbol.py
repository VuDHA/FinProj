"""AI insight service for a single market symbol."""

from typing import Any, Dict, List, Optional

from services.ai_insights.prompts import (
    base_prompt,
    format_currency,
    format_percent,
    generate_insight,
    minify_dict,
)


class SymbolAIInsightService:
    """Generate an AI analysis for a single stock or fund symbol."""

    def build_prompt(
        self,
        symbol: str,
        name: str,
        symbol_type: str,
        detail: Dict[str, Any],
        history: List[Dict[str, Any]],
        stats: Optional[Dict[str, Any]],
    ) -> str:
        data_lines = []
        data_lines.append(f"Mã: {symbol} ({name}) - Loại: {symbol_type}")

        if detail:
            compact = minify_dict(
                detail,
                [
                    "exchange",
                    "fund_type",
                    "owner",
                    "management_fee",
                    "inception_date",
                    "nav",
                    "sector",
                    "industry",
                    "market_cap",
                    "pe",
                    "pb",
                    "dividend_yield",
                    "price",
                    "change_percent",
                ],
            )
            data_lines.append("Thông tin cơ bản:")
            for key, value in compact.items():
                data_lines.append(f" - {key}: {value}")

        if stats:
            data_lines.append("Chỉ số kỹ thuật / lịch sử:")
            data_lines.append(
                f" - Tổng lợi nhuận: {format_percent(stats.get('total_return', 0))}"
            )
            data_lines.append(
                f" - Lợi nhuận kỳ vọng: {format_percent(stats.get('annualized_return', 0))}"
            )
            data_lines.append(
                f" - Biến động: {format_percent(stats.get('volatility', 0))}"
            )
            data_lines.append(
                f" - Giá cao nhất: {format_currency(stats.get('max', 0))}"
            )
            data_lines.append(
                f" - Giá thấp nhất: {format_currency(stats.get('min', 0))}"
            )
            data_lines.append(
                f" - Số phiên: {stats.get('days', 0)}"
            )

        if history:
            recent = minify_dict(history[-30:], ["date", "price"])
            data_lines.append("Giá 30 phiên gần nhất:")
            for point in recent:
                data_lines.append(
                    f" - {point.get('date', '')}: {format_currency(point.get('price', 0))}"
                )

        context = (
            f"Phân tích chi tiết mã {symbol}. Đưa ra nhận định tổng quan, điểm mạnh/yếu, "
            "xu hướng giá gần đây, rủi ro, và gợi ý hành động cho nhà đầu tư."
        )
        return base_prompt("\n".join(data_lines), "chuyên gia phân tích chứng khoán", context)

    def generate(
        self,
        symbol: str,
        name: str,
        symbol_type: str,
        detail: Dict[str, Any],
        history: List[Dict[str, Any]],
        stats: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(symbol, name, symbol_type, detail, history, stats)
        return generate_insight(prompt, task_name="symbol_insight")
