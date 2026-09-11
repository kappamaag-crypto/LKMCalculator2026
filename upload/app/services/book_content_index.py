"""Source-preserving content index for repository engineering documents.

Text extracted from source files is searchable reference material only. It is
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
    return re.sub(r"\s+", " ", text).strip()


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


def extract_content(source: BookSource, books_root: Path) -> tuple[BookContentChunk, ...]:
    """Extract searchable text while retaining source path and SHA-256.

    Supported formats are PDF and UTF-8 text-like files. Unsupported formats
    return no chunks rather than being interpreted heuristically.
    """
    path = books_root / source.relative_path
    suffix = source.suffix
    if suffix == ".pdf":
        parts = _read_pdf(path)
        locator_prefix = "page"
    elif suffix in {".txt", ".md", ".csv", ".json", ".yaml", ".yml"}:
        parts = _read_text(path)
        locator_prefix = "part"
    else:
        return ()

    chunks: list[BookContentChunk] = []
    for index, text in enumerate(parts, start=1):
        if not text:
            continue
        chunks.append(
            BookContentChunk(
                relative_path=source.relative_path,
                sha256=source.sha256,
                locator=f"{locator_prefix}:{index}",
                text=text,
            )
        )
    return tuple(chunks)


def build_content_index(books_root: Path) -> tuple[BookContentChunk, ...]:
    """Build a deterministic searchable index for all supported book files."""
    chunks: list[BookContentChunk] = []
    for source in index_books(books_root):
        chunks.extend(extract_content(source, books_root))
    return tuple(
        sorted(chunks, key=lambda item: (item.relative_path, item.locator))
    )


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
