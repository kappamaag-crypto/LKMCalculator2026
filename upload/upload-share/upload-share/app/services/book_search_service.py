"""Application service for source-linked engineering book search."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select

from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.engineering_book import EngineeringBookChunkORM

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

    def _persist_chunks(self, chunks: tuple[BookContentChunk, ...]) -> None:
        """Replace the DB search index with the deterministic source index."""
        with get_session_factory()() as session:
            session.execute(delete(EngineeringBookChunkORM))
            session.add_all(
                EngineeringBookChunkORM(
                    relative_path=chunk.relative_path,
                    sha256=chunk.sha256,
                    locator=chunk.locator,
                    text=chunk.text,
                )
                for chunk in chunks
            )
            session.commit()

    def rebuild(self) -> int:
        """Rebuild filesystem content index and persist it in the application DB."""
        self._chunks = build_content_index(self.books_root)
        self._persist_chunks(self._chunks)
        return len(self._chunks)

    @staticmethod
    def _from_orm(row: EngineeringBookChunkORM) -> BookSearchResult:
        return BookSearchResult(
            relative_path=row.relative_path,
            locator=row.locator,
            sha256=row.sha256,
            text=row.text,
        )

    def search_database(self, query: str, *, limit: int = 20) -> tuple[BookSearchResult, ...]:
        """Search the persisted DB index while retaining source identity."""
        terms = tuple(term for term in query.strip().lower().split() if term)
        if not terms or limit <= 0:
            return ()

        with get_session_factory()() as session:
            statement = select(EngineeringBookChunkORM)
            for term in terms:
                statement = statement.where(EngineeringBookChunkORM.text.ilike(f"%{term}%"))
            statement = statement.order_by(
                EngineeringBookChunkORM.relative_path,
                EngineeringBookChunkORM.locator,
            ).limit(limit)
            rows = session.scalars(statement).all()

        return tuple(self._from_orm(row) for row in rows)

    def search(self, query: str, *, limit: int = 20) -> tuple[BookSearchResult, ...]:
        """Search the DB index, rebuilding it only when no persisted index exists."""
        if not query.strip() or limit <= 0:
            return ()

        with get_session_factory()() as session:
            has_index = session.scalar(select(EngineeringBookChunkORM.id).limit(1)) is not None

        if not has_index:
            self.rebuild()
            return tuple(
                BookSearchResult(
                    relative_path=chunk.relative_path,
                    locator=chunk.locator,
                    sha256=chunk.sha256,
                    text=chunk.text,
                )
                for chunk in search_content(self._chunks or (), query, limit=limit)
            )

        return self.search_database(query, limit=limit)
