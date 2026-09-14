"""Regression for SPKEFFA TDS catalog with binary SHA-256 (not Git blob SHA-1)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.services.spk_effa_tds_catalog import (
    SPKEFFA_REPOSITORY,
    blank_universal_staged_rules,
    git_blob_sha1,
    spk_effa_tds_by_id,
    spk_effa_tds_documents,
    verify_spk_effa_local_files,
)
from app.services.tds_manifest import verify_manifest


FIXTURE_DIR = Path("/tmp/spk_pdfs")


def test_catalog_documents_are_known_with_binary_sha256() -> None:
    documents = spk_effa_tds_documents()
    assert len(documents) >= 7
    for document in documents:
        assert document.repository == SPKEFFA_REPOSITORY
        assert document.status == "KNOWN"
        assert document.sha256 is not None
        assert len(document.sha256) == 64
        assert all(ch in "0123456789abcdef" for ch in document.sha256)
        document.validate()
    verify_manifest(documents, ())


def test_git_blob_sha1_differs_from_binary_sha256_for_universal() -> None:
    path = FIXTURE_DIR / "Blank_Universal.pdf"
    if not path.is_file():
        pytest.skip("local Blank_Universal.pdf fixture not available")
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    blob = git_blob_sha1(data)
    document = spk_effa_tds_by_id("BLANK_UNIVERSAL_TDS")
    assert document is not None
    assert document.sha256 == sha256
    assert blob != sha256
    # Known Git blob SHA-1 from SPKEFFA tree for this file
    assert blob == "23eb95f2d327249845ca7ddb5d8b8e116fc2dd3a"


def test_verify_local_files_against_catalog(tmp_path: Path) -> None:
    if not FIXTURE_DIR.is_dir():
        pytest.skip("local SPKEFFA PDF fixtures not available")
    # Minimal local tree matching catalog source_path layout
    for document in spk_effa_tds_documents():
        src = FIXTURE_DIR / Path(document.source_path).name
        if not src.is_file():
            continue
        dest = tmp_path / document.source_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
    verified = verify_spk_effa_local_files(tmp_path)
    assert len(verified) == len(spk_effa_tds_documents())


def test_verify_detects_tampered_pdf(tmp_path: Path) -> None:
    document = spk_effa_tds_by_id("BLANK_UNIVERSAL_TDS")
    assert document is not None
    dest = tmp_path / document.source_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"%PDF-1.4 tampered content")
    # Other catalog files also required — create empty placeholders with wrong hash
    for other in spk_effa_tds_documents():
        if other.document_id == document.document_id:
            continue
        p = tmp_path / other.source_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-1.4 placeholder")
    with pytest.raises(ValueError, match="binary SHA-256 mismatch"):
        verify_spk_effa_local_files(tmp_path)


def test_staged_rules_remain_unknown() -> None:
    documents = spk_effa_tds_documents()
    rules = blank_universal_staged_rules()
    assert rules
    assert all(rule.status == "UNKNOWN" for rule in rules)
    verify_manifest(documents, rules)


def test_known_rule_still_requires_known_document_and_explicit_promotion() -> None:
    from app.services.tds_manifest import TDSRule

    documents = spk_effa_tds_documents()
    # Promotion is an explicit status change; catalog does not auto-promote.
    promoted = TDSRule(
        rule_id="BLANK_UNIVERSAL_DFT_RANGE",
        document_id="BLANK_UNIVERSAL_TDS",
        value="80-250 мкм",
        locator="Blank_Universal.pdf page 1, table thickness",
        applicability="recommended single-layer DFT",
        status="KNOWN",
    )
    verify_manifest(documents, (promoted,))
