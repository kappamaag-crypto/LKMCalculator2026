"""Safe Alembic migration runner for the application database."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import PROJECT_ROOT, DB_PATH


def upgrade_database() -> None:
    """Apply pending additive migrations to the configured SQLite database."""
    ini_path = PROJECT_ROOT / "alembic.ini"
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH}")
    command.upgrade(config, "head")
