"""AI insight service for the analytics page."""

from typing import Any, Dict

from services.ai_insights.prompts import (
    base_prompt,
    format_currency,
    format_percent,
    generate_insight,
    minify_dict,
)


class AnalyticsInsightService:
    """Generate an AI critique and suggestions for the analytics summary."""

    MAX_PERFORMERS = 5
    MAX_MONTHLY = 6

    def build_prompt(self, analytics: Dict[str, Any], portfolio: Dict[str, Any]) -> str:
        data_lines = []
        period = f"{analytics.get('period_start', '')} đến {analytics.get('period_end', '')}"
        data_lines.append(f"Kỳ phân tích: {period}")
        data_lines.append(
            f"Tổng danh mục: giá trị={format_currency(analytics.get('total_value', 0))}, "
            f"giá vốn={format_currency(analytics.get('total_cost', 0))}, "
            f"thu nhập={format_currency(analytics.get('total_income', 0))}"
        )

        top = minify_dict(analytics.get("top_performers", [])[: self.MAX_PERFORMERS], ["symbol", "pnl_percent"])
        if top:
            data_lines.append("Top performers:")
            for item in top:
                data_lines.append(f" - {item.get('symbol', '')}: {format_percent(item.get('pnl_percent', 0))}")

        bottom = minify_dict(analytics.get("bottom_performers", [])[: self.MAX_PERFORMERS], ["symbol", "pnl_percent"])
        if bottom:
            data_lines.append("Bottom performers:")
            for item in bottom:
                data_lines.append(f" - {item.get('symbol', '')}: {format_percent(item.get('pnl_percent', 0))}")

        type_returns = minify_dict(analytics.get("type_returns", []), ["type", "value", "pnl_percent"])
        if type_returns:
            data_lines.append("Lợi nhuận theo loại tài sản:")
            for t in type_returns:
                data_lines.append(
                    f" - {t.get('type', '')}: giá trị={format_currency(t.get('value', 0))}, "
                    f"lợi nhuận={format_percent(t.get('pnl_percent', 0))}"
                )

        monthly = minify_dict(analytics.get("monthly_pnl", [])[-self.MAX_MONTHLY :], ["month", "pnl"])
        if monthly:
            data_lines.append("Lợi nhuận tháng gần đây:")
            for m in monthly:
                data_lines.append(f" - {m.get('month', '')}: {format_currency(m.get('pnl', 0))}")

        income = minify_dict(analytics.get("income", []), ["type", "total"])
        if income:
            data_lines.append("Thu nhập theo loại:")
            for i in income:
                data_lines.append(f" - {i.get('type', '')}: {format_currency(i.get('total', 0))}")

        context = (
            "Đánh giá hiệu suất danh mục, chỉ ra điểm mạnh/yếu, "
            "và đề xuất hành động cụ thể (cắt lỗ, chốt lời, cân bằng lại, tăng/giảm loại tài sản)."
        )
        return base_prompt("\n".join(data_lines), "chuyên gia phân tích đầu tư", context)

    def generate(
        self,
        analytics: Dict[str, Any],
        portfolio: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(analytics, portfolio)
        return generate_insight(prompt, task_name="analytics_insight")
