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
