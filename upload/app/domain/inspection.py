"""Structured coating inspection records.

The inspection model stores observations and source identity only. It does not
turn missing standards, limits, or TDS data into acceptance decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class InspectionMeasurement:
    name: str
    value: Optional[float] = None
    unit: str = ""
    instrument: str = ""
    point: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InspectionDefect:
    name: str
    severity: str = "OBSERVATION"
    location: str = ""
    count: Optional[int] = None
    description: str = ""
    photo_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class InspectionRecord:
    inspection_id: str
    object_name: str = ""
    customer: str = ""
    project: str = ""
    inspector: str = ""
    inspection_date: Optional[datetime] = None
    standard_reference: str = ""
    standard_source: str = ""
    coating_system: str = ""
    substrate: str = ""
    preparation: str = ""
    measurements: tuple[InspectionMeasurement, ...] = ()
    defects: tuple[InspectionDefect, ...] = ()
    photo_refs: tuple[str, ...] = ()
    notes: str = ""
    conclusion: str = ""
    acceptance_status: str = "UNKNOWN"
    created_at: datetime = field(default_factory=datetime.now)

    def validate(self) -> None:
        if not self.inspection_id.strip():
            raise ValueError("Идентификатор инспекции не может быть пустым")
        if self.acceptance_status not in {"ACCEPTED", "REJECTED", "CONDITIONAL", "UNKNOWN"}:
            raise ValueError("Недопустимый статус инспекции")
        for measurement in self.measurements:
            if measurement.value is not None and not isinstance(measurement.value, (int, float)):
                raise ValueError("Значение измерения должно быть числом или UNKNOWN")
        for defect in self.defects:
            if defect.count is not None and defect.count < 0:
                raise ValueError("Количество дефектов не может быть отрицательным")

    @property
    def has_observations(self) -> bool:
        return bool(self.measurements or self.defects or self.photo_refs)


# --- DFT inspection workflow (§32) ---

DFT_WITHIN = "WITHIN"
DFT_BELOW = "BELOW"
DFT_ABOVE = "ABOVE"
DFT_UNKNOWN_LIMITS = "UNKNOWN_LIMITS"
DFT_VALUE_UNKNOWN = "VALUE_UNKNOWN"

DFT_OVERALL_OK = "OK"
DFT_OVERALL_OUT_OF_RANGE = "OUT_OF_RANGE"
DFT_OVERALL_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DftLayerLimits:
    """Acceptance band for one layer. Missing min/max = UNKNOWN_LIMITS (no invented tolerance)."""

    layer_index: int
    layer_name: str = ""
    target_dft_um: Optional[float] = None
    min_dft_um: Optional[float] = None
    max_dft_um: Optional[float] = None
    source_note: str = ""

    def has_acceptance_band(self) -> bool:
        return self.min_dft_um is not None or self.max_dft_um is not None


@dataclass(frozen=True)
class DftMeasurementPoint:
    """One measured DFT reading at a point on a layer."""

    layer_index: int
    point_id: str
    measured_dft_um: Optional[float] = None
    instrument: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.point_id.strip():
            raise ValueError("point_id is required")
        if self.measured_dft_um is not None and self.measured_dft_um < 0:
            raise ValueError("measured_dft_um must be non-negative")


@dataclass(frozen=True)
class DftPointEvaluation:
    point: DftMeasurementPoint
    limits: Optional[DftLayerLimits]
    status: str
    message: str


@dataclass
class DftInspectionReport:
    """Result of comparing measured DFT points against layer limits."""

    evaluations: list[DftPointEvaluation] = field(default_factory=list)
    overall_status: str = DFT_OVERALL_UNKNOWN

    def _recompute(self) -> None:
        if not self.evaluations:
            self.overall_status = DFT_OVERALL_UNKNOWN
            return
        statuses = {e.status for e in self.evaluations}
        if DFT_BELOW in statuses or DFT_ABOVE in statuses:
            self.overall_status = DFT_OVERALL_OUT_OF_RANGE
        elif statuses <= {DFT_WITHIN}:
            self.overall_status = DFT_OVERALL_OK
        else:
            self.overall_status = DFT_OVERALL_UNKNOWN

    def add(self, evaluation: DftPointEvaluation) -> None:
        self.evaluations.append(evaluation)
        self._recompute()

    def summary_lines(self) -> list[str]:
        lines = [f"DFT inspection overall: {self.overall_status}"]
        for e in self.evaluations:
            lines.append(
                f"[{e.status}] L{e.point.layer_index + 1} {e.point.point_id}: {e.message}"
            )
        return lines


def evaluate_dft_inspection(
    points: Sequence[DftMeasurementPoint],
    limits: Sequence[DftLayerLimits],
) -> DftInspectionReport:
    """Compare measured DFT points to layer acceptance bands.

    Rules (no invention):
    - measured None → VALUE_UNKNOWN
    - no limits for layer or neither min nor max set → UNKNOWN_LIMITS
      (target alone is design value, not acceptance band)
    - min only / max only / both → WITHIN / BELOW / ABOVE
    """
    limits_map = {lim.layer_index: lim for lim in limits}
    report = DftInspectionReport()

    for point in points:
        lim = limits_map.get(point.layer_index)
        if point.measured_dft_um is None:
            report.add(
                DftPointEvaluation(
                    point=point,
                    limits=lim,
                    status=DFT_VALUE_UNKNOWN,
                    message="Измеренная DFT не задана (UNKNOWN).",
                )
            )
            continue

        measured = point.measured_dft_um
        if lim is None or not lim.has_acceptance_band():
            src = lim.source_note if lim else ""
            extra = f" target={lim.target_dft_um:g}" if lim and lim.target_dft_um is not None else ""
            report.add(
                DftPointEvaluation(
                    point=point,
                    limits=lim,
                    status=DFT_UNKNOWN_LIMITS,
                    message=(
                        f"Измерено {measured:g} мкм; полоса приёмки (min/max) неизвестна"
                        f"{extra}. Источник: {src or 'отсутствует'}."
                    ),
                )
            )
            continue

        below = lim.min_dft_um is not None and measured < lim.min_dft_um
        above = lim.max_dft_um is not None and measured > lim.max_dft_um

        if below:
            report.add(
                DftPointEvaluation(
                    point=point,
                    limits=lim,
                    status=DFT_BELOW,
                    message=(
                        f"Измерено {measured:g} мкм < min {lim.min_dft_um:g} мкм"
                        f" ({lim.layer_name or f'слой {lim.layer_index + 1}'})."
                    ),
                )
            )
        elif above:
            report.add(
                DftPointEvaluation(
                    point=point,
                    limits=lim,
                    status=DFT_ABOVE,
                    message=(
                        f"Измерено {measured:g} мкм > max {lim.max_dft_um:g} мкм"
                        f" ({lim.layer_name or f'слой {lim.layer_index + 1}'})."
                    ),
                )
            )
        else:
            band = []
            if lim.min_dft_um is not None:
                band.append(f"min={lim.min_dft_um:g}")
            if lim.max_dft_um is not None:
                band.append(f"max={lim.max_dft_um:g}")
            report.add(
                DftPointEvaluation(
                    point=point,
                    limits=lim,
                    status=DFT_WITHIN,
                    message=(
                        f"Измерено {measured:g} мкм в полосе ({', '.join(band)})"
                        f" ({lim.layer_name or f'слой {lim.layer_index + 1}'})."
                    ),
                )
            )

    return report


def limits_from_calculation_result(
    result: "SystemCalculationResult",
    *,
    use_material_recommended: bool = True,
) -> list[DftLayerLimits]:
    """Build layer limits from SystemCalculationResult.

    target_dft always from LayerResult.
    min/max only from material.recommended_dft_* when use_material_recommended
    and values are present — never invent a band from target alone.
    """
    from app.domain.models import SystemCalculationResult  # local to avoid cycle at import

    if not isinstance(result, SystemCalculationResult):
        raise TypeError("result must be SystemCalculationResult")

    out: list[DftLayerLimits] = []
    for idx, layer in enumerate(result.layers):
        mat = layer.material
        name = mat.display_name() if hasattr(mat, "display_name") else (
            mat.material_name or f"layer-{idx + 1}"
        )
        min_um = None
        max_um = None
        source_parts = ["LayerResult.target_dft"]
        if use_material_recommended:
            if mat.recommended_dft_min is not None:
                min_um = mat.recommended_dft_min
                source_parts.append("material.recommended_dft_min")
            if mat.recommended_dft_max is not None:
                max_um = mat.recommended_dft_max
                source_parts.append("material.recommended_dft_max")
        out.append(
            DftLayerLimits(
                layer_index=idx,
                layer_name=name,
                target_dft_um=layer.target_dft,
                min_dft_um=min_um,
                max_dft_um=max_um,
                source_note="; ".join(source_parts),
            )
        )
    return out
