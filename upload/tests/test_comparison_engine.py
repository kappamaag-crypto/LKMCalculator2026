"""Регрессия сравнения систем АКЗ с разным количеством слоёв."""
from __future__ import annotations

from app.domain.calculator import LayerInput
from app.domain.comparison import ComparisonEngine
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.services.calculation_service import CalculationService


def _material(name: str, price: float) -> Material:
    return Material(
        manufacturer="Test",
        material_name=name,
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=price,
        price_per_liter=price * 1.4,
    )


def _result(layer_count: int, prefix: str = "A"):
    materials = [_material(f"{prefix} — материал {i}", 100 + i * 10) for i in range(1, layer_count + 1)]
    layers = [LayerInput(material=m, target_dft=80 + i * 20, losses_percent=5.0) for i, m in enumerate(materials)]
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name="Тест", area_m2=100.0), layers
    )
    assert not validation.has_errors
    return result


def test_compare_results_preserves_exact_multi_layer_results():
    first = _result(2, "A")
    second = _result(4, "B")

    comparison = ComparisonEngine().compare_results(first.object_data, [first, second])

    assert comparison.systems[0] is first
    assert comparison.systems[1] is second
    assert [len(s.layers) for s in comparison.systems] == [2, 4]
    assert [lr.material.material_name for lr in comparison.systems[1].layers] == [
        "B — материал 1",
        "B — материал 2",
        "B — материал 3",
        "B — материал 4",
    ]


def test_compare_supports_two_three_four_and_five_layers():
    engine = ComparisonEngine()
    results = [_result(n, str(n)) for n in (2, 3, 4, 5)]
    comparison = engine.compare_results(results[0].object_data, results)

    assert [len(s.layers) for s in comparison.systems] == [2, 3, 4, 5]
    rows = engine.to_table(comparison)
    indicators = [row["indicator"] for row in rows]
    assert "Слой 5: материал" in indicators
    assert "Слой 5: DFT, мкм" in indicators
    assert "Слой 5: расход, кг/м²" in indicators


def test_comparison_rejects_more_than_ten_systems():
    results = [_result(2, str(i)) for i in range(11)]
    try:
        ComparisonEngine().compare_results(results[0].object_data, results)
    except ValueError as exc:
        assert "10" in str(exc) or "Максимум" in str(exc)
    else:
        raise AssertionError("ComparisonEngine должен ограничивать сравнение 10 системами")
