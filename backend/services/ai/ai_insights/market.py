"""AI insight service for the market page."""

from typing import Any, Dict, List

from services.ai.ai_insights.prompts import (
    base_prompt,
    format_currency,
    format_percent,
    generate_insight,
    minify_dict,
)


class MarketInsightService:
    """Generate an AI summary and critique of current market data."""

    MAX_WATCHLIST = 10
    MAX_GOLD = 2
    MAX_FX = 3
    HOLDING_FIELDS = ["symbol", "current_value", "pnl_percent"]

    def build_prompt(
        self,
        watchlist: List[Dict[str, Any]],
        portfolio_holdings: List[Dict[str, Any]],
        gold_fx: Dict[str, Any],
    ) -> str:
        data_lines = []

        if watchlist:
            sorted_watchlist = sorted(
                watchlist,
                key=lambda q: abs(q.get("change_percent", 0) or 0),
                reverse=True,
            )[: self.MAX_WATCHLIST]
            data_lines.append("Top mã biến động mạnh:")
            for q in minify_dict(sorted_watchlist, ["symbol", "price", "change_percent"]):
                data_lines.append(
                    f" - {q.get('symbol', '')}: giá={q.get('price', 0)}, "
                    f"thay đổi={format_percent(q.get('change_percent', 0))}"
                )
        else:
            data_lines.append("Chưa có dữ liệu watchlist.")

        holdings = minify_dict(portfolio_holdings, self.HOLDING_FIELDS)
        if holdings:
            data_lines.append("Cổ phiếu/quỹ đang nắm giữ trong danh mục:")
            for item in holdings:
                data_lines.append(
                    f" - {item.get('symbol', '')}: giá trị={format_currency(item.get('current_value', 0))}, "
                    f"lợi nhuận={format_percent(item.get('pnl_percent', 0))}"
                )

        if gold_fx:
            gold = minify_dict(gold_fx.get("gold", [])[: self.MAX_GOLD], ["source", "buy", "sell"])
            fx = minify_dict(gold_fx.get("fx", [])[: self.MAX_FX], ["currency", "buy", "sell"])
            if gold:
                data_lines.append("Vàng:")
                for g in gold:
                    data_lines.append(
                        f" - {g.get('source', '')}: mua={g.get('buy', 0)}, bán={g.get('sell', 0)}"
                    )
            if fx:
                data_lines.append("Tỷ giá:")
                for f in fx:
                    data_lines.append(
                        f" - {f.get('currency', '')}: mua={f.get('buy', 0)}, bán={f.get('sell', 0)}"
                    )

        context = (
            "Tóm tắt tình hình thị trường, nhận định chi tiết, "
            "và gợi ý các mã cần chú ý hoặc hành động theo dõi."
        )
        return base_prompt("\n".join(data_lines), "nhà phân tích thị trường", context)

    def generate(
        self,
        watchlist: List[Dict[str, Any]],
        portfolio_holdings: List[Dict[str, Any]],
        gold_fx: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(watchlist, portfolio_holdings, gold_fx)
        return generate_insight(prompt, task_name="market_insight")
