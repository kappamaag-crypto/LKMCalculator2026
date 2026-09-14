import pytest

from app.services.tds_manifest import TDSDocument, TDSRule, verify_manifest


def known_document() -> TDSDocument:
    return TDSDocument(
        document_id="BLANK_UNIVERSAL_TDS",
        title="Blank Universal TDS",
        repository="kappamaag-crypto/SPKEFFA",
        source_path="docs/blank/Blank_Universal.pdf",
        sha256="a" * 64,
        revision="verified",
        status="KNOWN",
    )


def test_known_document_requires_approved_repository() -> None:
    document = known_document()
    bad = TDSDocument(
        document_id=document.document_id,
        title=document.title,
        repository="other/repository",
        source_path=document.source_path,
        sha256=document.sha256,
        revision=document.revision,
        status="KNOWN",
    )
    with pytest.raises(ValueError, match="approved SPKEFFA repository"):
        bad.validate()


def test_known_document_requires_binary_sha256() -> None:
    document = known_document()
    for sha256 in (None, "", "a" * 63, "a" * 65):
        bad = TDSDocument(
            document_id=document.document_id,
            title=document.title,
            repository=document.repository,
            source_path=document.source_path,
            sha256=sha256,
            revision=document.revision,
            status="KNOWN",
        )
        with pytest.raises(ValueError, match="binary PDF SHA-256"):
            bad.validate()


def test_known_rule_cannot_promote_unknown_document() -> None:
    document = TDSDocument(
        document_id="BLANK_UNIVERSAL_TDS",
        title="Blank Universal TDS",
        repository="kappamaag-crypto/SPKEFFA",
        source_path="docs/blank/Blank_Universal.pdf",
        sha256=None,
        status="UNKNOWN",
    )
    rule = TDSRule(
        rule_id="BLANK_UNIVERSAL_DFT",
        document_id=document.document_id,
        value="80–120 мкм",
        locator="PDF page 2, table Application",
        applicability="metal substrate",
        status="KNOWN",
    )
    with pytest.raises(ValueError, match="KNOWN TDS rule requires a KNOWN source document"):
        verify_manifest((document,), (rule,))


def test_unknown_rule_may_remain_unknown_with_known_document() -> None:
    document = known_document()
    rule = TDSRule(
        rule_id="BLANK_UNIVERSAL_DFT",
        document_id=document.document_id,
        value="80–120 мкм",
        locator="PDF page 2, table Application",
        applicability="metal substrate",
        status="UNKNOWN",
    )
    verify_manifest((document,), (rule,))


def test_rule_must_reference_existing_document() -> None:
    rule = TDSRule(
        rule_id="ORPHAN",
        document_id="MISSING",
        value="80 мкм",
        locator="PDF page 2",
        applicability="metal substrate",
        status="UNKNOWN",
    )
    with pytest.raises(ValueError, match="unknown document"):
        verify_manifest((), (rule,))
