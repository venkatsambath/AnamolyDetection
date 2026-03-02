# Copyright 2025 VenkatSambath
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
