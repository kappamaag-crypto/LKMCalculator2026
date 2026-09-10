"""Consistent SQLite backup and restore helpers for database safety."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _validate_paths(source: Path, target: Path) -> None:
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise ValueError("Source and target database paths must differ")
    if not source.exists():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)


def backup_database(source_path: Path, backup_path: Path) -> None:
    """Create a transactionally consistent SQLite backup.

    SQLite's online backup API is used instead of copying the database file,
    so the snapshot remains valid even when the source database is open.
    """
    source = Path(source_path)
    backup = Path(backup_path)
    _validate_paths(source, backup)

    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(backup) as backup_connection:
            source_connection.backup(backup_connection)


def restore_database(backup_path: Path, target_path: Path) -> None:
    """Restore a SQLite database from a previously created backup."""
    backup = Path(backup_path)
    target = Path(target_path)
    _validate_paths(backup, target)

    with sqlite3.connect(backup) as backup_connection:
        with sqlite3.connect(target) as target_connection:
            backup_connection.backup(target_connection)
