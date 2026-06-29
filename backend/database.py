import os

from sqlalchemy import event, inspect, text
from sqlmodel import SQLModel, create_engine, Session

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


def _seed_default_source_settings(session):
    from services.source_config import seed_default_sources
    seed_default_sources(session)


def init_db():
    SQLModel.metadata.create_all(engine)
    _ensure_columns()
    with Session(engine) as session:
        _seed_default_source_settings(session)


def get_session():
    with Session(engine) as session:
        yield session
