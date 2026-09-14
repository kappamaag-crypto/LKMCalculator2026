"""Load explicitly verified normative rules without inventing engineering values.

The loader accepts a human-reviewed JSON sidecar. It never extracts a PDF on
its own and never infers a rule from a document title. A manifest must identify
an existing repository source file and provide its SHA-256 digest; every KNOWN
rule must carry a value in the manifest and is bound to that verified source.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.domain.normative import NormativeModel, NormativeRegistry, NormativeRule, NormativeSource, UNKNOWN


class VerifiedNormativeLoadError(ValueError):
    """Raised when a normative sidecar cannot be safely verified or parsed."""


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VerifiedNormativeLoadError(f"required non-empty field: {key}")
    return value.strip()


def _safe_source_path(repository_root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerifiedNormativeLoadError("source relative_path must stay inside repository root")
    path = (repository_root / relative).resolve()
    root = repository_root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise VerifiedNormativeLoadError("source path escapes repository root") from exc
    if not path.is_file():
        raise VerifiedNormativeLoadError(f"source file not found: {relative_path}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_normative_model(manifest_path: Path, repository_root: Path) -> NormativeModel:
    """Load a reviewed sidecar and verify that it still belongs to its source.

    Values are taken verbatim from the manifest. No value is calculated,
    guessed, or extracted from PDF text by this loader.
    """
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerifiedNormativeLoadError(f"cannot read manifest: {manifest_path}") from exc
    if not isinstance(raw, dict):
        raise VerifiedNormativeLoadError("manifest root must be an object")

    source_data = raw.get("source")
    if not isinstance(source_data, dict):
        raise VerifiedNormativeLoadError("manifest.source must be an object")
    document_id = _required_text(source_data, "document_id")
    relative_path = _required_text(source_data, "relative_path")
    expected_sha256 = _required_text(source_data, "sha256").lower()
    if len(expected_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha256):
        raise VerifiedNormativeLoadError("source.sha256 must be a 64-character hexadecimal SHA-256 digest")

    source_path = _safe_source_path(repository_root, relative_path)
    actual_sha256 = _sha256(source_path)
    if actual_sha256 != expected_sha256:
        raise VerifiedNormativeLoadError(
            f"source digest mismatch for {relative_path}: expected {expected_sha256}, got {actual_sha256}"
        )

    source = NormativeSource(
        document_id=document_id,
        title=str(source_data.get("title", document_id)).strip(),
        revision=str(source_data.get("revision", "")).strip(),
        issuer=str(source_data.get("issuer", "")).strip(),
        source_uri=relative_path,
    )

    model_id = _required_text(raw, "model_id")
    version = _required_text(raw, "version")
    raw_rules = raw.get("rules")
    if not isinstance(raw_rules, list):
        raise VerifiedNormativeLoadError("manifest.rules must be a list")

    rules: dict[str, NormativeRule] = {}
    for item in raw_rules:
        if not isinstance(item, dict):
            raise VerifiedNormativeLoadError("each manifest rule must be an object")
        rule_id = _required_text(item, "rule_id")
        if rule_id in rules:
            raise VerifiedNormativeLoadError(f"duplicate rule_id: {rule_id}")
        status = str(item.get("status", UNKNOWN)).strip().upper()
        if status == "KNOWN" and "value" not in item:
            raise VerifiedNormativeLoadError(f"KNOWN rule has no explicit value: {rule_id}")
        if status not in {"KNOWN", UNKNOWN}:
            raise VerifiedNormativeLoadError(f"unsupported rule status: {status}")
        rules[rule_id] = NormativeRule(
            rule_id=rule_id,
            value=item.get("value"),
            status=status,
            source=source if status == "KNOWN" else None,
            applicability=str(item.get("applicability", "")).strip(),
            notes=str(item.get("notes", "")).strip(),
        )

    return NormativeModel(
        model_id=model_id,
        version=version,
        rules=rules,
        description=str(raw.get("description", "")).strip(),
    )


def load_verified_normative_registry(
    manifest_paths: Iterable[Path],
    repository_root: Path,
    registry: NormativeRegistry | None = None,
) -> NormativeRegistry:
    """Load verified sidecars into one deterministic normative registry.

    Each manifest is verified independently before registration. Duplicate
    ``model_id:version`` entries are rejected instead of silently replacing an
    already accepted model. No manifest is optional or auto-discovered: the
    caller explicitly supplies the sidecars that are approved for the workflow.
    """
    target = registry if registry is not None else NormativeRegistry()
    for manifest_path in manifest_paths:
        model = load_verified_normative_model(manifest_path, repository_root)
        target.register(model)
    return target
