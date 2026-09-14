"""Регрессия сквозного сравнения систем 2/3/4+ слоёв."""
from __future__ import annotations

import pytest

from app.domain.calculator import LayerInput
from app.domain.comparison import ComparisonEngine
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData


def _material(number: int, **kwargs) -> Material:
    return Material(
        id=number,
        manufacturer="Blank",
        material_name=f"Материал {number}",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=100.0 + number,
        **kwargs,
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


def test_comparison_result_path_rejects_mixed_areas():
    engine = ComparisonEngine()
    first = engine.compare(ObjectData(area_m2=100.0), [("A", _layers(2)), ("B", _layers(3))]).systems[0]
    second = engine.compare(ObjectData(area_m2=250.0), [("C", _layers(2)), ("D", _layers(4))]).systems[1]

    with pytest.raises(ValueError, match="разной площадью"):
        engine.compare_results(ObjectData(area_m2=100.0), [first, second])


def test_comparison_table_does_not_double_count_thinner_cost():
    comparison = _comparison([2, 3])
    rows = {row["indicator"]: row for row in ComparisonEngine().to_table(comparison)}
    result = comparison.systems[0]
    thinner_cost = sum(layer.thinner_cost_per_m2 or 0 for layer in result.layers)
    expected_total = result.total_cost_per_m2
    assert expected_total is not None
    assert rows["Стоимость ЛКМ + разбавителя, руб/м²"]["sys_0"] == pytest.approx(expected_total)
    assert rows["Стоимость ЛКМ, руб/м²"]["sys_0"] == pytest.approx(expected_total - thinner_cost)


def test_comparison_exposes_worst_case_technology_constraints():
    obj = ObjectData(area_m2=100.0)
    a = _material(1, min_application_temperature=-10.0, max_application_temperature=120.0,
                  min_recoat_time_h=2.0, max_recoat_time_h=48.0, full_cure_time_h=24.0,
                  max_relative_humidity=85.0, min_dew_point_margin_c=3.0)
    b = _material(2, min_application_temperature=5.0, max_application_temperature=100.0,
                  min_recoat_time_h=4.0, max_recoat_time_h=36.0, full_cure_time_h=30.0,
                  max_relative_humidity=80.0, min_dew_point_margin_c=5.0)
    engine = ComparisonEngine()
    comparison = engine.compare(obj, [
        ("Технологическая система", [
            LayerInput(material=a, target_dft=100.0),
            LayerInput(material=b, target_dft=100.0),
        ]),
        ("Пустая система", _layers(2)),
    ])
    rows = {row["indicator"]: row for row in engine.to_table(comparison)}
    assert rows["Мин. температура нанесения, °C"]["sys_0"] == 5.0
    assert rows["Макс. температура нанесения, °C"]["sys_0"] == 100.0
    assert rows["Мин. межслойная выдержка, ч"]["sys_0"] == 4.0
    assert rows["Макс. межслойная выдержка, ч"]["sys_0"] == 36.0
    assert rows["Полное отверждение, ч"]["sys_0"] == 30.0
    assert rows["Макс. относительная влажность, %"]["sys_0"] == 80.0
    assert rows["Мин. запас до точки росы, °C"]["sys_0"] == 5.0
