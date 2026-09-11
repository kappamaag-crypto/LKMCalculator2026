"""Application service for coating inspection records and DFT workflow."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from typing import Optional, Sequence

from app.domain.inspection import (
    InspectionDefect,
    InspectionMeasurement,
    InspectionRecord,
    DftLayerLimits,
    DftMeasurementPoint,
    DftInspectionReport,
    evaluate_dft_inspection,
    limits_from_calculation_result,
)
from app.domain.models import SystemCalculationResult


class InspectionService:
    """Build and validate inspection records without normative inference.

    DFT comparison never invents acceptance bands: missing min/max → UNKNOWN_LIMITS.
    Binding DFT into InspectionRecord does NOT auto-set acceptance_status.
    """

    @staticmethod
    def create_record(
        inspection_id: str,
        *,
        object_name: str = "",
        inspector: str = "",
        standard_reference: str = "",
        standard_source: str = "",
        coating_system: str = "",
        substrate: str = "",
        preparation: str = "",
        measurements=(),
        defects=(),
        photo_refs=(),
        notes: str = "",
        conclusion: str = "",
        acceptance_status: str = "UNKNOWN",
        dft_points: Sequence[DftMeasurementPoint] = (),
        dft_overall_status: str = "UNKNOWN",
        dft_summary: str = "",
    ) -> InspectionRecord:
        record = InspectionRecord(
            inspection_id=inspection_id.strip(),
            object_name=object_name.strip(),
            inspector=inspector.strip(),
            standard_reference=standard_reference.strip(),
            standard_source=standard_source.strip(),
            coating_system=coating_system.strip(),
            substrate=substrate.strip(),
            preparation=preparation.strip(),
            measurements=tuple(measurements),
            defects=tuple(defects),
            photo_refs=tuple(p for p in photo_refs if p),
            notes=notes.strip(),
            conclusion=conclusion.strip(),
            acceptance_status=acceptance_status,
            dft_points=tuple(dft_points),
            dft_overall_status=dft_overall_status,
            dft_summary=dft_summary.strip(),
            inspection_date=datetime.now(),
        )
        record.validate()
        return record

    @staticmethod
    def summary(record: InspectionRecord) -> str:
        record.validate()
        lines = [
            f"Инспекция: {record.inspection_id}",
            f"Статус приёмки: {record.acceptance_status}",
            f"Измерений: {len(record.measurements)}; дефектов: {len(record.defects)}; фото: {len(record.photo_refs)}",
        ]
        if record.object_name:
            lines.insert(1, f"Объект: {record.object_name}")
        if record.standard_reference:
            lines.append(
                f"Источник/НД: {record.standard_reference} {record.standard_source}".strip()
            )
        if record.dft_points or record.dft_overall_status != "UNKNOWN":
            lines.append(
                f"DFT: points={len(record.dft_points)}; overall={record.dft_overall_status}"
            )
            if record.dft_summary:
                lines.append(record.dft_summary)
        if record.acceptance_status == "UNKNOWN":
            lines.append("Приёмка не определена: критерий или решение не подтверждены.")
        return "\n".join(lines)

    @staticmethod
    def to_dict(record: InspectionRecord) -> dict:
        record.validate()
        data = asdict(record)
        data["inspection_date"] = (
            record.inspection_date.isoformat() if record.inspection_date else None
        )
        data["created_at"] = record.created_at.isoformat()
        return data

    @staticmethod
    def evaluate_dft(
        points: Sequence[DftMeasurementPoint],
        limits: Sequence[DftLayerLimits],
    ) -> DftInspectionReport:
        """Compare measured DFT points against explicit layer limits (domain pure)."""
        return evaluate_dft_inspection(points, limits)

    @staticmethod
    def evaluate_dft_against_calculation(
        points: Sequence[DftMeasurementPoint],
        result: SystemCalculationResult,
        *,
        use_material_recommended: bool = True,
    ) -> DftInspectionReport:
        """Build limits from SystemCalculationResult then evaluate points.

        Acceptance band only when material.recommended_dft_min/max present;
        target alone does not create a tolerance band.
        """
        limits = limits_from_calculation_result(
            result, use_material_recommended=use_material_recommended
        )
        return evaluate_dft_inspection(points, limits)

    @staticmethod
    def format_dft_report(report: DftInspectionReport) -> str:
        return "\n".join(report.summary_lines())

    @staticmethod
    def bind_dft_report(
        record: InspectionRecord,
        report: DftInspectionReport,
    ) -> InspectionRecord:
        """Bind DFT evaluation into InspectionRecord without changing acceptance_status."""
        bound = record.with_dft_report(report)
        bound.validate()
        return bound

    @staticmethod
    def create_record_with_dft(
        inspection_id: str,
        points: Sequence[DftMeasurementPoint],
        limits: Sequence[DftLayerLimits],
        **kwargs,
    ) -> InspectionRecord:
        """Create record and bind DFT evaluation in one step.

        acceptance_status stays UNKNOWN unless explicitly passed in kwargs.
        DFT overall is independent of acceptance.
        """
        report = evaluate_dft_inspection(points, limits)
        record = InspectionService.create_record(inspection_id, **kwargs)
        return InspectionService.bind_dft_report(record, report)

    @staticmethod
    def create_record_with_dft_from_calculation(
        inspection_id: str,
        points: Sequence[DftMeasurementPoint],
        result: SystemCalculationResult,
        *,
        use_material_recommended: bool = True,
        **kwargs,
    ) -> InspectionRecord:
        report = InspectionService.evaluate_dft_against_calculation(
            points, result, use_material_recommended=use_material_recommended
        )
        record = InspectionService.create_record(inspection_id, **kwargs)
        return InspectionService.bind_dft_report(record, report)
