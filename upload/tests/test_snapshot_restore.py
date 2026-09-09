from app.domain.calculator import LayerCalculator
from app.domain.models import Material
from app.domain.enums import BinderType, MaterialType
from app.services.snapshot_service import material_from_snapshot, thinner_from_snapshot
from app.ui.views.calculation_view import CalculationView


def test_material_restore_uses_snapshot_engineering_values_after_catalog_change():
    snapshot = {
        "material_id": 101,
        "material_name": "Material v1",
        "manufacturer": "Test",
        "brand": "TestBrand",
        "material_type": MaterialType.PRIMER_ENAMEL.value,
        "binder": BinderType.EPOXY.value,
        "density": 1.42,
        "solids_percent": 72.0,
        "solids_by_volume_percent": 64.0,
        "price_per_kg": 650.0,
        "price_per_liter": 923.0,
    }
    current_catalog = Material(
        id=101, manufacturer="Test", brand="TestBrand NEW", material_name="Material v2",
        material_type=MaterialType.FINISH, density=1.90, solids_percent=55.0,
        solids_by_volume_percent=48.0, price_per_kg=900.0, price_per_liter=1710.0,
    )
    restored = material_from_snapshot(snapshot, current_catalog)
    assert restored.id == 101
    assert restored.material_name == "Material v1"
    assert restored.density == 1.42
    assert restored.solids_by_volume_percent == 64.0
    assert restored.solids_percent == 72.0
    assert restored.price_per_kg == 650.0
    assert restored.price_per_liter == 923.0
    assert restored.material_type is MaterialType.PRIMER_ENAMEL
    assert restored.binder_type is BinderType.EPOXY


def test_material_restore_works_when_catalog_material_is_deleted():
    snapshot = {
        "material_id": 101, "material_name": "Deleted material", "manufacturer": "Test",
        "brand": "TestBrand", "material_type": MaterialType.EPOXY.value,
        "binder": BinderType.EPOXY.value, "density": 1.50, "solids_percent": 70.0,
        "solids_by_volume_percent": 62.0, "price_per_kg": 700.0, "price_per_liter": 1050.0,
    }
    restored = material_from_snapshot(snapshot)
    assert restored.id == 101
    assert restored.density == 1.50
    assert restored.solids_by_volume_percent == 62.0
    assert restored.price_per_kg == 700.0
    assert restored.price_per_liter == 1050.0
    assert restored.material_type is MaterialType.EPOXY


def test_restored_material_reproduces_original_calculation_after_catalog_change():
    snapshot = {
        "material_id": 101, "material_name": "Material v1",
        "material_type": MaterialType.PRIMER_ENAMEL.value, "binder": BinderType.EPOXY.value,
        "density": 1.42, "solids_by_volume_percent": 64.0, "price_per_kg": 650.0,
    }
    restored = material_from_snapshot(snapshot, Material(
        id=101, material_name="Material v2", density=1.90,
        solids_by_volume_percent=48.0, price_per_kg=900.0,
    ))
    original = material_from_snapshot(snapshot)
    old_result = LayerCalculator.calculate(original, 120.0, losses_percent=5.0)
    restored_result = LayerCalculator.calculate(restored, 120.0, losses_percent=5.0)
    assert restored_result.practical_consumption_kg == old_result.practical_consumption_kg
    assert restored_result.practical_consumption_l == old_result.practical_consumption_l
    assert restored_result.cost_per_m2 == old_result.cost_per_m2


def test_thinner_restore_uses_snapshot_values_after_catalog_change():
    snapshot = {
        "thinner_id": 202, "thinner_name": "Thinner v1", "thinner_density": 0.80,
        "thinner_price_per_kg": 120.0, "thinner_price_per_liter": 96.0,
        "thinner_basis": "BY_PAINT_VOLUME",
    }
    current_catalog = Material(id=202, material_name="Thinner v2", material_type=MaterialType.THINNER,
                               density=0.90, price_per_kg=200.0, price_per_liter=180.0)
    restored = thinner_from_snapshot(snapshot, current_catalog)
    assert restored.id == 202
    assert restored.material_name == "Thinner v1"
    assert restored.material_type is MaterialType.THINNER
    assert restored.density == 0.80
    assert restored.price_per_kg == 120.0
    assert restored.price_per_liter == 96.0


def test_legacy_thinner_snapshot_falls_back_to_current_catalog_for_absent_fields():
    snapshot = {
        "thinner_id": 202,
        "thinner_name": "Thinner v1",
        "thinner_basis": "BY_PAINT_VOLUME",
    }
    current_catalog = Material(
        id=202,
        material_name="Thinner v2",
        material_type=MaterialType.THINNER,
        density=0.90,
        price_per_kg=200.0,
        price_per_liter=180.0,
    )
    restored = thinner_from_snapshot(snapshot, current_catalog)
    assert restored.material_name == "Thinner v1"
    assert restored.density == 0.90
    assert restored.price_per_kg == 200.0
    assert restored.price_per_liter == 180.0


def test_explicit_unknown_thinner_density_is_not_replaced_by_catalog_value():
    snapshot = {
        "thinner_id": 202,
        "thinner_name": "Thinner v1",
        "thinner_density": None,
        "thinner_price_per_kg": 120.0,
        "thinner_price_per_liter": None,
        "thinner_basis": "BY_PAINT_VOLUME",
    }
    current_catalog = Material(
        id=202,
        material_name="Thinner v2",
        material_type=MaterialType.THINNER,
        density=0.90,
        price_per_kg=200.0,
        price_per_liter=180.0,
    )
    restored = thinner_from_snapshot(snapshot, current_catalog)
    assert restored.density is None
    assert restored.price_per_kg == 120.0
    assert restored.price_per_liter is None


def test_calculation_view_snapshot_number_preserves_unknown_dft():
    assert CalculationView._snapshot_number(None) is None
    assert CalculationView._snapshot_number(0) == 0.0
    assert CalculationView._snapshot_number("120") == 120.0
    assert CalculationView._snapshot_number("UNKNOWN") is None
