from __future__ import annotations

import sqlite3
from pathlib import Path

from app.infrastructure.database.backup import backup_database, restore_database
from app.infrastructure.database.migrate import upgrade_database


def test_sqlite_backup_and_restore_preserve_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"

    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('before-upgrade')")
        connection.commit()

    backup_database(source, backup)

    with sqlite3.connect(source) as connection:
        connection.execute("INSERT INTO sample(value) VALUES ('after-backup')")
        connection.commit()

    restore_database(backup, restored)

    with sqlite3.connect(restored) as connection:
        rows = connection.execute("SELECT value FROM sample ORDER BY id").fetchall()

    assert rows == [("before-upgrade",)]


def test_database_backup_rejects_same_path(tmp_path: Path) -> None:
    database = tmp_path / "database.sqlite3"
    database.touch()

    try:
        backup_database(database, database)
    except ValueError as exc:
        assert "must differ" in str(exc)
    else:
        raise AssertionError("same-path backup must be rejected")


def test_alembic_upgrade_is_idempotent_and_reaches_head(tmp_path: Path) -> None:
    database = tmp_path / "migration.sqlite3"

    upgrade_database(database)
    upgrade_database(database)

    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert revision == ("007_system_templates",)
    assert "calculations" in tables
    assert "coating_system_layers" in tables
