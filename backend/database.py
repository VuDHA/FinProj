import os

from sqlalchemy import event, inspect, text
from sqlmodel import SQLModel, create_engine, Session

import sqlite_vec

from config import settings


db_path = settings.DATABASE_URL.replace("sqlite:///", "")
os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_wal(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.enable_load_extension(True)
        sqlite_vec.load(dbapi_conn)
else:
    engine = create_engine(settings.DATABASE_URL, echo=False)


def _ensure_columns():
    """Add columns created by SQLModel 0.0.19 if the table already exists."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("asset")}
    with engine.connect() as conn:
        if "source" not in columns:
            conn.execute(text("ALTER TABLE asset ADD COLUMN source VARCHAR"))
        if "source_params" not in columns:
            conn.execute(text("ALTER TABLE asset ADD COLUMN source_params VARCHAR"))
        conn.commit()


def _ensure_news_columns():
    """Add region/relevance/standout columns to news tables for existing DBs."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    source_cols = {c["name"] for c in inspector.get_columns("newssource")}
    article_cols = {c["name"] for c in inspector.get_columns("newsarticle")}
    with engine.connect() as conn:
        if "region" not in source_cols:
            conn.execute(text("ALTER TABLE newssource ADD COLUMN region VARCHAR NOT NULL DEFAULT 'vn'"))
        if "region" not in article_cols:
            conn.execute(text("ALTER TABLE newsarticle ADD COLUMN region VARCHAR NOT NULL DEFAULT 'vn'"))
        if "relevance_score" not in article_cols:
            conn.execute(text("ALTER TABLE newsarticle ADD COLUMN relevance_score FLOAT"))
        if "is_standout" not in article_cols:
            conn.execute(text("ALTER TABLE newsarticle ADD COLUMN is_standout BOOLEAN NOT NULL DEFAULT 0"))
        if "tags" not in article_cols:
            conn.execute(text("ALTER TABLE newsarticle ADD COLUMN tags VARCHAR"))
        if "language" not in article_cols:
            conn.execute(text("ALTER TABLE newsarticle ADD COLUMN language VARCHAR"))
        conn.commit()


def _seed_default_source_settings(session):
    from services.source_config import seed_default_sources
    seed_default_sources(session)


def _seed_asset_type_settings(session):
    from services.asset_type_config import seed_asset_types
    seed_asset_types(session)


def _create_embedding_table():
    """Create the regular table for article embeddings.

    We previously used a sqlite-vec vec0 virtual table, but its fixed-size
    shadow tables can become corrupt (especially sqlite-vec 0.1.6 on Windows,
    which produces "Error opening vector blob" on the second chunk). A regular
    BLOB table plus the sqlite-vec scalar functions (vec_f32, vec_distance_L2)
    avoids the buggy vec0 storage while still supporting similarity search.
    """
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    embeddings_enabled = (
        settings.OLLAMA_EMBEDDING_ENABLED or settings.AI_PROVIDER == "gemini"
    )
    if not embeddings_enabled:
        return
    with engine.connect() as conn:
        # Drop any old vec0 virtual table (including its shadow tables) so we
        # start from a clean schema. Embeddings can be regenerated later.
        existing = conn.execute(
            text(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='article_embeddings'"
            )
        ).fetchone()
        if existing and "USING vec0" in (existing[0] or ""):
            print(
                "[database] dropping old vec0 article_embeddings table and shadow tables"
            )
            conn.execute(text("DROP TABLE IF EXISTS article_embeddings"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS article_embeddings (
                    article_id INTEGER PRIMARY KEY,
                    embedding BLOB NOT NULL
                )
                """
            )
        )
        conn.commit()


def init_db():
    SQLModel.metadata.create_all(engine)
    _ensure_columns()
    _ensure_news_columns()
    _create_embedding_table()
    with Session(engine) as session:
        _seed_default_source_settings(session)
        _seed_asset_type_settings(session)


def get_session():
    with Session(engine) as session:
        yield session
