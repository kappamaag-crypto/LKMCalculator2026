"""Service boundary for reviewed side-by-side DRAFT load (no auto-CONFIRM)."""
from pathlib import Path

from app.domain.system_template import SystemTemplateDraft
from app.services.system_template_service import SystemTemplateService


def _books_root() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "books",
        Path.cwd().parent / "books",
        Path.cwd() / "books",
        Path("/home/workdir/LKMCalculator2026/books"),
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise AssertionError("books/ root not found")


def test_load_reviewed_side_by_side_drafts_returns_only_draft_unknown_tds():
    root = _books_root()
    drafts = SystemTemplateService.load_reviewed_side_by_side_drafts(root)
    assert len(drafts) >= 10
    assert all(isinstance(d, SystemTemplateDraft) for d in drafts)
    assert all(d.status == "DRAFT" for d in drafts)
    assert all(d.metadata.get("tds_verified") == "UNKNOWN" for d in drafts)
    sheets = {d.source_sheet for d in drafts}
    assert "АКЗ" in sheets
    # Systems 2 and/or 3 contribute OGZ staging drafts
    assert any(d.source_sheet == "ОГЗ" for d in drafts)


def test_load_reviewed_side_by_side_drafts_respects_file_filter():
    root = _books_root()
    drafts = SystemTemplateService.load_reviewed_side_by_side_drafts(
        root, file_names=["Системы 3.xlsx"]
    )
    assert drafts
    assert all("Системы 3" in (d.source_path or "") or d.source_path.endswith("Системы 3.xlsx")
               for d in drafts)
    assert all(d.status == "DRAFT" for d in drafts)


def test_load_reviewed_side_by_side_drafts_missing_root_returns_empty():
    drafts = SystemTemplateService.load_reviewed_side_by_side_drafts(
        Path("/tmp/no-such-books-root-xyz")
    )
    assert drafts == ()


def test_can_confirm_rejects_reviewed_draft_without_tds_and_material_ids():
    root = _books_root()
    drafts = SystemTemplateService.load_reviewed_side_by_side_drafts(
        root, file_names=["Системы 3.xlsx"]
    )
    assert drafts
    ok, reasons = SystemTemplateService.can_confirm(drafts[0])
    assert ok is False
    assert any("TDS" in r or "материал" in r.lower() or "provenance" in r.lower() or "сопостав" in r.lower()
               for r in reasons)
