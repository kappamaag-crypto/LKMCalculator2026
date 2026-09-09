"""Регрессия сквозного сравнения систем 2/3/4+ слоёв."""
from __future__ import annotations

import pytest

from app.domain.calculator import LayerInput
from app.domain.comparison import ComparisonEngine
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData


def _material(number: int) -> Material:
    return Material(
        id=number,
        manufacturer="Blank",
        material_name=f"Материал {number}",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=100.0 + number,
    )


def _layers(count: int, thinner: bool = False) -> list[LayerInput]:
    thinner_material = Material(
        id=100,
        manufacturer="Blank",
        material_name="Разбавитель",
        material_type=MaterialType.THINNER,
        density=0.9,
        price_per_kg=50.0,
    )
    return [
        LayerInput(
            material=_material(i),
            target_dft=100.0 + i * 10,
            losses_percent=5.0,
            thinner_percent=5.0 if thinner and i % 2 else 0.0,
            thinner=thinner_material if thinner and i % 2 else None,
        )
        for i in range(1, count + 1)
    ]


def _comparison(counts: list[int]):
    obj = ObjectData(object_name="Объект", area_m2=100.0)
    engine = ComparisonEngine()
    return engine.compare(obj, [(f"Система {i + 1}", _layers(count, thinner=True)) for i, count in enumerate(counts)])


@pytest.mark.parametrize("counts", [[2, 2], [2, 3], [3, 4], [4, 5]])
def test_comparison_preserves_every_layer(counts):
    comparison = _comparison(counts)
    assert [len(result.layers) for result in comparison.systems] == counts
    table = ComparisonEngine().to_table(comparison)
    material_rows = [row for row in table if ": материал" in row["indicator"]]
    assert len(material_rows) == max(counts)
    assert material_rows[-1]["indicator"] == f"Слой {max(counts)}: материал"


def test_comparison_result_path_preserves_precalculated_results():
    obj = ObjectData(area_m2=100.0)
    engine = ComparisonEngine()
    first = engine.compare(obj, [("A", _layers(4, thinner=True)), ("B", _layers(3))]).systems[0]
    second = engine.compare(obj, [("C", _layers(2)), ("D", _layers(4))]).systems[1]

    comparison = engine.compare_results(obj, [first, second])
    assert comparison.systems == [first, second]
    assert [len(result.layers) for result in comparison.systems] == [4, 4]


def test_comparison_table_does_not_double_count_thinner_cost():
    comparison = _comparison([2, 3])
    rows = {row["indicator"]: row for row in ComparisonEngine().to_table(comparison)}
    result = comparison.systems[0]
    thinner_cost = sum(layer.thinner_cost_per_m2 or 0 for layer in result.layers)
    expected_total = result.total_cost_per_m2
    assert expected_total is not None
    assert rows["Стоимость ЛКМ + разбавителя, руб/м²"]["sys_0"] == pytest.approx(expected_total)
    assert rows["Стоимость ЛКМ, руб/м²"]["sys_0"] == pytest.approx(expected_total - thinner_cost)
