"""Read-only catalog of SPKEFFA TDS PDF identities with binary SHA-256.

Git blob SHA-1 is intentionally never used as a PDF digest. Document status may
be KNOWN only when the binary SHA-256 of the PDF bytes was measured. Technology
rules remain UNKNOWN until a human records locator, value and applicability and
promotes the rule explicitly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.services.tds_manifest import TDSDocument, TDSRule, verify_manifest

SPKEFFA_REPOSITORY = "kappamaag-crypto/SPKEFFA"

# Binary SHA-256 digests measured from the PDF file bytes downloaded from
# SPKEFFA (not Git blob SHA-1). Recompute with hashlib.sha256(open(path,'rb').read()).
_MEASURED_DOCUMENTS: tuple[tuple[str, str, str, str], ...] = (
    # document_id, title, source_path, sha256
    (
        "BLANK_UNIVERSAL_TDS",
        "Blank Universal TDS",
        "docs/blank/Blank_Universal.pdf",
        "9ab3872b849e523652088a3ba0d8b0788005c0134ac517305a9e2f01621b5887",
    ),
    (
        "BLANK_FINISH_TDS",
        "Blank Finish TDS",
        "docs/blank/Blank_Finish.pdf",
        "34465e17e1e1199c94f1391ca2d776dcd377d4d363e0c4513b4e8a40f7a9a235",
    ),
    (
        "BLANK_HP_TDS",
        "Blank HP TDS",
        "docs/blank/Blank_HP.pdf",
        "d75dfe44f3653e366fe227a0dbf51512dee4d25325c157bf82fe828cc3d4600a",
    ),
    (
        "BLANK_MIO_TDS",
        "Blank MIO TDS",
        "docs/blank/Blank_MIO.pdf",
        "26e4eeb50b353ad1dc24823afae08c3ec419676304f8bfd505c193e2b64bafd9",
    ),
    (
        "BLANK_TANK_TDS",
        "Blank Tank TDS",
        "docs/blank/Blank_Tank.pdf",
        "14a7d45b56d7fd800eaa43f7ef50294dcd925620bc351625ff7eb11a459cb72d",
    ),
    (
        "BLANK_ZINC_TDS",
        "Blank Zinc TDS",
        "docs/blank/Blank_Zinc.pdf",
        "bd0322e8ba8e3116dfdf52e9b6f85c97518ab136a6dba86ed469c16a8cce9c98",
    ),
    (
        "BLANK_DTM_TDS",
        "Blank DTM TDS",
        "docs/blank/Blank_DTM.pdf",
        "9643c005e47319099cec5842614f67a517336bdab4fdba0797efc46cbc77854b",
    ),
    (
        "BLANK_ONE_TDS",
        "Blank One TDS",
        "docs/blank/Blank_One.pdf",
        "4643d3692cc0f31fa177e801dff94710054a23301799c6e721202ffd9a2fd226",
    ),
    (
        "BLANK_TANK_LP_TDS",
        "Blank Tank LP TDS",
        "docs/blank/Blank_Tank_LP.pdf",
        "95a8e6a36e09f7fb09e8e8f2cbbae344f89409db20cd4ec097483d3116862588",
    ),
    (
        "EFFA_01B_TDS",
        "EFFA 01B TDS",
        "docs/effa/EFFA_01B.pdf",
        "f74b8548fa4e75f19a780dacf0c38196579ab2d9e8c840918ec7666099e92841",
    ),
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    """Compute Git blob SHA-1 for contrast only — never use as PDF identity."""
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def spk_effa_tds_documents() -> tuple[TDSDocument, ...]:
    """Return SPKEFFA TDS documents with measured binary SHA-256.

    Document status is KNOWN because source identity + binary digest are known.
    This does not promote any technology rule to KNOWN.
    """
    documents: list[TDSDocument] = []
    for document_id, title, source_path, sha256 in _MEASURED_DOCUMENTS:
        document = TDSDocument(
            document_id=document_id,
            title=title,
            repository=SPKEFFA_REPOSITORY,
            source_path=source_path,
            sha256=sha256,
            revision="measured-binary-sha256",
            status="KNOWN",
        )
        document.validate()
        documents.append(document)
    return tuple(documents)


def spk_effa_tds_by_id(document_id: str) -> TDSDocument | None:
    return next((d for d in spk_effa_tds_documents() if d.document_id == document_id), None)


def verify_spk_effa_local_files(repository_root: Path) -> tuple[TDSDocument, ...]:
    """Verify that local SPKEFFA files match the catalog binary SHA-256 digests.

    Raises ValueError when a catalogued file is missing or its binary digest
    differs from the measured catalog value. Does not invent rule values.
    """
    root = repository_root.resolve()
    verified: list[TDSDocument] = []
    for document in spk_effa_tds_documents():
        path = (root / document.source_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"TDS path escapes repository root: {document.source_path}") from exc
        if not path.is_file():
            raise ValueError(f"TDS file not found: {document.source_path}")
        actual = _sha256_file(path)
        if actual != document.sha256:
            raise ValueError(
                f"binary SHA-256 mismatch for {document.source_path}: "
                f"catalog={document.sha256}, actual={actual}"
            )
        # Guardrail: Git blob SHA-1 must not equal the catalog PDF digest.
        git_sha = git_blob_sha1(path.read_bytes())
        if git_sha == document.sha256:
            raise ValueError(
                f"catalog digest for {document.source_path} incorrectly equals Git blob SHA-1"
            )
        verified.append(document)
    verify_manifest(tuple(verified), ())
    return tuple(verified)


def blank_universal_staged_rules() -> tuple[TDSRule, ...]:
    """Example staged rules from Blank Universal TDS text — status remains UNKNOWN.

    Locators and values are recorded for review only. They are not promoted to
    KNOWN by extraction alone.
    """
    return (
        TDSRule(
            rule_id="BLANK_UNIVERSAL_DFT_RANGE",
            document_id="BLANK_UNIVERSAL_TDS",
            value="80-250 мкм",
            locator="Blank_Universal.pdf page 1, table «Толщина одного слоя» / «Толщина сухого слоя»",
            applicability="recommended single-layer dry film thickness for Blank Universal",
            status="UNKNOWN",
            notes="Extracted text evidence only; not promoted to KNOWN without human verification.",
        ),
        TDSRule(
            rule_id="BLANK_UNIVERSAL_SOLIDS_BY_VOLUME",
            document_id="BLANK_UNIVERSAL_TDS",
            value="73 ± 2%",
            locator="Blank_Universal.pdf page 1, «Характеристики продукта» / «Сухой остаток по объему»",
            applicability="volume solids for Blank Universal",
            status="UNKNOWN",
            notes="Extracted text evidence only; not promoted to KNOWN without human verification.",
        ),
        TDSRule(
            rule_id="BLANK_UNIVERSAL_DENSITY",
            document_id="BLANK_UNIVERSAL_TDS",
            value="1,4 кг/л",
            locator="Blank_Universal.pdf page 1, «Характеристики продукта» / «Плотность»",
            applicability="density for Blank Universal",
            status="UNKNOWN",
            notes="Extracted text evidence only; not promoted to KNOWN without human verification.",
        ),
    )
