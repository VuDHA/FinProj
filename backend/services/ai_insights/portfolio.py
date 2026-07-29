"""AI insight service for the portfolio / dashboard page."""

from typing import Any, Dict

from services.ai_insights.prompts import (
    base_prompt,
    format_currency,
    format_percent,
    generate_insight,
    minify_dict,
)


class PortfolioInsightService:
    """Generate an AI critique and suggestions for the current portfolio."""

    MAX_ITEMS = 20
    ITEM_FIELDS = ["symbol", "type", "current_value", "pnl_percent", "quantity"]

    def build_prompt(self, portfolio: Dict[str, Any], risk: Dict[str, Any], rebalance: Dict[str, Any]) -> str:
        data_lines = []
        data_lines.append(
            f"Tổng danh mục: giá trị={format_currency(portfolio.get('total_value', 0))}, "
            f"giá vốn={format_currency(portfolio.get('total_cost', 0))}, "
            f"lợi nhuận={format_currency(portfolio.get('total_pnl', 0))} "
            f"({format_percent(portfolio.get('total_pnl_percent', 0))})"
        )
        stable_value = portfolio.get('stable_value', 0)
        if stable_value:
            data_lines.append(
                f"Tài sản ổn định (không định giá thị trường hàng ngày): "
                f"giá trị={format_currency(stable_value)}. "
                f"Loại tài sản này được hiển thị riêng và không tính vào lợi nhuận/lỗ."
            )

        items = portfolio.get("items", [])
        if items:
            data_lines.append(f"Các tài sản đang nắm giữ (top {self.MAX_ITEMS}):")
            for item in minify_dict(items, self.ITEM_FIELDS)[: self.MAX_ITEMS]:
                data_lines.append(
                    f" - {item.get('symbol', '')} ({item.get('type', '')}): "
                    f"giá trị={format_currency(item.get('current_value', 0))}, "
                    f"lợi nhuận={format_percent(item.get('pnl_percent', 0))}, "
                    f"tỷ trọng={format_percent((float(item.get('current_value') or 0)) / max(float(portfolio.get('total_value') or 1), 1) * 100)}"
                )
        else:
            data_lines.append("Chưa có tài sản nào trong danh mục.")

        if risk:
            data_lines.append(
                f"Chỉ số rủi ro: max drawdown={format_percent(risk.get('max_drawdown_percent', 0))}, "
                f"volatility={format_percent(risk.get('volatility', 0))}, "
                f"sharpe={risk.get('sharpe_ratio', 'N/A')}"
            )

        if rebalance:
            suggestions = rebalance.get("suggestions", [])
            if suggestions:
                data_lines.append("Chênh lệch phân bổ so với mục tiêu:")
                for s in minify_dict(suggestions, ["type", "current_percent", "target_percent", "diff_value"]):
                    data_lines.append(
                        f" - {s.get('type', '')}: hiện tại={format_percent(s.get('current_percent', 0))}, "
                        f"mục tiêu={format_percent(s.get('target_percent', 0))}, "
                        f"chênh lệch={format_currency(s.get('diff_value', 0))}"
                    )

        context = (
            "Đánh giá tổng quan, phân tích chi tiết, và các hành động gợi ý tiếp theo "
            "(rebalancing, cảnh báo giá, đa dạng hóa)."
        )
        return base_prompt("\n".join(data_lines), "cố vấn tài chính cá nhân", context)

    def generate(
        self,
        portfolio: Dict[str, Any],
        risk: Dict[str, Any],
        rebalance: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(portfolio, risk, rebalance)
        return generate_insight(prompt, task_name="portfolio_insight")
