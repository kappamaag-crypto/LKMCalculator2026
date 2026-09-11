"""Source-preserving content index for repository engineering documents.

Extracted PDF/spreadsheet text is searchable reference material only. It is
never promoted to a normative rule automatically; verified normative values
must still enter through ``verified_normative_loader`` with an explicit source
identity and SHA-256 check.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .book_index import BookSource, index_books


@dataclass(frozen=True)
class BookContentChunk:
    """One searchable content unit tied to an immutable source identity."""

    relative_path: str
    sha256: str
    locator: str
    text: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _read_text(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return tuple(_normalize(part) for part in text.split("\f") if _normalize(part))


def _read_pdf(path: Path) -> tuple[str, ...]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF content indexing requires the optional pypdf dependency"
        ) from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = _normalize(page.extract_text() or "")
        pages.append(text)
    return tuple(pages)


def _read_spreadsheet(path: Path) -> tuple[tuple[str, str], ...]:
    """Return non-empty spreadsheet rows as ``(locator, text)`` pairs.

    Values are serialized for search only. Workbook data is not interpreted as
    material properties or engineering rules at this layer.
    """
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError(
            "Spreadsheet content indexing requires the openpyxl dependency"
        ) from exc

    workbook = load_workbook(path, read_only=True, data_only=False)
    rows: list[tuple[str, str]] = []
    try:
        for worksheet in workbook.worksheets:
            for row_number, row in enumerate(
                worksheet.iter_rows(values_only=True), start=1
            ):
                values = [_normalize(value) for value in row]
                values = [value for value in values if value]
                if not values:
                    continue
                text = _normalize(" | ".join(values))
                rows.append((f"sheet:{worksheet.title}!row:{row_number}", text))
    finally:
        workbook.close()
    return tuple(rows)


def extract_content(source: BookSource, books_root: Path) -> tuple[BookContentChunk, ...]:
    """Extract searchable text while retaining source path and SHA-256.

    Supported formats are PDF, UTF-8 text-like files and XLS/XLSX workbooks.
    Unsupported formats return no chunks rather than being interpreted
    heuristically.
    """
    path = books_root / source.relative_path
    suffix = source.suffix
    if suffix == ".pdf":
        parts = tuple((f"page:{index}", text) for index, text in enumerate(_read_pdf(path), start=1))
    elif suffix in {".txt", ".md", ".csv", ".json", ".yaml", ".yml"}:
        parts = tuple((f"part:{index}", text) for index, text in enumerate(_read_text(path), start=1))
    elif suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        parts = _read_spreadsheet(path)
    elif suffix == ".xls":
        # openpyxl deliberately does not support legacy BIFF .xls files.
        # Keep the source indexed by identity, but do not guess its contents.
        return ()
    else:
        return ()

    return tuple(
        BookContentChunk(
            relative_path=source.relative_path,
            sha256=source.sha256,
            locator=locator,
            text=text,
        )
        for locator, text in parts
        if text
    )


def build_content_index(books_root: Path) -> tuple[BookContentChunk, ...]:
    """Build a deterministic searchable index for all supported book files."""
    chunks: list[BookContentChunk] = []
    for source in index_books(books_root):
        chunks.extend(extract_content(source, books_root))
    return tuple(sorted(chunks, key=lambda item: (item.relative_path, item.locator)))


def search_content(
    chunks: tuple[BookContentChunk, ...], query: str, *, limit: int = 20
) -> tuple[BookContentChunk, ...]:
    """Return source-linked chunks containing all normalized query terms.

    Matching is deliberately simple and deterministic. This layer is a
    reference search facility, not an engineering recommendation engine.
    """
    terms = tuple(term for term in _normalize(query).lower().split(" ") if term)
    if not terms or limit <= 0:
        return ()

    matches = [
        chunk
        for chunk in chunks
        if all(term in chunk.text.lower() for term in terms)
    ]
    return tuple(matches[:limit])
