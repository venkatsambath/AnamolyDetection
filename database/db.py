"""SQLAlchemy engine and session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import app_config

engine = create_engine(
    app_config.DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + multithreading
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they do not already exist, then apply any pending column migrations."""
    from database import models  # noqa: F401 — import triggers table registration
    Base.metadata.create_all(bind=engine)
    _apply_migrations()


def _apply_migrations():
    """
    Lightweight additive migrations: add columns that were introduced after initial
    table creation. Each ALTER TABLE is wrapped in a try/except so it is a no-op
    when the column already exists (SQLite does not support IF NOT EXISTS for columns).
    """
    import sqlalchemy as sa
    migrations = [
        "ALTER TABLE model_versions ADD COLUMN baseline_from VARCHAR(32)",
        "ALTER TABLE model_versions ADD COLUMN baseline_to VARCHAR(32)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(sa.text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists — safe to ignore
