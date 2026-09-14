"""§19 legacy parity: History service — immutable snapshots + integrity.

v2 HistoryService stores calculation rows without a sealed integrity hash.
v3 seals snapshots with SHA-256 (`snapshot_hash`) and rejects tampered payloads
via `load_and_verify_snapshot`. Material fields are captured in the snapshot
so later catalog edits cannot rewrite history.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.snapshot_utils import (
    SNAPSHOT_HASH_KEY,
    load_and_verify_snapshot,
    seal_snapshot,
    snapshot_hash,
    snapshot_number,
    verify_snapshot,
)


def test_v2_history_has_no_snapshot_seal_helpers():
    root = Path(__file__).resolve().parents[2]
    v2_hist = (root / "v2" / "app" / "services" / "history_service.py").read_text(encoding="utf-8")
    assert "seal_snapshot" not in v2_hist
    assert "snapshot_hash" not in v2_hist
    assert "save_calculation" in v2_hist
    assert (root / "upload" / "app" / "services" / "snapshot_utils.py").exists()


def test_v3_seal_and_verify_round_trip():
    snap = {
        "snapshot_version": 8,
        "system": {"name": "Tank"},
        "layers": [
            {
                "material_id": 1,
                "density": 1.42,
                "solids_by_volume_percent": 64.0,
                "price_per_kg": 650.0,
                "target_dft": 120.0,
            }
        ],
        "totals": {"total_dft": 120.0, "total_cost_per_m2": None},
    }
    sealed = seal_snapshot(snap)
    assert SNAPSHOT_HASH_KEY in sealed
    assert verify_snapshot(sealed) is True
    payload = json.dumps(sealed, ensure_ascii=False)
    loaded = load_and_verify_snapshot(payload)
    assert loaded["layers"][0]["density"] == 1.42
    assert loaded["totals"]["total_cost_per_m2"] is None


def test_v3_tampered_snapshot_is_rejected():
    sealed = seal_snapshot({"snapshot_version": 8, "system": {"name": "A"}, "layers": []})
    sealed["system"]["name"] = "B"
    assert verify_snapshot(sealed) is False
    with pytest.raises(ValueError, match="повреждён|контрольной"):
        load_and_verify_snapshot(json.dumps(sealed, ensure_ascii=False))


def test_v3_unsealed_legacy_payload_is_rejected_by_loader():
    legacy = {"snapshot_version": 1, "layers": []}
    assert verify_snapshot(legacy) is False
    with pytest.raises(ValueError):
        load_and_verify_snapshot(json.dumps(legacy))


def test_v3_snapshot_number_does_not_invent_zero_for_unknown():
    assert snapshot_number(None) is None
    assert snapshot_number("UNKNOWN") is None
    assert snapshot_number(12.5) == 12.5


def test_v3_history_service_documents_immutable_snapshot_save():
    root = Path(__file__).resolve().parents[2]
    src = (root / "upload" / "app" / "services" / "history_service.py").read_text(encoding="utf-8")
    assert "seal_snapshot" in src
    assert "неизменяемый" in src or "immutable" in src.lower() or "снимок" in src
    assert "_material_snapshot" in src
