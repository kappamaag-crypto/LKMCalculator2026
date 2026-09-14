"""Explicit promotion of TDS rules from UNKNOWN evidence to KNOWN.

Promotion is never automatic from PDF text extraction. A rule becomes KNOWN
only when:
1. the source document is already KNOWN (identity + binary SHA-256);
2. locator, value and applicability are explicit;
3. promote_tds_rule() is called deliberately.
"""

from __future__ import annotations

from dataclasses import replace

from app.services.tds_manifest import TDSDocument, TDSRule, verify_manifest


def promote_tds_rule(
    document: TDSDocument,
    rule: TDSRule,
    *,
    verified_by: str,
    verification_note: str = "",
) -> TDSRule:
    """Promote one rule to KNOWN after explicit human verification.

    Raises ValueError when the document or rule cannot legally become KNOWN.
    """
    if document.status != "KNOWN":
        raise ValueError("Cannot promote rule: source document is not KNOWN")
    if rule.document_id != document.document_id:
        raise ValueError("Rule document_id does not match the provided document")
    if not verified_by.strip():
        raise ValueError("verified_by is required for promotion")
    if not rule.locator.strip() or not rule.applicability.strip():
        raise ValueError("KNOWN promotion requires locator and applicability")
    if rule.value in (None, ""):
        raise ValueError("KNOWN promotion requires an explicit value")

    notes = rule.notes.strip()
    promotion_mark = f"promoted_by={verified_by.strip()}"
    if verification_note.strip():
        promotion_mark = f"{promotion_mark}; {verification_note.strip()}"
    combined_notes = f"{notes}; {promotion_mark}".strip("; ").strip()

    promoted = replace(rule, status="KNOWN", notes=combined_notes)
    verify_manifest((document,), (promoted,))
    return promoted


def parse_dft_range_um(value: str) -> tuple[float, float] | None:
    """Parse TDS DFT range text like '80-250 мкм' into (min, max) micrometres.

    Returns None when the value cannot be parsed — caller must treat as UNKNOWN.
    """
    text = value.strip().lower().replace("мкм", "").replace("um", "").replace(" ", "")
    text = text.replace("–", "-").replace("—", "-")
    if "-" not in text:
        return None
    left, right = text.split("-", 1)
    try:
        low = float(left.replace(",", "."))
        high = float(right.replace(",", "."))
    except ValueError:
        return None
    if low < 0 or high < 0 or low > high:
        return None
    return low, high
