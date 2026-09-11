"""Tests for §26 Explanation Engine (domain + service entry)."""

from __future__ import annotations

import pytest

from app.domain.models import (
    Material,
    ObjectData,
    CoatingSystem,
    LayerResult,
    SystemCalculationResult,
)
from app.domain.engineering_context import EngineeringContext
from app.domain.explanation import (
    explain_system_calculation,
    format_explanation_text,
    INFO,
    WARNING,
    UNKNOWN_DATA,
    OK,
)
from app.domain.normative import NormativeModel, NormativeSource, UNKNOWN
from app.services.calculation_service import CalculationService


def _mat(
    name: str = "TestCoat",
    density: float | None = 1.4,
    sv: float | None = 60.0,
    incomplete: bool = False,
    price: float | None = 500.0,
) -> Material:
    return Material(
        manufacturer="Test",
        brand="Brand",
        material_name=name,
        density=density,
        solids_by_volume_percent=sv,
        solids_percent=sv,
        price_per_kg=price,
        is_incomplete=incomplete,
    )


def _layer(
    material: Material,
    dft: float = 100.0,
    losses: float = 0.0,
    wft: float = 0.0,
) -> LayerResult:
    if wft == 0.0 and material.solids_by_volume_percent and material.solids_by_volume_percent > 0:
        wft = dft * 100.0 / material.solids_by_volume_percent
    return LayerResult(
        material=material,
        target_dft=dft,
        losses_percent=losses,
        wft=wft,
        theoretical_coverage=1.0,
        practical_coverage=1.0,
    )


def _result(
    layers: list[LayerResult],
    area: float | None = 10.0,
    eng_ctx: EngineeringContext | None = None,
    cost: float | None = None,
) -> SystemCalculationResult:
    total_dft = sum(lr.target_dft for lr in layers)
    return SystemCalculationResult(
        system=CoatingSystem(system_name="Sys-A"),
        object_data=ObjectData(object_name="Obj", area_m2=area),
        layers=layers,
        total_dft=total_dft,
        total_cost_per_m2=cost,
        engineering_context=eng_ctx or EngineeringContext(),
    )


def test_explain_complete_layer_ok_status():
    mat = _mat()
    layer = _layer(mat, dft=120.0, losses=15.0)
    # approximate cost
    res = _result([layer], cost=12.5)
    report = explain_system_calculation(res)
    codes = {i.code for i in report.items}
    assert "SYS_OVERVIEW" in codes
    assert "LAYER_DFT_BASIS" in codes
    assert "LAYER_LOSSES_APPLIED" in codes
    assert "COST_KNOWN" in codes
    assert "PRECISION_NOTE" in codes
    # no UNKNOWN for density/sv
    assert "LAYER_DENSITY_MISSING" not in codes
    assert "LAYER_SV_MISSING" not in codes
    assert report.overall_status == UNKNOWN_DATA  # default ctx surface/normative UNKNOWN


def test_explain_missing_sv_and_density():
    mat = _mat(density=None, sv=None)
    layer = _layer(mat, dft=80.0, wft=0.0)
    res = _result([layer])
    report = explain_system_calculation(res)
    codes = {i.code for i in report.items}
    assert "LAYER_DENSITY_MISSING" in codes
    assert "LAYER_SV_MISSING" in codes
    assert report.has_unknown_data()
    assert report.overall_status == UNKNOWN_DATA


def test_explain_zero_losses_info_not_hidden_coeff():
    mat = _mat()
    layer = _layer(mat, losses=0.0)
    res = _result([layer])
    report = explain_system_calculation(res)
    zero_items = [i for i in report.items if i.code == "LAYER_LOSSES_ZERO"]
    assert len(zero_items) == 1
    assert "legacy default" in zero_items[0].message.lower() or "0.0" in zero_items[0].message
    assert zero_items[0].level == INFO


def test_explain_incomplete_material_warning():
    mat = _mat(incomplete=True)
    layer = _layer(mat)
    res = _result([layer])
    report = explain_system_calculation(res)
    inc = [i for i in report.items if i.code == "LAYER_MATERIAL_INCOMPLETE"]
    assert len(inc) == 1
    assert inc[0].level == WARNING


def test_explain_area_unknown():
    mat = _mat()
    layer = _layer(mat)
    res = _result([layer], area=None)
    report = explain_system_calculation(res)
    assert any(i.code == "OBJ_AREA_UNKNOWN" for i in report.items)
    assert report.has_unknown_data()


def test_explain_normative_unknown_by_default():
    mat = _mat()
    layer = _layer(mat)
    res = _result([layer], eng_ctx=EngineeringContext())
    report = explain_system_calculation(res)
    assert any(i.code == "CTX_NORMATIVE_UNKNOWN" for i in report.items)


def test_explain_normative_known_when_rules_present():
    from app.domain.normative import NormativeRule

    src = NormativeSource(
        document_id="doc-1",
        title="TDS X",
        issuer="SPK",
    )
    rule = NormativeRule(
        rule_id="r1",
        value={"min_um": 80},
        source=src,
        status="KNOWN",
        applicability="primer",
    )
    nm = NormativeModel(model_id="test-model", version="1", rules={"r1": rule})
    ctx = EngineeringContext(normative_model=nm)
    mat = _mat()
    layer = _layer(mat)
    res = _result([layer], eng_ctx=ctx)
    report = explain_system_calculation(res)
    assert any(i.code == "CTX_NORMATIVE_KNOWN" for i in report.items)
    assert not any(i.code == "CTX_NORMATIVE_UNKNOWN" for i in report.items)


def test_format_explanation_text_nonempty():
    mat = _mat()
    layer = _layer(mat)
    res = _result([layer])
    text = format_explanation_text(explain_system_calculation(res))
    assert "Explanation overall:" in text
    assert "SYS_OVERVIEW" in text


def test_service_explain_calculation():
    svc = CalculationService()
    mat = _mat()
    layer = _layer(mat, losses=10.0)
    res = _result([layer], cost=5.0)
    report = svc.explain_calculation(res)
    assert report is not None
    assert len(report.items) >= 3
    text = svc.format_explanation(res)
    assert "LAYER_LOSSES_APPLIED" in text or "losses" in text.lower()
