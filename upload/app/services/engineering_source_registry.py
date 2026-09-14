"""Catalog of repository-resident engineering source documents.

This registry contains source identities only. It deliberately does not turn a
document name into normative limits, permissions, or prohibitions. Rules remain
UNKNOWN until explicitly extracted and verified from the source.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.normative import NormativeSource


@dataclass(frozen=True)
class EngineeringSource:
    """A selectable repository source with no implied engineering rule."""

    source: NormativeSource
    relative_path: str
    category: str


_DEFAULT_SOURCES = (
    ("ГОСТ 34667.1 (ISO 12944)", "books/ГОСТ 34667.1 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.2 (ISO 12944)", "books/ГОСТ 34667.2 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.3 (ISO 12944)", "books/ГОСТ 34667.3 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.4 (ISO 12944)", "books/ГОСТ 34667.4 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.5 (ISO 12944)", "books/ГОСТ 34667.5 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.6 (ISO 12944)", "books/ГОСТ 34667.6 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.7 (ISO 12944)", "books/ГОСТ 34667.7 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.8 (ISO 12944)", "books/ГОСТ 34667.8 (ISO 12944).pdf", "Нормативный документ"),
    ("ГОСТ 34667.9 (ISO 12944)", "books/ГОСТ 34667.9 (ISO 12944).pdf", "Нормативный документ"),
    ("ПОДГОТОВКА ПОВЕРХНОСТИ", "books/ПОДГОТОВКА ПОВЕРХНОСТИ.pdf", "Подготовка поверхности"),
    ("ТРЕБОВАНИЯ К ПОВЕРХНОСТИ", "books/ТРЕБОВАНИЯ К ПОВЕРХНОСТИ.pdf", "Подготовка поверхности"),
    ("СПОСОБЫ НАНЕСЕНИЯ ЛКМ", "books/СПОСОБЫ НАНЕСЕНИЯ ЛКМ.pdf", "Технология нанесения"),
)


class EngineeringSourceRegistry:
    """Deterministic registry for selectable source documents."""

    def __init__(self, sources: tuple[EngineeringSource, ...] | None = None) -> None:
        self._sources = sources if sources is not None else self._default_sources()

    @staticmethod
    def _default_sources() -> tuple[EngineeringSource, ...]:
        return tuple(
            EngineeringSource(
                source=NormativeSource(document_id=document_id, title=document_id, source_uri=relative_path),
                relative_path=relative_path,
                category=category,
            )
            for document_id, relative_path, category in _DEFAULT_SOURCES
        )

    def all(self) -> tuple[EngineeringSource, ...]:
        return self._sources

    def by_category(self, category: str) -> tuple[EngineeringSource, ...]:
        return tuple(item for item in self._sources if item.category == category)

    def get(self, document_id: str) -> EngineeringSource | None:
        return next((item for item in self._sources if item.source.document_id == document_id), None)

    def existing(self, base_path: Path) -> tuple[EngineeringSource, ...]:
        """Return registered sources whose repository files actually exist."""
        return tuple(item for item in self._sources if (base_path / item.relative_path).is_file())
