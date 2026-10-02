"""
SQLAlchemy engine/session management.

SQLite is used for local development, as specified in the project brief.
The database_url is fully configurable via the DATABASE_URL environment
variable so the app can be pointed at Postgres/MySQL later without code
changes to the models or services.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_database_url(url: str) -> str:
    """Some hosts (Render, Heroku, etc.) hand out DATABASE_URL as
    'postgres://...', which SQLAlchemy 2.x rejects -- it requires the
    explicit 'postgresql://' scheme. Normalize transparently."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


_database_url = _normalize_database_url(settings.database_url)
connect_args = {"check_same_thread": False} if _database_url.startswith("sqlite") else {}

engine = create_engine(_database_url, connect_args=connect_args, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context manager for use outside of FastAPI request handlers (scripts, tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called on application startup."""
    from app.models import models  # noqa: F401  (ensures models are registered)

    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


# SQLAlchemy's create_all() only creates tables that don't exist yet -- it
# never alters an existing table to add a newly-introduced column. Since
# this project has no Alembic migration chain, new nullable columns are
# added here in a small, idempotent, cross-database-safe way so that an
# already-deployed database (local SQLite or a live Postgres instance)
# picks up schema additions without anyone needing to drop and recreate it.
_PENDING_COLUMNS: list[tuple[str, str, str]] = [
    # (table, column, SQL type) -- always nullable, always additive/safe.
    ("users", "security_question", "VARCHAR(255)"),
    ("users", "security_answer_hash", "VARCHAR(255)"),
]


def _run_lightweight_migrations() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, column, sql_type in _PENDING_COLUMNS:
            if table not in existing_tables:
                continue  # create_all() will have made it fresh with all current columns
            existing_columns = {c["name"] for c in inspector.get_columns(table)}
            if column in existing_columns:
                continue
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
            except Exception:
                # Another worker may have added it concurrently, or the
                # specific database dialect phrases this differently; never
                # let a best-effort migration crash app startup.
                pass
