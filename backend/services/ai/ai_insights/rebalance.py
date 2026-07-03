"""AI insight service for the rebalance page."""

from typing import Any, Dict

from services.ai.ai_insights.prompts import (
    base_prompt,
    format_currency,
    format_percent,
    generate_insight,
    minify_dict,
)


class RebalanceInsightService:
    """Generate an AI critique and suggested actions for rebalancing."""

    def build_prompt(self, rebalance: Dict[str, Any]) -> str:
        data_lines = []
        data_lines.append(
            f"Tổng giá trị danh mục: {format_currency(rebalance.get('total_value', 0))}"
        )

        suggestions = minify_dict(
            rebalance.get("suggestions", []),
            ["type", "current_percent", "target_percent", "diff_value"],
        )
        if suggestions:
            data_lines.append("Phân bổ hiện tại so với mục tiêu:")
            for s in suggestions:
                data_lines.append(
                    f" - {s.get('type', '')}: hiện tại={format_percent(s.get('current_percent', 0))}, "
                    f"mục tiêu={format_percent(s.get('target_percent', 0))}, "
                    f"chênh lệch={format_currency(s.get('diff_value', 0))}"
                )
        else:
            data_lines.append("Chưa có gợi ý cân bằng.")

        trades = minify_dict(
            rebalance.get("trades", []),
            ["symbol", "action", "quantity", "estimated_price", "estimated_value"],
        )
        if trades:
            data_lines.append("Giao dịch đề xuất:")
            for t in trades:
                data_lines.append(
                    f" - {t.get('symbol', '')}: {t.get('action', '')} "
                    f"{t.get('quantity', 0)} @ {format_currency(t.get('estimated_price', 0))} "
                    f"= {format_currency(t.get('estimated_value', 0))}"
                )
        else:
            data_lines.append("Không có giao dịch đề xuất.")

        context = (
            "Phân tích mức độ lệch so với mục tiêu, chỉ ra rủi ro hoặc cơ hội, "
            "và đề xuất các hành động tiếp theo (điều chỉnh mục tiêu, mua/bán, giữ nguyên, đặt cảnh báo)."
        )
        return base_prompt("\n".join(data_lines), "chuyên gia quản lý danh mục", context)

    def generate(self, rebalance: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self.build_prompt(rebalance)
        return generate_insight(prompt, task_name="rebalance_insight")
