#!/usr/bin/env python3
"""Re-generate AI tags for all existing news articles.

Usage:
    python scripts/retag_news.py
    python scripts/retag_news.py --only-empty
    python scripts/retag_news.py --force-ollama
    python scripts/retag_news.py --limit 1000 --offset 0
"""

import argparse
import logging
import os
import sys
from typing import List

# Ensure the backend package is importable regardless of where the script is run from.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from sqlmodel import Session, select

from config import settings
from database import engine, init_db
from models import NewsArticle, NewsSymbol
from services.news.dictionaries import get_known_symbols
from services.news.processor import NewsProcessor

logger = logging.getLogger(__name__)


def _build_processor(force_ollama: bool) -> NewsProcessor:
    if force_ollama:
        settings.OLLAMA_ENABLED = True
    return NewsProcessor(known_symbols=get_known_symbols())


def _article_to_dict(article: NewsArticle) -> dict:
    """Return an article dict with tags cleared so the processor re-generates them."""
    return {
        "title": article.title or "",
        "summary": article.summary or "",
        "content_text": article.content_text or "",
        "language": article.language or "vi",
        "tags": None,
        "published_at": article.published_at,
    }


def _replace_symbols(session: Session, article_id: int, symbols: List[str]) -> None:
    """Remove old symbol links and insert the newly extracted ones."""
    existing = session.exec(
        select(NewsSymbol).where(NewsSymbol.article_id == article_id)
    ).all()
    for link in existing:
        session.delete(link)
    for symbol in symbols:
        session.add(NewsSymbol(article_id=article_id, symbol=symbol))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-generate AI tags for existing news articles."
    )
    parser.add_argument(
        "--only-empty",
        action="store_true",
        help="Only process articles that currently have no tags.",
    )
    parser.add_argument(
        "--force-ollama",
        action="store_true",
        help="Force the local Ollama LLM to be used even if OLLAMA_ENABLED is false.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of articles to commit in each database transaction batch.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to process (useful for testing).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of articles to skip before processing.",
    )
    args = parser.parse_args()

    init_db()
    processor = _build_processor(args.force_ollama)

    with Session(engine) as session:
        query = select(NewsArticle)
        if args.only_empty:
            query = query.where(
                (NewsArticle.tags == None) | (NewsArticle.tags == "")  # noqa: E711
            )
        if args.offset:
            query = query.offset(args.offset)
        if args.limit:
            query = query.limit(args.limit)

        articles = session.exec(query).all()
        total = len(articles)
        logger.info("retag found %d articles to process", total)

        updated = 0
        for i, article in enumerate(articles, start=1):
            article_dict = _article_to_dict(article)
            processed = processor.process(article_dict)

            article.tags = processed.get("tags")
            article.sentiment_score = processed.get("sentiment_score")
            article.impact_score = processed.get("impact_score")
            article.summary = processed.get("summary") or article.summary
            session.add(article)

            _replace_symbols(session, article.id, processed.get("symbols", []))
            updated += 1

            if i % args.batch_size == 0:
                session.commit()
                logger.info(
                    "retag processed %d/%d articles, updated %d",
                    i, total, updated,
                )

        session.commit()

    logger.info(
        "retag done. processed %d articles, updated %d",
        total, updated,
    )


if __name__ == "__main__":
    main()
