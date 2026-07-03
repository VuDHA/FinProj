import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from common.models import Asset, NewsArticle, NewsSymbol, Transaction, Watchlist
from services.ai.embedding_store import EmbeddingStore


class RagContextService:
    """Build a personalized context for news AI tasks.

    Combines:
    - factual user context (portfolio, watchlist, recent transactions)
    - semantic retrieval of similar historical articles via sqlite-vec
    """

    def __init__(self, session: Session, embedding_store: Optional[EmbeddingStore] = None):
        self.session = session
        self.embeddings = embedding_store or EmbeddingStore()

    def user_facts(self) -> Dict[str, any]:
        """Collect user-specific facts that are relevant to news interpretation."""
        assets = self.session.exec(
            select(Asset)
            .where(Asset.is_active == True)
            .order_by(Asset.symbol)
        ).all()

        watchlist = self.session.exec(
            select(Watchlist)
            .order_by(Watchlist.added_at.desc())
        ).all()

        recent_transactions = self.session.exec(
            select(Transaction, Asset.symbol)
            .join(Asset, Asset.id == Transaction.asset_id)
            .order_by(Transaction.date.desc())
            .limit(5)
        ).all()

        # Aggregate portfolio by type for a quick allocation view.
        type_values = self.session.exec(
            select(Asset.type, func.sum(Transaction.quantity * Transaction.price))
            .join(Asset, Asset.id == Transaction.asset_id)
            .where(Transaction.type == "BUY")
            .group_by(Asset.type)
        ).all()

        return {
            "portfolio_symbols": [a.symbol for a in assets],
            "portfolio_summary": [
                {"symbol": a.symbol, "name": a.name, "type": a.type} for a in assets[:20]
            ],
            "watchlist": [w.symbol for w in watchlist],
            "recent_transactions": [
                {
                    "symbol": symbol,
                    "type": tx.type,
                    "quantity": tx.quantity,
                    "price": tx.price,
                    "date": tx.date.isoformat(),
                }
                for tx, symbol in recent_transactions
            ],
            "type_allocation": {t: round(float(v), 2) for t, v in type_values},
        }

    def similar_articles(self, title: str, summary: str, k: int = 5) -> List[Dict[str, any]]:
        """Find articles that are semantically similar to the provided text."""
        if not self.embeddings.enabled:
            return []

        query_text = f"{title or ''} {summary or ''}".strip()
        if not query_text:
            return []

        similar = self.embeddings.find_similar_for_text(query_text, k=k)
        if not similar:
            return []

        article_ids = [article_id for article_id, _ in similar]
        articles = self.session.exec(
            select(NewsArticle).where(NewsArticle.id.in_(article_ids))
        ).all()
        article_map = {a.id: a for a in articles}

        result = []
        for article_id, distance in similar:
            article = article_map.get(article_id)
            if not article:
                continue
            symbols = self.session.exec(
                select(NewsSymbol.symbol).where(NewsSymbol.article_id == article_id)
            ).all()
            result.append(
                {
                    "id": article_id,
                    "title": article.title,
                    "summary": article.summary,
                    "published_at": (
                        article.published_at.isoformat() if article.published_at else None
                    ),
                    "symbols": list(symbols),
                    "distance": round(distance, 4),
                }
            )
        return result

    def build_context(
        self,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        include_user_facts: bool = True,
        include_similar_articles: bool = True,
    ) -> Dict[str, any]:
        """Build the full RAG context for an AI prompt."""
        return {
            "user_facts": self.user_facts() if include_user_facts else {},
            "similar_articles": (
                self.similar_articles(title or "", summary or "")
                if include_similar_articles
                else []
            ),
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }

    def format_context(self, context: Dict[str, any], language: str = "vi") -> str:
        """Format the RAG context as a short string suitable for a small LLM prompt."""
        parts = []
        facts = context.get("user_facts") or {}
        similar = context.get("similar_articles") or []

        if facts.get("portfolio_symbols") or facts.get("watchlist"):
            if language == "vi":
                parts.append(
                    "Thông tin người dùng: "
                    + f"danh mục {', '.join(facts.get('portfolio_symbols', []))}; "
                    + f"theo dõi {', '.join(facts.get('watchlist', []))}."
                )
            else:
                parts.append(
                    "User context: "
                    + f"portfolio {', '.join(facts.get('portfolio_symbols', []))}; "
                    + f"watchlist {', '.join(facts.get('watchlist', []))}."
                )

        if similar:
            if language == "vi":
                parts.append("Các tin liên quan trước đây:")
            else:
                parts.append("Related past articles:")
            for article in similar[:3]:
                parts.append(f"- {article['title']}")

        return "\n".join(parts)
