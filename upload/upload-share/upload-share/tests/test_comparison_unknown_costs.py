"""Регрессии: UNKNOWN стоимость не превращается в нулевую стоимость."""
from __future__ import annotations

from app.domain.comparison import ComparisonEngine
from app.domain.enums import BinderType, MaterialType
from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult


def _result(name: str, thinner_cost: float | None) -> SystemCalculationResult:
    material = Material(
        manufacturer="Test",
        material_name=name,
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
    )
    layer = LayerResult(
        material=material,
        target_dft=100.0,
        cost_per_m2=100.0,
        thinner_cost_per_m2=thinner_cost,
        total_cost=100.0 if thinner_cost is None else 100.0 + thinner_cost,
    )
    obj = ObjectData(object_name="Тест", area_m2=100.0)
    return SystemCalculationResult(
        system=CoatingSystem(system_name=name),
        object_data=obj,
        layers=[layer],
        total_dft=100.0,
        total_cost_per_m2=layer.total_cost,
        total_cost=layer.total_cost * 100.0,
    )


def test_unknown_thinner_cost_does_not_become_zero():
    obj = ObjectData(object_name="Тест", area_m2=100.0)
    comparison = ComparisonEngine().compare_results(
        obj,
        [_result("UNKNOWN", None), _result("KNOWN", 10.0)],
    )

    rows = ComparisonEngine().to_table(comparison)
    thinner = next(row for row in rows if row["indicator"] == "Стоимость разбавителя, руб/м²")
    paint = next(row for row in rows if row["indicator"] == "Стоимость ЛКМ, руб/м²")

    assert thinner["sys_0"] is None
    assert paint["sys_0"] is None
    assert thinner["sys_1"] == 10.0
    assert paint["sys_1"] == 100.0


def test_explicit_zero_thinner_cost_remains_zero():
    obj = ObjectData(object_name="Тест", area_m2=100.0)
    comparison = ComparisonEngine().compare_results(
        obj,
        [_result("NO_THINNER", 0.0), _result("KNOWN", 10.0)],
    )

    rows = ComparisonEngine().to_table(comparison)
    thinner = next(row for row in rows if row["indicator"] == "Стоимость разбавителя, руб/м²")
    paint = next(row for row in rows if row["indicator"] == "Стоимость ЛКМ, руб/м²")

    assert thinner["sys_0"] == 0.0
    assert paint["sys_0"] == 100.0
