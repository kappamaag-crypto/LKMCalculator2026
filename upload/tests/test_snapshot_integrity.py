import json

import pytest

from app.services.snapshot_utils import (
    canonical_snapshot_json,
    load_and_verify_snapshot,
    seal_snapshot,
    verify_snapshot,
)


def test_sealed_snapshot_is_deterministic_and_verifiable():
    snapshot = {"snapshot_version": 4, "layers": [{"material_name": "ЭП-150", "target_dft": 120.0}], "area_m2": None}
    sealed = seal_snapshot(snapshot)

    assert sealed["snapshot_hash"]
    assert verify_snapshot(sealed)
    assert load_and_verify_snapshot(json.dumps(sealed, ensure_ascii=False)) == sealed
    assert canonical_snapshot_json(sealed) == canonical_snapshot_json({**sealed, "snapshot_hash": "ignored"})


def test_snapshot_tampering_is_rejected():
    sealed = seal_snapshot({"snapshot_version": 4, "total_dft": 240.0, "total_cost": None})
    tampered = dict(sealed)
    tampered["total_dft"] = 241.0

    assert not verify_snapshot(tampered)
    with pytest.raises(ValueError, match="повреждён"):
        load_and_verify_snapshot(json.dumps(tampered, ensure_ascii=False))


def test_unsealed_legacy_snapshot_is_not_presented_as_immutable():
    legacy = {"snapshot_version": 3, "total_dft": 240.0}

    assert not verify_snapshot(legacy)
    with pytest.raises(ValueError, match="не содержит контрольной суммы"):
        load_and_verify_snapshot(json.dumps(legacy, ensure_ascii=False))


def test_individual_layer_snapshot_is_sealed_and_detects_changes():
    layer = {
        "material_id": 17,
        "material_name": "ЭП-150",
        "density": 1.35,
        "price_per_kg": 607.0,
        "target_dft": 120.0,
    }
    sealed_layer = seal_snapshot(layer)

    assert verify_snapshot(sealed_layer)

    changed_catalog_value = dict(sealed_layer)
    changed_catalog_value["price_per_kg"] = 999.0
    assert not verify_snapshot(changed_catalog_value)

    restored = load_and_verify_snapshot(json.dumps(sealed_layer, ensure_ascii=False))
    assert restored["material_name"] == "ЭП-150"
    assert restored["price_per_kg"] == 607.0
    assert restored["target_dft"] == 120.0


def test_snapshot_number_preserves_none_and_rejects_garbage():
    from app.services.snapshot_utils import snapshot_number

    assert snapshot_number(None) is None
    assert snapshot_number("") is None
    assert snapshot_number("not-a-number") is None
    assert snapshot_number(12.5) == 12.5
    assert snapshot_number("3.0") == 3.0


def test_malformed_json_payload_is_rejected():
    with pytest.raises(ValueError, match="Некорректный"):
        load_and_verify_snapshot("{not-json")


def test_empty_hash_string_is_not_verified():
    payload = {"snapshot_version": 4, "total_dft": 100.0, "snapshot_hash": ""}
    assert not verify_snapshot(payload)
    with pytest.raises(ValueError):
        load_and_verify_snapshot(json.dumps(payload))
