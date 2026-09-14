"""Canonical, tamper-evident helpers for calculation-history snapshots."""
from __future__ import annotations

import hashlib
import json
from typing import Any

SNAPSHOT_HASH_KEY = "snapshot_hash"


def snapshot_number(value: Any) -> float | None:
    """Convert a snapshot numeric field without turning UNKNOWN/None into zero."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def canonical_snapshot_json(snapshot: dict[str, Any]) -> str:
    """Return deterministic JSON used as the snapshot integrity payload."""
    payload = dict(snapshot)
    payload.pop(SNAPSHOT_HASH_KEY, None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Calculate SHA-256 over snapshot data excluding its stored hash."""
    return hashlib.sha256(canonical_snapshot_json(snapshot).encode("utf-8")).hexdigest()


def seal_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a detached snapshot carrying its integrity hash."""
    sealed = dict(snapshot)
    sealed[SNAPSHOT_HASH_KEY] = snapshot_hash(sealed)
    return sealed


def verify_snapshot(snapshot: dict[str, Any]) -> bool:
    """Verify a sealed snapshot; legacy snapshots without a hash are not sealed."""
    if not isinstance(snapshot, dict):
        return False
    stored = snapshot.get(SNAPSHOT_HASH_KEY)
    if not isinstance(stored, str) or not stored:
        return False
    return snapshot_hash(snapshot) == stored


def load_and_verify_snapshot(payload: str) -> dict[str, Any]:
    """Parse JSON and reject malformed or tampered immutable snapshots."""
    try:
        snapshot = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Некорректный снимок истории.") from exc
    if not verify_snapshot(snapshot):
        raise ValueError("Снимок истории повреждён или не содержит контрольной суммы.")
    return snapshot
