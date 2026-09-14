"""Safe Alembic migration runner for the application database."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import PROJECT_ROOT, DB_PATH


def _alembic_config(db_path: Path) -> Config:
    ini_path = PROJECT_ROOT / "alembic.ini"
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def stamp_database(db_path: Path | None = None, revision: str = "head") -> None:
    """Record the given revision without running migrations (fresh create_all path)."""
    path = db_path or DB_PATH
    command.stamp(_alembic_config(path), revision)


def upgrade_database(db_path: Path | None = None) -> None:
    """Apply pending additive migrations to the requested SQLite database.

    Migrations 001+ are additive against an existing base schema. On a brand-new
    file we materialize the current ORM schema first, then stamp/upgrade so that
    additive ALTERs remain safe and idempotent.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    from sqlalchemy import create_engine, inspect
    from app.infrastructure.database.engine import Base

    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    # Import models so metadata is complete.
    from app.infrastructure.database import models  # noqa: F401
    from app.infrastructure.database import system_template_models  # noqa: F401

    tables = set(inspect(engine).get_table_names())
    if "materials" not in tables:
        Base.metadata.create_all(bind=engine)
        tables = set(inspect(engine).get_table_names())

    config = _alembic_config(path)
    if "alembic_version" not in tables:
        # Fresh schema from ORM already matches head — stamp then upgrade (no-op).
        command.stamp(config, "head")
    command.upgrade(config, "head")
