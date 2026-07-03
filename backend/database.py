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
    """Create the sqlite-vec virtual table for article embeddings."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    if not settings.OLLAMA_EMBEDDING_ENABLED:
        return
    dim = settings.OLLAMA_EMBEDDING_DIMENSION
    with engine.connect() as conn:
        conn.execute(
            text(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS article_embeddings USING vec0(
                    article_id INTEGER,
                    embedding FLOAT[{dim}],
                    chunk_size=64
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
