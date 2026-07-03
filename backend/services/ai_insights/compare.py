"""AI insight service for the compare page."""

from typing import Any, Dict, List

from services.ai_insights.prompts import (
    base_prompt,
    format_currency,
    format_percent,
    generate_insight,
    minify_dict,
)


class CompareInsightService:
    """Generate an AI critique of the current comparison stats."""

    METRIC_FIELDS = [
        "symbol",
        "total_return",
        "annualized_return",
        "volatility",
        "max_drawdown_percent",
        "sharpe_ratio",
    ]

    def build_prompt(
        self,
        symbols: List[str],
        metrics: List[Dict[str, Any]],
        correlation: List[List[float]],
    ) -> str:
        data_lines = []
        data_lines.append(f"Các mã đang so sánh: {', '.join(symbols)}")

        metrics_compact = minify_dict(metrics, self.METRIC_FIELDS)
        if metrics_compact:
            data_lines.append("Chỉ số so sánh:")
            for m in metrics_compact:
                data_lines.append(
                    f" - {m.get('symbol', '')}: tổng lợi nhuận={format_percent(m.get('total_return', 0))}, "
                    f"lợi nhuận kỳ vọng={format_percent(m.get('annualized_return', 0))}, "
                    f"biến động={format_percent(m.get('volatility', 0))}, "
                    f"max drawdown={format_percent(m.get('max_drawdown_percent', 0))}, "
                    f"sharpe={m.get('sharpe_ratio', 'N/A')}"
                )

        if correlation and symbols:
            data_lines.append("Ma trận tương quan:")
            for i, sym_i in enumerate(symbols):
                for j, sym_j in enumerate(symbols):
                    if i < j:
                        value = correlation[i][j] if i < len(correlation) and j < len(correlation[i]) else 0.0
                        data_lines.append(f" - {sym_i} vs {sym_j}: {value:.4f}")

        context = (
            "Phân tích điểm mạnh/yếu của từng mã, chỉ ra sự đa dạng hóa (diversification), "
            "và đề xuất kết hợp hoặc hành động phù hợp."
        )
        return base_prompt("\n".join(data_lines), "chuyên gia phân tích chứng khoán", context)

    def generate(
        self,
        symbols: List[str],
        metrics: List[Dict[str, Any]],
        correlation: List[List[float]],
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(symbols, metrics, correlation)
        return generate_insight(prompt, task_name="compare_insight")
