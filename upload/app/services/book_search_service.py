"""Application service for source-linked engineering book search."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .book_content_index import BookContentChunk, build_content_index, search_content


@dataclass(frozen=True)
class BookSearchResult:
    """A search hit with source identity kept explicit for UI/citations."""

    relative_path: str
    locator: str
    sha256: str
    text: str


class BookSearchService:
    """Search repository-resident engineering documents without normative inference."""

    def __init__(self, books_root: Path) -> None:
        self.books_root = books_root
        self._chunks: tuple[BookContentChunk, ...] | None = None

    def rebuild(self) -> int:
        """Rebuild the deterministic content index and return its chunk count."""
        self._chunks = build_content_index(self.books_root)
        return len(self._chunks)

    def search(self, query: str, *, limit: int = 20) -> tuple[BookSearchResult, ...]:
        """Search indexed content, rebuilding lazily when necessary."""
        if self._chunks is None:
            self.rebuild()
        assert self._chunks is not None
        return tuple(
            BookSearchResult(
                relative_path=chunk.relative_path,
                locator=chunk.locator,
                sha256=chunk.sha256,
                text=chunk.text,
            )
            for chunk in search_content(self._chunks, query, limit=limit)
        )
