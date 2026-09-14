"""Regression coverage for the §32 DFT inspection domain/service workflow."""
from __future__ import annotations

from app.domain.inspection import (
    DFT_OVERALL_OK,
    DFT_OVERALL_OUT_OF_RANGE,
    DFT_OVERALL_UNKNOWN,
    DFT_UNKNOWN_LIMITS,
    DFT_VALUE_UNKNOWN,
    DftLayerLimits,
    DftMeasurementPoint,
    evaluate_dft_inspection,
)
from app.domain.models import Material, ObjectData, CoatingSystem, LayerResult, SystemCalculationResult
from app.services.inspection_service import InspectionService


def _calculation_result(*, with_band: bool = True) -> SystemCalculationResult:
    material = Material(
        material_name="Coat",
        density=1.4,
        solids_by_volume_percent=60.0,
        recommended_dft_min=80.0 if with_band else None,
        recommended_dft_max=150.0 if with_band else None,
    )
    return SystemCalculationResult(
        system=CoatingSystem(system_name="S"),
        object_data=ObjectData(area_m2=10.0),
        layers=[LayerResult(material=material, target_dft=120.0, wft=200.0)],
        total_dft=120.0,
    )


def test_dft_missing_limits_stays_unknown_not_zero():
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=110.0)]
    report = InspectionService.evaluate_dft_against_calculation(
        points, _calculation_result(with_band=False)
    )

    assert report.overall_status == DFT_OVERALL_UNKNOWN
    assert report.evaluations[0].status == DFT_UNKNOWN_LIMITS
    assert "полоса приёмки (min/max) неизвестна" in report.evaluations[0].message


def test_dft_value_unknown_does_not_become_ok():
    report = evaluate_dft_inspection(
        [DftMeasurementPoint(0, "P1", measured_dft_um=None)],
        [DftLayerLimits(0, layer_name="Coat", min_dft_um=80.0, max_dft_um=150.0)],
    )

    assert report.overall_status == DFT_OVERALL_UNKNOWN
    assert report.evaluations[0].status == DFT_VALUE_UNKNOWN


def test_dft_out_of_range_is_rejected_by_dft_report():
    report = evaluate_dft_inspection(
        [DftMeasurementPoint(0, "P1", measured_dft_um=160.0)],
        [DftLayerLimits(0, layer_name="Coat", min_dft_um=80.0, max_dft_um=150.0)],
    )

    assert report.overall_status == DFT_OVERALL_OUT_OF_RANGE
    assert report.evaluations[0].status == "ABOVE"


def test_binding_dft_report_does_not_auto_accept_inspection():
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=110.0)]
    record = InspectionService.create_record_with_dft_from_calculation(
        "I-001",
        points,
        _calculation_result(),
    )

    assert record.dft_overall_status == DFT_OVERALL_OK
    assert record.acceptance_status == "UNKNOWN"
    assert record.has_dft_binding
