from __future__ import annotations

import sqlite3
from pathlib import Path

from app.infrastructure.database.backup import backup_database, restore_database
from app.infrastructure.database.migrate import upgrade_database


EXPECTED_HEAD = "009_nullable_material_thinner_required"


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

    assert revision == (EXPECTED_HEAD,)
    assert "calculations" in tables
    assert "coating_system_layers" in tables


def test_backup_missing_source_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    try:
        backup_database(missing, backup)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing source must raise FileNotFoundError")


def test_restore_missing_backup_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing_backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    try:
        restore_database(missing, target)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing backup must raise FileNotFoundError")


def test_backup_then_restore_roundtrip_with_multiple_tables(tmp_path: Path) -> None:
    source = tmp_path / "multi.sqlite3"
    backup = tmp_path / "multi.bak"
    restored = tmp_path / "multi.restored"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE a (id INTEGER PRIMARY KEY, v TEXT)")
        conn.execute("CREATE TABLE b (id INTEGER PRIMARY KEY, v TEXT)")
        conn.execute("INSERT INTO a(v) VALUES ('A1')")
        conn.execute("INSERT INTO b(v) VALUES ('B1')")
        conn.commit()
    backup_database(source, backup)
    with sqlite3.connect(source) as conn:
        conn.execute("INSERT INTO a(v) VALUES ('A2')")
        conn.commit()
    restore_database(backup, restored)
    with sqlite3.connect(restored) as conn:
        assert conn.execute("SELECT v FROM a ORDER BY id").fetchall() == [("A1",)]
        assert conn.execute("SELECT v FROM b ORDER BY id").fetchall() == [("B1",)]


def test_alembic_head_revision_id_matches_current_head() -> None:
    """Lock the current migration head identity used by upgrade tests."""
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    revs = {}
    downs = set()
    for path in versions.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        rev = None
        down = None
        for line in text.splitlines():
            if line.startswith("revision ="):
                rev = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("down_revision ="):
                down = line.split("=", 1)[1].strip().strip('"').strip("'")
                if down == "None":
                    down = None
        if rev:
            revs[rev] = down
            if down:
                downs.add(down)
    head_ids = [r for r in revs if r not in downs]
    assert head_ids == [EXPECTED_HEAD]
