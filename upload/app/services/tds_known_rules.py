"""Explicitly promoted KNOWN TDS rules from SPKEFFA.

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

# Longer / more specific hints first so "blank tank lp" wins over "blank tank".
MATERIAL_DOCUMENT_HINTS: tuple[tuple[str, str], ...] = (
    ("blank universal", "BLANK_UNIVERSAL_TDS"),
    ("blank finish", "BLANK_FINISH_TDS"),
    ("blank tank lp", "BLANK_TANK_LP_TDS"),
    ("blank tank", "BLANK_TANK_TDS"),
    ("blank zinc", "BLANK_ZINC_TDS"),
    ("blank mio", "BLANK_MIO_TDS"),
    ("blank dtm", "BLANK_DTM_TDS"),
    ("blank one", "BLANK_ONE_TDS"),
    ("blank hp", "BLANK_HP_TDS"),
    ("effa 01b", "EFFA_01B_TDS"),
    ("effa 01б", "EFFA_01B_TDS"),
    ("эффа 01b", "EFFA_01B_TDS"),
    ("эффа 01б", "EFFA_01B_TDS"),
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


def _dft(document_id: str, rule_prefix: str, value: str, pdf_name: str, sha_note: str) -> TDSRule:
    return _promote(
        document_id,
        f"{rule_prefix}_DFT_RANGE",
        value,
        f"{pdf_name} page 1, table «Толщина одного слоя» / «Толщина сухого слоя»",
        f"recommended single-layer dry film thickness for {rule_prefix.replace('_', ' ').title()}",
        verified_by="engineering-review",
        note=sha_note,
    )


def _solids(document_id: str, rule_prefix: str, value: str, pdf_name: str, sha_note: str) -> TDSRule:
    return _promote(
        document_id,
        f"{rule_prefix}_SOLIDS_BY_VOLUME",
        value,
        f"{pdf_name} page 1, «Характеристики продукта» / «Сухой остаток по объему»",
        f"volume solids for {rule_prefix.replace('_', ' ').title()}",
        verified_by="engineering-review",
        note=sha_note,
    )


def _density(document_id: str, rule_prefix: str, value: str, pdf_name: str, sha_note: str) -> TDSRule:
    return _promote(
        document_id,
        f"{rule_prefix}_DENSITY",
        value,
        f"{pdf_name} page 1, «Характеристики продукта» / «Плотность»",
        f"density for {rule_prefix.replace('_', ' ').title()}",
        verified_by="engineering-review",
        note=sha_note,
    )


def known_tds_rules() -> tuple[TDSRule, ...]:
    """Return the current set of explicitly promoted KNOWN rules."""
    rules = (
        _dft("BLANK_UNIVERSAL_TDS", "BLANK_UNIVERSAL", "80-250 мкм", "Blank_Universal.pdf",
             "Verified against binary SHA-256 9ab3872b849e523652088a3ba0d8b0788005c0134ac517305a9e2f01621b5887"),
        _solids("BLANK_UNIVERSAL_TDS", "BLANK_UNIVERSAL", "73 ± 2%", "Blank_Universal.pdf",
                "Verified against measured Blank_Universal.pdf binary SHA-256"),
        _density("BLANK_UNIVERSAL_TDS", "BLANK_UNIVERSAL", "1,4 кг/л", "Blank_Universal.pdf",
                 "Verified against measured Blank_Universal.pdf binary SHA-256"),
        _dft("BLANK_FINISH_TDS", "BLANK_FINISH", "50-90 мкм", "Blank_Finish.pdf",
             "Verified against binary SHA-256 34465e17e1e1199c94f1391ca2d776dcd377d4d363e0c4513b4e8a40f7a9a235"),
        _solids("BLANK_FINISH_TDS", "BLANK_FINISH", "58±3%", "Blank_Finish.pdf",
                "Verified against measured Blank_Finish.pdf binary SHA-256"),
        _density("BLANK_FINISH_TDS", "BLANK_FINISH", "1,3 г/см³", "Blank_Finish.pdf",
                 "Verified against measured Blank_Finish.pdf binary SHA-256"),
        _dft("BLANK_HP_TDS", "BLANK_HP", "200-500 мкм", "Blank_HP.pdf",
             "Verified against binary SHA-256 d75dfe44f3653e366fe227a0dbf51512dee4d25325c157bf82fe828cc3d4600a"),
        _solids("BLANK_HP_TDS", "BLANK_HP", "85 ± 2%", "Blank_HP.pdf",
                "Verified against measured Blank_HP.pdf binary SHA-256"),
        _density("BLANK_HP_TDS", "BLANK_HP", "1,5 кг/л", "Blank_HP.pdf",
                 "Verified against measured Blank_HP.pdf binary SHA-256"),
        _dft("BLANK_MIO_TDS", "BLANK_MIO", "80-200 мкм", "Blank_MIO.pdf",
             "Verified against binary SHA-256 26e4eeb50b353ad1dc24823afae08c3ec419676304f8bfd505c193e2b64bafd9"),
        _solids("BLANK_MIO_TDS", "BLANK_MIO", "73 ± 2%", "Blank_MIO.pdf",
                "Verified against measured Blank_MIO.pdf binary SHA-256"),
        _density("BLANK_MIO_TDS", "BLANK_MIO", "1,6 кг/л", "Blank_MIO.pdf",
                 "Verified against measured Blank_MIO.pdf binary SHA-256"),
        _dft("BLANK_TANK_TDS", "BLANK_TANK", "300-500 мкм", "Blank_Tank.pdf",
             "Verified against binary SHA-256 14a7d45b56d7fd800eaa43f7ef50294dcd925620bc351625ff7eb11a459cb72d"),
        _solids("BLANK_TANK_TDS", "BLANK_TANK", "90 ± 2%", "Blank_Tank.pdf",
                "Verified against measured Blank_Tank.pdf binary SHA-256"),
        _density("BLANK_TANK_TDS", "BLANK_TANK", "1,45 кг/л", "Blank_Tank.pdf",
                 "Verified against measured Blank_Tank.pdf binary SHA-256"),
        _dft("BLANK_ZINC_TDS", "BLANK_ZINC", "40-80 мкм", "Blank_Zinc.pdf",
             "Verified against binary SHA-256 bd0322e8ba8e3116dfdf52e9b6f85c97518ab136a6dba86ed469c16a8cce9c98"),
        _solids("BLANK_ZINC_TDS", "BLANK_ZINC", "58 ± 2%", "Blank_Zinc.pdf",
                "Verified against measured Blank_Zinc.pdf binary SHA-256"),
        _density("BLANK_ZINC_TDS", "BLANK_ZINC", "2,9 кг/л", "Blank_Zinc.pdf",
                 "Verified against measured Blank_Zinc.pdf binary SHA-256"),
        _dft("BLANK_DTM_TDS", "BLANK_DTM", "50-120 мкм", "Blank_DTM.pdf",
             "Verified against binary SHA-256 9643c005e47319099cec5842614f67a517336bdab4fdba0797efc46cbc77854b"),
        _solids("BLANK_DTM_TDS", "BLANK_DTM", "60 ± 2%", "Blank_DTM.pdf",
                "Verified against measured Blank_DTM.pdf binary SHA-256"),
        _density("BLANK_DTM_TDS", "BLANK_DTM", "1,3 кг/л", "Blank_DTM.pdf",
                 "Verified against measured Blank_DTM.pdf binary SHA-256"),
        _dft("BLANK_ONE_TDS", "BLANK_ONE", "60-100 мкм", "Blank_One.pdf",
             "Verified against binary SHA-256 4643d3692cc0f31fa177e801dff94710054a23301799c6e721202ffd9a2fd226"),
        _solids("BLANK_ONE_TDS", "BLANK_ONE", "50 ± 2%", "Blank_One.pdf",
                "Verified against measured Blank_One.pdf binary SHA-256"),
        _density("BLANK_ONE_TDS", "BLANK_ONE", "1,3 г/см3", "Blank_One.pdf",
                 "Verified against measured Blank_One.pdf binary SHA-256"),
        _dft("BLANK_TANK_LP_TDS", "BLANK_TANK_LP", "150-250 мкм", "Blank_Tank_LP.pdf",
             "Verified against binary SHA-256 95a8e6a36e09f7fb09e8e8f2cbbae344f89409db20cd4ec097483d3116862588"),
        _solids("BLANK_TANK_LP_TDS", "BLANK_TANK_LP", "58 ± 2%", "Blank_Tank_LP.pdf",
                "Verified against measured Blank_Tank_LP.pdf binary SHA-256 95a8e6a36e09f7fb09e8e8f2cbbae344f89409db20cd4ec097483d3116862588"),
        _density("BLANK_TANK_LP_TDS", "BLANK_TANK_LP", "1,2 кг/л", "Blank_Tank_LP.pdf",
                 "Verified against measured Blank_Tank_LP.pdf binary SHA-256 95a8e6a36e09f7fb09e8e8f2cbbae344f89409db20cd4ec097483d3116862588"),
        _solids("EFFA_01B_TDS", "EFFA_01B", "70±5%", "EFFA_01B.pdf",
                "Verified against measured EFFA_01B.pdf binary SHA-256 f74b8548fa4e75f19a780dacf0c38196579ab2d9e8c840918ec7666099e92841"),
        _density("EFFA_01B_TDS", "EFFA_01B", "1,25-1,3 кг/л", "EFFA_01B.pdf",
                 "Verified against measured EFFA_01B.pdf binary SHA-256 f74b8548fa4e75f19a780dacf0c38196579ab2d9e8c840918ec7666099e92841"),
        _promote(
            "EFFA_01B_TDS",
            "EFFA_01B_FIRE_DFT_MM",
            "2,1-2,5 мм (REI 180, таблица ТДС)",
            "EFFA_01B.pdf page 1, таблица «Огнезащитная эффективность для железобетона» / толщина сухого слоя",
            "design dry-film thickness for EFFA 01B fire protection (REI 180 examples; project-specific)",
            verified_by="engineering-review",
            note="Verified against binary SHA-256 f74b8548fa4e75f19a780dacf0c38196579ab2d9e8c840918ec7666099e92841; not a single-layer coating µm range",
        ),
    )
    verify_manifest(spk_effa_tds_documents(), rules)
    assert all(rule.status == "KNOWN" for rule in rules)
    return rules


def known_rules_for_document(document_id: str) -> tuple[TDSRule, ...]:
    return tuple(rule for rule in known_tds_rules() if rule.document_id == document_id)


def resolve_document_id_for_material_name(material_name: str) -> str | None:
    """Map a material display name to a catalogued TDS document when unambiguous.

    Hints are ordered longest/most specific first. When several hints match
    (e.g. "blank tank lp" contains "blank tank"), the longest matching hint wins.
    """
    lowered = material_name.strip().lower()
    if not lowered:
        return None
    matches = [(hint, doc_id) for hint, doc_id in MATERIAL_DOCUMENT_HINTS if hint in lowered]
    if not matches:
        return None
    matches.sort(key=lambda item: len(item[0]), reverse=True)
    best_len = len(matches[0][0])
    top = [doc for hint, doc in matches if len(hint) == best_len]
    if len(set(top)) == 1:
        return top[0]
    return None


def known_dft_rule_for_material_name(material_name: str) -> TDSRule | None:
    document_id = resolve_document_id_for_material_name(material_name)
    if document_id is None:
        return None
    for rule in known_rules_for_document(document_id):
        if rule.rule_id.endswith("_DFT_RANGE") and rule.status == "KNOWN":
            return rule
    return None
