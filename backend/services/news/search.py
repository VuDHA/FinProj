"""Hybrid news search service combining FTS5 (BM25) and sqlite-vec vector search.

Results from both retrieval methods are merged using Reciprocal Rank Fusion
(RRF, k=60), which is robust to different score scales and tends to surface
documents that are both lexically and semantically relevant.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine

logger = logging.getLogger(__name__)

# NewsArticle table name (SQLModel table=True lowercases the class name).
NEWS_TABLE = "newsarticle"
FTS_TABLE = "news_fts"
RRF_K = 60


# ---------------------------------------------------------------------------
# FTS5 index management
# ---------------------------------------------------------------------------

def _fts5_available() -> bool:
    """Check whether the SQLite build supports FTS5."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)"))
            conn.execute(text("DROP TABLE IF EXISTS _fts5_probe"))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("FTS5 is not available: %s", e)
        return False


def ensure_fts_index() -> bool:
    """Create the FTS5 virtual table for news articles if it doesn't exist.

    Uses an external-content table backed by ``newsarticle`` so the FTS index
    doesn't duplicate article text. Returns True on success.
    """
    if not _fts5_available():
        return False
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
                        title,
                        content,
                        content={NEWS_TABLE},
                        content_rowid=id
                    )
                    """
                )
            )
        logger.info("FTS5 news index ensured")
        return True
    except Exception as e:
        logger.warning("Failed to create FTS5 index: %s", e)
        return False


def index_article(article_id: int, title: str, content: Optional[str]) -> None:
    """Insert or update a single article in the FTS5 index."""
    if not ensure_fts_index():
        return
    try:
        with engine.begin() as conn:
            # External-content tables require a rowid delete-then-insert to update.
            conn.execute(
                text(f"DELETE FROM {FTS_TABLE} WHERE rowid = :id"),
                {"id": article_id},
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO {FTS_TABLE} (rowid, title, content)
                    VALUES (:id, :title, :content)
                    """
                ),
                {
                    "id": article_id,
                    "title": title or "",
                    "content": content or "",
                },
            )
    except Exception as e:
        logger.warning("Failed to index article %d in FTS5: %s", article_id, e)


def index_articles_batch(items: List[Tuple[int, str, Optional[str]]]) -> int:
    """Index multiple articles into FTS5. Returns the number indexed."""
    if not items or not ensure_fts_index():
        return 0
    count = 0
    try:
        with engine.begin() as conn:
            for article_id, title, content in items:
                conn.execute(
                    text(f"DELETE FROM {FTS_TABLE} WHERE rowid = :id"),
                    {"id": article_id},
                )
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {FTS_TABLE} (rowid, title, content)
                        VALUES (:id, :title, :content)
                        """
                    ),
                    {
                        "id": article_id,
                        "title": title or "",
                        "content": content or "",
                    },
                )
                count += 1
    except Exception as e:
        logger.warning("Failed to batch index articles in FTS5: %s", e)
    return count


def remove_article_from_index(article_id: int) -> None:
    """Remove an article from the FTS5 index."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {FTS_TABLE} WHERE rowid = :id"),
                {"id": article_id},
            )
    except Exception as e:
        logger.warning("Failed to remove article %d from FTS5: %s", article_id, e)


def sync_fts_index() -> int:
    """Rebuild the FTS5 index from all existing news articles.

    Returns the number of articles indexed. This is a full sync — useful after
    enabling FTS5 for the first time or after bulk imports.
    """
    if not ensure_fts_index():
        return 0
    try:
        with engine.begin() as conn:
            # Clear and rebuild.
            conn.execute(text(f"DELETE FROM {FTS_TABLE}"))
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, title, COALESCE(content_text, summary, '') AS content
                    FROM {NEWS_TABLE}
                    WHERE is_active = 1
                    """
                )
            ).fetchall()
            count = 0
            for row in rows:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {FTS_TABLE} (rowid, title, content)
                        VALUES (:id, :title, :content)
                        """
                    ),
                    {"id": int(row[0]), "title": row[1] or "", "content": row[2] or ""},
                )
                count += 1
        logger.info("FTS5 index synced: %d articles", count)
        return count
    except Exception as e:
        logger.warning("Failed to sync FTS5 index: %s", e)
        return 0


# ---------------------------------------------------------------------------
# BM25 keyword search via FTS5
# ---------------------------------------------------------------------------

def _bm25_search(query: str, limit: int) -> List[int]:
    """Run a BM25 keyword search and return ranked article ids."""
    if not ensure_fts_index():
        return []
    # FTS5 query syntax: wrap terms in quotes to avoid injection / parse errors.
    # Use a simple OR of terms for robustness.
    safe_query = _build_fts_query(query)
    if not safe_query:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT rowid, bm25({FTS_TABLE}) AS score
                    FROM {FTS_TABLE}
                    WHERE {FTS_TABLE} MATCH :q
                    ORDER BY score
                    LIMIT :limit
                    """
                ),
                {"q": safe_query, "limit": limit},
            ).fetchall()
        return [int(row[0]) for row in rows]
    except Exception as e:
        logger.warning("BM25 search failed: %s", e)
        return []


def _build_fts_query(query: str) -> str:
    """Build a safe FTS5 MATCH expression from a free-text query.

    Splits on whitespace and quotes each token, joining with OR so partial
    matches still surface results. This avoids FTS5 syntax errors from
    special characters.
    """
    tokens = [t.strip() for t in query.split() if t.strip()]
    if not tokens:
        return ""
    quoted = ['"{}"'.format(t.replace('"', "")) for t in tokens]
    return " OR ".join(quoted)


# ---------------------------------------------------------------------------
# Vector search via sqlite-vec
# ---------------------------------------------------------------------------

def _vector_search(query: str, limit: int) -> List[int]:
    """Run a vector similarity search and return ranked article ids."""
    try:
        from services.embedding_store import get_embedding
    except Exception as e:
        logger.warning("Could not import embedding_store: %s", e)
        return []

    vector = get_embedding(query)
    if not vector:
        return []
    try:
        import json
        serialized = json.dumps(vector, separators=(",", ":"))
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT article_id,
                           vec_distance_L2(embedding, vec_f32(:embedding)) AS distance
                    FROM article_embeddings
                    ORDER BY distance
                    LIMIT :limit
                    """
                ),
                {"embedding": serialized, "limit": limit},
            ).fetchall()
        return [int(row[0]) for row in rows]
    except Exception as e:
        logger.warning("Vector search failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    bm25_results: List[int],
    vector_results: List[int],
    k: int = RRF_K,
) -> List[Tuple[int, float]]:
    """Combine ranked result lists using Reciprocal Rank Fusion.

    Returns a list of (doc_id, fused_score) tuples sorted by score descending.
    """
    scores: Dict[int, float] = {}
    for rank, doc_id in enumerate(bm25_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, doc_id in enumerate(vector_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------

def _fetch_article_details(article_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Fetch article details for the given ids from the newsarticle table."""
    if not article_ids:
        return {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, title, summary, url, published_at, source_id,
                           category, tags, sentiment_score, impact_score,
                           relevance_score, language, region
                    FROM {NEWS_TABLE}
                    WHERE id IN :ids
                    """
                ),
                {"ids": tuple(article_ids)},
            ).fetchall()
        result: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            result[int(row[0])] = {
                "id": int(row[0]),
                "title": row[1],
                "summary": row[2],
                "url": row[3],
                "published_at": str(row[4]) if row[4] else None,
                "source_id": int(row[5]) if row[5] is not None else None,
                "category": row[6],
                "tags": row[7],
                "sentiment_score": float(row[8]) if row[8] is not None else None,
                "impact_score": float(row[9]) if row[9] is not None else None,
                "relevance_score": float(row[10]) if row[10] is not None else None,
                "language": row[11],
                "region": row[12],
            }
        return result
    except Exception as e:
        logger.warning("Failed to fetch article details: %s", e)
        return {}


def search_news(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Hybrid search for news articles.

    Combines FTS5 BM25 keyword search with sqlite-vec vector search using
    Reciprocal Rank Fusion. Falls back gracefully if either backend is
    unavailable.

    Returns a list of dicts with article details and a ``score`` field.
    """
    if not query or not query.strip():
        return []
    query = query.strip()

    # Fetch more candidates than `limit` so fusion has a richer pool.
    candidate_limit = max(limit * 3, 30)

    bm25_results = _bm25_search(query, candidate_limit)
    vector_results = _vector_search(query, candidate_limit)

    if not bm25_results and not vector_results:
        logger.info("Hybrid search returned no results for query: %s", query[:80])
        return []

    fused = reciprocal_rank_fusion(bm25_results, vector_results)
    top_ids = [doc_id for doc_id, _ in fused[:limit]]
    if not top_ids:
        return []

    details = _fetch_article_details(top_ids)

    # Build result list in fused-rank order, attaching the RRF score.
    results: List[Dict[str, Any]] = []
    score_map = {doc_id: score for doc_id, score in fused}
    for doc_id in top_ids:
        article = details.get(doc_id)
        if article is None:
            continue
        article["score"] = score_map.get(doc_id, 0.0)
        results.append(article)
    return results
