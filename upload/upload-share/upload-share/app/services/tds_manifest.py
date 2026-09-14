"""Explicit TDS evidence/verification boundary.

Extracted PDF text is evidence only. A technology rule becomes KNOWN only when
its source document identity, binary SHA-256, locator and applicability are
explicitly recorded and the rule has been manually verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["KNOWN", "UNKNOWN"]


@dataclass(frozen=True)
class TDSDocument:
    document_id: str
    title: str
    repository: str
    source_path: str
    sha256: str | None = None
    revision: str = ""
    status: Status = "UNKNOWN"

    def validate(self) -> None:
        if not self.document_id.strip():
            raise ValueError("TDS document_id is required")
        if not self.title.strip():
            raise ValueError("TDS title is required")
        if self.status == "KNOWN":
            if self.repository != "kappamaag-crypto/SPKEFFA":
                raise ValueError("KNOWN TDS must reference the approved SPKEFFA repository")
            if not self.source_path.strip():
                raise ValueError("KNOWN TDS source_path is required")
            if not self.sha256 or len(self.sha256) != 64:
                raise ValueError("KNOWN TDS requires the binary PDF SHA-256")


@dataclass(frozen=True)
class TDSRule:
    rule_id: str
    document_id: str
    value: str | float | int
    locator: str
    applicability: str
    status: Status = "UNKNOWN"
    notes: str = ""

    def validate(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("TDS rule_id is required")
        if not self.document_id.strip():
            raise ValueError("TDS rule document_id is required")
        if not self.locator.strip():
            raise ValueError("TDS rule locator is required")
        if not self.applicability.strip():
            raise ValueError("TDS rule applicability is required")
        if self.status == "KNOWN" and self.value in (None, ""):
            raise ValueError("KNOWN TDS rule requires an explicit value")


def verify_manifest(documents: tuple[TDSDocument, ...], rules: tuple[TDSRule, ...]) -> None:
    """Validate the manifest structure without promoting extracted text to rules."""
    by_id: dict[str, TDSDocument] = {}
    for document in documents:
        document.validate()
        if document.document_id in by_id:
            raise ValueError(f"Duplicate TDS document: {document.document_id}")
        by_id[document.document_id] = document

    for rule in rules:
        rule.validate()
        document = by_id.get(rule.document_id)
        if document is None:
            raise ValueError(f"TDS rule references unknown document: {rule.document_id}")
        if rule.status == "KNOWN" and document.status != "KNOWN":
            raise ValueError("KNOWN TDS rule requires a KNOWN source document")
