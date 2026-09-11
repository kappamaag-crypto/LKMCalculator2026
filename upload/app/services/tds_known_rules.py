"""First explicitly promoted KNOWN TDS rules from SPKEFFA.

Each rule was promoted only after:
- document identity + binary SHA-256 were measured (spk_effa_tds_catalog);
- locator/value/applicability were recorded from the TDS PDF text;
- promote_tds_rule() was applied deliberately.

Rules not listed here remain UNKNOWN even if the document is KNOWN.
"""

from __future__ import annotations

from app.services.spk_effa_tds_catalog import spk_effa_tds_by_id, spk_effa_tds_documents
from app.services.tds_manifest import TDSRule, verify_manifest
from app.services.tds_rule_promotion import promote_tds_rule

# Material name substrings used to bind calculation materials to TDS documents.
MATERIAL_DOCUMENT_HINTS: tuple[tuple[str, str], ...] = (
    ("blank universal", "BLANK_UNIVERSAL_TDS"),
    ("blank finish", "BLANK_FINISH_TDS"),
)


def _promote(
    document_id: str,
    rule_id: str,
    value: str,
    locator: str,
    applicability: str,
    verified_by: str,
    note: str,
) -> TDSRule:
    document = spk_effa_tds_by_id(document_id)
    if document is None:
        raise ValueError(f"Unknown TDS document: {document_id}")
    staged = TDSRule(
        rule_id=rule_id,
        document_id=document_id,
        value=value,
        locator=locator,
        applicability=applicability,
        status="UNKNOWN",
        notes="Staged from TDS PDF text prior to explicit promotion.",
    )
    return promote_tds_rule(
        document,
        staged,
        verified_by=verified_by,
        verification_note=note,
    )


def known_tds_rules() -> tuple[TDSRule, ...]:
    """Return the current set of explicitly promoted KNOWN rules."""
    rules = (
        _promote(
            "BLANK_UNIVERSAL_TDS",
            "BLANK_UNIVERSAL_DFT_RANGE",
            "80-250 мкм",
            "Blank_Universal.pdf page 1, table «Толщина одного слоя» / «Толщина сухого слоя»",
            "recommended single-layer dry film thickness for Blank Universal",
            verified_by="engineering-review",
            note="Verified against SPKEFFA Blank_Universal.pdf binary "
            "SHA-256 9ab3872b849e523652088a3ba0d8b0788005c0134ac517305a9e2f01621b5887",
        ),
        _promote(
            "BLANK_UNIVERSAL_TDS",
            "BLANK_UNIVERSAL_SOLIDS_BY_VOLUME",
            "73 ± 2%",
            "Blank_Universal.pdf page 1, «Характеристики продукта» / «Сухой остаток по объему»",
            "volume solids for Blank Universal",
            verified_by="engineering-review",
            note="Verified against measured Blank_Universal.pdf binary SHA-256",
        ),
        _promote(
            "BLANK_UNIVERSAL_TDS",
            "BLANK_UNIVERSAL_DENSITY",
            "1,4 кг/л",
            "Blank_Universal.pdf page 1, «Характеристики продукта» / «Плотность»",
            "density for Blank Universal",
            verified_by="engineering-review",
            note="Verified against measured Blank_Universal.pdf binary SHA-256",
        ),
        _promote(
            "BLANK_FINISH_TDS",
            "BLANK_FINISH_DFT_RANGE",
            "50-90 мкм",
            "Blank_Finish.pdf page 1, table «Толщина одного слоя» / «Толщина сухого слоя»",
            "recommended single-layer dry film thickness for Blank Finish",
            verified_by="engineering-review",
            note="Verified against SPKEFFA Blank_Finish.pdf binary "
            "SHA-256 34465e17e1e1199c94f1391ca2d776dcd377d4d363e0c4513b4e8a40f7a9a235",
        ),
        _promote(
            "BLANK_FINISH_TDS",
            "BLANK_FINISH_SOLIDS_BY_VOLUME",
            "58±3%",
            "Blank_Finish.pdf page 1, «Характеристики продукта» / «Сухой остаток по объему»",
            "volume solids for Blank Finish",
            verified_by="engineering-review",
            note="Verified against measured Blank_Finish.pdf binary SHA-256",
        ),
        _promote(
            "BLANK_FINISH_TDS",
            "BLANK_FINISH_DENSITY",
            "1,3 г/см³",
            "Blank_Finish.pdf page 1, «Характеристики продукта» / «Плотность»",
            "density for Blank Finish",
            verified_by="engineering-review",
            note="Verified against measured Blank_Finish.pdf binary SHA-256",
        ),
    )
    verify_manifest(spk_effa_tds_documents(), rules)
    assert all(rule.status == "KNOWN" for rule in rules)
    return rules


def known_rules_for_document(document_id: str) -> tuple[TDSRule, ...]:
    return tuple(rule for rule in known_tds_rules() if rule.document_id == document_id)


def resolve_document_id_for_material_name(material_name: str) -> str | None:
    """Map a material display name to a catalogued TDS document when unambiguous."""
    lowered = material_name.strip().lower()
    if not lowered:
        return None
    matches = [doc_id for hint, doc_id in MATERIAL_DOCUMENT_HINTS if hint in lowered]
    if len(matches) == 1:
        return matches[0]
    return None


def known_dft_rule_for_material_name(material_name: str) -> TDSRule | None:
    document_id = resolve_document_id_for_material_name(material_name)
    if document_id is None:
        return None
    for rule in known_rules_for_document(document_id):
        if rule.rule_id.endswith("_DFT_RANGE") and rule.status == "KNOWN":
            return rule
    return None
