"""Tests for inspection records and §32 DFT inspection workflow."""

from __future__ import annotations

import pytest

from app.domain.inspection import (
    InspectionDefect,
    InspectionMeasurement,
    DftLayerLimits,
    DftMeasurementPoint,
    evaluate_dft_inspection,
    limits_from_calculation_result,
    DFT_WITHIN,
    DFT_BELOW,
    DFT_ABOVE,
    DFT_UNKNOWN_LIMITS,
    DFT_VALUE_UNKNOWN,
    DFT_OVERALL_OK,
    DFT_OVERALL_OUT_OF_RANGE,
    DFT_OVERALL_UNKNOWN,
)
from app.domain.models import (
    Material,
    ObjectData,
    CoatingSystem,
    LayerResult,
    SystemCalculationResult,
)
from app.services.inspection_service import InspectionService


def test_inspection_record_preserves_unknown_acceptance():
    record = InspectionService.create_record(
        "I-001",
        object_name="Object",
        measurements=[InspectionMeasurement("DFT", 180, "um", point="P1")],
        defects=[InspectionDefect("Pinholes", severity="MINOR", location="Zone A")],
    )
    assert record.acceptance_status == "UNKNOWN"
    assert record.has_observations
    assert "UNKNOWN" in InspectionService.summary(record)


def test_inspection_rejects_invalid_status():
    try:
        InspectionService.create_record("I-002", acceptance_status="NOT_A_STATUS")
    except ValueError as exc:
        assert "статус" in str(exc).lower()
    else:
        raise AssertionError("invalid inspection status was accepted")


def test_dft_within_band():
    limits = [
        DftLayerLimits(layer_index=0, layer_name="Primer", min_dft_um=80, max_dft_um=120)
    ]
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=100.0)]
    report = evaluate_dft_inspection(points, limits)
    assert report.overall_status == DFT_OVERALL_OK
    assert report.evaluations[0].status == DFT_WITHIN


def test_dft_below_and_above():
    limits = [
        DftLayerLimits(layer_index=0, min_dft_um=80.0, max_dft_um=120.0)
    ]
    points = [
        DftMeasurementPoint(0, "P1", measured_dft_um=70.0),
        DftMeasurementPoint(0, "P2", measured_dft_um=130.0),
    ]
    report = evaluate_dft_inspection(points, limits)
    assert report.overall_status == DFT_OVERALL_OUT_OF_RANGE
    statuses = {e.point.point_id: e.status for e in report.evaluations}
    assert statuses["P1"] == DFT_BELOW
    assert statuses["P2"] == DFT_ABOVE


def test_dft_target_only_is_unknown_limits():
    """Target without min/max must not invent a tolerance band."""
    limits = [
        DftLayerLimits(layer_index=0, target_dft_um=100.0, source_note="design")
    ]
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=100.0)]
    report = evaluate_dft_inspection(points, limits)
    assert report.evaluations[0].status == DFT_UNKNOWN_LIMITS
    assert report.overall_status == DFT_OVERALL_UNKNOWN


def test_dft_missing_measurement_value():
    limits = [DftLayerLimits(layer_index=0, min_dft_um=50.0, max_dft_um=150.0)]
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=None)]
    report = evaluate_dft_inspection(points, limits)
    assert report.evaluations[0].status == DFT_VALUE_UNKNOWN
    assert report.overall_status == DFT_OVERALL_UNKNOWN


def test_dft_no_limits_for_layer():
    points = [DftMeasurementPoint(1, "P1", measured_dft_um=90.0)]
    report = evaluate_dft_inspection(points, limits=[])
    assert report.evaluations[0].status == DFT_UNKNOWN_LIMITS


def test_limits_from_calculation_without_recommended():
    mat = Material(material_name="Coat", density=1.4, solids_by_volume_percent=60.0)
    layer = LayerResult(material=mat, target_dft=100.0, wft=166.67)
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="S"),
        object_data=ObjectData(),
        layers=[layer],
        total_dft=100.0,
    )
    limits = limits_from_calculation_result(result, use_material_recommended=True)
    assert len(limits) == 1
    assert limits[0].target_dft_um == 100.0
    assert limits[0].min_dft_um is None
    assert limits[0].max_dft_um is None
    assert not limits[0].has_acceptance_band()


def test_limits_from_calculation_with_recommended():
    mat = Material(
        material_name="Coat",
        density=1.4,
        solids_by_volume_percent=60.0,
        recommended_dft_min=80.0,
        recommended_dft_max=150.0,
    )
    layer = LayerResult(material=mat, target_dft=120.0, wft=200.0)
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="S"),
        object_data=ObjectData(),
        layers=[layer],
        total_dft=120.0,
    )
    limits = limits_from_calculation_result(result)
    assert limits[0].min_dft_um == 80.0
    assert limits[0].max_dft_um == 150.0
    assert limits[0].has_acceptance_band()


def test_service_evaluate_dft_against_calculation():
    mat = Material(
        material_name="Coat",
        density=1.4,
        solids_by_volume_percent=60.0,
        recommended_dft_min=80.0,
        recommended_dft_max=150.0,
    )
    layer = LayerResult(material=mat, target_dft=120.0, wft=200.0)
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="S"),
        object_data=ObjectData(area_m2=10.0),
        layers=[layer],
        total_dft=120.0,
    )
    points = [
        DftMeasurementPoint(0, "A1", measured_dft_um=110.0),
        DftMeasurementPoint(0, "A2", measured_dft_um=70.0),
    ]
    report = InspectionService.evaluate_dft_against_calculation(points, result)
    assert report.overall_status == DFT_OVERALL_OUT_OF_RANGE
    assert any(e.status == DFT_WITHIN for e in report.evaluations)
    assert any(e.status == DFT_BELOW for e in report.evaluations)
    text = InspectionService.format_dft_report(report)
    assert "DFT inspection overall" in text


def test_negative_measured_rejected():
    with pytest.raises(ValueError):
        DftMeasurementPoint(0, "P1", measured_dft_um=-1.0)


def test_bind_dft_does_not_change_acceptance():
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=100.0)]
    limits = [DftLayerLimits(layer_index=0, min_dft_um=80.0, max_dft_um=120.0)]
    record = InspectionService.create_record_with_dft(
        "I-DFT-1",
        points,
        limits,
        object_name="Tank",
    )
    assert record.acceptance_status == "UNKNOWN"
    assert record.dft_overall_status == DFT_OVERALL_OK
    assert record.has_dft_binding
    assert len(record.dft_points) == 1
    assert "DFT inspection overall" in record.dft_summary
    assert "UNKNOWN" in InspectionService.summary(record)
    assert "DFT:" in InspectionService.summary(record)


def test_bind_dft_out_of_range_still_unknown_acceptance():
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=50.0)]
    limits = [DftLayerLimits(layer_index=0, min_dft_um=80.0, max_dft_um=120.0)]
    record = InspectionService.create_record_with_dft("I-DFT-2", points, limits)
    assert record.dft_overall_status == DFT_OVERALL_OUT_OF_RANGE
    assert record.acceptance_status == "UNKNOWN"


def test_bind_dft_from_calculation():
    mat = Material(
        material_name="Coat",
        density=1.4,
        solids_by_volume_percent=60.0,
        recommended_dft_min=80.0,
        recommended_dft_max=150.0,
    )
    layer = LayerResult(material=mat, target_dft=120.0, wft=200.0)
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="S"),
        object_data=ObjectData(),
        layers=[layer],
        total_dft=120.0,
    )
    points = [DftMeasurementPoint(0, "A1", measured_dft_um=110.0)]
    record = InspectionService.create_record_with_dft_from_calculation(
        "I-DFT-3", points, result
    )
    assert record.dft_overall_status == DFT_OVERALL_OK
    assert record.has_observations
    data = InspectionService.to_dict(record)
    assert data["dft_overall_status"] == DFT_OVERALL_OK
    assert len(data["dft_points"]) == 1


def test_with_dft_report_on_existing_record():
    base = InspectionService.create_record("I-DFT-4", acceptance_status="CONDITIONAL")
    points = [DftMeasurementPoint(0, "P1", measured_dft_um=90.0)]
    limits = [DftLayerLimits(0, min_dft_um=80.0, max_dft_um=100.0)]
    report = evaluate_dft_inspection(points, limits)
    bound = InspectionService.bind_dft_report(base, report)
    assert bound.acceptance_status == "CONDITIONAL"  # preserved
    assert bound.dft_overall_status == DFT_OVERALL_OK
