"""Hybrid news search API endpoint."""

import logging

from fastapi import APIRouter, Query

from services.news.search import search_news

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


@router.get("/search/news")
def search_news_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
):
    """Hybrid search across news articles (FTS5 BM25 + vector similarity)."""
    results = search_news(q, limit)
    return {"query": q, "results": results, "count": len(results)}
