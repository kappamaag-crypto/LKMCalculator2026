"""Structured coating inspection records.

The inspection model stores observations and source identity only. It does not
turn missing standards, limits, or TDS data into acceptance decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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
