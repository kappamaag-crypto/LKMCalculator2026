"""Database engine and session management."""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import DB_PATH, ensure_directories


class Base(DeclarativeBase):
    pass


def get_engine(db_path: Path | None = None):
    ensure_directories()
    path = db_path or DB_PATH
    engine = create_engine(
        f"sqlite:///{path}",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory=None) -> Generator[Session, None, None]:
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
    """Create missing tables and apply pending non-destructive migrations."""
    if engine is None:
        engine = get_engine()
    from app.infrastructure.database import models  # noqa: F401
    from app.infrastructure.database import system_template_models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    database = engine.url.database
    if not database or database == ":memory:":
        return

    from app.infrastructure.database.migrate import stamp_database, upgrade_database
    from sqlalchemy import inspect

    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables:
        stamp_database(Path(database), "head")
    else:
        upgrade_database(Path(database))
