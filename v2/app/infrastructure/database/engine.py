"""Database engine and session management."""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.config import DB_PATH, ensure_directories


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


def get_engine(db_path: Path | None = None):
    """Create SQLAlchemy engine."""
    ensure_directories()
    path = db_path or DB_PATH
    url = f"sqlite:///{path}"
    engine = create_engine(
        url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(engine=None):
    """Return a sessionmaker bound to the engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory=None) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    if session_factory is None:
        session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine=None) -> None:
    """Create all tables."""
    if engine is None:
        engine = get_engine()
    # Import models so they are registered with Base.metadata
    from app.infrastructure.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)