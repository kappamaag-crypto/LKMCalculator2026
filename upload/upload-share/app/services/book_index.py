"""Deterministic index of repository-resident engineering source files.

This module deliberately indexes source identity and file integrity only. It does
not infer engineering rules from filenames or PDF text. Normative values remain
UNKNOWN until they are explicitly verified through the normative sidecar flow.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BookSource:
    """One repository-resident source document."""

    relative_path: str
    title: str
    suffix: str
    size_bytes: int
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_books(books_root: Path) -> tuple[BookSource, ...]:
    """Return a deterministic integrity index for files under ``books_root``.

    Only regular files are included. The returned paths are repository-relative
to ``books_root`` and sorted for stable persistence, comparison and later KB
assembly. PDF contents are intentionally not interpreted here.
    """
    root = books_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"books directory not found: {books_root}")

    entries: list[BookSource] = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        entries.append(
            BookSource(
                relative_path=relative,
                title=path.stem,
                suffix=path.suffix.lower(),
                size_bytes=path.stat().st_size,
                sha256=_sha256(path),
            )
        )
    return tuple(entries)
